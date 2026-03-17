"""
Configuration de la base de données MongoDB
Architecture propre avec best practices
"""
from motor.motor_asyncio import AsyncIOMotorClient
import structlog
from app.core.config.config import settings

logger = structlog.get_logger(__name__)

# ============================================================================
# CLIENT CONFIGURATION
# ============================================================================

class MongoDBClient:
    client: AsyncIOMotorClient = None

db_client = MongoDBClient()

async def connect_to_mongo():
    """Crée la connexion MongoDB globale."""
    logger.info("Connexion à MongoDB...")
    db_client.client = AsyncIOMotorClient(
        settings.MONGODB_URL,
        serverSelectionTimeoutMS=5000,
        maxPoolSize=20,
        minPoolSize=5
    )
    # Vérification rapide
    await db_client.client.admin.command('ping')
    logger.info("Connecté à MongoDB avec succès.")

async def close_mongo_connection():
    """Ferme la connexion MongoDB globale."""
    if db_client.client:
        logger.info("Fermeture de la connexion MongoDB...")
        db_client.client.close()
        logger.info("Connexion MongoDB fermée.")

# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================

async def get_db():
    """
    Dependency injection pour obtenir la base de données MongoDB.
    """
    try:
        db = db_client.client[settings.MONGODB_DB_NAME]
        yield db
    except Exception as e:
        logger.error("Erreur lors de l'accès à la DB MongoDB", error=str(e))
        raise
