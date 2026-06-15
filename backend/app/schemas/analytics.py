from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AnalyticsSummary(BaseModel):
    total_documents: int
    total_chunks: int
    total_queries: int


class QueryVolumeItem(BaseModel):
    date: str
    count: int


class TopKeyword(BaseModel):
    keyword: str
    count: int


class ResponseTimeStats(BaseModel):
    average_ms: float
    min_ms: Optional[int] = None
    max_ms: Optional[int] = None
    count: int
