from __future__ import annotations

import os
from typing import Any

import httpx


_TAVILY_SEARCH_URL = "https://api.tavily.com/search"
_DEFAULT_TIMEOUT_SECONDS = float(os.getenv("TAVILY_TIMEOUT_SECONDS", "15"))


def _normalize_tavily_results(raw_results: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for item in raw_results or []:
        if not isinstance(item, dict):
            continue
        results.append(
            {
                "title": item.get("title"),
                "url": item.get("url"),
                "content": item.get("content"),
                "score": item.get("score"),
                "published_date": item.get("published_date"),
            }
        )
    return results


def run_web_search(*, query: str, limit: int = 3, **_: Any) -> dict[str, Any]:
    """Search web via Tavily API; expects TAVILY_API_KEY in environment."""
    api_key = (os.getenv("TAVILY_API_KEY") or "").strip()
    q = (query or "").strip()
    top_k = max(1, min(int(limit), 10))

    if not q:
        return {
            "provider": "tavily",
            "query": q,
            "results": [],
            "error": "empty query",
        }
    if not api_key:
        return {
            "provider": "tavily",
            "query": q,
            "results": [],
            "error": "missing TAVILY_API_KEY",
        }

    payload = {
        "api_key": api_key,
        "query": q,
        "search_depth": "advanced",
        "include_answer": False,
        "include_raw_content": False,
        "max_results": top_k,
    }
    try:
        with httpx.Client(timeout=httpx.Timeout(_DEFAULT_TIMEOUT_SECONDS)) as client:
            response = client.post(_TAVILY_SEARCH_URL, json=payload)
            response.raise_for_status()
            data = response.json()
    except Exception as e:
        return {
            "provider": "tavily",
            "query": q,
            "results": [],
            "error": str(e),
        }

    results = _normalize_tavily_results(data.get("results"))
    return {
        "provider": "tavily",
        "query": q,
        "results": results,
        "answer": data.get("answer"),
        "response_time": data.get("response_time"),
    }
