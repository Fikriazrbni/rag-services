import asyncio
from typing import AsyncGenerator, Optional

import httpx
import litellm
from cryptography.fernet import Fernet
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.provider_config import ProviderConfig

# Suppress litellm verbose logging
litellm.suppress_debug_info = True


class ProviderAdapter:
    """Unified interface for LLM and embedding calls via LiteLLM."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._fernet = Fernet(settings.encryption_key.encode()) if settings.encryption_key else None

    def _encrypt_key(self, api_key: str) -> str:
        if not self._fernet:
            return api_key  # No encryption in dev if key not set
        return self._fernet.encrypt(api_key.encode()).decode()

    def _decrypt_key(self, encrypted_key: str) -> str:
        if not self._fernet:
            return encrypted_key
        return self._fernet.decrypt(encrypted_key.encode()).decode()

    async def get_active_config(self, config_type: str) -> Optional[ProviderConfig]:
        """Get the active provider configuration for a given type."""
        result = await self.db.execute(
            select(ProviderConfig).where(
                ProviderConfig.config_type == config_type,
                ProviderConfig.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def set_config(
        self,
        config_type: str,
        provider: str,
        model: str,
        api_key: Optional[str] = None,
        endpoint_url: Optional[str] = None,
    ) -> ProviderConfig:
        """Set a new active config, deactivating the previous one."""
        # Deactivate existing active config
        await self.db.execute(
            update(ProviderConfig)
            .where(
                ProviderConfig.config_type == config_type,
                ProviderConfig.is_active == True,
            )
            .values(is_active=False)
        )

        # Create new active config
        encrypted_key = self._encrypt_key(api_key) if api_key else None
        new_config = ProviderConfig(
            config_type=config_type,
            provider_name=provider,
            model_identifier=model,
            api_key_encrypted=encrypted_key,
            endpoint_url=endpoint_url,
            is_active=True,
        )
        self.db.add(new_config)
        await self.db.flush()
        return new_config

    async def validate_config(
        self, provider: str, model: str, api_key: Optional[str] = None,
        endpoint_url: Optional[str] = None,
    ) -> bool:
        """Validate provider connectivity within 10 seconds."""
        if provider == "ollama":
            return await self._check_ollama_connectivity(endpoint_url or settings.ollama_base_url, model)

        if provider == "voyage":
            return await self._check_voyage_connectivity(api_key)

        try:
            model_string = f"{provider}/{model}"
            response = await asyncio.wait_for(
                litellm.acompletion(
                    model=model_string,
                    messages=[{"role": "user", "content": "hi"}],
                    api_key=api_key,
                    max_tokens=5,
                ),
                timeout=10.0,
            )
            return True
        except Exception:
            return False

    async def _check_voyage_connectivity(self, api_key: Optional[str]) -> bool:
        """Check if Voyage AI API key is valid."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://api.voyageai.com/v1/embeddings",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={"input": ["test"], "model": "voyage-3-lite"},
                )
                return response.status_code == 200
        except Exception:
            return False

    async def _check_ollama_connectivity(self, base_url: str, model: str) -> bool:
        """Check if Ollama is reachable and the model is available."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    def _build_model_string(self, config: ProviderConfig) -> str:
        """Build LiteLLM model string from config."""
        if config.provider_name == "ollama":
            return f"ollama/{config.model_identifier}"
        return f"{config.provider_name}/{config.model_identifier}"

    def _get_api_key(self, config: ProviderConfig) -> Optional[str]:
        """Decrypt and return the API key."""
        if config.api_key_encrypted:
            return self._decrypt_key(config.api_key_encrypted)
        return None

    async def generate(
        self, messages: list[dict], stream: bool = True
    ) -> AsyncGenerator[str, None]:
        """Generate a response from the configured LLM provider."""
        config = await self.get_active_config("llm")
        if not config:
            raise ValueError("No active LLM provider configured")

        model_string = self._build_model_string(config)
        api_key = self._get_api_key(config)

        kwargs = {
            "model": model_string,
            "messages": messages,
            "stream": stream,
            "api_key": api_key,
            "timeout": 60,
        }
        if config.provider_name == "ollama" and config.endpoint_url:
            kwargs["api_base"] = config.endpoint_url

        response = await litellm.acompletion(**kwargs)

        if stream:
            async for chunk in response:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        else:
            yield response.choices[0].message.content

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        config = await self.get_active_config("embedding")
        if not config:
            raise ValueError("No active embedding provider configured")

        # Voyage AI uses its own API
        if config.provider_name == "voyage":
            return await self._voyage_embed(texts, config)

        model_string = self._build_model_string(config)
        api_key = self._get_api_key(config)

        kwargs = {
            "model": model_string,
            "input": texts,
            "api_key": api_key,
        }
        if config.provider_name == "ollama" and config.endpoint_url:
            kwargs["api_base"] = config.endpoint_url

        response = await litellm.aembedding(**kwargs)
        return [item["embedding"] for item in response.data]

    async def _voyage_embed(self, texts: list[str], config) -> list[list[float]]:
        """Generate embeddings using Voyage AI API directly."""
        api_key = self._get_api_key(config)
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.voyageai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "input": texts,
                    "model": config.model_identifier,
                },
            )
            if response.status_code != 200:
                raise ValueError(f"Voyage AI error: {response.text}")
            data = response.json()
            return [item["embedding"] for item in data["data"]]
