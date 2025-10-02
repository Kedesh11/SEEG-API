"""
Middleware pour tracker les requêtes avec Application Insights
"""
import time
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from typing import Callable

from app.core.monitoring.app_insights import app_insights

logger = structlog.get_logger(__name__)


class ApplicationInsightsMiddleware(BaseHTTPMiddleware):
    """Middleware pour tracker automatiquement les requêtes HTTP"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Intercepter et tracker chaque requête
        
        Args:
            request: Requête HTTP entrante
            call_next: Fonction suivante dans la chaîne de middleware
            
        Returns:
            Response HTTP
        """
        # Ignorer les endpoints de health check et docs
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Timestamp de début
        start_time = time.time()
        
        # Variables pour le tracking
        status_code = 500
        success = False
        exception_occurred = None
        
        try:
            # Exécuter la requête
            response: Response = await call_next(request)
            status_code = response.status_code
            success = 200 <= status_code < 400
            
            return response
            
        except Exception as e:
            exception_occurred = e
            logger.error(
                "Exception dans le middleware",
                path=request.url.path,
                method=request.method,
                error=str(e)
            )
            raise
            
        finally:
            # Calculer la durée
            duration_ms = (time.time() - start_time) * 1000
            
            # Properties additionnelles
            properties = {
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "user_agent": request.headers.get("user-agent", "unknown"),
                "client_host": request.client.host if request.client else "unknown",
            }
            
            # Ajouter l'user_id si disponible
            if hasattr(request.state, "user_id"):
                properties["user_id"] = request.state.user_id
            
            # Tracker la requête
            app_insights.track_request(
                name=f"{request.method} {request.url.path}",
                url=str(request.url),
                duration=duration_ms,
                response_code=status_code,
                success=success,
                properties=properties
            )
            
            # Tracker l'exception si elle s'est produite
            if exception_occurred:
                app_insights.track_exception(
                    exception=exception_occurred,
                    properties=properties
                )
            
            # Logger les requêtes lentes (> 1 seconde)
            if duration_ms > 1000:
                logger.warning(
                    "Requête lente détectée",
                    path=request.url.path,
                    method=request.method,
                    duration_ms=duration_ms,
                    status_code=status_code
                )

