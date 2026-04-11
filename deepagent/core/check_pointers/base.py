from __future__ import annotations

from typing import Any, Literal

Provider = Literal["redis", "postgres"]

_PROVIDER_ALIASES: dict[str, Provider] = {
    "redis": "redis",
    "postgres": "postgres",
    "postgresql": "postgres",
    "psql": "postgres",
}


def create_checkpointer(*, provider: str, **provider_kwargs: Any) -> Any:
    """Create a checkpointer by provider.

    This is a lightweight factory scaffold. Detailed implementations for Redis
    and Postgres can be added later without changing the public API.
    """
    normalized_provider = _normalize_provider(provider)
    builder = _BUILDERS[normalized_provider]
    return builder(provider_kwargs)


def _create_redis_checkpointer(provider_kwargs: dict[str, Any]) -> Any:
    print(f"[checkpointer] redis selected, kwargs={provider_kwargs}")
    return {"provider": "redis", "status": "not_implemented"}


def _create_postgres_checkpointer(provider_kwargs: dict[str, Any]) -> Any:
    print(f"[checkpointer] postgres selected, kwargs={provider_kwargs}")
    return {"provider": "postgres", "status": "not_implemented"}


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
    "redis": _create_redis_checkpointer,
    "postgres": _create_postgres_checkpointer,
}


__all__ = ["Provider", "create_checkpointer"]
