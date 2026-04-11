from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import torch
from sentence_transformers import SentenceTransformer


MODEL_NAME = "AITeamVN/Vietnamese_Embedding_v2"


@dataclass(frozen=True)
class LoadedEmbeddingModel:
    model: SentenceTransformer
    device: str
    model_name: str


_LOADED: Optional[LoadedEmbeddingModel] = None


def _select_device() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"


def load_model() -> LoadedEmbeddingModel:
    """Load the embedding model once and keep it in-memory."""
    global _LOADED
    if _LOADED is not None:
        return _LOADED

    device = _select_device()
    print(f"Loading model on {device}")
    model = SentenceTransformer(MODEL_NAME)
    model = model.to(device)

    _LOADED = LoadedEmbeddingModel(model=model, device=device, model_name=MODEL_NAME)
    return _LOADED


def get_loaded_model() -> LoadedEmbeddingModel:
    """Return a cached model instance (loads it if needed)."""
    return load_model()


def is_model_loaded() -> bool:
    return _LOADED is not None


def unload_model() -> None:
    """Best-effort cleanup for graceful shutdown."""
    global _LOADED
    _LOADED = None
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


__all__ = [
    "MODEL_NAME",
    "LoadedEmbeddingModel",
    "load_model",
    "get_loaded_model",
    "is_model_loaded",
    "unload_model",
]
