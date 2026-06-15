"""Conversation management endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.chat import ConversationCreate
from app.schemas.common import SuccessResponse, PaginatedResponse, PaginationMeta, Meta

router = APIRouter(prefix="/api/v1/conversations", tags=["Conversations"])


@router.post("", response_model=SuccessResponse)
async def create_conversation(
    request: ConversationCreate = ConversationCreate(),
    db: AsyncSession = Depends(get_db),
):
    """Create a new conversation session."""
    conversation = Conversation(title=request.title)
    db.add(conversation)
    await db.flush()

    return SuccessResponse(
        data={
            "id": str(conversation.id),
            "title": conversation.title,
            "created_at": conversation.created_at.isoformat(),
        }
    )


@router.get("", response_model=PaginatedResponse)
async def list_conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List conversations ordered by most recent activity."""
    total_count = await db.scalar(select(func.count(Conversation.id)))

    offset = (page - 1) * page_size
    result = await db.execute(
        select(Conversation)
        .order_by(Conversation.updated_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    conversations = result.scalars().all()
    total_pages = (total_count + page_size - 1) // page_size if total_count else 0

    return PaginatedResponse(
        data=[
            {
                "id": str(c.id),
                "title": c.title,
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat(),
            }
            for c in conversations
        ],
        meta=Meta(),
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_count=total_count or 0,
            total_pages=total_pages,
        ),
    )


@router.get("/{conversation_id}/messages", response_model=PaginatedResponse)
async def get_conversation_messages(
    conversation_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get messages for a conversation in chronological order."""
    # Verify conversation exists
    conversation = await db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=404,
            detail={"code": "SESSION_NOT_FOUND", "message": "Conversation not found."},
        )

    total_count = await db.scalar(
        select(func.count(Message.id)).where(
            Message.conversation_id == conversation_id
        )
    )

    offset = (page - 1) * page_size
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .offset(offset)
        .limit(page_size)
    )
    messages = result.scalars().all()
    total_pages = (total_count + page_size - 1) // page_size if total_count else 0

    return PaginatedResponse(
        data=[
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "source_references": m.source_references,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
        meta=Meta(),
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_count=total_count or 0,
            total_pages=total_pages,
        ),
    )


@router.delete("/{conversation_id}", response_model=SuccessResponse)
async def delete_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation and all its messages."""
    conversation = await db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=404,
            detail={"code": "SESSION_NOT_FOUND", "message": "Conversation not found."},
        )

    await db.delete(conversation)
    await db.flush()

    return SuccessResponse(
        data={"id": str(conversation_id), "message": "Conversation deleted."}
    )
