import uuid
from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: uuid.UUID
    question: str = Field(..., max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    threshold: float = Field(default=0.3, ge=0.0, le=1.0)


class ChatSourceReference(BaseModel):
    chunk_id: uuid.UUID
    document_name: str
    page_number: Optional[int] = None
    excerpt: str = Field(..., max_length=200)
    confidence_score: float = Field(..., ge=0.0, le=1.0)


class ConversationCreate(BaseModel):
    title: Optional[str] = None


class ConversationResponse(BaseModel):
    id: uuid.UUID
    title: Optional[str] = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    source_references: Optional[list[ChatSourceReference]] = None
    created_at: str

    model_config = {"from_attributes": True}
