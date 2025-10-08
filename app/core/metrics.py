"""
Module de gestion des métriques pour l'application SEEG-API.

Utilise Prometheus pour collecter et exposer des métriques sur les performances,
l'utilisation et la santé de l'application.
"""
from prometheus_client import Counter, Histogram, Gauge, Summary, Info
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from functools import wraps
from typing import Callable
import time
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)

# Informations sur l'application
app_info = Info(
    'seeg_api_info',
    'Informations sur l\'application SEEG API'
)

# Compteurs pour les requêtes HTTP
http_requests_total = Counter(
    'seeg_api_http_requests_total',
    'Nombre total de requêtes HTTP',
    ['method', 'endpoint', 'status']
)

http_request_duration = Histogram(
    'seeg_api_http_request_duration_seconds',
    'Durée des requêtes HTTP en secondes',
    ['method', 'endpoint', 'status'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

# Métriques pour l'authentification
auth_attempts_total = Counter(
    'seeg_api_auth_attempts_total',
    'Nombre total de tentatives d\'authentification',
    ['type', 'status']
)

active_sessions = Gauge(
    'seeg_api_active_sessions',
    'Nombre de sessions actives'
)

# Métriques pour les candidatures
applications_created_total = Counter(
    'seeg_api_applications_created_total',
    'Nombre total de candidatures créées',
    ['job_category']
)

applications_status = Gauge(
    'seeg_api_applications_by_status',
    'Nombre de candidatures par statut',
    ['status']
)

# Métriques pour les documents
documents_uploaded_total = Counter(
    'seeg_api_documents_uploaded_total',
    'Nombre total de documents uploadés',
    ['type']
)

documents_size_bytes = Summary(
    'seeg_api_documents_size_bytes',
    'Taille des documents uploadés en octets',
    ['type']
)

# Métriques pour la base de données
db_connections_active = Gauge(
    'seeg_api_db_connections_active',
    'Nombre de connexions actives à la base de données'
)

db_query_duration = Histogram(
    'seeg_api_db_query_duration_seconds',
    'Durée des requêtes à la base de données',
    ['operation', 'table'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5)
)

db_errors_total = Counter(
    'seeg_api_db_errors_total',
    'Nombre total d\'erreurs de base de données',
    ['operation', 'error_type']
)

# Métriques pour le cache
cache_hits_total = Counter(
    'seeg_api_cache_hits_total',
    'Nombre total de cache hits',
    ['cache_type']
)

cache_misses_total = Counter(
    'seeg_api_cache_misses_total',
    'Nombre total de cache misses',
    ['cache_type']
)

cache_operations_duration = Histogram(
    'seeg_api_cache_operations_duration_seconds',
    'Durée des opérations de cache',
    ['operation', 'cache_type']
)

# Métriques pour les emails
emails_sent_total = Counter(
    'seeg_api_emails_sent_total',
    'Nombre total d\'emails envoyés',
    ['type', 'status']
)

# Métriques système
system_cpu_usage = Gauge(
    'seeg_api_system_cpu_usage_percent',
    'Utilisation CPU en pourcentage'
)

system_memory_usage = Gauge(
    'seeg_api_system_memory_usage_bytes',
    'Utilisation mémoire en octets'
)

# Métriques pour les tâches asynchrones
async_tasks_total = Counter(
    'seeg_api_async_tasks_total',
    'Nombre total de tâches asynchrones',
    ['task_name', 'status']
)

async_task_duration = Histogram(
    'seeg_api_async_task_duration_seconds',
    'Durée des tâches asynchrones',
    ['task_name']
)

# Métriques pour les erreurs
errors_total = Counter(
    'seeg_api_errors_total',
    'Nombre total d\'erreurs',
    ['error_type', 'endpoint']
)

# Rate limiting
rate_limit_exceeded_total = Counter(
    'seeg_api_rate_limit_exceeded_total',
    'Nombre de fois où le rate limit a été dépassé',
    ['endpoint', 'user_type']
)


class MetricsCollector:
    """Collecteur de métriques centralisé."""
    
    def __init__(self):
        """Initialise le collecteur de métriques."""
        # Définir les informations de l'application
        app_info.info({
            'version': '1.0.0',
            'environment': 'production',
            'start_time': datetime.now().isoformat()
        })
    
    @staticmethod
    def track_http_request(method: str, endpoint: str, status: int, duration: float):
        """
        Enregistre les métriques d'une requête HTTP.
        
        Args:
            method: Méthode HTTP (GET, POST, etc.)
            endpoint: Endpoint appelé
            status: Code de statut HTTP
            duration: Durée de la requête en secondes
        """
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=str(status)
        ).inc()
        
        http_request_duration.labels(
            method=method,
            endpoint=endpoint,
            status=str(status)
        ).observe(duration)
        
        if status >= 500:
            errors_total.labels(
                error_type='http_5xx',
                endpoint=endpoint
            ).inc()
        elif status >= 400:
            errors_total.labels(
                error_type='http_4xx',
                endpoint=endpoint
            ).inc()
    
    @staticmethod
    def track_auth_attempt(auth_type: str, success: bool):
        """
        Enregistre une tentative d'authentification.
        
        Args:
            auth_type: Type d'authentification (login, signup, etc.)
            success: Si l'authentification a réussi
        """
        status = 'success' if success else 'failure'
        auth_attempts_total.labels(type=auth_type, status=status).inc()
    
    @staticmethod
    def track_application_created(job_category: str = 'general'):
        """Enregistre la création d'une candidature."""
        applications_created_total.labels(job_category=job_category).inc()
    
    @staticmethod
    def track_document_upload(doc_type: str, size_bytes: int):
        """
        Enregistre l'upload d'un document.
        
        Args:
            doc_type: Type de document
            size_bytes: Taille en octets
        """
        documents_uploaded_total.labels(type=doc_type).inc()
        documents_size_bytes.labels(type=doc_type).observe(size_bytes)
    
    @staticmethod
    def track_db_query(operation: str, table: str, duration: float, error: str = None):
        """
        Enregistre une requête à la base de données.
        
        Args:
            operation: Type d'opération (select, insert, update, delete)
            table: Table concernée
            duration: Durée en secondes
            error: Type d'erreur si applicable
        """
        db_query_duration.labels(operation=operation, table=table).observe(duration)
        
        if error:
            db_errors_total.labels(operation=operation, error_type=error).inc()
    
    @staticmethod
    def track_cache_operation(operation: str, cache_type: str, hit: bool, duration: float):
        """
        Enregistre une opération de cache.
        
        Args:
            operation: Type d'opération (get, set, delete)
            cache_type: Type de cache
            hit: True si cache hit (pour get uniquement)
            duration: Durée en secondes
        """
        if operation == 'get':
            if hit:
                cache_hits_total.labels(cache_type=cache_type).inc()
            else:
                cache_misses_total.labels(cache_type=cache_type).inc()
        
        cache_operations_duration.labels(
            operation=operation,
            cache_type=cache_type
        ).observe(duration)
    
    @staticmethod
    def track_email_sent(email_type: str, success: bool):
        """
        Enregistre l'envoi d'un email.
        
        Args:
            email_type: Type d'email
            success: Si l'envoi a réussi
        """
        status = 'success' if success else 'failure'
        emails_sent_total.labels(type=email_type, status=status).inc()
    
    @staticmethod
    def track_async_task(task_name: str, duration: float, success: bool):
        """
        Enregistre l'exécution d'une tâche asynchrone.
        
        Args:
            task_name: Nom de la tâche
            duration: Durée en secondes
            success: Si la tâche a réussi
        """
        status = 'success' if success else 'failure'
        async_tasks_total.labels(task_name=task_name, status=status).inc()
        async_task_duration.labels(task_name=task_name).observe(duration)
    
    @staticmethod
    def update_system_metrics(cpu_percent: float, memory_bytes: int):
        """
        Met à jour les métriques système.
        
        Args:
            cpu_percent: Utilisation CPU en pourcentage
            memory_bytes: Utilisation mémoire en octets
        """
        system_cpu_usage.set(cpu_percent)
        system_memory_usage.set(memory_bytes)
    
    @staticmethod
    def update_active_sessions(count: int):
        """Met à jour le nombre de sessions actives."""
        active_sessions.set(count)
    
    @staticmethod
    def update_applications_by_status(status_counts: dict):
        """
        Met à jour le nombre de candidatures par statut.
        
        Args:
            status_counts: Dictionnaire {status: count}
        """
        for status, count in status_counts.items():
            applications_status.labels(status=status).set(count)
    
    @staticmethod
    def update_db_connections(active_count: int):
        """Met à jour le nombre de connexions DB actives."""
        db_connections_active.set(active_count)
    
    @staticmethod
    def track_rate_limit_exceeded(endpoint: str, user_type: str = 'anonymous'):
        """
        Enregistre un dépassement de rate limit.
        
        Args:
            endpoint: Endpoint concerné
            user_type: Type d'utilisateur
        """
        rate_limit_exceeded_total.labels(
            endpoint=endpoint,
            user_type=user_type
        ).inc()


# Instance globale du collecteur
metrics_collector = MetricsCollector()


# Décorateurs pour faciliter la collecte de métriques
def track_execution_time(metric_name: str = None):
    """
    Décorateur pour mesurer le temps d'exécution d'une fonction.
    
    Args:
        metric_name: Nom de la métrique (par défaut: nom de la fonction)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                name = metric_name or func.__name__
                
                metrics_collector.track_async_task(
                    task_name=name,
                    duration=duration,
                    success=success
                )
                
                logger.debug(
                    "Fonction exécutée",
                    function=name,
                    duration=duration,
                    success=success
                )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                name = metric_name or func.__name__
                
                metrics_collector.track_async_task(
                    task_name=name,
                    duration=duration,
                    success=success
                )
        
        # Retourner le wrapper approprié
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def get_metrics():
    """
    Retourne les métriques au format Prometheus.
    
    Returns:
        Tuple (métriques, content_type)
    """
    return generate_latest(), CONTENT_TYPE_LATEST
