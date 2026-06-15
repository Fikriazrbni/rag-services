# Deployment Guide (Free Tier)

## Architecture

```
Vercel (Frontend) → Render (Backend) → Neon (PostgreSQL + pgvector)
                         ↓
              Groq (LLM) + Voyage AI (Embedding)
```

## Step 1: Push to GitHub

```bash
cd "/Users/fikriazharirabbani/Documents/Self Data/Belajar/Saas"
git init
git add .
git commit -m "Initial commit: RAG-as-a-Service"
gh repo create rag-service --public --source=. --push
```

## Step 2: Neon Database (PostgreSQL + pgvector)

1. Go to https://neon.tech → Sign up with GitHub
2. Create project: name = `rag-service`, region = `Singapore`
3. Copy the connection string (looks like: `postgresql://user:pass@ep-xxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require`)
4. Enable pgvector:
   - Go to SQL Editor in Neon dashboard
   - Run: `CREATE EXTENSION IF NOT EXISTS vector;`
5. Run migrations:
   ```bash
   # From your local machine
   cd backend
   source .venv/bin/activate
   DATABASE_URL="YOUR_NEON_CONNECTION_STRING" alembic upgrade head
   ```
   Note: Replace `postgresql://` with `postgresql+asyncpg://` for the app env var.

## Step 3: Voyage AI (Embedding)

1. Go to https://dash.voyageai.com → Sign up
2. Go to API Keys → Create new key
3. Save the key (starts with `pa-...`)
4. Free tier: 200M tokens/month

## Step 4: Render (Backend)

1. Go to https://render.com → Sign up with GitHub
2. New → Web Service → Connect your `rag-service` repo
3. Settings:
   - Name: `rag-service-backend`
   - Region: `Singapore`
   - Runtime: `Python 3`
   - Build Command: `cd backend && pip install .`
   - Start Command: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Plan: `Free`
4. Environment Variables (add these):

| Key | Value |
|-----|-------|
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@ep-xxx.neon.tech/neondb?sslmode=require` |
| `UPLOAD_DIR` | `/tmp/rag-uploads` |
| `MAX_FILE_SIZE_MB` | `50` |
| `MAX_FILES_PER_REQUEST` | `20` |
| `CHUNK_SIZE_TOKENS` | `512` |
| `CHUNK_OVERLAP_TOKENS` | `50` |
| `DEFAULT_TOP_K` | `5` |
| `SIMILARITY_THRESHOLD` | `0.3` |
| `CONTEXT_WINDOW_MESSAGES` | `10` |
| `ENCRYPTION_KEY` | *(generate: see below)* |
| `DEFAULT_LLM_PROVIDER` | `groq` |
| `DEFAULT_LLM_MODEL` | `llama-3.1-8b-instant` |
| `DEFAULT_EMBEDDING_PROVIDER` | `voyage` |
| `DEFAULT_EMBEDDING_MODEL` | `voyage-3-lite` |
| `OLLAMA_BASE_URL` | *(leave empty)* |

Generate encryption key:
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

5. Deploy → wait for build

## Step 5: Vercel (Frontend)

1. Go to https://vercel.com → Sign up with GitHub
2. Import → select `rag-service` repo
3. Settings:
   - Framework: Next.js
   - Root Directory: `frontend`
4. Environment Variables:

| Key | Value |
|-----|-------|
| `NEXT_PUBLIC_API_URL` | `https://rag-service-backend.onrender.com/api/v1` |

5. Deploy

## Step 6: First-time Setup

After deployment, configure providers via API:

```bash
# Replace with your actual Render URL
API_URL="https://rag-service-backend.onrender.com/api/v1"

# Configure Groq (LLM)
curl -X PUT $API_URL/providers/llm \
  -H "Content-Type: application/json" \
  -d '{"provider": "groq", "model": "llama-3.1-8b-instant", "api_key": "YOUR_GROQ_KEY"}'

# Configure Voyage AI (Embedding)
curl -X PUT $API_URL/providers/embedding \
  -H "Content-Type: application/json" \
  -d '{"provider": "voyage", "model": "voyage-3-lite", "api_key": "YOUR_VOYAGE_KEY"}'
```

## Done!

Your app is live at your Vercel URL (e.g., `https://rag-service-xxx.vercel.app`)

## Notes

- Render free tier sleeps after 15 min idle (first request after sleep takes ~30s)
- Neon free tier: 0.5GB storage, auto-suspends after 5 min idle
- Voyage AI free: 200M tokens/month
- Groq free: rate-limited but generous for personal use
- Local development still works with `./start.sh` (unchanged)

## Updating

Push to GitHub → Render & Vercel auto-deploy:
```bash
git add .
git commit -m "update"
git push
```
