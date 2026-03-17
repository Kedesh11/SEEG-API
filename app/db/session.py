"""
Gestion des sessions de base de données (Version MongoDB).
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.database import get_db
import structlog

logger = structlog.get_logger(__name__)

@asynccontextmanager
async def get_async_db_session() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """
    Contexte manager pour une session de base de données MongoDB.
    
    Yields:
        AsyncIOMotorDatabase: Base de données MongoDB
    """
    async for db in get_db():
        yield db

class DatabaseManager:
    """
    Gestionnaire de base de données pour MongoDB.
    Note: Les transactions MongoDB nécessitent un cluster réplica set.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.session = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

# Fonction legacy pour compatibilité
async def get_async_session():
    async for db in get_db():
        yield db
