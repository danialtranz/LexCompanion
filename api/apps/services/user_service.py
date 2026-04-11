"""Re-export UserService for middleware and modules expecting this path."""

from api.apps.services.user_2tenant_2usertenant_service import UserService

__all__ = ["UserService"]
