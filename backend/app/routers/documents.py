"""Document upload and management endpoints."""

import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, BackgroundTasks
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.chunk import Chunk
from app.models.document import Document
from app.schemas.common import SuccessResponse, PaginatedResponse, PaginationMeta, Meta
from app.schemas.document import DocumentResponse, DocumentUploadItem, DocumentUploadResponse
from app.services.document_processor import DocumentProcessor

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])

SUPPORTED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "text/plain": ".txt",
}

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def _get_mime_type(filename: str, content_type: Optional[str]) -> Optional[str]:
    """Determine mime type from filename extension or content type."""
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        return "application/pdf"
    elif ext == ".docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif ext == ".txt":
        return "text/plain"
    # Fallback to content_type header
    if content_type in SUPPORTED_MIME_TYPES:
        return content_type
    return None


@router.post("/upload", response_model=SuccessResponse)
async def upload_documents(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload one or more documents for processing."""
    # Validate file count
    if len(files) > settings.max_files_per_request:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "TOO_MANY_FILES",
                "message": f"Maximum {settings.max_files_per_request} files per request.",
            },
        )

    results: list[DocumentUploadItem] = []
    max_size = settings.max_file_size_mb * 1024 * 1024

    for file in files:
        # Validate format
        mime_type = _get_mime_type(file.filename or "", file.content_type)
        if not mime_type:
            raise HTTPException(
                status_code=415,
                detail={
                    "code": "UNSUPPORTED_FORMAT",
                    "message": f"Unsupported file format: {file.filename}. "
                               f"Supported: PDF, DOCX, TXT",
                },
            )

        # Read file content
        content = await file.read()

        # Validate size
        if len(content) > max_size:
            raise HTTPException(
                status_code=413,
                detail={
                    "code": "FILE_TOO_LARGE",
                    "message": f"File {file.filename} exceeds maximum size of "
                               f"{settings.max_file_size_mb}MB.",
                },
            )

        # Validate not empty
        if len(content) == 0:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "EMPTY_FILE",
                    "message": f"File {file.filename} is empty (zero bytes).",
                },
            )

        # Save file
        doc_id = uuid.uuid4()
        filename = f"{doc_id}_{file.filename}"
        file_path = os.path.join(settings.upload_dir, filename)
        os.makedirs(settings.upload_dir, exist_ok=True)

        with open(file_path, "wb") as f:
            f.write(content)

        # Create document record
        document = Document(
            id=doc_id,
            filename=file.filename or "unknown",
            file_size=len(content),
            mime_type=mime_type,
            status="pending",
        )
        db.add(document)
        await db.flush()

        results.append(DocumentUploadItem(
            id=doc_id,
            filename=file.filename or "unknown",
            status="pending",
        ))

        # Trigger async processing
        processor = DocumentProcessor()
        background_tasks.add_task(processor.process_document, doc_id, file_path)

    # Explicitly commit so background tasks can see the documents
    await db.commit()

    return SuccessResponse(
        data=DocumentUploadResponse(documents=results).model_dump()
    )


@router.get("", response_model=PaginatedResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List all documents with pagination."""
    # Count total
    total_count = await db.scalar(select(func.count(Document.id)))

    # Fetch page
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Document)
        .order_by(Document.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    documents = result.scalars().all()

    total_pages = (total_count + page_size - 1) // page_size if total_count else 0

    return PaginatedResponse(
        data=[DocumentResponse.model_validate(d).model_dump() for d in documents],
        meta=Meta(),
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_count=total_count or 0,
            total_pages=total_pages,
        ),
    )


@router.get("/{document_id}", response_model=SuccessResponse)
async def get_document(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get document metadata by ID."""
    doc = await db.get(Document, document_id)
    if not doc:
        raise HTTPException(
            status_code=404,
            detail={"code": "DOCUMENT_NOT_FOUND", "message": "Document not found."},
        )
    return SuccessResponse(data=DocumentResponse.model_validate(doc).model_dump())


@router.delete("/{document_id}", response_model=SuccessResponse)
async def delete_document(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Delete a document and its chunks/embeddings."""
    doc = await db.get(Document, document_id)
    if not doc:
        raise HTTPException(
            status_code=404,
            detail={"code": "DOCUMENT_NOT_FOUND", "message": "Document not found."},
        )

    if doc.status in ("pending", "processing"):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "DOCUMENT_PROCESSING",
                "message": "Cannot delete a document that is still being processed.",
            },
        )

    # Count chunks before deletion
    chunk_count = await db.scalar(
        select(func.count(Chunk.id)).where(Chunk.document_id == document_id)
    )

    # Delete (cascades to chunks)
    await db.delete(doc)
    await db.flush()

    # Remove file from disk
    file_path = os.path.join(settings.upload_dir, f"{document_id}_{doc.filename}")
    if os.path.exists(file_path):
        os.remove(file_path)

    return SuccessResponse(
        data={
            "id": str(document_id),
            "chunks_removed": chunk_count or 0,
            "message": "Document deleted successfully.",
        }
    )
