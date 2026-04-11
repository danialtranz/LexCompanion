from __future__ import annotations

from typing import Any, Literal

from langchain_core.retrievers import BaseRetriever
from langchain_elasticsearch import ElasticsearchRetriever

Provider = Literal["elasticsearch"]

_PROVIDER_ALIASES: dict[str, Provider] = {
    "elasticsearch": "elasticsearch",
    "elastic": "elasticsearch",
    "es": "elasticsearch",
}


def create_retriever(
    *,
    provider: str,
    **provider_kwargs: Any,
) -> BaseRetriever:
    """Create a retriever instance and switch by provider.

    For provider='elasticsearch', this supports both self-host (`es_url`) and
    cloud (`es_cloud_id`) connection styles.
    """
    normalized_provider = _normalize_provider(provider)
    builder = _BUILDERS[normalized_provider]
    return builder(provider_kwargs)


def _create_elasticsearch_retriever(
    *,
    provider_kwargs: dict[str, Any],
) -> ElasticsearchRetriever:
    index_name = provider_kwargs.pop("index_name", None)
    body_func = provider_kwargs.pop("body_func", None)
    content_field = provider_kwargs.pop("content_field", None)
    document_mapper = provider_kwargs.pop("document_mapper", None)
    client = provider_kwargs.pop("client", None)
    es_url = provider_kwargs.pop("es_url", None)
    es_cloud_id = provider_kwargs.pop("es_cloud_id", None)
    es_user = provider_kwargs.pop("es_user", None)
    es_api_key = provider_kwargs.pop("es_api_key", None)
    es_password = provider_kwargs.pop("es_password", None)

    if index_name is None:
        raise ValueError("index_name is required for provider='elasticsearch'")
    if body_func is None:
        raise ValueError("body_func is required for provider='elasticsearch'")
    if not callable(body_func):
        raise ValueError("body_func must be callable")

    es_client = client or _build_elasticsearch_client(
        es_url=es_url,
        es_cloud_id=es_cloud_id,
        es_user=es_user,
        es_api_key=es_api_key,
        es_password=es_password,
    )

    kwargs = _compact_kwargs(
        content_field=content_field,
        document_mapper=document_mapper,
        client=es_client,
    )
    return ElasticsearchRetriever(
        index_name=index_name,
        body_func=body_func,
        **kwargs,
        **provider_kwargs,
    )


def build_elasticsearch_client(
    *,
    es_url: str | None = None,
    es_cloud_id: str | None = None,
    es_user: str | None = None,
    es_api_key: str | None = None,
    es_password: str | None = None,
) -> Any:
    """Public helper: same client as ``create_retriever`` uses (indexing, admin, bulk)."""
    return _build_elasticsearch_client(
        es_url=es_url,
        es_cloud_id=es_cloud_id,
        es_user=es_user,
        es_api_key=es_api_key,
        es_password=es_password,
    )


def _build_elasticsearch_client(
    *,
    es_url: str | None,
    es_cloud_id: str | None,
    es_user: str | None,
    es_api_key: str | None,
    es_password: str | None,
) -> Any:
    if not es_url and not es_cloud_id:
        raise ValueError("Provide either es_url (self-host) or es_cloud_id (cloud)")

    try:
        from elasticsearch import Elasticsearch
    except ImportError as exc:
        raise ImportError(
            "Missing 'elasticsearch' package. Install with: uv pip install -U elasticsearch"
        ) from exc

    if es_cloud_id:
        cloud_kwargs = _compact_kwargs(
            cloud_id=es_cloud_id,
            basic_auth=(es_user, es_password) if es_user and es_password else None,
            api_key=es_api_key,
        )
        return Elasticsearch(**cloud_kwargs)

    self_host_kwargs = _compact_kwargs(
        hosts=[es_url] if es_url else None,
        basic_auth=(es_user, es_password) if es_user and es_password else None,
        api_key=es_api_key,
    )
    return Elasticsearch(**self_host_kwargs)


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


def _compact_kwargs(**kwargs: Any) -> dict[str, Any]:
    return {key: value for key, value in kwargs.items() if value is not None}


_BUILDERS: dict[Provider, Any] = {
    "elasticsearch": _create_elasticsearch_retriever,
}


__all__ = ["Provider", "create_retriever", "build_elasticsearch_client"]
