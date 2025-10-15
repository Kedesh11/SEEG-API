"""
Middleware de logging avancé pour FastAPI
Trace toutes les requêtes HTTP avec contexte complet et mesure de performance

Principes:
- Observabilité totale: Chaque requête est tracée
- Correlation IDs: Permet de suivre une requête à travers tous les logs
- Performance monitoring: Mesure automatique des temps de réponse
- Security audit: Log des événements de sécurité
- Error tracking: Capture détaillée des erreurs
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp
from uuid import uuid4
from datetime import datetime
import time
import structlog
from typing import Callable, Optional
import json

from app.core.logging.enhanced_logging import request_id_var, user_id_var

logger = structlog.get_logger(__name__)


class EnhancedLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware de logging enrichi pour tracer toutes les requêtes
    
    Fonctionnalités:
    - Génération automatique de correlation ID (request_id)
    - Logging début/fin de requête avec durée
    - Extraction automatique de l'user_id depuis le token JWT
    - Logging des headers pertinents
    - Mesure de performance avec alertes sur requêtes lentes
    - Gestion des erreurs avec contexte complet
    """
    
    def __init__(
        self,
        app: ASGIApp,
        slow_request_threshold: float = 1.0,
        log_request_body: bool = False,
        log_response_body: bool = False,
        excluded_paths: Optional[list] = None
    ):
        """
        Initialiser le middleware
        
        Args:
            app: Application ASGI
            slow_request_threshold: Seuil (secondes) pour considérer une requête comme lente
            log_request_body: Logger le corps des requêtes (attention: données sensibles)
            log_response_body: Logger le corps des réponses (attention: taille)
            excluded_paths: Chemins à exclure du logging (ex: /health, /metrics)
        """
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.excluded_paths = excluded_paths or [
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json"
        ]
    
    async def dispatch(
        self, 
        request: Request, 
        call_next: Callable
    ) -> Response:
        """
        Traiter la requête avec logging complet
        
        Args:
            request: Requête HTTP
            call_next: Fonction pour appeler le handler suivant
            
        Returns:
            Response HTTP
        """
        # Vérifier si le chemin est exclu
        if any(request.url.path.startswith(path) for path in self.excluded_paths):
            return await call_next(request)
        
        # Générer un ID unique pour la requête
        request_id = str(uuid4())
        request_id_var.set(request_id)
        
        # Extraire l'user_id depuis le token JWT si présent
        user_id = self._extract_user_id_from_request(request)
        if user_id:
            user_id_var.set(user_id)
        
        # Préparer les informations de base de la requête
        request_info = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params) if request.query_params else {},
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent"),
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Logger le début de la requête
        logger.info(
            f"🌐 ➡️  {request.method} {request.url.path}",
            **request_info,
            event_type="request_started"
        )
        
        # Logger le body si activé (attention aux données sensibles)
        if self.log_request_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await self._get_request_body(request)
                if body:
                    logger.debug(
                        "Request body",
                        request_id=request_id,
                        body=body[:500]  # Limiter à 500 caractères
                    )
            except Exception as e:
                logger.warning(
                    "Failed to read request body",
                    request_id=request_id,
                    error=str(e)
                )
        
        # Mesurer le temps de traitement
        start_time = time.time()
        status_code = 500  # Par défaut en cas d'erreur
        error_occurred = None
        
        try:
            # Traiter la requête
            response = await call_next(request)
            status_code = response.status_code
            
        except Exception as e:
            error_occurred = e
            status_code = 500
            
            # Logger l'erreur avec contexte complet
            logger.error(
                f"❌ Erreur non capturée dans {request.method} {request.url.path}",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                error_type=type(e).__name__,
                error_message=str(e),
                user_id=user_id,
                exc_info=True,
                event_type="request_error"
            )
            
            # Re-lever l'erreur pour qu'elle soit gérée par FastAPI
            raise
            
        finally:
            # Calculer la durée
            duration = time.time() - start_time
            
            # Préparer les informations de réponse
            response_info = {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_seconds": round(duration, 3),
                "duration_ms": round(duration * 1000, 2),
                "user_id": user_id,
                "event_type": "request_completed"
            }
            
            # Déterminer le niveau de log selon le statut et la durée
            log_level = self._determine_log_level(status_code, duration)
            emoji = self._get_status_emoji(status_code)
            
            # Logger la fin de la requête
            log_message = f"{emoji} {request.method} {request.url.path} [{status_code}] - {duration*1000:.2f}ms"
            
            getattr(logger, log_level)(
                log_message,
                **response_info
            )
            
            # Alerte spécifique pour requêtes lentes
            if duration > self.slow_request_threshold:
                logger.warning(
                    f"⚠️  SLOW REQUEST: {request.method} {request.url.path}",
                    request_id=request_id,
                    duration_seconds=round(duration, 3),
                    threshold_seconds=self.slow_request_threshold,
                    exceeded_by_seconds=round(duration - self.slow_request_threshold, 3),
                    event_type="slow_request"
                )
            
            # Logger les événements de sécurité
            self._log_security_events(request, status_code, user_id or "anonymous", request_id)
        
        return response
    
    def _extract_user_id_from_request(self, request: Request) -> Optional[str]:
        """
        Extraire l'user_id depuis le token JWT
        
        Args:
            request: Requête HTTP
            
        Returns:
            User ID ou None
        """
        try:
            # Chercher dans les headers Authorization
            auth_header = request.headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                
                # Décoder le token (sans vérifier la signature pour le logging)
                import jwt
                try:
                    payload = jwt.decode(token, options={"verify_signature": False})
                    return payload.get("sub") or payload.get("user_id")
                except Exception:
                    pass
        except Exception:
            pass
        
        return None
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Obtenir l'adresse IP du client (gérer les proxies)
        
        Args:
            request: Requête HTTP
            
        Returns:
            Adresse IP
        """
        # Vérifier les headers de proxy
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback sur l'IP directe
        if request.client:
            return request.client.host
        
        return "unknown"
    
    async def _get_request_body(self, request: Request) -> Optional[dict]:
        """
        Lire le body de la requête
        
        Args:
            request: Requête HTTP
            
        Returns:
            Body parsé ou None
        """
        try:
            body_bytes = await request.body()
            if body_bytes:
                body_str = body_bytes.decode('utf-8')
                return json.loads(body_str)
        except Exception:
            pass
        
        return None
    
    def _determine_log_level(self, status_code: int, duration: float) -> str:
        """
        Déterminer le niveau de log selon le statut et la durée
        
        Args:
            status_code: Code de statut HTTP
            duration: Durée de traitement
            
        Returns:
            Niveau de log (debug, info, warning, error)
        """
        # Erreurs serveur -> error
        if status_code >= 500:
            return "error"
        
        # Erreurs client -> warning
        if status_code >= 400:
            return "warning"
        
        # Requêtes lentes -> warning
        if duration > self.slow_request_threshold:
            return "warning"
        
        # Sinon -> info
        return "info"
    
    def _get_status_emoji(self, status_code: int) -> str:
        """
        Obtenir un emoji selon le statut HTTP
        
        Args:
            status_code: Code de statut HTTP
            
        Returns:
            Emoji
        """
        if status_code < 300:
            return "✅"
        elif status_code < 400:
            return "↪️ "
        elif status_code < 500:
            return "⚠️ "
        else:
            return "❌"
    
    def _log_security_events(
        self,
        request: Request,
        status_code: int,
        user_id: str,
        request_id: str
    ):
        """
        Logger les événements de sécurité importants
        
        Args:
            request: Requête HTTP
            status_code: Code de statut
            user_id: ID utilisateur
            request_id: ID de la requête
        """
        # Échecs d'authentification
        if status_code == 401:
            logger.warning(
                f"🔐 Tentative d'accès non authentifiée: {request.method} {request.url.path}",
                request_id=request_id,
                path=request.url.path,
                client_ip=self._get_client_ip(request),
                event_type="authentication_failed"
            )
        
        # Échecs d'autorisation
        elif status_code == 403:
            logger.warning(
                f"🚫 Accès refusé: {request.method} {request.url.path}",
                request_id=request_id,
                path=request.url.path,
                user_id=user_id,
                client_ip=self._get_client_ip(request),
                event_type="authorization_failed"
            )
        
        # Trop de requêtes (rate limit)
        elif status_code == 429:
            logger.warning(
                f"🚦 Rate limit dépassé: {request.method} {request.url.path}",
                request_id=request_id,
                path=request.url.path,
                user_id=user_id,
                client_ip=self._get_client_ip(request),
                event_type="rate_limit_exceeded"
            )
        
        # Connexion réussie
        elif request.url.path in ["/api/v1/auth/login", "/api/v1/auth/token"] and status_code == 200:
            logger.info(
                f"🔐 Connexion réussie",
                request_id=request_id,
                user_id=user_id,
                client_ip=self._get_client_ip(request),
                event_type="login_success"
            )
        
        # Déconnexion
        elif request.url.path == "/api/v1/auth/logout" and status_code == 200:
            logger.info(
                f"👋 Déconnexion",
                request_id=request_id,
                user_id=user_id,
                client_ip=self._get_client_ip(request),
                event_type="logout"
            )

