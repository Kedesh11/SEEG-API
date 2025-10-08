"""
Module de gestion du cache pour l'application SEEG-API.

Implémente un système de cache avec Redis pour améliorer les performances
et réduire la charge sur la base de données.
"""
import json
import pickle
from typing import Any, Optional, Union, Callable
from datetime import timedelta
from functools import wraps
import hashlib
import redis
from redis import asyncio as aioredis
from app.core.config.config import settings
import structlog

logger = structlog.get_logger(__name__)


class CacheManager:
    """Gestionnaire de cache avec support Redis."""
    
    def __init__(self):
        """Initialise le gestionnaire de cache."""
        self.redis_url = settings.REDIS_URL if settings.REDIS_URL else "redis://localhost:6379/0"
        self.redis_client = None
        self.async_redis_client = None
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialise les clients Redis synchrone et asynchrone."""
        try:
            # Client synchrone
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Client asynchrone
            self.async_redis_client = aioredis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Test de connexion
            self.redis_client.ping()
            logger.info("Connexion Redis établie", redis_url=self.redis_url)
            
        except Exception as e:
            logger.error("Erreur connexion Redis", error=str(e))
            self.redis_client = None
            self.async_redis_client = None
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """
        Génère une clé de cache unique basée sur les arguments.
        
        Args:
            prefix: Préfixe de la clé
            *args: Arguments positionnels
            **kwargs: Arguments nommés
            
        Returns:
            Clé de cache unique
        """
        # Créer une représentation unique des arguments
        key_parts = [prefix]
        
        # Ajouter les arguments positionnels
        for arg in args:
            if isinstance(arg, (str, int, float, bool)):
                key_parts.append(str(arg))
            else:
                # Pour les objets complexes, utiliser un hash
                key_parts.append(hashlib.md5(str(arg).encode()).hexdigest()[:8])
        
        # Ajouter les arguments nommés triés
        for k, v in sorted(kwargs.items()):
            if isinstance(v, (str, int, float, bool)):
                key_parts.append(f"{k}:{v}")
            else:
                key_parts.append(f"{k}:{hashlib.md5(str(v).encode()).hexdigest()[:8]}")
        
        return ":".join(key_parts)
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Récupère une valeur du cache.
        
        Args:
            key: Clé de cache
            
        Returns:
            Valeur du cache ou None
        """
        if not self.async_redis_client:
            return None
        
        try:
            value = await self.async_redis_client.get(key)
            if value:
                # Essayer de décoder en JSON d'abord
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    # Si ce n'est pas du JSON, essayer pickle
                    try:
                        return pickle.loads(value.encode('latin-1'))
                    except:
                        return value
            return None
            
        except Exception as e:
            logger.error("Erreur lecture cache", key=key, error=str(e))
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        expire: Optional[Union[int, timedelta]] = None
    ) -> bool:
        """
        Stocke une valeur dans le cache.
        
        Args:
            key: Clé de cache
            value: Valeur à stocker
            expire: Durée d'expiration en secondes ou timedelta
            
        Returns:
            True si succès, False sinon
        """
        if not self.async_redis_client:
            return False
        
        try:
            # Sérialiser la valeur
            if isinstance(value, (dict, list)):
                serialized = json.dumps(value)
            else:
                serialized = pickle.dumps(value).decode('latin-1')
            
            # Convertir timedelta en secondes
            if isinstance(expire, timedelta):
                expire = int(expire.total_seconds())
            
            # Stocker dans Redis
            if expire:
                await self.async_redis_client.setex(key, expire, serialized)
            else:
                await self.async_redis_client.set(key, serialized)
            
            return True
            
        except Exception as e:
            logger.error("Erreur écriture cache", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Supprime une valeur du cache.
        
        Args:
            key: Clé de cache
            
        Returns:
            True si supprimé, False sinon
        """
        if not self.async_redis_client:
            return False
        
        try:
            result = await self.async_redis_client.delete(key)
            return bool(result)
        except Exception as e:
            logger.error("Erreur suppression cache", key=key, error=str(e))
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        Supprime toutes les clés correspondant au pattern.
        
        Args:
            pattern: Pattern de clés (ex: "user:*")
            
        Returns:
            Nombre de clés supprimées
        """
        if not self.async_redis_client:
            return 0
        
        try:
            keys = []
            async for key in self.async_redis_client.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                return await self.async_redis_client.delete(*keys)
            return 0
            
        except Exception as e:
            logger.error("Erreur suppression pattern", pattern=pattern, error=str(e))
            return 0
    
    async def exists(self, key: str) -> bool:
        """
        Vérifie si une clé existe dans le cache.
        
        Args:
            key: Clé de cache
            
        Returns:
            True si la clé existe
        """
        if not self.async_redis_client:
            return False
        
        try:
            return bool(await self.async_redis_client.exists(key))
        except Exception as e:
            logger.error("Erreur vérification existence", key=key, error=str(e))
            return False


# Instance globale du gestionnaire de cache
cache_manager = CacheManager()


def cache_key_wrapper(
    prefix: str,
    expire: Optional[Union[int, timedelta]] = 300,
    key_builder: Optional[Callable] = None
):
    """
    Décorateur pour mettre en cache le résultat d'une fonction asynchrone.
    
    Args:
        prefix: Préfixe de la clé de cache
        expire: Durée d'expiration (par défaut 5 minutes)
        key_builder: Fonction personnalisée pour construire la clé
    
    Example:
        @cache_key_wrapper("user", expire=timedelta(hours=1))
        async def get_user(user_id: str):
            return await db.get_user(user_id)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Construire la clé de cache
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                cache_key = cache_manager._generate_key(prefix, *args, **kwargs)
            
            # Vérifier le cache
            cached_value = await cache_manager.get(cache_key)
            if cached_value is not None:
                logger.debug("Cache hit", key=cache_key)
                return cached_value
            
            # Exécuter la fonction
            result = await func(*args, **kwargs)
            
            # Mettre en cache le résultat
            if result is not None:
                await cache_manager.set(cache_key, result, expire)
                logger.debug("Cache set", key=cache_key)
            
            return result
        
        # Ajouter des méthodes utilitaires
        wrapper.invalidate = lambda *args, **kwargs: cache_manager.delete(
            key_builder(*args, **kwargs) if key_builder else 
            cache_manager._generate_key(prefix, *args, **kwargs)
        )
        
        return wrapper
    return decorator


# Décorateurs de cache prédéfinis pour différents cas d'usage
cache_user = lambda expire=3600: cache_key_wrapper("user", expire=expire)
cache_job_offer = lambda expire=1800: cache_key_wrapper("job_offer", expire=expire)
cache_application = lambda expire=600: cache_key_wrapper("application", expire=expire)
cache_stats = lambda expire=300: cache_key_wrapper("stats", expire=expire)


# Fonctions utilitaires pour invalider le cache
async def invalidate_user_cache(user_id: str):
    """Invalide toutes les entrées de cache pour un utilisateur."""
    await cache_manager.delete_pattern(f"user:{user_id}:*")
    await cache_manager.delete_pattern(f"*:user_id:{user_id}:*")


async def invalidate_job_cache(job_id: str):
    """Invalide toutes les entrées de cache pour une offre d'emploi."""
    await cache_manager.delete_pattern(f"job_offer:{job_id}:*")
    await cache_manager.delete_pattern(f"*:job_offer_id:{job_id}:*")


async def invalidate_application_cache(application_id: str):
    """Invalide toutes les entrées de cache pour une candidature."""
    await cache_manager.delete_pattern(f"application:{application_id}:*")
    await cache_manager.delete_pattern(f"*:application_id:{application_id}:*")
