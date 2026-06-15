from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import SuccessResponse, ErrorResponse
from app.schemas.provider import (
    ProviderConfigRequest,
    ProviderConfigResponse,
    ProviderStatusResponse,
)
from app.services.provider_adapter import ProviderAdapter

router = APIRouter(prefix="/api/v1/providers", tags=["Providers"])


@router.get("/config", response_model=SuccessResponse)
async def get_provider_config(db: AsyncSession = Depends(get_db)):
    """Get current active LLM and embedding provider configurations."""
    adapter = ProviderAdapter(db)

    llm_config = await adapter.get_active_config("llm")
    embedding_config = await adapter.get_active_config("embedding")

    status = ProviderStatusResponse(
        llm=ProviderConfigResponse(
            config_type="llm",
            provider_name=llm_config.provider_name,
            model_identifier=llm_config.model_identifier,
            endpoint_url=llm_config.endpoint_url,
        ) if llm_config else None,
        embedding=ProviderConfigResponse(
            config_type="embedding",
            provider_name=embedding_config.provider_name,
            model_identifier=embedding_config.model_identifier,
            endpoint_url=embedding_config.endpoint_url,
        ) if embedding_config else None,
    )

    return SuccessResponse(data=status.model_dump())


@router.put("/llm", response_model=SuccessResponse)
async def set_llm_provider(
    request: ProviderConfigRequest,
    db: AsyncSession = Depends(get_db),
):
    """Configure the LLM provider for chat generation."""
    adapter = ProviderAdapter(db)

    # Validate
    valid = await adapter.validate_config(
        provider=request.provider,
        model=request.model,
        api_key=request.api_key,
        endpoint_url=request.endpoint_url,
    )
    if not valid:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "PROVIDER_VALIDATION_FAILED",
                "message": f"Could not validate {request.provider}/{request.model}. "
                           "Check your API key or provider availability.",
            },
        )

    config = await adapter.set_config(
        config_type="llm",
        provider=request.provider,
        model=request.model,
        api_key=request.api_key,
        endpoint_url=request.endpoint_url,
    )

    return SuccessResponse(
        data=ProviderConfigResponse(
            config_type="llm",
            provider_name=config.provider_name,
            model_identifier=config.model_identifier,
            endpoint_url=config.endpoint_url,
        ).model_dump()
    )


@router.put("/embedding", response_model=SuccessResponse)
async def set_embedding_provider(
    request: ProviderConfigRequest,
    db: AsyncSession = Depends(get_db),
):
    """Configure the embedding provider for document processing."""
    adapter = ProviderAdapter(db)

    # For embedding, we validate connectivity (not full completion test)
    if request.provider == "ollama":
        valid = await adapter._check_ollama_connectivity(
            request.endpoint_url or "http://host.docker.internal:11434",
            request.model,
        )
    else:
        # Try a minimal embedding call
        try:
            import litellm
            import asyncio
            model_string = f"{request.provider}/{request.model}"
            await asyncio.wait_for(
                litellm.aembedding(
                    model=model_string,
                    input=["test"],
                    api_key=request.api_key,
                ),
                timeout=10.0,
            )
            valid = True
        except Exception:
            valid = False

    if not valid:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "PROVIDER_VALIDATION_FAILED",
                "message": f"Could not validate embedding provider {request.provider}/{request.model}. "
                           "Check your API key or provider availability.",
            },
        )

    config = await adapter.set_config(
        config_type="embedding",
        provider=request.provider,
        model=request.model,
        api_key=request.api_key,
        endpoint_url=request.endpoint_url,
    )

    return SuccessResponse(
        data=ProviderConfigResponse(
            config_type="embedding",
            provider_name=config.provider_name,
            model_identifier=config.model_identifier,
            endpoint_url=config.endpoint_url,
        ).model_dump()
    )
