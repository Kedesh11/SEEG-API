"""
Gestion des sessions de base de données.
Respecte le principe de responsabilité unique (Single Responsibility Principle).
"""

from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator

from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import SessionLocal, AsyncSessionLocal
import structlog

logger = structlog.get_logger(__name__)


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Contexte manager pour une session de base de données synchrone.
    
    Yields:
        Session: Session SQLAlchemy
        
    Raises:
        Exception: En cas d'erreur, la session est rollback
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error("Database session error", error=str(e))
        db.rollback()
        raise
    finally:
        db.close()


@asynccontextmanager
async def get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Contexte manager pour une session de base de données asynchrone.
    
    Yields:
        AsyncSession: Session SQLAlchemy asynchrone
        
    Raises:
        Exception: En cas d'erreur, la session est rollback
    """
    db = AsyncSessionLocal()
    try:
        yield db
        await db.commit()
    except Exception as e:
        logger.error("Async database session error", error=str(e))
        await db.rollback()
        raise
    finally:
        await db.close()


class DatabaseManager:
    """
    Gestionnaire de base de données pour les transactions complexes.
    Respecte le principe de responsabilité unique.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def begin_transaction(self):
        """Débuter une transaction"""
        await self.session.begin()
    
    async def commit_transaction(self):
        """Valider une transaction"""
        await self.session.commit()
    
    async def rollback_transaction(self):
        """Annuler une transaction"""
        await self.session.rollback()
    
    async def __aenter__(self):
        await self.begin_transaction()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self.rollback_transaction()
        else:
            await self.commit_transaction()


# Fonction pour obtenir une session asynchrone (pour les tests)
async def get_async_session():
    """Générateur pour obtenir une session asynchrone"""
    async with AsyncSessionLocal() as session:
        yield session
