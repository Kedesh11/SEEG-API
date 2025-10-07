"""
Configuration du rate limiting pour l'API
"""
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from app.core.config.config import settings
import structlog

logger = structlog.get_logger(__name__)

def get_identifier(request: Request) -> str:
    """
    Identifier pour le rate limiting.
    Utilise l'IP du client ou le user_id si authentifié.
    """
    # Essayer de récupérer le user_id depuis le token JWT
    try:
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            from app.core.security.security import TokenManager
            token = auth_header.split(" ", 1)[1].strip()
            payload = TokenManager.verify_token(token)
            if payload and payload.get("sub"):
                user_id = payload["sub"]
                logger.debug("Rate limit identifier: user_id", user_id=user_id)
                return f"user:{user_id}"
    except Exception:
        pass
    
    # Fallback sur l'IP
    ip = get_remote_address(request)
    logger.debug("Rate limit identifier: IP", ip=ip)
    return f"ip:{ip}"


# Configuration du limiter
storage_uri = "memory://"
try:
    if settings.ENVIRONMENT.lower() in ["production", "staging"] and settings.REDIS_URL:
        storage_uri = settings.REDIS_URL
except Exception:
    pass

# Désactiver le rate limiting en environnement de test
if settings.ENVIRONMENT == "testing":
    limiter = Limiter(
        key_func=get_identifier,
        default_limits=[],  # Pas de limites en test
        storage_uri=storage_uri,
        headers_enabled=False,
        enabled=False,
    )
    logger.info("Rate limiting désactivé en environnement de test")
else:
    limiter = Limiter(
        key_func=get_identifier,
        default_limits=["1000/hour", "100/minute"],
        storage_uri=storage_uri,
        headers_enabled=True,
    )

# Limites spécifiques par route (format: "X/minute;Y/hour")
AUTH_LIMITS = "5/minute;20/hour" if settings.ENVIRONMENT != "testing" else ""
SIGNUP_LIMITS = "3/minute;10/hour" if settings.ENVIRONMENT != "testing" else ""
UPLOAD_LIMITS = "10/minute;50/hour" if settings.ENVIRONMENT != "testing" else ""
DEFAULT_LIMITS = "60/minute;500/hour" if settings.ENVIRONMENT != "testing" else ""

