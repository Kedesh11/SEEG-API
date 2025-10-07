"""
Configuration d'Azure Application Insights pour le monitoring
"""
import logging
import structlog
from typing import Optional
from opencensus.ext.azure.log_exporter import AzureLogHandler
from opencensus.ext.azure.trace_exporter import AzureExporter
from opencensus.trace.samplers import ProbabilitySampler
from opencensus.trace import config_integration
from opencensus.trace.tracer import Tracer

from app.core.config.config import settings

logger = structlog.get_logger(__name__)


class ApplicationInsights:
    """Gestionnaire Azure Application Insights"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialiser Application Insights (singleton)"""
        if not self._initialized:
            self.connection_string = settings.APPLICATIONINSIGHTS_CONNECTION_STRING
            self.enabled = bool(self.connection_string and self.connection_string != "")
            self.exporter: Optional[AzureExporter] = None
            self.tracer: Optional[Tracer] = None
            ApplicationInsights._initialized = True
    
    def setup(self):
        """Configurer Application Insights"""
        if not self.enabled:
            logger.warning(
                "Application Insights désactivé",
                reason="APPLICATIONINSIGHTS_CONNECTION_STRING non configuré"
            )
            return
        
        try:
            # Configuration du tracer
            self.exporter = AzureExporter(connection_string=self.connection_string)
            
            # Sampler : 100% en dev, 10% en prod
            sample_rate = 1.0 if settings.ENVIRONMENT == "development" else 0.1
            sampler = ProbabilitySampler(sample_rate)
            
            self.tracer = Tracer(exporter=self.exporter, sampler=sampler)
            
            # Intégrations automatiques
            config_integration.trace_integrations(['requests', 'logging'])
            
            # Configuration du logging handler
            self._setup_logging()
            
            logger.info(
                "Application Insights configuré",
                sample_rate=sample_rate,
                environment=settings.ENVIRONMENT
            )
            
        except Exception as e:
            # Ne pas propager l'erreur pendant les tests
            self.enabled = False
    
    def _setup_logging(self):
        """Configurer le handler de logging Azure"""
        try:
            # Ajouter le handler Azure au logger root
            azure_handler = AzureLogHandler(
                connection_string=self.connection_string
            )
            
            # Configurer le niveau de log
            log_level = logging.WARNING if settings.ENVIRONMENT == "production" else logging.INFO
            azure_handler.setLevel(log_level)
            
            # Ajouter au logger root
            root_logger = logging.getLogger()
            if root_logger is not None:
                root_logger.addHandler(azure_handler)
                logger.info("Handler de logging Azure configuré", level=log_level)
            
        except Exception as e:
            # Ne pas propager l'erreur pendant les tests
            pass
    
    def track_event(self, name: str, properties: dict = None):
        """
        Tracker un événement personnalisé
        
        Args:
            name: Nom de l'événement
            properties: Propriétés additionnelles
        """
        if not self.enabled or not self.tracer:
            return
        
        try:
            with self.tracer.span(name=name) as span:
                if properties:
                    for key, value in properties.items():
                        span.add_attribute(key, str(value))
                        
        except Exception as e:
            logger.error("Erreur lors du tracking d'événement", event=name, error=str(e))
    
    def track_exception(self, exception: Exception, properties: dict = None):
        """
        Tracker une exception
        
        Args:
            exception: L'exception à tracker
            properties: Propriétés additionnelles
        """
        if not self.enabled:
            return
        
        try:
            logger.error(
                "Exception trackée",
                exception_type=type(exception).__name__,
                exception_message=str(exception),
                properties=properties or {}
            )
        except Exception as e:
            logger.error("Erreur lors du tracking d'exception", error=str(e))
    
    def track_metric(self, name: str, value: float, properties: dict = None):
        """
        Tracker une métrique personnalisée
        
        Args:
            name: Nom de la métrique
            value: Valeur de la métrique
            properties: Propriétés additionnelles
        """
        if not self.enabled:
            return
        
        try:
            logger.info(
                "Métrique trackée",
                metric_name=name,
                metric_value=value,
                properties=properties or {}
            )
        except Exception as e:
            logger.error("Erreur lors du tracking de métrique", metric=name, error=str(e))
    
    def track_request(
        self, 
        name: str, 
        url: str, 
        duration: float, 
        response_code: int,
        success: bool,
        properties: dict = None
    ):
        """
        Tracker une requête HTTP
        
        Args:
            name: Nom de la requête
            url: URL de la requête
            duration: Durée en ms
            response_code: Code de réponse HTTP
            success: Succès ou échec
            properties: Propriétés additionnelles
        """
        if not self.enabled:
            return
        
        try:
            logger.info(
                "Requête trackée",
                request_name=name,
                url=url,
                duration_ms=duration,
                status_code=response_code,
                success=success,
                properties=properties or {}
            )
        except Exception as e:
            logger.error("Erreur lors du tracking de requête", request=name, error=str(e))


# Instance globale
app_insights = ApplicationInsights()

