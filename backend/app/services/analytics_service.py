"""Analytics service for query and usage metrics."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import Chunk
from app.models.document import Document
from app.models.query_log import QueryLog


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_summary(self) -> dict:
        """Get total counts of documents, chunks, and queries."""
        total_docs = await self.db.scalar(select(func.count(Document.id))) or 0
        total_chunks = await self.db.scalar(select(func.count(Chunk.id))) or 0
        total_queries = await self.db.scalar(select(func.count(QueryLog.id))) or 0

        return {
            "total_documents": total_docs,
            "total_chunks": total_chunks,
            "total_queries": total_queries,
        }

    async def get_query_volume(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        granularity: str = "daily",
    ) -> list[dict]:
        """Get query volume over time."""
        if not end_date:
            end_date = datetime.now(timezone.utc)
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Truncate based on granularity
        trunc_map = {"daily": "day", "weekly": "week", "monthly": "month"}
        trunc = trunc_map.get(granularity, "day")

        result = await self.db.execute(
            select(
                func.date_trunc(trunc, QueryLog.created_at).label("period"),
                func.count(QueryLog.id).label("count"),
            )
            .where(
                QueryLog.created_at >= start_date,
                QueryLog.created_at <= end_date,
            )
            .group_by("period")
            .order_by("period")
        )

        return [
            {"date": row.period.isoformat(), "count": row.count}
            for row in result.all()
        ]

    async def get_top_keywords(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10,
    ) -> list[dict]:
        """Get most frequently queried keywords."""
        if not end_date:
            end_date = datetime.now(timezone.utc)
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Simple keyword extraction: split queries into words, count frequency
        result = await self.db.execute(
            select(
                func.unnest(
                    func.string_to_array(func.lower(QueryLog.query_text), " ")
                ).label("word"),
                func.count().label("count"),
            )
            .where(
                QueryLog.created_at >= start_date,
                QueryLog.created_at <= end_date,
            )
            .group_by("word")
            .order_by(func.count().desc())
            .limit(limit)
        )

        # Filter out common stop words
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "what", "how",
                      "why", "when", "where", "who", "which", "do", "does", "did",
                      "can", "could", "will", "would", "should", "to", "of", "in",
                      "for", "on", "with", "at", "by", "from", "it", "this", "that",
                      "i", "my", "me", "we", "you", "and", "or", "not", "be", "have",
                      "has", "had"}

        keywords = []
        for row in result.all():
            if row.word and len(row.word) > 2 and row.word not in stop_words:
                keywords.append({"keyword": row.word, "count": row.count})

        return keywords[:limit]

    async def get_response_times(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
        """Get average response time statistics."""
        if not end_date:
            end_date = datetime.now(timezone.utc)
        if not start_date:
            start_date = end_date - timedelta(days=30)

        result = await self.db.execute(
            select(
                func.avg(QueryLog.response_time_ms).label("avg_ms"),
                func.min(QueryLog.response_time_ms).label("min_ms"),
                func.max(QueryLog.response_time_ms).label("max_ms"),
                func.count(QueryLog.id).label("count"),
            ).where(
                QueryLog.created_at >= start_date,
                QueryLog.created_at <= end_date,
            )
        )

        row = result.one()
        return {
            "average_ms": round(float(row.avg_ms), 2) if row.avg_ms else 0,
            "min_ms": row.min_ms,
            "max_ms": row.max_ms,
            "count": row.count or 0,
        }
