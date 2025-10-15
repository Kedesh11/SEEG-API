"""
Gestionnaires d'exceptions globaux pour FastAPI
Centralise la gestion des erreurs selon le principe DRY
"""
import structlog
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, OperationalError
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import (
    ApplicationError,
    ValidationError,
    NotFoundError,
    AuthenticationError,
    AuthorizationError,
    DatabaseError,
    get_http_status_code
)

logger = structlog.get_logger(__name__)


async def application_error_handler(request: Request, exc: ApplicationError) -> JSONResponse:
    """
    Gestionnaire pour toutes les exceptions personnalisées de l'application
    
    Args:
        request: Requête FastAPI
        exc: Exception de l'application
        
    Returns:
        Réponse JSON formatée
    """
    status_code = get_http_status_code(exc)
    
    # Logger l'erreur avec le niveau approprié
    if status_code >= 500:
        logger.error(
            "Erreur serveur",
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
            path=request.url.path,
            method=request.method
        )
    elif status_code >= 400:
        logger.warning(
            "Erreur client",
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
            path=request.url.path,
            method=request.method
        )
    
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details
        }
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Gestionnaire pour les erreurs de validation Pydantic
    
    Args:
        request: Requête FastAPI
        exc: Erreur de validation
        
    Returns:
        Réponse JSON formatée
    """
    logger.warning(
        "Erreur de validation",
        errors=exc.errors(),
        path=request.url.path,
        method=request.method
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": "VALIDATION_ERROR",
            "message": "Données de requête invalides",
            "details": {
                "errors": exc.errors()
            }
        }
    )


async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    """
    Gestionnaire pour les erreurs d'intégrité de base de données
    
    Args:
        request: Requête FastAPI
        exc: Erreur d'intégrité
        
    Returns:
        Réponse JSON formatée
    """
    logger.error(
        "Erreur d'intégrité base de données",
        error=str(exc.orig) if hasattr(exc, 'orig') else str(exc),
        path=request.url.path,
        method=request.method
    )
    
    # Analyser le type d'erreur d'intégrité
    error_message = str(exc.orig) if hasattr(exc, 'orig') else str(exc)
    
    if "foreign key" in error_message.lower():
        message = "Référence invalide : la ressource référencée n'existe pas"
        error_code = "FOREIGN_KEY_VIOLATION"
    elif "unique" in error_message.lower() or "duplicate" in error_message.lower():
        message = "Cette ressource existe déjà"
        error_code = "UNIQUE_VIOLATION"
    elif "not null" in error_message.lower():
        message = "Champ obligatoire manquant"
        error_code = "NOT_NULL_VIOLATION"
    else:
        message = "Erreur d'intégrité des données"
        error_code = "INTEGRITY_ERROR"
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "error": error_code,
            "message": message,
            "details": {}
        }
    )


async def operational_error_handler(request: Request, exc: OperationalError) -> JSONResponse:
    """
    Gestionnaire pour les erreurs opérationnelles de base de données
    
    Args:
        request: Requête FastAPI
        exc: Erreur opérationnelle
        
    Returns:
        Réponse JSON formatée
    """
    logger.error(
        "Erreur opérationnelle base de données",
        error=str(exc.orig) if hasattr(exc, 'orig') else str(exc),
        path=request.url.path,
        method=request.method
    )
    
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "success": False,
            "error": "DATABASE_UNAVAILABLE",
            "message": "Service temporairement indisponible",
            "details": {}
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Gestionnaire pour toutes les exceptions non gérées
    
    Args:
        request: Requête FastAPI
        exc: Exception générique
        
    Returns:
        Réponse JSON formatée
    """
    logger.error(
        "Erreur non gérée",
        error_type=type(exc).__name__,
        error=str(exc),
        path=request.url.path,
        method=request.method,
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "INTERNAL_SERVER_ERROR",
            "message": "Une erreur interne s'est produite",
            "details": {}
        }
    )


def register_error_handlers(app):
    """
    Enregistrer tous les gestionnaires d'erreurs sur l'application FastAPI
    
    Args:
        app: Application FastAPI
    """
    # Exceptions personnalisées
    app.add_exception_handler(ApplicationError, application_error_handler)
    
    # Exceptions de validation
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    
    # Exceptions de base de données
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(OperationalError, operational_error_handler)
    
    # Exception générique (catch-all)
    app.add_exception_handler(Exception, generic_exception_handler)
    
    logger.info("✅ Gestionnaires d'erreurs enregistrés")

