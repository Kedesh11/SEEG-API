"""
Unit of Work Pattern (Version MongoDB).
"""
from motor.motor_asyncio import AsyncIOMotorDatabase
import structlog

logger = structlog.get_logger(__name__)

class UnitOfWork:
    """
    Pattern Unit of Work simplifié pour MongoDB.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self._committed = False
        self._rolled_back = False
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self.rollback()
            return False
        
        if not self._committed and not self._rolled_back:
            await self.commit()
        
        return False
    
    async def commit(self):
        self._committed = True
    
    async def rollback(self):
        self._rolled_back = True
    
    async def refresh(self, instance):
        """Pass - Directement géré par les dictionnaires dans MongoDB"""
        pass

class ReadOnlyUnitOfWork:
    """Unit of Work en lecture seule pour MongoDB."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False
    
    async def refresh(self, instance):
        pass
