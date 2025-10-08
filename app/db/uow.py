"""
Unit of Work Pattern - Gestion des transactions
Architecture propre respectant les principes SOLID
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

logger = structlog.get_logger(__name__)


class UnitOfWork:
    """
    Pattern Unit of Work pour gérer les transactions de manière explicite.
    
    AVANTAGES:
    - Transactions explicites et contrôlées
    - Rollback automatique en cas d'erreur
    - Support du context manager (async with)
    - Logging des transactions
    
    USAGE:
        async with UnitOfWork(db) as uow:
            # Faire des opérations
            service.create_user(...)
            # Commit automatique à la fin du context
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialise l'Unit of Work avec une session.
        
        Args:
            session: Session SQLAlchemy active
        """
        self.session = session
        self._committed = False
        self._rolled_back = False
    
    async def __aenter__(self):
        """Entre dans le context manager"""
        logger.debug("UoW: Début de transaction", session_id=id(self.session))
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Sort du context manager.
        
        - Si exception: rollback automatique
        - Sinon: commit automatique (si pas déjà fait)
        """
        if exc_type is not None:
            # Exception levée => rollback
            logger.warning(
                "UoW: Exception détectée, rollback",
                exception_type=exc_type.__name__,
                error=str(exc_val),
                session_id=id(self.session)
            )
            await self.rollback()
            return False  # Re-raise l'exception
        
        # Pas d'exception => commit si pas déjà fait
        if not self._committed and not self._rolled_back:
            logger.debug("UoW: Commit automatique", session_id=id(self.session))
            await self.commit()
        
        return False
    
    async def commit(self):
        """
        Commit explicite de la transaction.
        
        Raises:
            Exception: Si le commit échoue
        """
        if self._rolled_back:
            raise RuntimeError("Cannot commit after rollback")
        
        if self._committed:
            logger.warning("UoW: Tentative de commit multiple ignorée")
            return
        
        try:
            await self.session.commit()
            self._committed = True
            logger.info("UoW: Transaction committée avec succès", session_id=id(self.session))
        except Exception as e:
            logger.error("UoW: Erreur lors du commit", error=str(e), session_id=id(self.session))
            await self.rollback()
            raise
    
    async def rollback(self):
        """
        Rollback explicite de la transaction.
        """
        if self._rolled_back:
            logger.warning("UoW: Tentative de rollback multiple ignorée")
            return
        
        try:
            await self.session.rollback()
            self._rolled_back = True
            logger.info("UoW: Transaction annulée (rollback)", session_id=id(self.session))
        except Exception as e:
            logger.error("UoW: Erreur lors du rollback", error=str(e), session_id=id(self.session))
            raise
    
    async def refresh(self, instance):
        """
        Rafraîchit un objet depuis la base de données.
        
        Utile après un commit pour recharger les relations.
        
        Args:
            instance: Instance SQLAlchemy à rafraîchir
        """
        await self.session.refresh(instance)
    
    @property
    def is_committed(self) -> bool:
        """Retourne True si la transaction a été committée"""
        return self._committed
    
    @property
    def is_rolled_back(self) -> bool:
        """Retourne True si la transaction a été annulée"""
        return self._rolled_back


class ReadOnlyUnitOfWork:
    """
    Unit of Work en lecture seule.
    
    Ne fait JAMAIS de commit.
    Utile pour les endpoints de lecture (GET).
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def __aenter__(self):
        logger.debug("UoW (Read-Only): Début", session_id=id(self.session))
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Sort du context - ne fait RIEN (lecture seule)"""
        logger.debug("UoW (Read-Only): Fin", session_id=id(self.session))
        return False
    
    async def refresh(self, instance):
        """Rafraîchit un objet depuis la base de données"""
        await self.session.refresh(instance)

