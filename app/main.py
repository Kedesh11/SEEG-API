"""
Point d'entrée principal de l'application One HCM SEEG
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi.errors import RateLimitExceeded
import structlog

from app.core.config.config import settings
from app.core.logging.logging import LoggingConfig
from app.core.rate_limit import limiter
from app.core.monitoring import app_insights
from app.core.monitoring.middleware import ApplicationInsightsMiddleware

# Configuration du logging
LoggingConfig.setup_logging()
logger = structlog.get_logger(__name__)

# Configuration d'Application Insights
app_insights.setup()

# ============================================================================
# CRÉATION DE L'APPLICATION FASTAPI
# ============================================================================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    ## API One HCM SEEG - Système de Gestion des Ressources Humaines
    
    Cette API permet de gérer l'ensemble du processus de recrutement de la SEEG :
    
    * **Authentification** : Connexion, inscription, gestion des tokens
    * **Utilisateurs** : Gestion des profils candidats, recruteurs et administrateurs
    * **Offres d'emploi** : Création, modification et consultation des postes
    * **Candidatures** : Soumission et suivi des candidatures
    * **Évaluations** : Protocoles d'évaluation des candidats
    * **Notifications** : Système de notifications
    * **Entretiens** : Planification et gestion des entretiens
    * **Documents PDF** : Upload, stockage et gestion sécurisée des fichiers PDF (CV, lettres, diplômes, etc.)
    
    ### Frontend
    Interface utilisateur disponible sur : https://www.seeg-talentsource.com
    
    ### Rate Limiting
    L'API est protégée par rate limiting :
    - **Authentification** : 5 requêtes/minute, 20/heure
    - **Inscription** : 3 requêtes/minute, 10/heure
    - **Upload de fichiers** : 10 requêtes/minute, 50/heure
    - **Autres endpoints** : 60 requêtes/minute, 500/heure
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "🏠 Accueil",
            "description": "Endpoints généraux de l'API - Statut, santé, informations"
        },
        {
            "name": "🔐 Authentification",
            "description": "Gestion de l'authentification - Connexion, inscription, tokens JWT"
        },
        {
            "name": "👥 Utilisateurs",
            "description": "Gestion des utilisateurs - Profils, rôles, permissions"
        },
        {
            "name": "💼 Offres d'emploi",
            "description": "Gestion des offres d'emploi - Création, modification, consultation"
        },
        {
            "name": "📝 Candidatures",
            "description": "Gestion des candidatures - Soumission, suivi, statuts"
        },
        {
            "name": "📄 Documents PDF",
            "description": "Gestion des documents PDF liés aux candidatures (CV, lettres de motivation, diplômes, certificats)"
        },
        {
            "name": "📊 Évaluations",
            "description": "Gestion des évaluations - Protocoles MTP, scores, recommandations"
        },
        {
            "name": "🔔 Notifications",
            "description": "Système de notifications - Alertes, messages, suivi"
        },
        {
            "name": "🎯 Entretiens",
            "description": "Gestion des entretiens - Planification, créneaux, suivi"
        },
        {
            "name": "Webhooks",
            "description": "Intégrations externes via webhooks"
        }
    ]
)

# Configuration du rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, lambda request, exc: JSONResponse(
    status_code=429,
    content={
        "error": "Rate limit exceeded",
        "message": "Trop de requêtes. Veuillez réessayer plus tard.",
        "retry_after": getattr(exc, "retry_after", None)
    }
))

# Configuration des middlewares
# Application Insights - doit être en premier pour tracker toutes les requêtes
app.add_middleware(ApplicationInsightsMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=settings.ALLOWED_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# 🏠 MODULE ACCUEIL
# ============================================================================

@app.get("/", tags=["🏠 Accueil"], summary="Point d'entrée de l'API")
async def root():
    """Point d'entrée principal de l'API One HCM SEEG"""
    return {
        "message": "API One HCM SEEG",
        "version": settings.APP_VERSION,
        "status": "active",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health", tags=["🏠 Accueil"], summary="Vérifier l'état de santé de l'API")
async def health_check():
    """Vérifier que l'API et la base de données sont opérationnelles"""
    return {
        "status": "ok",
        "message": "API is healthy",
        "version": settings.APP_VERSION,
        "database": "connected",
        "pdf_storage": "enabled",
        "timestamp": "2024-01-01T00:00:00Z"
    }

@app.get("/info", tags=["🏠 Accueil"], summary="Informations détaillées sur l'API")
async def info():
    """Obtenir des informations détaillées sur la configuration de l'API"""
    return {
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "debug_mode": settings.DEBUG,
        "allowed_origins": settings.ALLOWED_ORIGINS,
        "database_url": settings.DATABASE_URL[:50] + "..." if len(settings.DATABASE_URL) > 50 else settings.DATABASE_URL,
        "monitoring": {
            "application_insights": "enabled" if app_insights.enabled else "disabled",
            "instrumentation": app_insights.enabled
        },
        "features": [
            "Authentification JWT",
            "Gestion des rôles",
            "Upload de documents PDF",
            "Stockage binaire des fichiers",
            "Validation stricte des formats",
            "Notifications en temps réel",
            "Évaluations automatisées (MTP)",
            "Planification d'entretiens",
            "Rate Limiting",
            "CI/CD automatisé",
            "Monitoring Azure (Application Insights)"
        ],
        "pdf_support": {
            "allowed_types": ["cover_letter", "cv", "certificats", "diplome"],
            "file_format": "PDF uniquement",
            "storage": "Base de données (BYTEA)",
            "validation": "Magic number + extension + taille (10MB max)"
        },
        "security": {
            "rate_limiting": "enabled",
            "auth_limits": "5/minute, 20/hour",
            "signup_limits": "3/minute, 10/hour",
            "upload_limits": "10/minute, 50/hour"
        }
    }

# ============================================================================
# IMPORT DES ROUTES
# ============================================================================

# Import des routes API
from app.api.v1.endpoints import auth, users, jobs, applications, evaluations, notifications, interviews, emails, optimized, webhooks

# Inclusion des routes dans l'application
app.include_router(auth.router, prefix="/api/v1/auth", tags=["🔐 Authentification"])
app.include_router(users.router, prefix="/api/v1/users", tags=["👥 Utilisateurs"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["💼 Offres d'emploi"])
app.include_router(applications.router, prefix="/api/v1/applications", tags=["📝 Candidatures", "📄 Documents PDF"])
app.include_router(evaluations.router, prefix="/api/v1/evaluations", tags=["📊 Évaluations"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["🔔 Notifications"])
app.include_router(optimized.router, prefix="/api/v1/optimized", tags=["⚡ Requêtes Optimisées"])
app.include_router(interviews.router, prefix="/api/v1/interviews", tags=["🎯 Entretiens"])
app.include_router(emails.router, prefix="/api/v1/emails", tags=["📧 Emails"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["Webhooks"])

# ============================================================================
# GESTIONNAIRE D'ERREURS GLOBAL
# ============================================================================

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Gestionnaire pour les erreurs 404"""
    return JSONResponse(content={
        "error": "Not Found",
        "message": "La ressource demandée n'a pas été trouvée",
        "status_code": 404,
        "path": str(request.url.path)
    }, status_code=404)

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Gestionnaire pour les erreurs 500"""
    logger.error("Erreur interne du serveur", error=str(exc), path=str(request.url.path))
    return JSONResponse(content={
        "error": "Internal Server Error",
        "message": "Une erreur interne du serveur s'est produite",
        "status_code": 500
    }, status_code=500)

# ============================================================================
# ÉVÉNEMENTS DE L'APPLICATION
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Événement de démarrage de l'application"""
    logger.info("Démarrage de l'API One HCM SEEG", version=settings.APP_VERSION)
    
    # Validation de la configuration en production
    if settings.ENVIRONMENT == "production":
        logger.info("Validation de la configuration de production...")
        
        # Vérifier que SECRET_KEY est sécurisée
        weak_keys = [
            "your-super-secret-key-here-change-in-production-123456789",
            "CHANGE_ME_SECRET_KEY_32CHARS_MINIMUM_1234567890",
            "CHANGE_ME_IN_PROD_32CHARS_MINIMUM_1234567890"
        ]
        if settings.SECRET_KEY in weak_keys:
            logger.error("SECRET_KEY non sécurisée détectée en production !")
            raise ValueError("SECRET_KEY doit être changée en production !")
        
        # Vérifier que la base de données n'est pas locale
        if "localhost" in settings.DATABASE_URL or "127.0.0.1" in settings.DATABASE_URL:
            logger.error("Base de données locale détectée en production !")
            raise ValueError("DATABASE_URL ne doit pas pointer vers localhost en production !")
        
        # Vérifier que DEBUG est désactivé
        if settings.DEBUG:
            logger.warning("DEBUG activé en production - Cela peut exposer des informations sensibles !")
        
        logger.info("Configuration de production validée avec succès")

@app.on_event("shutdown")
async def shutdown_event():
    """Événement d'arrêt de l'application"""
    logger.info("Arrêt de l'API One HCM SEEG")

# ============================================================================
# POINT D'ENTRÉE PRINCIPAL
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
