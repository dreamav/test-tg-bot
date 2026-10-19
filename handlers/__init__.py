"""Пакет хэндлеров."""

from handlers.admin import router as admin_router
from handlers.menu import router as menu_router
from handlers.user import router as user_router

__all__ = ["menu_router", "user_router", "admin_router"]
