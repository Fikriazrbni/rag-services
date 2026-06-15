#!/bin/bash
# =============================================================================
# RAG-as-a-Service - Local Development Startup Script
# =============================================================================

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "🚀 Starting RAG-as-a-Service..."
echo ""

# 1. Start PostgreSQL (Docker)
echo "📦 Starting PostgreSQL + pgvector..."
docker compose up -d db
sleep 3

# 2. Start Ollama (for embeddings)
echo "🧠 Starting Ollama..."
if pgrep -x "ollama" > /dev/null; then
    echo "   Ollama already running"
else
    ollama serve &>/dev/null &
    sleep 2
fi

# 3. Start Backend
echo "⚙️  Starting Backend (FastAPI)..."
cd backend
source .venv/bin/activate
DATABASE_URL="postgresql+asyncpg://rag:rag@localhost:5432/ragservice" \
UPLOAD_DIR="/tmp/rag-uploads" \
OLLAMA_BASE_URL="http://localhost:11434" \
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..
sleep 2

# 4. Start Frontend
echo "🌐 Starting Frontend (Next.js)..."
cd frontend
npm run dev -- -p 3000 &
FRONTEND_PID=$!
cd ..
sleep 3

echo ""
echo "✅ All services running!"
echo ""
echo "   Frontend:  http://localhost:3000"
echo "   Backend:   http://localhost:8000"
echo "   API Docs:  http://localhost:8000/docs"
echo "   Database:  localhost:5432"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait and cleanup on exit
trap "echo ''; echo 'Stopping...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; docker compose stop db; echo 'Done.'" EXIT
wait
