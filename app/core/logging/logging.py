"""
Configuration du système de logging.
Respecte le principe de responsabilité unique (Single Responsibility Principle).
"""

import logging
import sys
from typing import Any, Dict, Optional

import structlog
from structlog.stdlib import LoggerFactory

from app.core.config.config import settings


class LoggingConfig:
    """Configuration du système de logging."""
    
    @staticmethod
    def setup_logging() -> None:
        """Configure le système de logging pour l'application."""
        
        # Configuration de base
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=getattr(logging, settings.LOG_LEVEL.upper()),
        )
        
        # Configuration de structlog
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    
    @staticmethod
    def get_logger(name: str) -> structlog.BoundLogger:
        """
        Retourne un logger configuré.
        
        Args:
            name: Nom du logger
            
        Returns:
            structlog.BoundLogger: Logger configuré
        """
        return structlog.get_logger(name)


class RequestLogger:
    """Logger spécialisé pour les requêtes HTTP."""
    
    def __init__(self):
        self.logger = LoggingConfig.get_logger("request")
    
    def log_request(
        self,
        method: str,
        url: str,
        status_code: int,
        response_time: float,
        user_id: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """
        Log une requête HTTP.
        
        Args:
            method: Méthode HTTP
            url: URL de la requête
            status_code: Code de statut de la réponse
            response_time: Temps de réponse en secondes
            user_id: ID de l'utilisateur (optionnel)
            **kwargs: Arguments supplémentaires
        """
        self.logger.info(
            "HTTP Request",
            method=method,
            url=url,
            status_code=status_code,
            response_time=response_time,
            user_id=user_id,
            **kwargs
        )
    
    def log_error(
        self,
        method: str,
        url: str,
        error: Exception,
        user_id: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """
        Log une erreur de requête.
        
        Args:
            method: Méthode HTTP
            url: URL de la requête
            error: Exception levée
            user_id: ID de l'utilisateur (optionnel)
            **kwargs: Arguments supplémentaires
        """
        self.logger.error(
            "HTTP Request Error",
            method=method,
            url=url,
            error=str(error),
            error_type=type(error).__name__,
            user_id=user_id,
            **kwargs
        )


class DatabaseLogger:
    """Logger spécialisé pour les opérations de base de données."""
    
    def __init__(self):
        self.logger = LoggingConfig.get_logger("database")
    
    def log_query(
        self,
        operation: str,
        table: str,
        duration: float,
        user_id: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """
        Log une requête de base de données.
        
        Args:
            operation: Type d'opération (SELECT, INSERT, UPDATE, DELETE)
            table: Nom de la table
            duration: Durée de l'opération en secondes
            user_id: ID de l'utilisateur (optionnel)
            **kwargs: Arguments supplémentaires
        """
        self.logger.info(
            "Database Query",
            operation=operation,
            table=table,
            duration=duration,
            user_id=user_id,
            **kwargs
        )
    
    def log_error(
        self,
        operation: str,
        table: str,
        error: Exception,
        user_id: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """
        Log une erreur de base de données.
        
        Args:
            operation: Type d'opération
            table: Nom de la table
            error: Exception levée
            user_id: ID de l'utilisateur (optionnel)
            **kwargs: Arguments supplémentaires
        """
        self.logger.error(
            "Database Error",
            operation=operation,
            table=table,
            error=str(error),
            error_type=type(error).__name__,
            user_id=user_id,
            **kwargs
        )


class SecurityLogger:
    """Logger spécialisé pour les événements de sécurité."""
    
    def __init__(self):
        self.logger = LoggingConfig.get_logger("security")
    
    def log_login_attempt(
        self,
        email: str,
        success: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """
        Log une tentative de connexion.
        
        Args:
            email: Email de l'utilisateur
            success: Succès de la connexion
            ip_address: Adresse IP (optionnel)
            user_agent: User agent (optionnel)
            **kwargs: Arguments supplémentaires
        """
        self.logger.info(
            "Login Attempt",
            email=email,
            success=success,
            ip_address=ip_address,
            user_agent=user_agent,
            **kwargs
        )
    
    def log_permission_denied(
        self,
        user_id: str,
        permission: str,
        resource: str,
        ip_address: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """
        Log un accès refusé.
        
        Args:
            user_id: ID de l'utilisateur
            permission: Permission requise
            resource: Ressource accédée
            ip_address: Adresse IP (optionnel)
            **kwargs: Arguments supplémentaires
        """
        self.logger.warning(
            "Permission Denied",
            user_id=user_id,
            permission=permission,
            resource=resource,
            ip_address=ip_address,
            **kwargs
        )
    
    def log_suspicious_activity(
        self,
        user_id: Optional[str],
        activity: str,
        details: Dict[str, Any],
        ip_address: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """
        Log une activité suspecte.
        
        Args:
            user_id: ID de l'utilisateur (optionnel)
            activity: Type d'activité
            details: Détails de l'activité
            ip_address: Adresse IP (optionnel)
            **kwargs: Arguments supplémentaires
        """
        self.logger.warning(
            "Suspicious Activity",
            user_id=user_id,
            activity=activity,
            details=details,
            ip_address=ip_address,
            **kwargs
        )


# Instances globales des loggers
request_logger = RequestLogger()
database_logger = DatabaseLogger()
security_logger = SecurityLogger()
