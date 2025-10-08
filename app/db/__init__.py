"""
Configuration de la base de données.
Respecte le principe de séparation des préoccupations.
"""

from .database import get_db, get_db_sync, engine, async_engine
from .session import SessionLocal, AsyncSessionLocal

__all__ = [
    "get_db",
    "get_db_sync",
    "engine",
    "async_engine",
    "SessionLocal",
    "AsyncSessionLocal",
]
