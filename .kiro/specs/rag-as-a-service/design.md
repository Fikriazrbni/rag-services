# Technical Design Document

## Overview

This document describes the technical architecture for the RAG-as-a-Service platform — a model-agnostic Knowledge Base Builder deployed as a single-tenant Docker stack. The design prioritizes free/open-source tools for MVP while noting paid alternatives for production scaling.

## Tech Stack

| Layer | MVP (Free) | Pro Alternative (Paid) |
|-------|-----------|----------------------|
| Backend | Python 3.11 + FastAPI | Same |
| LLM Adapter | LiteLLM | Same |
| Vector DB | PostgreSQL 16 + pgvector | Pinecone / Qdrant Cloud |
| Relational DB | PostgreSQL 16 (shared instance) | Amazon RDS / Supabase |
| Frontend | Next.js 14 (React) | Same |
| Document Parsing | PyMuPDF (PDF), python-docx (DOCX) | Unstructured.io / AWS Textract |
| Task Queue | In-process async (asyncio) | Celery + Redis |
| Streaming | Server-Sent Events (SSE) | Same |
| Containerization | Docker Compose | Kubernetes / ECS |
| Embedding (free) | Ollama (local) or Gemini free tier | OpenAI text-embedding-3-large |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Docker Compose                            │
│                                                                  │
│  ┌──────────────┐     ┌──────────────────────────────────────┐  │
│  │   Frontend   │     │            Backend (FastAPI)          │  │
│  │  (Next.js)   │────▶│                                      │  │
│  │  Port 3000   │     │  ┌────────────┐  ┌───────────────┐  │  │
│  └──────────────┘     │  │ API Gateway │  │Doc Processor  │  │  │
│                        │  │  (Routes)   │  │(Parse/Chunk/  │  │  │
│                        │  └─────┬──────┘  │ Embed)        │  │  │
│                        │        │         └───────┬───────┘  │  │
│                        │        ▼                 │          │  │
│                        │  ┌────────────┐          │          │  │
│                        │  │ Provider   │◀─────────┘          │  │
│                        │  │ Adapter    │                     │  │
│                        │  │ (LiteLLM)  │                     │  │
│                        │  └─────┬──────┘                     │  │
│                        │        │                            │  │
│                        └────────┼────────────────────────────┘  │
│                                 │                                │
│                                 ▼                                │
│                        ┌────────────────┐                       │
│                        │  PostgreSQL    │                       │
│                        │  + pgvector    │                       │
│                        │  Port 5432     │                       │
│                        └────────────────┘                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼ (external API calls)
                    ┌─────────────────────────┐
                    │  LLM Providers          │
                    │  OpenAI / Anthropic /   │
                    │  Gemini / Groq / Ollama │
                    └─────────────────────────┘
```

## Project Structure

```
rag-service/
├── docker-compose.yml
├── .env.example
├── README.md
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic/                    # DB migrations
│   │   ├── alembic.ini
│   │   └── versions/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app entry point
│   │   ├── config.py               # Settings via pydantic-settings
│   │   ├── database.py             # SQLAlchemy + async engine
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── document.py
│   │   │   ├── chunk.py
│   │   │   ├── conversation.py
│   │   │   ├── message.py
│   │   │   ├── provider_config.py
│   │   │   └── query_log.py
│   │   ├── schemas/                # Pydantic request/response schemas
│   │   │   ├── __init__.py
│   │   │   ├── document.py
│   │   │   ├── chat.py
│   │   │   ├── provider.py
│   │   │   ├── analytics.py
│   │   │   └── common.py
│   │   ├── routers/                # API route handlers
│   │   │   ├── __init__.py
│   │   │   ├── documents.py
│   │   │   ├── chat.py
│   │   │   ├── providers.py
│   │   │   ├── conversations.py
│   │   │   ├── analytics.py
│   │   │   └── status.py
│   │   ├── services/               # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── document_processor.py
│   │   │   ├── retriever.py
│   │   │   ├── chat_service.py
│   │   │   ├── provider_adapter.py
│   │   │   └── analytics_service.py
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── file_parser.py      # PDF/DOCX/TXT parsing
│   │       ├── chunker.py          # Text splitting logic
│   │       └── sse.py              # SSE streaming helpers
│   └── tests/
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── next.config.js
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx            # Chat page (default)
│   │   │   ├── documents/
│   │   │   │   └── page.tsx        # Document management
│   │   │   ├── analytics/
│   │   │   │   └── page.tsx        # Analytics dashboard
│   │   │   └── settings/
│   │   │       └── page.tsx        # Provider configuration
│   │   ├── components/
│   │   │   ├── chat/
│   │   │   ├── documents/
│   │   │   ├── analytics/
│   │   │   └── common/
│   │   ├── lib/
│   │   │   ├── api.ts              # API client
│   │   │   └── sse.ts              # SSE client helper
│   │   └── types/
│   │       └── index.ts
│   └── tailwind.config.js
└── docs/
    └── api.md
```

## Data Models

### PostgreSQL Tables (with pgvector extension)

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Documents table
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename VARCHAR(255) NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    -- status: pending | processing | completed | failed
    pipeline_stage VARCHAR(20),
    -- pipeline_stage: parsing | chunking | embedding | NULL
    chunk_count INTEGER DEFAULT 0,
    skipped_pages INTEGER[] DEFAULT '{}',
    error_type VARCHAR(100),
    error_message TEXT,
    processing_duration_ms BIGINT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Chunks table (with vector embedding)
CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    page_number INTEGER,
    paragraph_position INTEGER,
    character_offset INTEGER,
    embedding vector(1536),  -- dimension depends on model, 1536 for OpenAI
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for vector similarity search
CREATE INDEX chunks_embedding_idx ON chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Conversations table
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Messages table
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,  -- 'user' | 'assistant'
    content TEXT NOT NULL,
    source_references JSONB,    -- array of source references
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Provider configuration table
CREATE TABLE provider_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_type VARCHAR(20) NOT NULL,  -- 'llm' | 'embedding'
    provider_name VARCHAR(50) NOT NULL,
    model_identifier VARCHAR(100) NOT NULL,
    api_key_encrypted TEXT,  -- encrypted at rest
    endpoint_url VARCHAR(500),  -- for Ollama custom endpoints
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(config_type, is_active) -- only one active config per type
);

-- Query logs for analytics
CREATE TABLE query_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id),
    query_text TEXT NOT NULL,
    response_time_ms INTEGER NOT NULL,
    chunks_retrieved INTEGER NOT NULL,
    provider_used VARCHAR(50) NOT NULL,
    model_used VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_chunks_document_id ON chunks(document_id);
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
CREATE INDEX idx_query_logs_created_at ON query_logs(created_at);
CREATE INDEX idx_provider_configs_active ON provider_configs(config_type, is_active);
```

## API Endpoints Design

### Base URL: `http://localhost:8000/api/v1`

### Documents

| Method | Path | Description | Req |
|--------|------|-------------|-----|
| POST | `/documents/upload` | Upload one or more documents | 1 |
| GET | `/documents` | List all documents (paginated) | 8 |
| GET | `/documents/{id}` | Get document metadata | 8 |
| DELETE | `/documents/{id}` | Delete document + chunks + embeddings | 8 |
| GET | `/documents/{id}/status` | Get processing status | 12 |
| GET | `/documents/status/stream` | SSE stream for status updates | 12 |

### Chat

| Method | Path | Description | Req |
|--------|------|-------------|-----|
| POST | `/chat` | Send a query (streaming SSE response) | 5 |
| POST | `/conversations` | Create new conversation session | 6 |
| GET | `/conversations` | List conversations (paginated) | 6 |
| GET | `/conversations/{id}/messages` | Get conversation messages (paginated) | 6 |

### Providers

| Method | Path | Description | Req |
|--------|------|-------------|-----|
| GET | `/providers/config` | Get current active configurations | 4 |
| PUT | `/providers/llm` | Set LLM provider config | 4 |
| PUT | `/providers/embedding` | Set embedding provider config | 4 |

### Analytics

| Method | Path | Description | Req |
|--------|------|-------------|-----|
| GET | `/analytics/summary` | Total counts (docs, chunks, queries) | 10 |
| GET | `/analytics/query-volume` | Query volume over time | 10 |
| GET | `/analytics/top-keywords` | Top queried keywords | 10 |
| GET | `/analytics/response-times` | Average response times | 10 |

### Health

| Method | Path | Description | Req |
|--------|------|-------------|-----|
| GET | `/health` | Health check endpoint | 11 |

## Components and Interfaces

### 1. Provider Adapter (LiteLLM Integration)

```python
# services/provider_adapter.py
from litellm import completion, acompletion, embedding
from app.models.provider_config import ProviderConfig

class ProviderAdapter:
    """
    Unified interface for LLM and embedding calls.
    Uses LiteLLM to abstract provider differences.
    Supports: openai, anthropic, gemini, groq, ollama
    """

    async def generate(self, messages: list[dict], stream: bool = True):
        """Send messages to configured LLM provider."""
        config = await self._get_active_config("llm")
        model_string = self._build_model_string(config)
        response = await acompletion(
            model=model_string,
            messages=messages,
            stream=stream,
            api_key=config.api_key_decrypted,
            timeout=60
        )
        return response

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        config = await self._get_active_config("embedding")
        model_string = self._build_model_string(config)
        response = await embedding(
            model=model_string,
            input=texts,
            api_key=config.api_key_decrypted
        )
        return [r["embedding"] for r in response.data]

    async def validate_config(self, config_type: str, provider: str,
                              model: str, api_key: str) -> bool:
        """Validate provider config with a test request."""
        if provider == "ollama":
            return await self._check_ollama_connectivity(model)
        # Perform minimal test call
        ...

    def _build_model_string(self, config: ProviderConfig) -> str:
        """Build LiteLLM model string: 'provider/model'"""
        # e.g., "openai/gpt-4o", "anthropic/claude-3-sonnet"
        return f"{config.provider_name}/{config.model_identifier}"
```

### 2. Document Processor (Async Pipeline)

```python
# services/document_processor.py

class DocumentProcessor:
    """
    Orchestrates the document processing pipeline:
    upload → parse → chunk → embed → store
    
    Each stage updates document status and emits SSE events.
    """

    async def process_document(self, document_id: UUID, file_path: str):
        """Main pipeline orchestrator."""
        try:
            # Stage 1: Parse
            await self._update_status(document_id, "processing", "parsing")
            text_content, metadata = await self._parse(file_path)

            # Stage 2: Chunk
            await self._update_status(document_id, "processing", "chunking")
            chunks = await self._chunk(text_content, metadata)

            # Stage 3: Embed
            await self._update_status(document_id, "processing", "embedding")
            await self._embed_and_store(document_id, chunks)

            # Done
            await self._update_status(document_id, "completed", None)
        except ProcessingError as e:
            await self._update_status(
                document_id, "failed", e.stage,
                error_type=e.error_type, error_message=str(e)
            )

    async def _parse(self, file_path: str) -> tuple[str, dict]:
        """Delegate to file_parser based on mime type."""
        ...

    async def _chunk(self, text: str, metadata: dict) -> list[ChunkData]:
        """Split text into chunks with overlap."""
        ...

    async def _embed_and_store(self, doc_id: UUID, chunks: list[ChunkData]):
        """Generate embeddings with retry logic and store in pgvector."""
        ...
```

### 3. Retriever (Semantic Search)

```python
# services/retriever.py

class Retriever:
    """
    Converts user query to embedding, searches pgvector for
    top-k most similar chunks using cosine distance.
    """

    async def search(self, query: str, top_k: int = 5,
                     threshold: float = 0.7) -> list[ChunkResult]:
        """
        1. Embed the query using Provider_Adapter
        2. Execute pgvector similarity search
        3. Filter by threshold
        4. Return ranked results with scores
        """
        query_embedding = await self.provider_adapter.embed([query])

        # pgvector cosine similarity search
        results = await self.db.execute(
            select(Chunk)
            .order_by(Chunk.embedding.cosine_distance(query_embedding[0]))
            .limit(top_k)
        )

        # Filter by threshold and build response
        return [
            ChunkResult(
                chunk=chunk,
                score=1 - cosine_distance,  # convert distance to similarity
                document=chunk.document
            )
            for chunk in results
            if (1 - cosine_distance) >= threshold
        ]
```

### 4. Chat Service (RAG Orchestration)

```python
# services/chat_service.py

class ChatService:
    """
    Orchestrates the full RAG flow:
    query → retrieve → augment prompt → generate → stream response
    """

    async def query(self, session_id: UUID, question: str):
        """
        Full RAG pipeline with conversation context.
        Returns an async generator for SSE streaming.
        """
        # 1. Load conversation history
        history = await self._get_history(session_id)

        # 2. Retrieve relevant chunks
        chunks = await self.retriever.search(question)

        # 3. Build augmented prompt
        messages = self._build_rag_prompt(history, question, chunks)

        # 4. Generate response (streaming)
        response_stream = await self.provider_adapter.generate(
            messages=messages, stream=True
        )

        # 5. Yield tokens + save response when complete
        full_response = ""
        async for token in response_stream:
            full_response += token
            yield token

        # 6. Save message + log query
        await self._save_messages(session_id, question, full_response, chunks)
        await self._log_query(question, chunks, response_time)

    def _build_rag_prompt(self, history, question, chunks) -> list[dict]:
        """Construct system + context + history + question."""
        system_prompt = (
            "You are a helpful assistant. Answer questions based on "
            "the provided context. Cite sources using [Source N] notation."
        )
        context = "\n\n".join([
            f"[Source {i+1}] (from {c.document.filename}, page {c.page_number}):\n{c.content}"
            for i, c in enumerate(chunks)
        ])
        return [
            {"role": "system", "content": f"{system_prompt}\n\nContext:\n{context}"},
            *history,  # previous messages
            {"role": "user", "content": question}
        ]
```

## Data Flow Diagrams

### Document Upload & Processing Flow

```
User uploads file(s)
        │
        ▼
[POST /api/v1/documents/upload]
        │
        ├── Validate: format, size, count
        │   └── Reject if invalid (400)
        │
        ▼
Save file to disk → Create document record (status: "pending")
        │
        ▼ (async background task)
┌─────────────────────────────────────────┐
│ PIPELINE (updates status via SSE)       │
│                                         │
│ 1. PARSING                              │
│    ├── PDF → PyMuPDF                    │
│    ├── DOCX → python-docx              │
│    └── TXT → raw read                  │
│    Output: raw text + page metadata     │
│                                         │
│ 2. CHUNKING                             │
│    ├── Split by token count             │
│    ├── Apply overlap                    │
│    └── Attach metadata per chunk        │
│    Output: list of ChunkData            │
│                                         │
│ 3. EMBEDDING                            │
│    ├── Batch chunks (max 20 per call)   │
│    ├── Call Provider_Adapter.embed()    │
│    ├── Retry on failure (3x backoff)    │
│    └── Store in pgvector                │
│    Output: vectors stored               │
│                                         │
│ Final: status → "completed"             │
└─────────────────────────────────────────┘
```

### Chat Query Flow

```
User sends question
        │
        ▼
[POST /api/v1/chat]
  body: { session_id, question }
        │
        ├── Validate: question length, session exists
        │
        ▼
┌─────────────────────────────────────────┐
│ RAG PIPELINE                            │
│                                         │
│ 1. Embed question                       │
│    └── Provider_Adapter.embed(question) │
│                                         │
│ 2. Vector search (pgvector)             │
│    └── Top-k chunks by cosine sim       │
│                                         │
│ 3. Filter by threshold                  │
│    └── If none found → "no info" msg    │
│                                         │
│ 4. Build prompt                         │
│    ├── System instruction               │
│    ├── Retrieved context                │
│    ├── Conversation history             │
│    └── User question                    │
│                                         │
│ 5. LLM generation (streaming)           │
│    └── Provider_Adapter.generate()      │
│                                         │
│ 6. Stream response via SSE              │
│    ├── Token-by-token delivery          │
│    └── Final event: source_references   │
│                                         │
│ 7. Persist messages + log query         │
└─────────────────────────────────────────┘
        │
        ▼
SSE Stream to client:
  event: token    → { "content": "..." }
  event: sources  → { "references": [...] }
  event: done     → { "message_id": "..." }
```

## Response Schemas

### Standard Success Response
```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

### Paginated Response
```json
{
  "success": true,
  "data": [ ... ],
  "meta": {
    "request_id": "uuid",
    "timestamp": "2024-01-01T00:00:00Z",
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total_count": 150,
      "total_pages": 8
    }
  }
}
```

### Standard Error Response
```json
{
  "success": false,
  "error": {
    "code": "DOCUMENT_NOT_FOUND",
    "message": "Document with id '...' was not found",
    "details": {}
  },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

### Chat SSE Stream Events
```
event: token
data: {"content": "Based on"}

event: token
data: {"content": " the document,"}

event: sources
data: {"references": [
  {
    "document_name": "manual.pdf",
    "page_number": 5,
    "excerpt": "The system requires...",
    "confidence_score": 0.92,
    "chunk_id": "uuid"
  }
]}

event: done
data: {"message_id": "uuid", "response_time_ms": 1234}
```

### Document Status SSE Stream
```
event: status_change
data: {
  "document_id": "uuid",
  "status": "processing",
  "pipeline_stage": "embedding",
  "progress": null,
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Frontend Architecture

### Pages & Components

```
App Layout (sidebar navigation)
├── /chat (default)
│   ├── ConversationList (sidebar)
│   ├── ChatMessages (main area)
│   │   ├── MessageBubble
│   │   └── SourceReferenceCard
│   │       └── ExpandableChunkPanel
│   └── ChatInput
│
├── /documents
│   ├── UploadDropzone
│   ├── DocumentTable
│   │   ├── StatusBadge (pending/processing/completed/failed)
│   │   └── ActionButtons (delete, view details)
│   └── DocumentDetailModal
│
├── /analytics
│   ├── SummaryCards (total docs, chunks, queries)
│   ├── QueryVolumeChart (line chart, time range selector)
│   ├── TopKeywordsTable
│   └── ResponseTimeChart
│
└── /settings
    ├── LLMProviderForm
    ├── EmbeddingProviderForm
    └── CurrentConfigDisplay
```

### State Management

- **Server state**: TanStack Query (React Query) for API data fetching, caching, and invalidation
- **SSE connections**: Custom hooks (`useSSEStream`, `useDocumentStatus`) managing EventSource instances
- **UI state**: React useState/useReducer for local component state
- **No global state library needed** for MVP scope

### Key Frontend Libraries

| Library | Purpose |
|---------|---------|
| Next.js 14 | Framework (App Router) |
| TailwindCSS | Styling |
| shadcn/ui | UI components |
| TanStack Query | Server state management |
| Recharts | Analytics charts |
| react-dropzone | File upload |
| react-markdown | Rendering AI responses |

## Docker Compose Design

```yaml
# docker-compose.yml structure
version: "3.8"

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://rag:rag@db:5432/ragservice
      - UPLOAD_DIR=/app/uploads
    volumes:
      - uploads:/app/uploads
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
    depends_on:
      - backend
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000"]
      interval: 10s
      timeout: 5s
      retries: 5

  db:
    image: pgvector/pgvector:pg16
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=rag
      - POSTGRES_PASSWORD=rag
      - POSTGRES_DB=ragservice
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U rag"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
  uploads:
```

## Environment Variables (.env.example)

```env
# Database
DATABASE_URL=postgresql+asyncpg://rag:rag@db:5432/ragservice
POSTGRES_USER=rag
POSTGRES_PASSWORD=rag
POSTGRES_DB=ragservice

# Backend
UPLOAD_DIR=/app/uploads
MAX_FILE_SIZE_MB=50
MAX_FILES_PER_REQUEST=20
CHUNK_SIZE_TOKENS=512
CHUNK_OVERLAP_TOKENS=50
DEFAULT_TOP_K=5
SIMILARITY_THRESHOLD=0.7
CONTEXT_WINDOW_MESSAGES=10

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1

# LLM Provider (configure via API, but can set defaults here)
DEFAULT_LLM_PROVIDER=ollama
DEFAULT_LLM_MODEL=llama3
DEFAULT_EMBEDDING_PROVIDER=ollama
DEFAULT_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

## Key Design Decisions

### 1. Single PostgreSQL for everything
- **Why**: Simplifies deployment, reduces operational overhead for single-tenant MVP
- **How**: pgvector extension adds vector search to standard PostgreSQL
- **Trade-off**: Won't scale to millions of vectors efficiently
- **Pro upgrade**: Pinecone or Qdrant Cloud for >1M vectors

### 2. LiteLLM as unified provider interface
- **Why**: Single API for 100+ models, handles auth and format differences
- **How**: `litellm.completion("provider/model", ...)` pattern
- **Benefit**: Adding new providers = zero code change, just config

### 3. Async background processing (no task queue)
- **Why**: Avoids Redis/Celery complexity for MVP
- **How**: FastAPI BackgroundTasks + asyncio for document processing
- **Trade-off**: Processing blocked if server restarts mid-pipeline
- **Pro upgrade**: Celery + Redis for reliable job processing with retries

### 4. SSE over WebSocket
- **Why**: Simpler server implementation, works through proxies/CDNs, auto-reconnect
- **How**: FastAPI StreamingResponse for chat, dedicated endpoint for status
- **Trade-off**: Unidirectional only (server → client)
- **Sufficient**: Chat flow is request-response + server push

### 5. pgvector IVFFlat index
- **Why**: Good balance of speed and accuracy for <500K vectors
- **How**: Pre-built lists for approximate nearest neighbor search
- **Trade-off**: Needs reindexing when data grows significantly
- **Pro upgrade**: HNSW index for better recall, or dedicated vector DB

### 6. File storage on local disk (Docker volume)
- **Why**: Zero cost, works with Docker volumes, simple
- **Trade-off**: Can't scale horizontally, limited by disk
- **Pro upgrade**: S3/MinIO for distributed file storage

### 7. No auth for MVP
- **Why**: Single-tenant deployment, focus on core RAG value
- **Future**: Add API key auth → OAuth → RBAC as product matures

## Security Considerations (MVP)

- API keys stored encrypted at rest (Fernet symmetric encryption)
- File upload validation: MIME type check + magic bytes verification
- SQL injection prevented by SQLAlchemy ORM (parameterized queries)
- File size limits enforced at both nginx/proxy and application level
- No sensitive data in logs (API keys masked)
- CORS configured for frontend origin only

## Performance Targets (MVP)

| Metric | Target |
|--------|--------|
| Document processing (100 pages) | < 60 seconds |
| Chat query (end-to-end first token) | < 3 seconds |
| Vector search (10K chunks) | < 200ms |
| API response (non-streaming) | < 500ms |
| Concurrent chat sessions | 10+ |

## Dependencies (Python Backend)

```
# pyproject.toml key dependencies
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
sqlalchemy[asyncio]>=2.0
asyncpg>=0.29.0
alembic>=1.13.0
litellm>=1.40.0
pgvector>=0.3.0
pymupdf>=1.24.0          # PDF parsing
python-docx>=1.1.0       # DOCX parsing
tiktoken>=0.7.0          # Token counting for chunking
pydantic>=2.7.0
pydantic-settings>=2.3.0
python-multipart>=0.0.9  # File uploads
cryptography>=42.0.0     # API key encryption
sse-starlette>=2.0.0     # Server-Sent Events
```

## Dependencies (Frontend)

```json
{
  "dependencies": {
    "next": "^14.2.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "@tanstack/react-query": "^5.0.0",
    "tailwindcss": "^3.4.0",
    "recharts": "^2.12.0",
    "react-dropzone": "^14.2.0",
    "react-markdown": "^9.0.0",
    "lucide-react": "^0.400.0"
  }
}
```

## Error Handling

### Error Categories & HTTP Status Codes

| Category | HTTP Code | Error Code | Example |
|----------|-----------|-----------|---------|
| Validation | 400 | `VALIDATION_ERROR` | Missing required field, invalid format |
| Not Found | 404 | `DOCUMENT_NOT_FOUND` | Document ID doesn't exist |
| Conflict | 409 | `DOCUMENT_PROCESSING` | Delete while still processing |
| Payload Too Large | 413 | `FILE_TOO_LARGE` | File exceeds 50MB |
| Unsupported Media | 415 | `UNSUPPORTED_FORMAT` | Non-PDF/DOCX/TXT file |
| Provider Error | 502 | `PROVIDER_UNAVAILABLE` | LLM/embedding API unreachable |
| Timeout | 504 | `REQUEST_TIMEOUT` | Processing exceeded 60s |
| Internal | 500 | `INTERNAL_ERROR` | Unexpected server failure |

### Retry Strategy (Document Processing)

```
Embedding failures:
  Retry 1: wait 1s
  Retry 2: wait 2s  
  Retry 3: wait 4s
  After 3 failures: mark document as "failed", rollback partial embeddings
```

### Provider Failover

- No automatic failover between providers (user explicitly configures)
- On provider error during chat: return error with suggestion to check config
- On provider error during embedding: retry with backoff, then fail document
- Previous config preserved on validation failure (no broken state)

## Correctness Properties

### Property 1: Document Status State Machine

**Validates: Requirements 1.1, 2.4, 2.5, 3.4, 3.7, 12.1, 12.2, 12.3**

1. **Document status consistency**: A document can only transition through: `pending → processing → completed` OR `pending → processing → failed`. No other transitions are valid.
2. **Chunk-document integrity**: Every chunk in the Vector_Store has a valid `document_id` referencing an existing document. Document deletion cascades to all its chunks.
3. **Embedding dimension consistency**: All embeddings in the Vector_Store have the same dimension matching the active embedding model. Changing models requires re-embedding.
4. **Single active provider**: At most one active LLM config and one active embedding config exist at any time.
5. **Conversation ordering**: Messages within a conversation are stored and returned in chronological order by `created_at` timestamp.

### Property 2: Pre/Post Conditions

**Validates: Requirements 4.4, 5.7, 8.5, 8.6**

| Operation | Pre-condition | Post-condition |
|-----------|--------------|----------------|
| Upload document | Valid format, size < 50MB | Document record created with status "pending" |
| Delete document | Status is "completed" or "failed" | Document + chunks + embeddings removed |
| Chat query | Active LLM + embedding config, ≥1 document completed | Response streamed with source references |
| Switch provider | Valid API key (or Ollama connectivity) | New provider active, old config deactivated |

## Testing Strategy

### Unit Tests (Backend)

- **File parser**: Test PDF/DOCX/TXT extraction with sample files
- **Chunker**: Test chunk size, overlap, edge cases (empty doc, single word)
- **Provider adapter**: Mock LiteLLM calls, test retry logic
- **Retriever**: Mock pgvector queries, test threshold filtering

### Integration Tests

- **Document pipeline**: Upload → parse → chunk → embed → verify in DB
- **Chat flow**: Upload doc → query → verify answer includes source refs
- **Provider config**: Set config → validate → verify active config changes
- **API contracts**: Verify all endpoints match OpenAPI spec

### E2E Tests

- **Happy path**: Upload PDF → wait for processing → ask question → get answer with sources
- **Error paths**: Upload invalid file → verify error; query with no docs → verify message
- **Provider swap**: Configure OpenAI → query → switch to Ollama → query → both work

### Test Tools

| Tool | Purpose |
|------|---------|
| pytest + pytest-asyncio | Backend unit/integration tests |
| httpx | Async test client for FastAPI |
| testcontainers | PostgreSQL + pgvector in tests |
| Playwright or Cypress | Frontend E2E (future) |
