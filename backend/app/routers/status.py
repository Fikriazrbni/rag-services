"""Document processing status endpoints with SSE streaming."""

import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.document import Document
from app.schemas.common import SuccessResponse
from app.schemas.document import DocumentStatusResponse
from app.utils.sse import status_sse_manager

router = APIRouter(prefix="/api/v1/documents", tags=["Status"])


@router.get("/{document_id}/status", response_model=SuccessResponse)
async def get_document_status(
    document_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    """Get the current processing status of a document."""
    doc = await db.get(Document, document_id)
    if not doc:
        raise HTTPException(
            status_code=404,
            detail={"code": "DOCUMENT_NOT_FOUND", "message": "Document not found."},
        )

    return SuccessResponse(
        data=DocumentStatusResponse.model_validate(doc).model_dump()
    )


@router.get("/status/stream")
async def stream_document_status():
    """SSE endpoint for real-time document processing status updates."""
    queue = status_sse_manager.add_listener()

    async def event_generator():
        try:
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield message
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            status_sse_manager.remove_listener(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
