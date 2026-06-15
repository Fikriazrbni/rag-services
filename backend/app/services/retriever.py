"""Semantic search over document chunks using pgvector."""

import uuid
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import Chunk
from app.models.document import Document
from app.services.provider_adapter import ProviderAdapter


@dataclass
class ChunkResult:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_name: str
    content: str
    page_number: Optional[int]
    paragraph_position: Optional[int]
    score: float  # cosine similarity (0-1)


class Retriever:
    """Performs semantic search over document embeddings."""

    def __init__(self, db: AsyncSession, provider_adapter: ProviderAdapter):
        self.db = db
        self.adapter = provider_adapter

    async def search(
        self, query: str, top_k: int = 5, threshold: float = 0.7
    ) -> list[ChunkResult]:
        """
        1. Embed the query
        2. Cosine similarity search in pgvector
        3. Filter by threshold
        4. Return ranked results
        """
        # Check if knowledge base has any chunks
        total_chunks = await self.db.scalar(select(func.count(Chunk.id)))
        if not total_chunks:
            return []

        # Embed the query
        query_embedding = await self.adapter.embed([query])
        embedding_vector = query_embedding[0]

        # Perform cosine similarity search using pgvector
        # cosine_distance returns 0 for identical, 2 for opposite
        # similarity = 1 - distance
        distance_expr = Chunk.embedding.cosine_distance(embedding_vector)

        result = await self.db.execute(
            select(
                Chunk,
                Document.filename,
                (1 - distance_expr).label("similarity"),
            )
            .join(Document, Chunk.document_id == Document.id)
            .where(Document.status == "completed")
            .order_by(distance_expr)
            .limit(top_k)
        )

        rows = result.all()

        # Filter by threshold
        results = []
        for chunk, filename, similarity in rows:
            if similarity >= threshold:
                results.append(
                    ChunkResult(
                        chunk_id=chunk.id,
                        document_id=chunk.document_id,
                        document_name=filename,
                        content=chunk.content,
                        page_number=chunk.page_number,
                        paragraph_position=chunk.paragraph_position,
                        score=float(similarity),
                    )
                )

        return results
