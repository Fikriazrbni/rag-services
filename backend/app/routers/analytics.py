"""Analytics endpoints."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import SuccessResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


@router.get("/summary", response_model=SuccessResponse)
async def get_analytics_summary(db: AsyncSession = Depends(get_db)):
    """Get total counts of documents, chunks, and queries."""
    service = AnalyticsService(db)
    summary = await service.get_summary()
    return SuccessResponse(data=summary)


@router.get("/query-volume", response_model=SuccessResponse)
async def get_query_volume(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    granularity: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
    db: AsyncSession = Depends(get_db),
):
    """Get query volume over time."""
    service = AnalyticsService(db)
    data = await service.get_query_volume(start_date, end_date, granularity)
    return SuccessResponse(data=data)


@router.get("/top-keywords", response_model=SuccessResponse)
async def get_top_keywords(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get most frequently queried keywords."""
    service = AnalyticsService(db)
    data = await service.get_top_keywords(start_date, end_date, limit)
    return SuccessResponse(data=data)


@router.get("/response-times", response_model=SuccessResponse)
async def get_response_times(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get average response time statistics."""
    service = AnalyticsService(db)
    data = await service.get_response_times(start_date, end_date)
    return SuccessResponse(data=data)
