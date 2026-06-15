from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://rag:rag@db:5432/ragservice"

    # File upload
    upload_dir: str = "/app/uploads"
    max_file_size_mb: int = 50
    max_files_per_request: int = 20

    # Chunking
    chunk_size_tokens: int = 512
    chunk_overlap_tokens: int = 50

    # Retrieval
    default_top_k: int = 5
    similarity_threshold: float = 0.3

    # Conversation
    context_window_messages: int = 10

    # Encryption
    encryption_key: str = ""

    # LLM Defaults
    default_llm_provider: str = "ollama"
    default_llm_model: str = "llama3"
    default_embedding_provider: str = "ollama"
    default_embedding_model: str = "nomic-embed-text"
    ollama_base_url: str = "http://host.docker.internal:11434"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
