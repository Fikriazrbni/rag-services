"""Chat endpoint with SSE streaming."""

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.chat import ChatRequest
from app.services.chat_service import ChatService

router = APIRouter(prefix="/api/v1", tags=["Chat"])


@router.post("/chat")
async def chat_query(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """Send a query and receive streaming AI response with source references."""
    chat_service = ChatService(db)

    async def event_generator():
        async for event in chat_service.query(
            session_id=request.session_id,
            question=request.question,
            top_k=request.top_k,
            threshold=request.threshold,
        ):
            event_type = event["event"]
            data = json.dumps(event["data"])
            yield f"event: {event_type}\ndata: {data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
