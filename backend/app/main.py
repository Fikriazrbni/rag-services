from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers import documents, chat, providers, conversations, analytics, status

app = FastAPI(
    title="RAG-as-a-Service",
    description="Model-agnostic Knowledge Base Builder API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://rag-services.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_origin_regex=r"https://.*\.vercel\.app",
)

# Include routers
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(providers.router)
app.include_router(conversations.router)
app.include_router(analytics.router)
app.include_router(status.router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred.",
                "details": {},
            },
        },
    )


@app.get("/api/v1/health", tags=["Health"])
async def health_check():
    """Health check endpoint for Docker and monitoring."""
    return {
        "status": "healthy",
        "service": "rag-service-backend",
        "version": "0.1.0",
    }
