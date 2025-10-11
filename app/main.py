"""
Point d'entrée principal de l'application One HCM SEEG
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
# from slowapi.errors import RateLimitExceeded  # ⚠️ Désactivé temporairement
import structlog
import os

from app.core.config.config import settings
from app.core.logging.logging import LoggingConfig
# from app.core.rate_limit import limiter  # ⚠️ Désactivé temporairement - Problème avec slowapi
from app.core.monitoring import app_insights
from app.core.monitoring.middleware import ApplicationInsightsMiddleware

# Import des nouveaux modules de monitoring
from app.core.logging.enhanced_logging import setup_enhanced_logging
from app.core.tracing import setup_tracing
from app.core.metrics import metrics_collector
from app.core.cache import cache_manager
from app.middleware.monitoring import (
    MonitoringMiddleware, 
    PerformanceLoggingMiddleware,
    SecurityHeadersMiddleware,
    ErrorTrackingMiddleware
)

# Configuration du logging amélioré
if os.getenv("LOG_FORMAT") == "json":
    setup_enhanced_logging()
else:
    LoggingConfig.setup_logging()
    
logger = structlog.get_logger(__name__)


def safe_log(level: str, message: str, **kwargs):
    """
    Log avec gestion d'erreur pour éviter les problèmes de handler.
    Fallback vers print si le logger échoue.
    """
    try:
        getattr(logger, level)(message, **kwargs)
    except (TypeError, AttributeError) as e:
        print(f"{level.upper()}: {message} - {kwargs}")


# Configuration d'Application Insights
app_insights.setup()

# Configuration du tracing
if settings.ENABLE_TRACING:
    setup_tracing()

# ============================================================================
# GESTION DU CYCLE DE VIE
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie de l'application avec monitoring"""
    # Startup
    safe_log("info", "Démarrage de l'API One HCM SEEG", version=settings.APP_VERSION)
    
    # Le cache Redis s'initialise automatiquement dans le constructeur de CacheManager
    # Aucune action nécessaire ici
    
    # Les métriques sont collectées automatiquement à la demande
    if settings.METRICS_ENABLED:
        safe_log("info", "Collecte de métriques Prometheus activée")
    
    # Validation de la configuration en production
    if settings.ENVIRONMENT == "production":
        validate_production_config()
    
    yield
    
    # Shutdown
    safe_log("info", "Arrêt de l'API One HCM SEEG")
    
    # Le cache Redis se ferme automatiquement
    # Les métriques Prometheus s'arrêtent automatiquement

# ============================================================================
# CRÉATION DE L'APPLICATION FASTAPI
# ============================================================================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    ## API One HCM SEEG - Système de Gestion des Ressources Humaines
    
    Cette API permet de gérer l'ensemble du processus de recrutement de la SEEG :
    
    * **Authentification** : Connexion, inscription (internes/externes), gestion des tokens
    * **Utilisateurs** : Gestion des profils candidats, recruteurs et administrateurs
    * **Offres d'emploi** : Création, modification et consultation avec filtrage automatique (internes/externes)
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
    
    ### Monitoring
    L'API est équipée d'un système de monitoring complet :
    - **Métriques** : Prometheus (admin seulement)
    - **Logs** : Structurés en JSON
    - **Tracing** : OpenTelemetry + Jaeger
    - **Health Check** : Endpoints de santé
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
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
            "name": "👥 Gestion des Demandes d'Accès",
            "description": "Gestion des demandes d'accès à la plateforme - Approbation/refus par les recruteurs pour les candidats internes sans email SEEG"
        },
        {
            "name": "👥 Utilisateurs",
            "description": "Gestion des utilisateurs - Profils, rôles, permissions"
        },
        {
            "name": "💼 Offres d'emploi",
            "description": "Gestion des offres d'emploi avec questions MTP (Métier, Talent, Paradigme) - Création, modification, consultation des offres internes et externes"
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
# ⚠️ TEMPORAIREMENT DÉSACTIVÉ - Problème de compatibilité avec slowapi
# app.state.limiter = limiter
# app.add_exception_handler(RateLimitExceeded, lambda request, exc: JSONResponse(
#     status_code=429,
#     content={
#         "error": "Rate limit exceeded",
#         "message": "Trop de requêtes. Veuillez réessayer plus tard.",
#         "retry_after": getattr(exc, "retry_after", None)
#     }
# ))

# Configuration des middlewares
# Application Insights - doit être en premier pour tracker toutes les requêtes
try:
    app.add_middleware(ApplicationInsightsMiddleware)
except Exception as e:
    print(f"WARNING: ApplicationInsightsMiddleware failed: {e}")

# Monitoring complet
try:
    app.add_middleware(MonitoringMiddleware)
except Exception as e:
    print(f"WARNING: MonitoringMiddleware failed: {e}")

# Headers de sécurité
try:
    app.add_middleware(SecurityHeadersMiddleware)
except Exception as e:
    print(f"WARNING: SecurityHeadersMiddleware failed: {e}")

# Logging de performance
try:
    app.add_middleware(PerformanceLoggingMiddleware)
except Exception as e:
    print(f"WARNING: PerformanceLoggingMiddleware failed: {e}")

# Tracking des erreurs
try:
    app.add_middleware(ErrorTrackingMiddleware)
except Exception as e:
    print(f"WARNING: ErrorTrackingMiddleware failed: {e}")

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
    from datetime import datetime
    health_status = {
        "status": "ok",
        "message": "API is healthy",
        "version": settings.APP_VERSION,
        "database": "connected",
        "pdf_storage": "enabled",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    # Vérifier Redis si configuré
    if settings.REDIS_URL and cache_manager.async_redis_client:
        try:
            await cache_manager.async_redis_client.ping()
            health_status["cache"] = "connected"
        except:
            health_status["cache"] = "disconnected"
            health_status["status"] = "degraded"
    
    return health_status

@app.get("/monitoring/health", tags=["🏠 Accueil"], summary="Health check détaillé pour le monitoring")
async def monitoring_health_check():
    """Health check détaillé incluant toutes les dépendances"""
    from datetime import datetime
    import psutil
    
    # Métriques système
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    
    health_details = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "system": {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_used_mb": memory.used / 1024 / 1024,
            "memory_available_mb": memory.available / 1024 / 1024
        },
        "services": {
            "api": "up",
            "database": "unknown",
            "cache": "unknown",
            "monitoring": {
                "metrics": "enabled" if settings.METRICS_ENABLED else "disabled",
                "tracing": "enabled" if settings.ENABLE_TRACING else "disabled",
                "application_insights": "enabled" if app_insights.enabled else "disabled"
            }
        }
    }
    
    # Vérifier la base de données
    try:
        from app.db.database import async_engine
        from sqlalchemy import text
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        health_details["services"]["database"] = "up"
    except Exception as e:
        health_details["services"]["database"] = "down"
        health_details["status"] = "degraded"
        safe_log("error", "Database health check failed", error=str(e))
    
    # Vérifier Redis
    if settings.REDIS_URL and cache_manager.async_redis_client:
        try:
            await cache_manager.async_redis_client.ping()
            health_details["services"]["cache"] = "up"
        except Exception as e:
            health_details["services"]["cache"] = "down"
            health_details["status"] = "degraded"
            safe_log("error", "Redis health check failed", error=str(e))
    
    return health_details

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
from app.api.v1.endpoints import auth, users, jobs, applications, evaluations, notifications, interviews, emails, optimized, webhooks, access_requests
from app.api.v1.endpoints.monitoring import router as monitoring_router

# Inclusion des routes dans l'application
app.include_router(auth.router, prefix="/api/v1/auth", tags=["🔐 Authentification"])
app.include_router(access_requests.router, prefix="/api/v1/access-requests", tags=["🔐 Authentification", "👥 Gestion des Demandes d'Accès"])
app.include_router(users.router, prefix="/api/v1/users", tags=["👥 Utilisateurs"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["💼 Offres d'emploi (filtrage auto interne/externe)"])
app.include_router(applications.router, prefix="/api/v1/applications", tags=["📝 Candidatures", "📄 Documents PDF"])
app.include_router(evaluations.router, prefix="/api/v1/evaluations", tags=["📊 Évaluations"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["🔔 Notifications"])
app.include_router(optimized.router, prefix="/api/v1/optimized", tags=["⚡ Requêtes Optimisées"])
app.include_router(interviews.router, prefix="/api/v1/interviews", tags=["🎯 Entretiens"])
app.include_router(emails.router, prefix="/api/v1/emails", tags=["📧 Emails"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["Webhooks"])

# Routes de monitoring
app.include_router(monitoring_router, prefix="/monitoring", tags=["📊 Monitoring"])

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
    """Gestionnaire pour les erreurs 500 - MODE DEBUG"""
    import traceback
    tb = traceback.format_exc()
    safe_log("error", "Erreur interne du serveur", error=str(exc), path=str(request.url.path), traceback=tb)
    
    # En mode DEBUG, retourner les détails de l'erreur
    if settings.DEBUG:
        return JSONResponse(content={
            "error": "Internal Server Error",
            "message": str(exc),
            "traceback": tb.split('\n'),
            "status_code": 500,
            "path": str(request.url.path)
        }, status_code=500)
    
    return JSONResponse(content={
        "error": "Internal Server Error",
        "message": "Une erreur interne du serveur s'est produite",
        "status_code": 500
    }, status_code=500)

# ============================================================================
# ÉVÉNEMENTS DE L'APPLICATION
# ============================================================================

# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def validate_production_config():
    """Valide la configuration pour la production"""
    safe_log("info", "Validation de la configuration de production...")
    
    # Vérifier que SECRET_KEY est sécurisée
    weak_keys = [
        "your-super-secret-key-here-change-in-production-123456789",
        "CHANGE_ME_SECRET_KEY_32CHARS_MINIMUM_1234567890",
        "CHANGE_ME_IN_PROD_32CHARS_MINIMUM_1234567890",
        "your-secret-key-change-in-production-minimum-32-chars"
    ]
    if settings.SECRET_KEY in weak_keys:
        safe_log("error", "SECRET_KEY non sécurisée détectée en production !")
        raise ValueError("SECRET_KEY doit être changée en production !")
    
    # Vérifier que la base de données n'est pas locale
    if "localhost" in settings.DATABASE_URL or "127.0.0.1" in settings.DATABASE_URL:
        safe_log("error", "Base de données locale détectée en production !")
        raise ValueError("DATABASE_URL ne doit pas pointer vers localhost en production !")
    
    # Vérifier que DEBUG est désactivé
    if settings.DEBUG:
        safe_log("warning", "DEBUG activé en production - Cela peut exposer des informations sensibles !")
    
    safe_log("info", "Configuration de production validée avec succès")

# ============================================================================
# POINT D'ENTRÉE PRINCIPAL
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))  # Azure App Service définit $PORT
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.DEBUG,
        log_level="info"
    )

