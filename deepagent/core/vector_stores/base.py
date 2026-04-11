from __future__ import annotations

from typing import Any, Literal

Provider = Literal["chroma", "elasticsearch"]

_PROVIDER_ALIASES: dict[str, Provider] = {
    "chroma": "chroma",
    "es": "elasticsearch",
}


def create_vector_store(*, provider: str, **provider_kwargs: Any) -> Any:
    """Create a vector store instance by provider.

    This is a lightweight factory scaffold. Concrete implementations can be
    added later without changing the public API.
    """
    normalized_provider = _normalize_provider(provider)
    builder = _BUILDERS[normalized_provider]
    return builder(provider_kwargs)


def create_chroma_vector_store(provider_kwargs: dict[str, Any]) -> Any:
    print(f"[vector_store] chroma selected, kwargs={provider_kwargs}")
    return {"provider": "chroma", "status": "not_implemented"}

def create_elasticsearch_vector_store(provider_kwargs: dict[str, Any]) -> Any:
    print(f"[vector_store] elasticsearch selected, kwargs={provider_kwargs}")
    return {"provider": "elasticsearch", "status": "not_implemented"}

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


_BUILDERS: dict[Provider, Any] = {
    "chroma": create_chroma_vector_store,
    "elasticsearch": create_elasticsearch_vector_store,
}


__all__ = ["Provider", "create_vector_store", "create_chroma_vector_store", "create_elasticsearch_vector_store"]
