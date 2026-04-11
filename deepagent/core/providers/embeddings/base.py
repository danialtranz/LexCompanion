from __future__ import annotations

from typing import Any, Literal

from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings

Provider = Literal["openai", "localai"]

DEFAULT_MODELS: dict[Provider, str] = {
    "openai": "text-embedding-3-small",
    "localai": "embedding-model-name",
}

_PROVIDER_ALIASES: dict[str, Provider] = {
    "openai": "openai",
    "localai": "localai",
    "local-ai": "localai",
}


def create_embeddings(
    *,
    provider: str,
    **provider_kwargs: Any,
) -> Embeddings:
    """Create an embeddings provider instance and switch by provider."""
    normalized_provider = _normalize_provider(provider)
    builder = _BUILDERS[normalized_provider]
    return builder(provider_kwargs)


def _build_openai_embeddings(provider_kwargs: dict[str, Any]) -> Embeddings:
    api_key = _require_str(provider_kwargs, "api_key")
    model = provider_kwargs.pop("model", DEFAULT_MODELS["openai"])
    dimensions = provider_kwargs.pop("dimensions", None)
    base_url = provider_kwargs.pop("base_url", None)
    max_retrys = provider_kwargs.pop("max_retrys", None)

    common_kwargs = _compact_kwargs(
        model=model,
        dimensions=dimensions,
        max_retries=max_retrys,
    )
    openai_kwargs = _compact_kwargs(api_key=api_key, base_url=base_url)
    return OpenAIEmbeddings(**common_kwargs, **openai_kwargs, **provider_kwargs)


def _build_localai_embeddings(provider_kwargs: dict[str, Any]) -> Embeddings:
    api_key = _require_str(provider_kwargs, "api_key")
    base_url = provider_kwargs.pop("base_url", None)
    max_retrys = provider_kwargs.pop("max_retrys", None)

    common_kwargs = _compact_kwargs(
        max_retries=max_retrys,
    )
    localai_kwargs = _compact_kwargs(openai_api_key=api_key, openai_api_base=base_url)
    return _create_localai_embeddings(
        **common_kwargs,
        **localai_kwargs,
        **provider_kwargs,
    )


def _create_localai_embeddings(**kwargs: Any) -> Embeddings:
    try:
        from langchain_localai import LocalAIEmbeddings
    except ImportError as exc:
        raise ImportError(
            "langchain-localai is required for provider='localai'. "
            "Install it with: uv pip install -U langchain-localai"
        ) from exc
    return LocalAIEmbeddings(**kwargs)


def _normalize_provider(provider: str) -> Provider:
    if not provider:
        raise ValueError("provider is required")

    normalized = provider.strip().lower()
    if normalized not in _PROVIDER_ALIASES:
        supported = ", ".join(sorted(_PROVIDER_ALIASES.keys()))
        raise ValueError(
            f"Unsupported provider '{provider}'. Supported values: {supported}"
        )
    return _PROVIDER_ALIASES[normalized]


def _require_str(provider_kwargs: dict[str, Any], key: str) -> str:
    value = provider_kwargs.pop(key, None)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is required for this provider")
    return value


def _compact_kwargs(**kwargs: Any) -> dict[str, Any]:
    return {key: value for key, value in kwargs.items() if value is not None}


_BUILDERS: dict[Provider, Any] = {
    "openai": _build_openai_embeddings,
    "localai": _build_localai_embeddings,
}


__all__ = ["Provider", "DEFAULT_MODELS", "create_embeddings"]
