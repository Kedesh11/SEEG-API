"""
Middleware de monitoring pour l'application SEEG-API.

Ce module contient les middlewares pour intégrer métriques, logging et tracing.
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import time
import uuid
from app.core.logging.enhanced_logging import request_id_var, user_id_var
from app.core.metrics import metrics_collector
from app.core.tracing import create_span
import structlog

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


def safe_track_metrics(method: str, endpoint: str, status_code: int, duration: float):
    """
    Enregistrement sécurisé des métriques HTTP.
    """
    try:
        if hasattr(metrics_collector, 'track_http_request'):
            metrics_collector.track_http_request(
                method=method,
                endpoint=endpoint,
                status=status_code,
                duration=duration
            )
    except Exception as e:
        # Silently fail - metrics shouldn't break the app
        pass


def safe_track_error(error_type: str, error_message: str):
    """
    Enregistrement sécurisé des erreurs.
    """
    try:
        if hasattr(metrics_collector, 'track_error'):
            metrics_collector.track_error(error_type, error_message)
    except Exception as e:
        # Silently fail
        pass


class MonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware principal pour le monitoring."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Générer un request ID unique
        request_id = str(uuid.uuid4())
        request_id_var.set(request_id)
        
        # Ajouter le request ID aux headers
        request.state.request_id = request_id
        
        # Démarrer le timer
        start_time = time.time()
        
        # Traiter la requête
        try:
            response = await call_next(request)
            
            # Enregistrer les métriques
            duration = time.time() - start_time
            safe_track_metrics(
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code,
                duration=duration
            )
            
            # Ajouter le request ID à la réponse
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Enregistrer l'erreur
            duration = time.time() - start_time
            safe_track_metrics(
                method=request.method,
                endpoint=request.url.path,
                status_code=500,
                duration=duration
            )
            safe_track_error("http_request_error", str(e))
            raise
        finally:
            # Nettoyer le contexte
            request_id_var.set(None)


class PerformanceLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware pour logger les requêtes lentes."""
    
    def __init__(self, app, threshold_seconds: float = 1.0):
        super().__init__(app)
        self.threshold_seconds = threshold_seconds
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        
        # Logger si la requête est lente
        if duration > self.threshold_seconds:
            safe_log(
                "warning",
                "Slow request detected",
                method=request.method,
                path=request.url.path,
                duration_seconds=duration,
                status_code=response.status_code
            )
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware pour ajouter des headers de sécurité."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Ajouter les headers de sécurité
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response


class ErrorTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware pour tracker les erreurs."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            # Logger l'erreur avec contexte
            try:
                safe_log(
                    "error",
                    "Unhandled exception",
                    method=request.method,
                    path=request.url.path,
                    error=str(e)
                )
            except:
                print(f"ERROR: Unhandled exception - {request.method} {request.url.path} - {str(e)}")
            
            # Re-lancer l'exception
            raise