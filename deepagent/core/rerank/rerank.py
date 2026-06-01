"""Rerank Elasticsearch lex_chunks hits with BAAI/bge-reranker-v2-m3 (FlagEmbedding)."""

from __future__ import annotations

import os
from copy import deepcopy
from typing import Any, Mapping, Sequence

from api.utils.logger import setup_logging

logger = setup_logging()

_DEFAULT_MODEL = "BAAI/bge-reranker-v2-m3"

_INSTANCE: "BgeM3Reranker | None" = None


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _scores_to_list(raw_scores: Any) -> list[float]:
    if raw_scores is None:
        return []
    if hasattr(raw_scores, "tolist"):
        raw_scores = raw_scores.tolist()
    if isinstance(raw_scores, (int, float)):
        return [float(raw_scores)]
    return [float(s) for s in raw_scores]


class BgeM3Reranker:
    """Rerank search hits using ``FlagReranker`` (cross-encoder)."""

    def __init__(
        self,
        *,
        model_name: str = _DEFAULT_MODEL,
        use_fp16: bool = True,
        batch_size: int = 32,
        max_query_length: int = 512,
        max_length: int = 512,
        normalize: bool = False,
        device: str | None = None,
    ) -> None:
        from FlagEmbedding import FlagReranker

        logger.info(
            "Loading reranker model={} use_fp16={} device={}",
            model_name,
            use_fp16,
            device or "auto",
        )
        kwargs: dict[str, Any] = {
            "use_fp16": use_fp16,
            "batch_size": batch_size,
            "query_max_length": max_query_length,
            "max_length": max_length,
            "normalize": normalize,
        }
        if device:
            kwargs["devices"] = device
        self.model = FlagReranker(model_name, **kwargs)
        self.model_name = model_name
        self.batch_size = batch_size
        self.max_query_length = max_query_length
        self.max_length = max_length
        self.normalize = normalize
        logger.info("Reranker model loaded: {}", model_name)

    @classmethod
    def init(
        cls,
        *,
        model_name: str | None = None,
        use_fp16: bool | None = None,
        batch_size: int | None = None,
        max_query_length: int | None = None,
        max_length: int | None = None,
        normalize: bool | None = None,
        device: str | None = None,
        force: bool = False,
    ) -> "BgeM3Reranker":
        """Load singleton reranker (idempotent unless ``force=True``)."""
        global _INSTANCE
        if _INSTANCE is not None and not force:
            return _INSTANCE

        _INSTANCE = cls(
            model_name=model_name or os.getenv("RERANK_MODEL_NAME", _DEFAULT_MODEL),
            use_fp16=use_fp16
            if use_fp16 is not None
            else _env_bool("RERANK_USE_FP16", True),
            batch_size=batch_size
            or max(1, int(os.getenv("RERANK_BATCH_SIZE", "32"))),
            max_query_length=max_query_length
            or max(32, int(os.getenv("RERANK_MAX_QUERY_LENGTH", "512"))),
            max_length=max_length
            or max(
                32,
                int(
                    os.getenv(
                        "RERANK_MAX_LENGTH",
                        os.getenv("RERANK_MAX_PASSAGE_LENGTH", "512"),
                    )
                ),
            ),
            normalize=normalize
            if normalize is not None
            else _env_bool("RERANK_NORMALIZE", False),
            device=device or os.getenv("RERANK_DEVICE") or None,
        )
        return _INSTANCE

    @staticmethod
    def _unwrap_source(chunk: Any) -> Mapping[str, Any]:
        if isinstance(chunk, Mapping):
            source = chunk.get("_source")
            if isinstance(source, Mapping):
                return source
            return chunk
        metadata = getattr(chunk, "metadata", None)
        if isinstance(metadata, Mapping):
            return metadata
        page_content = getattr(chunk, "page_content", None)
        if page_content is not None:
            return {"content_text": str(page_content)}
        return {}

    @classmethod
    def passage_text(
        cls,
        chunk: Any,
        *,
        text_field: str = "content_text",
        include_titles: bool = True,
    ) -> str:
        """Build passage string for scoring (titles + body)."""
        source = cls._unwrap_source(chunk)
        parts: list[str] = []
        if include_titles:
            for key in ("article_title", "chapter_title", "subject_title", "topic_title"):
                value = source.get(key)
                if value and str(value).strip():
                    parts.append(str(value).strip())
        body = source.get(text_field) or source.get("page_content") or ""
        if str(body).strip():
            parts.append(str(body).strip())
        return "\n".join(parts).strip()

    @staticmethod
    def _attach_score(chunk: Any, score: float) -> Any:
        if isinstance(chunk, Mapping):
            out = deepcopy(chunk) if hasattr(chunk, "copy") else dict(chunk)
            if isinstance(out.get("_source"), Mapping):
                out["_source"] = {**out["_source"], "rerank_score": score}
            else:
                out["rerank_score"] = score
            return out

        metadata = getattr(chunk, "metadata", None)
        if isinstance(metadata, dict):
            metadata["rerank_score"] = score
        elif metadata is not None and hasattr(metadata, "__setitem__"):
            try:
                metadata["rerank_score"] = score  # type: ignore[index]
            except Exception:
                pass
        setattr(chunk, "rerank_score", score)
        return chunk

    def rerank(
        self,
        query: str,
        chunks: Sequence[Any],
        *,
        top_k: int = 5,
        text_field: str = "content_text",
        include_titles: bool = True,
    ) -> list[Any]:
        """
        Rerank ES/LangChain chunks and return top ``top_k`` by relevance score.

        Each returned item includes ``rerank_score`` (in ``_source`` or root dict).
        """
        if not chunks:
            return []
        if not (query or "").strip():
            return list(chunks)[:top_k]

        indexed = list(enumerate(chunks))
        pairs: list[tuple[str, str]] = []
        for _, chunk in indexed:
            passage = self.passage_text(
                chunk,
                text_field=text_field,
                include_titles=include_titles,
            )
            pairs.append((query.strip(), passage or "."))

        raw_scores = self.model.compute_score(
            pairs,
            batch_size=self.batch_size,
            query_max_length=self.max_query_length,
            max_length=self.max_length,
            normalize=self.normalize,
        )
        scores = _scores_to_list(raw_scores)

        if len(scores) != len(indexed):
            raise RuntimeError(
                f"Rerank score count mismatch: {len(scores)} != {len(indexed)}"
            )

        ranked: list[tuple[float, int, Any]] = []
        for (index, chunk), score in zip(indexed, scores):
            ranked.append((float(score), index, self._attach_score(chunk, float(score))))

        ranked.sort(key=lambda item: (-item[0], item[1]))
        limit = max(0, top_k)
        return [item[2] for item in ranked[:limit]]


def get_reranker() -> BgeM3Reranker:
    """Return initialized singleton reranker."""
    if _INSTANCE is None:
        raise RuntimeError(
            "BgeM3Reranker is not initialized. Call init_reranker() during app startup."
        )
    return _INSTANCE


def init_reranker(**kwargs: Any) -> BgeM3Reranker:
    """Initialize global reranker instance."""
    return BgeM3Reranker.init(**kwargs)


def is_reranker_ready() -> bool:
    return _INSTANCE is not None
