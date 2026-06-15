# RAG-as-a-Service

Model-agnostic Knowledge Base Builder. Upload documents, ask questions, get AI-powered answers with source references.

## Features

- **Model-agnostic**: Swap LLM providers (OpenAI, Anthropic, Gemini, Groq, Ollama) without changing workflows
- **Document processing**: Upload PDF, DOCX, TXT → automatic parsing, chunking, and embedding
- **Semantic search**: Vector similarity search powered by pgvector
- **Source references**: Every answer cites the exact document, page, and paragraph
- **Streaming responses**: Real-time token delivery via Server-Sent Events
- **Analytics**: Track usage, popular queries, and response times
- **API-first**: Full REST API with OpenAPI documentation

## Quick Start

### Prerequisites

- Docker & Docker Compose (v2.0+)
- 4GB RAM minimum (8GB recommended)
- 10GB disk space

### 1. Clone & Configure

```bash
cp .env.example .env
# Edit .env with your settings (defaults work for local development)
```

### 2. Start Services

```bash
docker compose up --build
```

### 3. Access

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000/api/v1
- **API Docs (Swagger)**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health

### 4. Configure a Provider

Before uploading documents, configure an LLM and embedding provider via the Settings page or API:

```bash
# Example: Configure Ollama (local, free)
curl -X PUT http://localhost:8000/api/v1/providers/llm \
  -H "Content-Type: application/json" \
  -d '{"provider": "ollama", "model": "llama3"}'

curl -X PUT http://localhost:8000/api/v1/providers/embedding \
  -H "Content-Type: application/json" \
  -d '{"provider": "ollama", "model": "nomic-embed-text"}'
```

## Architecture

```
Frontend (Next.js :3000) → Backend (FastAPI :8000) → PostgreSQL+pgvector (:5432)
                                    ↓
                           LLM Providers (external)
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.11, FastAPI, SQLAlchemy |
| Frontend | Next.js 14, React, TailwindCSS |
| Database | PostgreSQL 16 + pgvector |
| LLM Interface | LiteLLM (100+ models) |
| Containerization | Docker Compose |

## Development

### Backend (without Docker)

```bash
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

### Frontend (without Docker)

```bash
cd frontend
npm install
npm run dev
```

## Environment Variables

See `.env.example` for all available configuration options.

## License

MIT
