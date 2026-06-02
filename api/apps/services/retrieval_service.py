"""Backward-compatible imports for retrieval service."""

from api.apps.services.retrieval import admin_retrieve_and_answer, should_end_conversation

__all__ = ["admin_retrieve_and_answer", "should_end_conversation"]
