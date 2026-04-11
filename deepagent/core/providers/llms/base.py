from __future__ import annotations

from typing import Any, Literal

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

Provider = Literal["openai", "anthropic"]

DEFAULT_MODELS: dict[Provider, str] = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-haiku-latest",
}

_PROVIDER_ALIASES: dict[str, Provider] = {
    "openai": "openai",
    "anthropic": "anthropic",
    "claude": "anthropic",
}


def create_chat_model(
    *,
    provider: str,
    **provider_kwargs: Any,
) -> BaseChatModel:
    """Create a LangChain chat model and switch by provider."""
    normalized_provider = _normalize_provider(provider)
    builder = _BUILDERS[normalized_provider]
    return builder(provider_kwargs)


def _build_openai_chat_model(provider_kwargs: dict[str, Any]) -> BaseChatModel:
    api_key = _require_str(provider_kwargs, "api_key")
    model = provider_kwargs.pop("model", DEFAULT_MODELS["openai"])
    temperature = provider_kwargs.pop("temperature", None)
    max_tokens = provider_kwargs.pop("max_tokens", None)
    timeout = provider_kwargs.pop("timeout", None)
    base_url = provider_kwargs.pop("base_url", None)

    common_kwargs = _compact_kwargs(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )
    openai_kwargs = _compact_kwargs(api_key=api_key, base_url=base_url)
    return ChatOpenAI(**common_kwargs, **openai_kwargs, **provider_kwargs)


def _build_anthropic_chat_model(provider_kwargs: dict[str, Any]) -> BaseChatModel:
    api_key = _require_str(provider_kwargs, "api_key")
    model = provider_kwargs.pop("model", DEFAULT_MODELS["anthropic"])
    temperature = provider_kwargs.pop("temperature", None)
    max_tokens = provider_kwargs.pop("max_tokens", None)
    timeout = provider_kwargs.pop("timeout", None)

    common_kwargs = _compact_kwargs(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )
    anthropic_kwargs = _compact_kwargs(api_key=api_key)
    return ChatAnthropic(**common_kwargs, **anthropic_kwargs, **provider_kwargs)


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
    "openai": _build_openai_chat_model,
    "anthropic": _build_anthropic_chat_model,
}


__all__ = ["Provider", "create_chat_model", "DEFAULT_MODELS"]
