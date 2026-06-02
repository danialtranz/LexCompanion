from __future__ import annotations

from typing import Any

from api.utils.elastic_chunk_index import hit_to_api_chunk


def format_ieee_citation(index: int, chunk: dict[str, Any]) -> str:
    """Một dòng tham chiếu kiểu IEEE numbered [n]."""
    doc_title = chunk.get("doc_title")
    if doc_title and str(doc_title).strip():
        doc_type = chunk.get("doc_type")
        suffix = f" ({doc_type})" if doc_type and str(doc_type).strip() else ""
        return f"[{index}] {str(doc_title).strip()}{suffix}, tài liệu người dùng tải lên"

    segments: list[str] = []
    for key in ("topic_title", "subject_title", "article_title", "chapter_title"):
        value = chunk.get(key)
        if value and str(value).strip():
            segments.append(str(value).strip())
    title = ", ".join(segments) if segments else "Văn bản pháp luật"
    link = chunk.get("source_link")
    if link and str(link).strip():
        return f"[{index}] {title}, {str(link).strip()}"
    return f"[{index}] {title}"


def build_references(
    reranked_hits: list[dict[str, Any]],
    cited_indexes: list[int],
) -> list[dict[str, Any]]:
    references: list[dict[str, Any]] = []
    max_index = len(reranked_hits)
    for index in cited_indexes:
        if index < 1 or index > max_index:
            continue
        chunk = hit_to_api_chunk(reranked_hits[index - 1], include_rerank=True)
        ref = {
            "index": index,
            "ieee": format_ieee_citation(index, chunk),
            **chunk,
        }
        references.append(ref)
    return references
