"""
Décorateurs de logging pour automatiser le logging des fonctions/méthodes
Respect des principes DRY et de traçabilité complète
"""
import functools
import time
import structlog
from typing import Any, Callable, Optional
from uuid import uuid4
import inspect
import json

logger = structlog.get_logger(__name__)


def log_execution(
    log_args: bool = True,
    log_result: bool = False,
    log_performance: bool = True,
    level: str = "info",
    exclude_args: Optional[list] = None
):
    """
    Décorateur pour logger automatiquement l'exécution d'une fonction
    
    Principes appliqués:
    - DRY: Évite la répétition du code de logging
    - Observabilité: Trace toutes les exécutions
    - Performance: Mesure automatique du temps d'exécution
    - Sécurité: Permet d'exclure des arguments sensibles
    
    Args:
        log_args: Logger les arguments d'entrée
        log_result: Logger le résultat (attention aux données sensibles)
        log_performance: Logger le temps d'exécution
        level: Niveau de log (debug, info, warning, error)
        exclude_args: Liste des noms d'arguments à exclure (ex: password)
        
    Example:
        @log_execution(log_args=True, exclude_args=['password'])
        async def create_user(email: str, password: str):
            pass
    """
    if exclude_args is None:
        exclude_args = ['password', 'token', 'secret', 'api_key']
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            func_name = func.__qualname__
            execution_id = str(uuid4())[:8]
            
            # Préparer les informations sur les arguments
            call_info = {
                "function": func_name,
                "execution_id": execution_id,
                "is_async": True
            }
            
            if log_args:
                # Filtrer les arguments sensibles
                safe_kwargs = {
                    k: v for k, v in kwargs.items() 
                    if k not in exclude_args
                }
                # Limiter la taille des arguments pour éviter des logs trop volumineux
                call_info["args_count"] = len(args)
                call_info["kwargs"] = _sanitize_for_logging(safe_kwargs)
            
            # Log début d'exécution
            getattr(logger, level)(
                f"🚀 Début exécution: {func_name}",
                **call_info
            )
            
            start_time = time.time()
            error_occurred = None
            result = None
            
            try:
                result = await func(*args, **kwargs)
                
                duration = time.time() - start_time
                
                # Log fin d'exécution
                end_info = {
                    "function": func_name,
                    "execution_id": execution_id,
                    "duration_seconds": round(duration, 3),
                    "duration_ms": round(duration * 1000, 2),
                    "status": "success"
                }
                
                if log_result and result is not None:
                    end_info["result_type"] = type(result).__name__
                    # Ne logger que les types simples pour éviter les logs massifs
                    if isinstance(result, (str, int, float, bool)):
                        end_info["result"] = result
                
                if log_performance:
                    # Avertissement si exécution lente (> 1 seconde)
                    if duration > 1.0:
                        getattr(logger, "warning")(
                            f"⚠️ Exécution lente: {func_name}",
                            **end_info
                        )
                    else:
                        getattr(logger, level)(
                            f"✅ Fin exécution: {func_name}",
                            **end_info
                        )
                else:
                    getattr(logger, level)(
                        f"✅ Fin exécution: {func_name}",
                        **end_info
                    )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                error_occurred = e
                
                # Log erreur avec contexte complet
                error_info = {
                    "function": func_name,
                    "execution_id": execution_id,
                    "duration_seconds": round(duration, 3),
                    "status": "error",
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
                
                logger.error(
                    f"❌ Erreur dans: {func_name}",
                    **error_info,
                    exc_info=True
                )
                
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            func_name = func.__qualname__
            execution_id = str(uuid4())[:8]
            
            call_info = {
                "function": func_name,
                "execution_id": execution_id,
                "is_async": False
            }
            
            if log_args:
                safe_kwargs = {
                    k: v for k, v in kwargs.items() 
                    if k not in exclude_args
                }
                call_info["args_count"] = len(args)
                call_info["kwargs"] = _sanitize_for_logging(safe_kwargs)
            
            getattr(logger, level)(
                f"🚀 Début exécution: {func_name}",
                **call_info
            )
            
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                end_info = {
                    "function": func_name,
                    "execution_id": execution_id,
                    "duration_seconds": round(duration, 3),
                    "duration_ms": round(duration * 1000, 2),
                    "status": "success"
                }
                
                if log_result and result is not None:
                    end_info["result_type"] = type(result).__name__
                
                if log_performance and duration > 1.0:
                    logger.warning(f"⚠️ Exécution lente: {func_name}", **end_info)
                else:
                    getattr(logger, level)(f"✅ Fin exécution: {func_name}", **end_info)
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                logger.error(
                    f"❌ Erreur dans: {func_name}",
                    function=func_name,
                    execution_id=execution_id,
                    duration_seconds=round(duration, 3),
                    status="error",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    exc_info=True
                )
                
                raise
        
        # Retourner le wrapper approprié selon si la fonction est async ou non
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def log_database_operation(operation_type: str):
    """
    Décorateur spécialisé pour les opérations de base de données
    
    Args:
        operation_type: Type d'opération (SELECT, INSERT, UPDATE, DELETE)
        
    Example:
        @log_database_operation("INSERT")
        async def create_user_in_db(user_data):
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            func_name = func.__qualname__
            operation_id = str(uuid4())[:8]
            
            logger.info(
                f"🗄️ Opération DB: {operation_type}",
                function=func_name,
                operation_id=operation_id,
                operation_type=operation_type
            )
            
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                logger.info(
                    f"✅ DB {operation_type} réussie",
                    function=func_name,
                    operation_id=operation_id,
                    operation_type=operation_type,
                    duration_seconds=round(duration, 3),
                    duration_ms=round(duration * 1000, 2)
                )
                
                # Avertir si l'opération est lente
                if duration > 0.5:  # Plus de 500ms
                    logger.warning(
                        f"⚠️ Opération DB lente: {operation_type}",
                        function=func_name,
                        duration_seconds=round(duration, 3),
                        threshold_exceeded=True
                    )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                logger.error(
                    f"❌ Erreur DB {operation_type}",
                    function=func_name,
                    operation_id=operation_id,
                    operation_type=operation_type,
                    duration_seconds=round(duration, 3),
                    error_type=type(e).__name__,
                    error_message=str(e),
                    exc_info=True
                )
                
                raise
        
        return wrapper
    
    return decorator


def log_business_event(event_type: str, entity_type: str):
    """
    Décorateur pour logger les événements métier
    
    Args:
        event_type: Type d'événement (created, updated, deleted, etc.)
        entity_type: Type d'entité (user, application, job_offer, etc.)
        
    Example:
        @log_business_event("created", "user")
        async def create_user(user_data):
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            func_name = func.__qualname__
            event_id = str(uuid4())[:8]
            
            logger.info(
                f"📊 Événement métier: {entity_type}.{event_type}",
                function=func_name,
                event_id=event_id,
                event_type=event_type,
                entity_type=entity_type
            )
            
            try:
                result = await func(*args, **kwargs)
                
                # Extraire l'ID de l'entité du résultat si possible
                entity_id = None
                if hasattr(result, 'id'):
                    entity_id = str(result.id)
                elif isinstance(result, dict) and 'id' in result:
                    entity_id = str(result['id'])
                
                logger.info(
                    f"✅ Événement métier traité: {entity_type}.{event_type}",
                    function=func_name,
                    event_id=event_id,
                    event_type=event_type,
                    entity_type=entity_type,
                    entity_id=entity_id
                )
                
                return result
                
            except Exception as e:
                logger.error(
                    f"❌ Erreur événement métier: {entity_type}.{event_type}",
                    function=func_name,
                    event_id=event_id,
                    event_type=event_type,
                    entity_type=entity_type,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    exc_info=True
                )
                
                raise
        
        return wrapper
    
    return decorator


def log_api_endpoint(method: str, path: str):
    """
    Décorateur pour logger les endpoints API
    
    Args:
        method: Méthode HTTP (GET, POST, PUT, DELETE)
        path: Chemin de l'endpoint
        
    Example:
        @log_api_endpoint("POST", "/api/v1/users")
        async def create_user_endpoint(...):
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            func_name = func.__qualname__
            request_id = str(uuid4())[:8]
            
            logger.info(
                f"🌐 API Request: {method} {path}",
                function=func_name,
                request_id=request_id,
                method=method,
                path=path
            )
            
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                logger.info(
                    f"✅ API Response: {method} {path}",
                    function=func_name,
                    request_id=request_id,
                    method=method,
                    path=path,
                    duration_seconds=round(duration, 3),
                    duration_ms=round(duration * 1000, 2),
                    status="success"
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                logger.error(
                    f"❌ API Error: {method} {path}",
                    function=func_name,
                    request_id=request_id,
                    method=method,
                    path=path,
                    duration_seconds=round(duration, 3),
                    error_type=type(e).__name__,
                    error_message=str(e),
                    exc_info=True
                )
                
                raise
        
        return wrapper
    
    return decorator


def _sanitize_for_logging(data: Any, max_length: int = 200) -> Any:
    """
    Sanitize data pour le logging (éviter les logs trop volumineux)
    
    Args:
        data: Données à sanitizer
        max_length: Longueur maximale des chaînes
        
    Returns:
        Données sanitizées
    """
    if isinstance(data, str):
        if len(data) > max_length:
            return data[:max_length] + "... (truncated)"
        return data
    
    elif isinstance(data, dict):
        return {
            k: _sanitize_for_logging(v, max_length) 
            for k, v in list(data.items())[:10]  # Limiter à 10 clés
        }
    
    elif isinstance(data, (list, tuple)):
        if len(data) > 5:  # Limiter à 5 éléments
            return [_sanitize_for_logging(item, max_length) for item in data[:5]] + ["... (more items)"]
        return [_sanitize_for_logging(item, max_length) for item in data]
    
    elif isinstance(data, (int, float, bool, type(None))):
        return data
    
    else:
        # Pour les objets complexes, retourner juste le type
        return f"<{type(data).__name__}>"


# Décorateur pour retry avec logging
def log_retry(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Décorateur pour retry avec logging automatique
    
    Args:
        max_retries: Nombre maximum de tentatives
        delay: Délai initial entre les tentatives (secondes)
        backoff: Facteur multiplicatif du délai
        
    Example:
        @log_retry(max_retries=3, delay=1.0)
        async def unstable_operation():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            func_name = func.__qualname__
            current_delay = delay
            
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        logger.info(
                            f"🔄 Nouvelle tentative: {func_name}",
                            function=func_name,
                            attempt=attempt + 1,
                            max_retries=max_retries
                        )
                    
                    result = await func(*args, **kwargs)
                    
                    if attempt > 0:
                        logger.info(
                            f"✅ Succès après retry: {func_name}",
                            function=func_name,
                            attempts=attempt + 1
                        )
                    
                    return result
                    
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(
                            f"❌ Échec définitif après {max_retries} tentatives: {func_name}",
                            function=func_name,
                            attempts=max_retries,
                            error_type=type(e).__name__,
                            error_message=str(e),
                            exc_info=True
                        )
                        raise
                    
                    logger.warning(
                        f"⚠️ Tentative échouée: {func_name}",
                        function=func_name,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        next_retry_in=current_delay,
                        error_type=type(e).__name__,
                        error_message=str(e)
                    )
                    
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
        
        return wrapper
    
    return decorator


# Import asyncio for retry decorator
import asyncio

