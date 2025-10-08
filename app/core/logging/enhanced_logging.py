"""
Module de logging enrichi pour l'application SEEG-API.

Utilise structlog pour fournir des logs structurés avec contexte enrichi,
correlation IDs et intégration avec les métriques.
"""
import structlog
import logging
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from contextvars import ContextVar
import json
from pythonjsonlogger import jsonlogger

# Context variables pour le tracking des requêtes
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
session_id_var: ContextVar[Optional[str]] = ContextVar('session_id', default=None)


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Formateur JSON personnalisé pour les logs."""
    
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        
        # Ajouter des champs personnalisés
        log_record['timestamp'] = datetime.utcnow().isoformat()
        log_record['level'] = record.levelname
        log_record['logger_name'] = record.name
        
        # Ajouter le contexte de la requête
        if request_id := request_id_var.get():
            log_record['request_id'] = request_id
        
        if user_id := user_id_var.get():
            log_record['user_id'] = user_id
        
        if session_id := session_id_var.get():
            log_record['session_id'] = session_id
        
        # Ajouter des informations sur l'origine
        if hasattr(record, 'pathname'):
            log_record['source'] = {
                'file': record.pathname,
                'line': record.lineno,
                'function': record.funcName
            }


def setup_logging(
    log_level: str = "INFO",
    json_logs: bool = True,
    log_file: Optional[str] = None
):
    """
    Configure le système de logging.
    
    Args:
        log_level: Niveau de log (DEBUG, INFO, WARNING, ERROR)
        json_logs: Si True, utilise le format JSON
        log_file: Fichier de log optionnel
    """
    # Configuration de base de logging
    handlers = []
    
    # Handler console
    console_handler = logging.StreamHandler(sys.stdout)
    if json_logs:
        formatter = CustomJsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s'
        )
        console_handler.setFormatter(formatter)
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
    
    handlers.append(console_handler)
    
    # Handler fichier si spécifié
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    # Configuration du logger racine
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        handlers=handlers
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
            add_request_context,
            add_app_context,
            structlog.processors.CallsiteParameterAdder(
                parameters=[
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                ]
            ),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer() if json_logs else structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def add_request_context(logger, log_method, event_dict):
    """Ajoute le contexte de la requête aux logs."""
    if request_id := request_id_var.get():
        event_dict['request_id'] = request_id
    
    if user_id := user_id_var.get():
        event_dict['user_id'] = user_id
    
    if session_id := session_id_var.get():
        event_dict['session_id'] = session_id
    
    return event_dict


def add_app_context(logger, log_method, event_dict):
    """Ajoute le contexte de l'application aux logs."""
    event_dict['app'] = 'seeg-api'
    event_dict['environment'] = 'production'  # À configurer selon l'environnement
    event_dict['version'] = '1.0.0'  # À récupérer depuis la config
    
    return event_dict


class LogContext:
    """Gestionnaire de contexte pour enrichir les logs."""
    
    def __init__(self, **kwargs):
        self.context = kwargs
        self.tokens = []
    
    def __enter__(self):
        for key, value in self.context.items():
            if key == 'request_id':
                token = request_id_var.set(value)
            elif key == 'user_id':
                token = user_id_var.set(value)
            elif key == 'session_id':
                token = session_id_var.set(value)
            else:
                continue
            self.tokens.append((key, token))
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        for key, token in self.tokens:
            if key == 'request_id':
                request_id_var.reset(token)
            elif key == 'user_id':
                user_id_var.reset(token)
            elif key == 'session_id':
                session_id_var.reset(token)


def get_logger(name: str = None) -> structlog.BoundLogger:
    """
    Obtient un logger configuré.
    
    Args:
        name: Nom du logger (par défaut: nom du module appelant)
        
    Returns:
        Logger structlog configuré
    """
    return structlog.get_logger(name)


def log_performance(
    logger: structlog.BoundLogger,
    operation: str,
    duration: float,
    **kwargs
):
    """
    Log les métriques de performance.
    
    Args:
        logger: Logger à utiliser
        operation: Nom de l'opération
        duration: Durée en secondes
        **kwargs: Contexte additionnel
    """
    logger.info(
        "Performance metric",
        operation=operation,
        duration_seconds=duration,
        duration_ms=duration * 1000,
        **kwargs
    )


def log_database_query(
    logger: structlog.BoundLogger,
    query: str,
    duration: float,
    rows_affected: int = None,
    **kwargs
):
    """
    Log une requête de base de données.
    
    Args:
        logger: Logger à utiliser
        query: Requête SQL
        duration: Durée en secondes
        rows_affected: Nombre de lignes affectées
        **kwargs: Contexte additionnel
    """
    logger.info(
        "Database query",
        query=query[:200],  # Limiter la taille
        duration_seconds=duration,
        rows_affected=rows_affected,
        **kwargs
    )


def log_api_call(
    logger: structlog.BoundLogger,
    method: str,
    url: str,
    status_code: int,
    duration: float,
    **kwargs
):
    """
    Log un appel API externe.
    
    Args:
        logger: Logger à utiliser
        method: Méthode HTTP
        url: URL appelée
        status_code: Code de statut
        duration: Durée en secondes
        **kwargs: Contexte additionnel
    """
    logger.info(
        "External API call",
        method=method,
        url=url,
        status_code=status_code,
        duration_seconds=duration,
        **kwargs
    )


def log_business_event(
    logger: structlog.BoundLogger,
    event_type: str,
    entity_type: str,
    entity_id: str,
    **kwargs
):
    """
    Log un événement métier.
    
    Args:
        logger: Logger à utiliser
        event_type: Type d'événement (created, updated, deleted, etc.)
        entity_type: Type d'entité (user, application, job_offer, etc.)
        entity_id: ID de l'entité
        **kwargs: Contexte additionnel
    """
    logger.info(
        f"{entity_type}.{event_type}",
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        **kwargs
    )


def log_security_event(
    logger: structlog.BoundLogger,
    event_type: str,
    user_id: str = None,
    ip_address: str = None,
    **kwargs
):
    """
    Log un événement de sécurité.
    
    Args:
        logger: Logger à utiliser
        event_type: Type d'événement (login, logout, access_denied, etc.)
        user_id: ID de l'utilisateur
        ip_address: Adresse IP
        **kwargs: Contexte additionnel
    """
    logger.warning(
        f"Security event: {event_type}",
        event_type=event_type,
        user_id=user_id,
        ip_address=ip_address,
        **kwargs
    )


def log_error_with_context(
    logger: structlog.BoundLogger,
    error: Exception,
    operation: str,
    **kwargs
):
    """
    Log une erreur avec contexte enrichi.
    
    Args:
        logger: Logger à utiliser
        error: Exception
        operation: Opération qui a échoué
        **kwargs: Contexte additionnel
    """
    logger.error(
        f"Error in {operation}",
        operation=operation,
        error_type=type(error).__name__,
        error_message=str(error),
        **kwargs,
        exc_info=True
    )


# Créer des loggers spécialisés
api_logger = get_logger("api")
db_logger = get_logger("database")
security_logger = get_logger("security")
business_logger = get_logger("business")
performance_logger = get_logger("performance")


def setup_enhanced_logging():
    """Configure le système de logging enrichi pour l'application."""
    # Configuration de base de structlog
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
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configuration du logging standard Python
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )
    
    # Ajouter le formateur JSON aux handlers
    json_formatter = CustomJsonFormatter()
    for handler in logging.root.handlers:
        handler.setFormatter(json_formatter)
