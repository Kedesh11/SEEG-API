"""
Configuration de la base de données
Architecture propre avec best practices
"""
from typing import AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session
from app.core.config.config import settings
import structlog

logger = structlog.get_logger(__name__)

# ============================================================================
# ENGINES CONFIGURATION
# ============================================================================

# Moteur synchrone
engine = create_engine(
    settings.DATABASE_URL_SYNC,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.DEBUG
)

# Moteur asynchrone avec configuration robuste pour éviter les déconnexions
async_engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Vérifie la connexion avant utilisation
    pool_recycle=300,  # Recycle les connexions après 5 minutes
    pool_size=10,  # Nombre de connexions dans le pool
    max_overflow=20,  # Connexions supplémentaires autorisées
    pool_timeout=30,  # Timeout pour obtenir une connexion
    echo=settings.DEBUG,
    connect_args={
        "server_settings": {"jit": "off"},  # Désactive JIT pour stabilité
        "command_timeout": 60,  # Timeout des commandes SQL
        "timeout": 10  # Timeout de connexion
    }
)

# ============================================================================
# SESSION FACTORIES
# ============================================================================

# Session factory synchrone
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Session factory asynchrone
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False  # Important: permet l'accès aux objets après commit
)

# ============================================================================
# DEPENDENCY INJECTION - SUIVANT LES BEST PRACTICES
# ============================================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency injection pour obtenir une session de base de données asynchrone.
    
    ARCHITECTURE PROPRE:
    - Crée une session
    - Yield la session (disponible dans l'endpoint)
    - En cas d'erreur: rollback automatique
    - En fin: fermeture propre de la session
    
    IMPORTANT:
    - Ne fait PAS de commit automatique
    - L'endpoint décide quand committer
    - Garantit le rollback en cas d'exception
    
    Usage:
        @router.post("/endpoint")
        async def my_endpoint(db: AsyncSession = Depends(get_db)):
            # Utiliser db
            await db.commit()  # Commit explicite par l'endpoint
    
    Yields:
        AsyncSession: Session de base de données active
    """
    session = AsyncSessionLocal()
    try:
        logger.debug("Session DB créée", session_id=id(session))
        yield session
        
    except Exception as e:
        # Rollback automatique en cas d'erreur
        logger.error("Erreur dans la session DB, rollback", error=str(e), session_id=id(session))
        await session.rollback()
        raise
        
    finally:
        # Fermeture propre de la session
        logger.debug("Session DB fermée", session_id=id(session))
        await session.close()


def get_db_sync() -> Session:
    """
    Dependency injection pour obtenir une session synchrone.
    
    Usage pour scripts/migrations synchrones uniquement.
    Les endpoints doivent utiliser get_db() (async).
    
    Yields:
        Session: Session synchrone
    """
    session = SessionLocal()
    try:
        yield session
    except Exception as e:
        logger.error("Erreur dans la session DB synchrone, rollback", error=str(e))
        session.rollback()
        raise
    finally:
        session.close()
