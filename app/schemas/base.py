"""
Schémas de base pour l'API
"""
from typing import Any, Dict, Optional, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar('T')

class ResponseSchema(BaseModel, Generic[T]):
    """Schéma de réponse de base"""
    success: bool = True
    message: str = ""
    data: Optional[T] = None
    errors: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Schéma de réponse d'erreur"""
    success: bool = False
    message: str
    errors: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None


class PaginationSchema(BaseModel):
    """Schéma de pagination"""
    page: int = 1
    per_page: int = 10
    total: int = 0
    pages: int = 0


class PaginatedResponse(ResponseSchema[T]):
    """Schéma de réponse paginée"""
    pagination: Optional[PaginationSchema] = None
