"""Chat service: orchestrates the full RAG pipeline."""

import time
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.query_log import QueryLog
from app.schemas.chat import ChatSourceReference
from app.services.provider_adapter import ProviderAdapter
from app.services.retriever import ChunkResult, Retriever


class ChatService:
    """Orchestrates: query → retrieve → augment → generate → stream."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.adapter = ProviderAdapter(db)
        self.retriever = Retriever(db, self.adapter)

    async def query(
        self,
        session_id: uuid.UUID,
        question: str,
        top_k: int = 5,
        threshold: float = 0.7,
    ) -> AsyncGenerator[dict, None]:
        """
        Full RAG pipeline with streaming.
        Yields dicts with event type and data.
        """
        start_time = time.time()

        # 1. Validate session exists
        conversation = await self.db.get(Conversation, session_id)
        if not conversation:
            yield {"event": "error", "data": {"message": "Session not found."}}
            return

        # 2. Retrieve relevant chunks
        chunks = await self.retriever.search(
            query=question, top_k=top_k, threshold=threshold
        )

        # 3. Build source references
        source_refs = [
            ChatSourceReference(
                chunk_id=c.chunk_id,
                document_name=c.document_name,
                page_number=c.page_number,
                excerpt=c.content[:200],
                confidence_score=round(c.score, 4),
            )
            for c in chunks
        ]

        # 4. Check empty KB
        if not chunks:
            # Check if KB has any documents at all
            from sqlalchemy import func
            from app.models.chunk import Chunk

            total = await self.db.scalar(select(func.count(Chunk.id)))
            if total == 0:
                yield {
                    "event": "error",
                    "data": {
                        "message": "Knowledge base is empty. Please upload documents first."
                    },
                }
                return
            else:
                yield {
                    "event": "error",
                    "data": {
                        "message": "No relevant information found in the knowledge base for your question."
                    },
                }
                return

        # 5. Load conversation history
        history = await self._get_history(session_id)

        # 6. Build augmented prompt
        messages = self._build_rag_prompt(history, question, chunks)

        # 7. Generate response (streaming)
        full_response = ""
        try:
            async for token in self.adapter.generate(messages, stream=True):
                full_response += token
                yield {"event": "token", "data": {"content": token}}
        except Exception as e:
            yield {
                "event": "error",
                "data": {
                    "message": f"LLM provider unavailable. Please check your provider configuration. Error: {str(e)}"
                },
            }
            return

        # 8. Send source references
        yield {
            "event": "sources",
            "data": {"references": [
                {**r.model_dump(), "chunk_id": str(r.chunk_id)}
                for r in source_refs
            ]},
        }

        # 9. Save messages
        response_time_ms = int((time.time() - start_time) * 1000)

        user_msg = Message(
            conversation_id=session_id,
            role="user",
            content=question,
        )
        assistant_msg = Message(
            conversation_id=session_id,
            role="assistant",
            content=full_response,
            source_references=[
                {**r.model_dump(), "chunk_id": str(r.chunk_id)}
                for r in source_refs
            ],
        )
        self.db.add(user_msg)
        self.db.add(assistant_msg)

        # Update conversation timestamp
        conversation.updated_at = datetime.now(timezone.utc)

        # 10. Log query
        config = await self.adapter.get_active_config("llm")
        query_log = QueryLog(
            conversation_id=session_id,
            query_text=question,
            response_time_ms=response_time_ms,
            chunks_retrieved=len(chunks),
            provider_used=config.provider_name if config else "unknown",
            model_used=config.model_identifier if config else "unknown",
        )
        self.db.add(query_log)
        await self.db.flush()

        yield {
            "event": "done",
            "data": {
                "message_id": str(assistant_msg.id),
                "response_time_ms": response_time_ms,
            },
        }

    async def _get_history(self, session_id: uuid.UUID) -> list[dict]:
        """Load last N messages from conversation."""
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == session_id)
            .order_by(Message.created_at.desc())
            .limit(settings.context_window_messages)
        )
        messages = list(reversed(result.scalars().all()))
        return [{"role": m.role, "content": m.content} for m in messages]

    def _build_rag_prompt(
        self, history: list[dict], question: str, chunks: list[ChunkResult]
    ) -> list[dict]:
        """Build system + context + history + question."""
        system_prompt = (
            "You are a helpful assistant that answers questions based on the provided context. "
            "Always cite your sources using [Source N] notation. "
            "If the context doesn't contain enough information to fully answer the question, "
            "say so clearly."
        )

        context_parts = []
        for i, chunk in enumerate(chunks):
            source_info = f"[Source {i + 1}] (from {chunk.document_name}"
            if chunk.page_number:
                source_info += f", page {chunk.page_number}"
            source_info += f"):\n{chunk.content}"
            context_parts.append(source_info)

        context = "\n\n".join(context_parts)

        messages = [
            {"role": "system", "content": f"{system_prompt}\n\nContext:\n{context}"},
            *history,
            {"role": "user", "content": question},
        ]
        return messages
