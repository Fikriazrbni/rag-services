"""Document processing pipeline: parse → chunk → embed → store."""

import asyncio
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session
from app.models.chunk import Chunk
from app.models.document import Document
from app.services.provider_adapter import ProviderAdapter
from app.utils.chunker import ChunkData, TextChunker
from app.utils.file_parser import FileParser
from app.utils.sse import status_sse_manager


class ProcessingError(Exception):
    def __init__(self, stage: str, error_type: str, message: str):
        self.stage = stage
        self.error_type = error_type
        super().__init__(message)


class DocumentProcessor:
    """Orchestrates the document processing pipeline."""

    BATCH_SIZE = 20  # Embeddings per API call

    async def process_document(self, document_id: uuid.UUID, file_path: str):
        """Main pipeline: parse → chunk → embed → store."""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Starting processing for document {document_id}")
        start_time = time.time()

        async with async_session() as db:
            try:
                # Stage 1: Parse
                await self._update_status(db, document_id, "processing", "parsing")
                parser = FileParser()
                doc = await db.get(Document, document_id)
                if not doc:
                    # Document might not be visible yet, retry once
                    await asyncio.sleep(1)
                    doc = await db.get(Document, document_id)
                if not doc:
                    logger.error(f"Document {document_id} not found in DB")
                    return
                parse_result = parser.parse(file_path, doc.mime_type)

                # Update skipped pages if any
                if parse_result.skipped_pages:
                    doc.skipped_pages = parse_result.skipped_pages
                    await db.flush()

                # Stage 2: Chunk
                await self._update_status(db, document_id, "processing", "chunking")
                chunker = TextChunker(
                    chunk_size=settings.chunk_size_tokens,
                    chunk_overlap=settings.chunk_overlap_tokens,
                )
                chunks = chunker.chunk_pages(parse_result.pages)

                if not chunks:
                    raise ProcessingError(
                        "chunking", "NO_CONTENT", "Document produced zero chunks."
                    )

                # Stage 3: Embed
                await self._update_status(db, document_id, "processing", "embedding")
                adapter = ProviderAdapter(db)
                await self._embed_and_store(db, adapter, document_id, chunks)

                # Complete
                duration_ms = int((time.time() - start_time) * 1000)
                doc = await db.get(Document, document_id)
                doc.status = "completed"
                doc.pipeline_stage = None
                doc.chunk_count = len(chunks)
                doc.processing_duration_ms = duration_ms
                doc.updated_at = datetime.now(timezone.utc)
                await db.commit()

                await status_sse_manager.broadcast("status_change", {
                    "document_id": str(document_id),
                    "status": "completed",
                    "pipeline_stage": None,
                    "chunk_count": len(chunks),
                    "processing_duration_ms": duration_ms,
                })

            except ProcessingError as e:
                logger.error(f"Processing error for {document_id}: {e}")
                await self._mark_failed(db, document_id, e.stage, e.error_type, str(e))
            except ValueError as e:
                logger.error(f"Value error for {document_id}: {e}")
                await self._mark_failed(db, document_id, "parsing", "PARSE_ERROR", str(e))
            except Exception as e:
                logger.error(f"Unexpected error for {document_id}: {e}", exc_info=True)
                await self._mark_failed(
                    db, document_id, "embedding", "INTERNAL_ERROR", str(e)
                )

    async def _embed_and_store(
        self,
        db: AsyncSession,
        adapter: ProviderAdapter,
        document_id: uuid.UUID,
        chunks: list[ChunkData],
    ):
        """Generate embeddings in batches and store with retry logic."""
        all_db_chunks: list[Chunk] = []

        for i in range(0, len(chunks), self.BATCH_SIZE):
            batch = chunks[i : i + self.BATCH_SIZE]
            texts = [c.content for c in batch]

            # Retry with exponential backoff
            embeddings = None
            for attempt in range(3):
                try:
                    embeddings = await adapter.embed(texts)
                    break
                except Exception as e:
                    if attempt == 2:
                        # Rollback partial embeddings
                        await db.execute(
                            delete(Chunk).where(Chunk.document_id == document_id)
                        )
                        await db.flush()
                        raise ProcessingError(
                            "embedding",
                            "PROVIDER_UNAVAILABLE",
                            f"Embedding failed after 3 retries. "
                            f"Failed chunks: {len(chunks) - i}. Error: {str(e)}",
                        )
                    delay = 2**attempt  # 1s, 2s, 4s
                    await asyncio.sleep(delay)

            # Store chunks with embeddings
            for j, chunk_data in enumerate(batch):
                db_chunk = Chunk(
                    document_id=document_id,
                    content=chunk_data.content,
                    page_number=chunk_data.page_number,
                    paragraph_position=chunk_data.paragraph_position,
                    character_offset=chunk_data.character_offset,
                    embedding=embeddings[j] if embeddings else None,
                )
                db.add(db_chunk)
                all_db_chunks.append(db_chunk)

        await db.flush()

    async def _update_status(
        self, db: AsyncSession, document_id: uuid.UUID, status: str, stage: Optional[str]
    ):
        """Update document status and emit SSE event."""
        doc = await db.get(Document, document_id)
        if doc:
            doc.status = status
            doc.pipeline_stage = stage
            doc.updated_at = datetime.now(timezone.utc)
            await db.flush()

        await status_sse_manager.broadcast("status_change", {
            "document_id": str(document_id),
            "status": status,
            "pipeline_stage": stage,
        })

    async def _mark_failed(
        self,
        db: AsyncSession,
        document_id: uuid.UUID,
        stage: str,
        error_type: str,
        error_message: str,
    ):
        """Mark document as failed with error details."""
        doc = await db.get(Document, document_id)
        if doc:
            doc.status = "failed"
            doc.pipeline_stage = stage
            doc.error_type = error_type
            doc.error_message = error_message
            doc.updated_at = datetime.now(timezone.utc)
            await db.commit()

        await status_sse_manager.broadcast("status_change", {
            "document_id": str(document_id),
            "status": "failed",
            "pipeline_stage": stage,
            "error_type": error_type,
            "error_message": error_message,
        })
