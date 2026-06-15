import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: uuid.UUID
    filename: str
    file_size: int
    mime_type: str
    status: str
    pipeline_stage: Optional[str] = None
    chunk_count: int = 0
    skipped_pages: list[int] = []
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    processing_duration_ms: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentStatusResponse(BaseModel):
    id: uuid.UUID
    status: str
    pipeline_stage: Optional[str] = None
    processing_duration_ms: Optional[int] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}


class DocumentUploadItem(BaseModel):
    id: uuid.UUID
    filename: str
    status: str


class DocumentUploadResponse(BaseModel):
    documents: list[DocumentUploadItem]
