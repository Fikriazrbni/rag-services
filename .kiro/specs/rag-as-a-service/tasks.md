# Implementation Plan:

## Overview

This plan implements the RAG-as-a-Service platform in 20 tasks, organized from infrastructure setup through backend services to frontend UI. Tasks are ordered to minimize blocking dependencies — foundation first (Docker, DB, schemas), then core backend services, then frontend pages.

## Tasks

- [x] 1. Project Scaffolding & Docker Setup
  Requirements: 11.1, 11.2, 11.4, 11.5
  Set up the monorepo structure with Docker Compose configuration, backend (FastAPI) and frontend (Next.js) project skeletons, PostgreSQL with pgvector, environment variables, and health check endpoints.
  Files: docker-compose.yml, .env.example, README.md, backend/Dockerfile, backend/pyproject.toml, backend/app/__init__.py, backend/app/main.py, backend/app/config.py, frontend/Dockerfile, frontend/package.json, frontend/next.config.js, frontend/tailwind.config.js, frontend/src/app/layout.tsx, frontend/src/app/page.tsx

- [x] 2. Database Models & Migrations
  Requirements: 1.1, 2.3, 3.1, 4.1, 6.2, 10.5
  Create SQLAlchemy async ORM models for all tables (documents, chunks, conversations, messages, provider_configs, query_logs), set up Alembic migrations, and initialize the pgvector extension.
  Files: backend/app/database.py, backend/app/models/__init__.py, backend/app/models/document.py, backend/app/models/chunk.py, backend/app/models/conversation.py, backend/app/models/message.py, backend/app/models/provider_config.py, backend/app/models/query_log.py, backend/alembic.ini, backend/alembic/env.py, backend/alembic/versions/001_initial_schema.py

- [x] 3. Pydantic Schemas & Common Response Structures
  Requirements: 9.2, 9.4, 9.6
  Create all Pydantic request/response schemas including the standard response envelope (success/error/meta), pagination metadata, and validation error structures used across all endpoints.
  Files: backend/app/schemas/__init__.py, backend/app/schemas/common.py, backend/app/schemas/document.py, backend/app/schemas/chat.py, backend/app/schemas/provider.py, backend/app/schemas/analytics.py

- [x] 4. Provider Adapter Service (LiteLLM)
  Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8
  Implement the ProviderAdapter service wrapping LiteLLM for unified LLM generation and embedding calls. Includes API key encryption, config validation (with Ollama connectivity check), and provider configuration endpoints.
  Files: backend/app/services/__init__.py, backend/app/services/provider_adapter.py, backend/app/routers/__init__.py, backend/app/routers/providers.py, backend/app/utils/__init__.py

- [x] 5. File Upload & Validation
  Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7
  Implement the document upload endpoint with file validation (format, size, count, empty file), file storage to disk, and creation of document records with "pending" status.
  Files: backend/app/routers/documents.py, backend/app/services/document_processor.py

- [x] 6. Document Parsing (PDF/DOCX/TXT)
  Requirements: 2.1, 2.4, 2.6
  Implement file parsers for PDF (PyMuPDF), DOCX (python-docx), and TXT files. Extract text content while preserving structural metadata (page numbers, headings, paragraphs). Handle mixed-content documents and unextractable files.
  Files: backend/app/utils/file_parser.py

- [x] 7. Text Chunking Engine
  Requirements: 2.2, 2.3, 2.5, 2.7
  Implement the text chunker that splits parsed content into overlapping chunks with configurable chunk size and overlap using tiktoken for token counting. Attaches metadata to each chunk.
  Files: backend/app/utils/chunker.py

- [x] 8. Embedding Generation & Storage
  Requirements: 3.1, 3.2, 3.3, 3.4, 3.6, 3.7
  Implement embedding generation for document chunks using the ProviderAdapter. Batch chunks for efficient API calls, implement retry logic with exponential backoff, store vectors in pgvector, and handle partial failures with rollback.
  Files: backend/app/services/document_processor.py

- [x] 9. Document Processing Pipeline & Status
  Requirements: 12.1, 12.2, 12.3, 12.4, 12.5
  Wire together the full async processing pipeline (parse → chunk → embed) triggered after upload. Implement status tracking with pipeline stage visibility and SSE event emission for real-time status updates.
  Files: backend/app/services/document_processor.py, backend/app/routers/status.py, backend/app/utils/sse.py

- [x] 10. Knowledge Base Management API
  Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6
  Implement document listing (paginated), detail retrieval, and deletion endpoints. Deletion cascades to chunks and embeddings. Prevent deletion of documents in processing state.
  Files: backend/app/routers/documents.py

- [x] 11. Retriever Service (Semantic Search)
  Requirements: 5.1, 5.5, 7.1, 7.4
  Implement the Retriever service that converts a user query into an embedding, performs cosine similarity search on pgvector, filters by threshold, and returns ranked chunks with confidence scores.
  Files: backend/app/services/retriever.py

- [x] 12. Chat Service & Streaming Endpoint
  Requirements: 5.1, 5.2, 5.3, 5.4, 5.6, 5.7, 6.1, 7.1, 7.5
  Implement the ChatService orchestrating the full RAG flow: load conversation history, retrieve chunks, build augmented prompt, stream LLM response via SSE, persist messages, and generate source references.
  Files: backend/app/services/chat_service.py, backend/app/routers/chat.py

- [x] 13. Conversation Management API
  Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
  Implement conversation CRUD: create new sessions, list conversations (paginated), retrieve messages for a conversation (paginated), and handle invalid session IDs.
  Files: backend/app/routers/conversations.py

- [x] 14. Analytics Backend Service & API
  Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7
  Implement analytics service that queries aggregated data from query_logs and documents tables. Expose endpoints for summary counts, query volume over time, top keywords, and response times.
  Files: backend/app/services/analytics_service.py, backend/app/routers/analytics.py

- [x] 15. Frontend - App Shell & Navigation
  Requirements: 11.1
  Set up the Next.js 14 app with App Router, TailwindCSS, shadcn/ui, and the main layout with sidebar navigation between Chat, Documents, Analytics, and Settings pages.
  Files: frontend/src/app/layout.tsx, frontend/src/app/page.tsx, frontend/src/components/common/Sidebar.tsx, frontend/src/components/common/Header.tsx, frontend/src/lib/api.ts, frontend/src/types/index.ts

- [x] 16. Frontend - Chat Interface
  Requirements: 5.3, 6.3, 7.2, 7.3
  Build the chat page with conversation list sidebar, message display with streaming support, source reference cards with expandable panels, and chat input with SSE consumption.
  Files: frontend/src/app/page.tsx, frontend/src/components/chat/ConversationList.tsx, frontend/src/components/chat/ChatMessages.tsx, frontend/src/components/chat/MessageBubble.tsx, frontend/src/components/chat/SourceReferenceCard.tsx, frontend/src/components/chat/ChatInput.tsx, frontend/src/lib/sse.ts

- [x] 17. Frontend - Document Management Page
  Requirements: 1.1, 8.1, 8.2, 12.5
  Build the documents page with drag-and-drop upload, document table with status badges, deletion with confirmation, and real-time processing status via SSE.
  Files: frontend/src/app/documents/page.tsx, frontend/src/components/documents/UploadDropzone.tsx, frontend/src/components/documents/DocumentTable.tsx, frontend/src/components/documents/StatusBadge.tsx, frontend/src/components/documents/DocumentDetailModal.tsx

- [x] 18. Frontend - Analytics Dashboard
  Requirements: 10.1, 10.2, 10.3, 10.4, 10.7
  Build the analytics page with summary cards, query volume line chart with time range selector, top keywords table, and average response time display using Recharts.
  Files: frontend/src/app/analytics/page.tsx, frontend/src/components/analytics/SummaryCards.tsx, frontend/src/components/analytics/QueryVolumeChart.tsx, frontend/src/components/analytics/TopKeywordsTable.tsx, frontend/src/components/analytics/ResponseTimeChart.tsx

- [x] 19. Frontend - Settings Page (Provider Configuration)
  Requirements: 4.1, 4.3, 4.7, 4.8
  Build the settings page with forms for LLM and embedding provider configuration, showing current active config and handling validation feedback with re-embedding warnings.
  Files: frontend/src/app/settings/page.tsx, frontend/src/components/settings/LLMProviderForm.tsx, frontend/src/components/settings/EmbeddingProviderForm.tsx, frontend/src/components/settings/CurrentConfigDisplay.tsx

- [x] 20. OpenAPI Documentation & Final Integration
  Requirements: 9.1, 9.3, 9.5, 9.7, 11.3, 11.5, 11.6
  Ensure FastAPI auto-generates complete OpenAPI/Swagger docs, add request timeout middleware (60s), verify SSE streaming through Docker networking, write README with deployment guide, and validate full end-to-end flow.
  Files: backend/app/main.py, README.md, docs/api.md

## Task Dependency Graph

```json
{
  "waves": [
    {
      "wave": 1,
      "tasks": [1],
      "description": "Project scaffolding and Docker setup"
    },
    {
      "wave": 2,
      "tasks": [2],
      "description": "Database models and migrations"
    },
    {
      "wave": 3,
      "tasks": [3],
      "description": "Pydantic schemas and response structures"
    },
    {
      "wave": 4,
      "tasks": [4, 5, 6, 7],
      "description": "Provider adapter, file upload, parsing, and chunking (parallelizable)"
    },
    {
      "wave": 5,
      "tasks": [8, 10],
      "description": "Embedding generation and KB management"
    },
    {
      "wave": 6,
      "tasks": [9, 11, 13, 14, 15],
      "description": "Processing pipeline, retriever, conversations, analytics backend, frontend shell"
    },
    {
      "wave": 7,
      "tasks": [12, 16, 17, 18, 19],
      "description": "Chat service and all frontend pages"
    },
    {
      "wave": 8,
      "tasks": [20],
      "description": "OpenAPI docs, integration testing, README"
    }
  ]
}
```

## Notes

- Tasks 1-3 are foundation and must be completed first sequentially.
- Tasks 4-14 (backend services) can be partially parallelized: Provider Adapter (4) unblocks Embedding (8), Retriever (11), and Chat (12). Parsing (6) and Chunking (7) are independent of provider setup.
- Frontend tasks (15-19) can begin once Task 15 (shell) is done, but require corresponding backend APIs to be functional for integration testing.
- Task 20 is the final integration/documentation pass.
- For local development without Docker: run PostgreSQL locally, start backend with `uvicorn`, start frontend with `next dev`.
