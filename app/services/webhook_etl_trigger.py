"""
Service de déclenchement automatique du webhook ETL
====================================================
Architecture: Event-Driven + Separation of Concerns + Fail-Safe

Principes SOLID appliqués:
- Single Responsibility: Ne fait qu'une chose - déclencher le webhook ETL
- Open/Closed: Extensible sans modification
- Dependency Inversion: Dépend d'abstractions (httpx.AsyncClient)
- Interface Segregation: Interface minimale et claire

Pattern: Fire-and-Forget avec gestion d'erreur non-bloquante
"""
from typing import Optional
import httpx
import structlog
from datetime import datetime

from app.core.config.config import settings

logger = structlog.get_logger(__name__)


class ETLWebhookTriggerService:
    """
    Service pour déclencher automatiquement le webhook ETL lors de la création d'une candidature.
    
    **Pattern: Fire-and-Forget**
    - Non-bloquant: ne ralentit pas la création de candidature
    - Fail-safe: échec du webhook n'empêche pas la candidature
    - Observabilité: logs structurés pour debugging
    
    **Utilisation:**
    ```python
    etl_trigger = ETLWebhookTriggerService()
    await etl_trigger.trigger_application_submitted(application_id="uuid...")
    ```
    """
    
    def __init__(
        self,
        webhook_url: Optional[str] = None,
        webhook_secret: Optional[str] = None,
        timeout: float = 5.0
    ):
        """
        Initialise le service de déclenchement webhook ETL.
        
        Args:
            webhook_url: URL du webhook ETL (défaut: depuis settings ou localhost)
            webhook_secret: Secret d'authentification (défaut: depuis settings)
            timeout: Timeout en secondes pour l'appel HTTP (défaut: 5s)
        """
        # URL du webhook : configurable via env ou défaut localhost
        self.webhook_url = webhook_url or self._get_webhook_url()
        
        # Secret webhook : depuis settings ou variable d'environnement
        self.webhook_secret = webhook_secret or getattr(settings, "WEBHOOK_SECRET", "")
        
        self.timeout = timeout
        self.enabled = self._is_enabled()
    
    def _get_webhook_url(self) -> str:
        """
        Récupère l'URL du webhook selon l'environnement.
        
        Priorité:
        1. Variable WEBHOOK_ETL_URL (si définie explicitement)
        2. Variable API_URL (URL de l'API en production)
        3. Fallback localhost (développement uniquement)
        
        Returns:
            URL du webhook ETL
        """
        # 1. URL webhook explicite (priorité maximale)
        webhook_etl_url = getattr(settings, "WEBHOOK_ETL_URL", None)
        if webhook_etl_url:
            return webhook_etl_url
        
        # 2. Construire depuis l'URL de l'API (production par défaut)
        # En production: settings.API_URL = "https://api.seeg.ga"
        # En développement: settings.API_URL = "http://localhost:8000"
        api_base_url = getattr(settings, "API_URL", None)
        
        # 3. Fallback développement si aucune URL définie
        if not api_base_url:
            api_base_url = "http://localhost:8000"
        
        return f"{api_base_url}/api/v1/webhooks/application-submitted"
    
    def _is_enabled(self) -> bool:
        """
        Vérifie si le service ETL webhook est activé.
        
        Returns:
            True si le service est activé
        """
        # Vérifier si Azure Storage est configuré (nécessaire pour ETL)
        has_storage = bool(
            getattr(settings, "AZURE_STORAGE_CONNECTION_STRING", "").strip()
        )
        
        # Désactiver si pas de configuration storage
        if not has_storage:
            logger.info(
                "ETL Webhook désactivé: AZURE_STORAGE_CONNECTION_STRING non configuré"
            )
            return False
        
        return True
    
    async def trigger_application_submitted(
        self,
        application_id: str,
        last_watermark: Optional[str] = None
    ) -> dict:
        """
        Déclenche le webhook ETL pour une candidature soumise.
        
        **Pattern: Fire-and-Forget avec logging**
        - Appel asynchrone non-bloquant
        - Ne lève pas d'exception (fail-safe)
        - Retourne un statut pour observabilité
        
        Args:
            application_id: ID de la candidature (UUID string)
            last_watermark: Timestamp ISO8601 pour export incrémental (optionnel)
        
        Returns:
            Dict avec statut du déclenchement:
            {
                "triggered": bool,
                "status_code": int | None,
                "error": str | None,
                "webhook_url": str
            }
        """
        if not self.enabled:
            logger.debug(
                "ETL Webhook ignoré (service désactivé)",
                application_id=application_id
            )
            return {
                "triggered": False,
                "status_code": None,
                "error": "Service désactivé",
                "webhook_url": self.webhook_url
            }
        
        try:
            logger.info(
                "🚀 Déclenchement webhook ETL",
                application_id=application_id,
                webhook_url=self.webhook_url
            )
            
            # Préparer le payload
            payload = {
                "application_id": application_id,
                "last_watermark": last_watermark
            }
            
            # Headers avec authentification
            headers = {}
            if self.webhook_secret:
                headers["X-Webhook-Token"] = self.webhook_secret
            
            # Appel HTTP asynchrone avec timeout
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    headers=headers
                )
                
                # Vérifier le statut de la réponse
                if response.status_code == 202:  # Accepted
                    logger.info(
                        "✅ Webhook ETL déclenché avec succès",
                        application_id=application_id,
                        status_code=response.status_code,
                        webhook_url=self.webhook_url
                    )
                    return {
                        "triggered": True,
                        "status_code": response.status_code,
                        "error": None,
                        "webhook_url": self.webhook_url
                    }
                else:
                    logger.warning(
                        "⚠️ Webhook ETL réponse inattendue",
                        application_id=application_id,
                        status_code=response.status_code,
                        response_text=response.text[:200],
                        webhook_url=self.webhook_url
                    )
                    return {
                        "triggered": True,
                        "status_code": response.status_code,
                        "error": f"Status {response.status_code}",
                        "webhook_url": self.webhook_url
                    }
        
        except httpx.TimeoutException as e:
            logger.warning(
                "⚠️ Timeout webhook ETL",
                application_id=application_id,
                timeout=self.timeout,
                error=str(e),
                webhook_url=self.webhook_url
            )
            return {
                "triggered": False,
                "status_code": None,
                "error": f"Timeout après {self.timeout}s",
                "webhook_url": self.webhook_url
            }
        
        except httpx.ConnectError as e:
            logger.warning(
                "⚠️ Erreur connexion webhook ETL",
                application_id=application_id,
                error=str(e),
                webhook_url=self.webhook_url
            )
            return {
                "triggered": False,
                "status_code": None,
                "error": "Erreur de connexion",
                "webhook_url": self.webhook_url
            }
        
        except Exception as e:
            logger.error(
                "❌ Erreur inattendue webhook ETL",
                application_id=application_id,
                error=str(e),
                error_type=type(e).__name__,
                webhook_url=self.webhook_url
            )
            return {
                "triggered": False,
                "status_code": None,
                "error": f"{type(e).__name__}: {str(e)}",
                "webhook_url": self.webhook_url
            }


# Factory function pour dependency injection
def get_etl_webhook_trigger() -> ETLWebhookTriggerService:
    """
    Factory pour créer une instance du service ETL Webhook Trigger.
    
    Utilisé pour dependency injection dans FastAPI:
    ```python
    async def create_application(
        ...,
        etl_trigger: ETLWebhookTriggerService = Depends(get_etl_webhook_trigger)
    ):
        ...
        await etl_trigger.trigger_application_submitted(application_id)
    ```
    
    Returns:
        Instance configurée du service
    """
    return ETLWebhookTriggerService()

