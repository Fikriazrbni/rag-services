from typing import Optional

from pydantic import BaseModel, Field


class ProviderConfigRequest(BaseModel):
    provider: str = Field(..., description="Provider name: openai, anthropic, gemini, groq, ollama")
    model: str = Field(..., description="Model identifier, e.g. gpt-4o, claude-3-sonnet")
    api_key: Optional[str] = Field(None, description="API key (not required for ollama)")
    endpoint_url: Optional[str] = Field(None, description="Custom endpoint URL (for ollama)")


class ProviderConfigResponse(BaseModel):
    config_type: str
    provider_name: str
    model_identifier: str
    endpoint_url: Optional[str] = None
    is_active: bool = True


class ProviderStatusResponse(BaseModel):
    llm: Optional[ProviderConfigResponse] = None
    embedding: Optional[ProviderConfigResponse] = None
