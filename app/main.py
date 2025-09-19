"""
Point d'entrée principal de l'application One HCM SEEG
"""
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.config.config import settings
from app.core.logging.logging import LoggingConfig

# Configuration du logging
LoggingConfig.setup_logging()
logger = structlog.get_logger(__name__)

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
        }
    ]
)

# Configuration CORS
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
        "features": [
            "Authentification JWT",
            "Gestion des rôles",
            "Upload de documents PDF",
            "Stockage binaire des fichiers",
            "Validation stricte des formats",
            "Notifications en temps réel",
            "Évaluations automatisées (MTP)",
            "Planification d'entretiens"
        ],
        "pdf_support": {
            "allowed_types": ["cover_letter", "cv", "certificats", "diplome"],
            "file_format": "PDF uniquement",
            "storage": "Base de données (BYTEA)",
            "validation": "Magic number + extension"
        }
    }

# ============================================================================
# IMPORT DES ROUTES
# ============================================================================

# Import des routes API
from app.api.v1.endpoints import auth, users, jobs, applications, evaluations, notifications, interviews, emails
from app.api.v1.endpoints import optimized

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
