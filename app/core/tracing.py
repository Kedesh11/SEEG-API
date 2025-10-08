"""
Module de tracing distribué pour l'application SEEG-API.

Utilise OpenTelemetry pour implémenter le tracing distribué,
permettant de suivre les requêtes à travers tous les services.
"""
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from opentelemetry.trace import Status, StatusCode
from opentelemetry.propagate import set_global_textmap
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from contextlib import contextmanager
from typing import Dict, Any, Optional, Callable
from functools import wraps
import structlog

logger = structlog.get_logger(__name__)


def safe_log(level: str, message: str, **kwargs):
    """
    Log avec gestion d'erreur pour éviter les problèmes de handler.
    Fallback vers print si le logger échoue.
    """
    try:
        getattr(logger, level)(message, **kwargs)
    except (TypeError, AttributeError) as e:
        print(f"{level.upper()}: {message} - {kwargs}")


class TracingConfig:
    """Configuration pour le tracing."""
    
    def __init__(
        self,
        service_name: str = "seeg-api",
        service_version: str = "1.0.0",
        environment: str = "production",
        otlp_endpoint: Optional[str] = None,
        jaeger_endpoint: Optional[str] = None,
        console_export: bool = False,
        sample_rate: float = 1.0
    ):
        self.service_name = service_name
        self.service_version = service_version
        self.environment = environment
        self.otlp_endpoint = otlp_endpoint
        self.jaeger_endpoint = jaeger_endpoint
        self.console_export = console_export
        self.sample_rate = sample_rate


class TracingManager:
    """Gestionnaire du tracing distribué."""
    
    def __init__(self, config: TracingConfig):
        self.config = config
        self.tracer_provider = None
        self.tracer = None
        self._setup_tracing()
    
    def _setup_tracing(self):
        """Configure le système de tracing."""
        # Créer la resource avec les métadonnées du service
        resource = Resource.create({
            SERVICE_NAME: self.config.service_name,
            SERVICE_VERSION: self.config.service_version,
            "environment": self.config.environment,
            "deployment.environment": self.config.environment,
        })
        
        # Créer le provider
        self.tracer_provider = TracerProvider(resource=resource)
        
        # Configurer les exporters
        if self.config.otlp_endpoint:
            otlp_exporter = OTLPSpanExporter(
                endpoint=self.config.otlp_endpoint,
                insecure=True
            )
            self.tracer_provider.add_span_processor(
                BatchSpanProcessor(otlp_exporter)
            )
        
        if self.config.jaeger_endpoint:
            jaeger_exporter = JaegerExporter(
                agent_host_name=self.config.jaeger_endpoint.split(':')[0],
                agent_port=int(self.config.jaeger_endpoint.split(':')[1]) if ':' in self.config.jaeger_endpoint else 6831,
                max_tag_value_length=1024
            )
            self.tracer_provider.add_span_processor(
                BatchSpanProcessor(jaeger_exporter)
            )
        
        if self.config.console_export:
            console_exporter = ConsoleSpanExporter()
            self.tracer_provider.add_span_processor(
                BatchSpanProcessor(console_exporter)
            )
        
        # Définir le provider global
        trace.set_tracer_provider(self.tracer_provider)
        
        # Définir le propagateur
        set_global_textmap(TraceContextTextMapPropagator())
        
        # Obtenir le tracer
        self.tracer = trace.get_tracer(
            self.config.service_name,
            self.config.service_version
        )
        
        safe_log("info", "Tracing configuré", config=self.config.__dict__)
    
    def instrument_app(self, app):
        """
        Instrumente l'application FastAPI.
        
        Args:
            app: Instance FastAPI
        """
        FastAPIInstrumentor.instrument_app(
            app,
            tracer_provider=self.tracer_provider,
            excluded_urls="health,metrics"
        )
        
        safe_log("info", "Application FastAPI instrumentée")
    
    def instrument_sqlalchemy(self, engine):
        """
        Instrumente SQLAlchemy.
        
        Args:
            engine: Engine SQLAlchemy
        """
        SQLAlchemyInstrumentor().instrument(
            engine=engine,
            tracer_provider=self.tracer_provider
        )
        
        safe_log("info", "SQLAlchemy instrumenté")
    
    def instrument_asyncpg(self):
        """Instrumente AsyncPG."""
        AsyncPGInstrumentor().instrument(
            tracer_provider=self.tracer_provider
        )
        
        safe_log("info", "AsyncPG instrumenté")
    
    def instrument_redis(self):
        """Instrumente Redis."""
        RedisInstrumentor().instrument(
            tracer_provider=self.tracer_provider
        )
        
        safe_log("info", "Redis instrumenté")
    
    def instrument_httpx(self):
        """Instrumente HTTPX pour les appels HTTP sortants."""
        HTTPXClientInstrumentor().instrument(
            tracer_provider=self.tracer_provider
        )
        
        safe_log("info", "HTTPX instrumenté")


# Instance globale du gestionnaire de tracing
tracing_manager = None


def init_tracing(config: TracingConfig):
    """
    Initialise le système de tracing.
    
    Args:
        config: Configuration du tracing
    """
    global tracing_manager
    tracing_manager = TracingManager(config)
    return tracing_manager


def get_tracer() -> trace.Tracer:
    """Obtient le tracer actuel."""
    if tracing_manager:
        return tracing_manager.tracer
    return trace.get_tracer(__name__)


@contextmanager
def create_span(
    name: str,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL,
    attributes: Dict[str, Any] = None
):
    """
    Crée un span de tracing.
    
    Args:
        name: Nom du span
        kind: Type de span
        attributes: Attributs du span
        
    Yields:
        Span actif
    """
    tracer = get_tracer()
    with tracer.start_as_current_span(
        name,
        kind=kind,
        attributes=attributes or {}
    ) as span:
        try:
            yield span
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise


def trace_method(
    span_name: Optional[str] = None,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None
):
    """
    Décorateur pour tracer une méthode.
    
    Args:
        span_name: Nom du span (par défaut: nom de la méthode)
        kind: Type de span
        attributes: Attributs additionnels
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            name = span_name or f"{func.__module__}.{func.__name__}"
            
            with create_span(name, kind, attributes) as span:
                # Ajouter les paramètres comme attributs
                if args:
                    span.set_attribute("args.count", len(args))
                if kwargs:
                    for key, value in kwargs.items():
                        if isinstance(value, (str, int, float, bool)):
                            span.set_attribute(f"kwargs.{key}", value)
                
                result = await func(*args, **kwargs)
                
                # Ajouter le résultat si possible
                if isinstance(result, (str, int, float, bool)):
                    span.set_attribute("result", result)
                elif hasattr(result, '__len__'):
                    span.set_attribute("result.length", len(result))
                
                return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            name = span_name or f"{func.__module__}.{func.__name__}"
            
            with create_span(name, kind, attributes) as span:
                # Ajouter les paramètres comme attributs
                if args:
                    span.set_attribute("args.count", len(args))
                if kwargs:
                    for key, value in kwargs.items():
                        if isinstance(value, (str, int, float, bool)):
                            span.set_attribute(f"kwargs.{key}", value)
                
                result = func(*args, **kwargs)
                
                # Ajouter le résultat si possible
                if isinstance(result, (str, int, float, bool)):
                    span.set_attribute("result", result)
                elif hasattr(result, '__len__'):
                    span.set_attribute("result.length", len(result))
                
                return result
        
        # Retourner le wrapper approprié
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def add_span_attributes(**attributes):
    """
    Ajoute des attributs au span actuel.
    
    Args:
        **attributes: Attributs à ajouter
    """
    span = trace.get_current_span()
    if span and span.is_recording():
        for key, value in attributes.items():
            if isinstance(value, (str, int, float, bool)):
                span.set_attribute(key, value)


def add_span_event(name: str, attributes: Dict[str, Any] = None):
    """
    Ajoute un événement au span actuel.
    
    Args:
        name: Nom de l'événement
        attributes: Attributs de l'événement
    """
    span = trace.get_current_span()
    if span and span.is_recording():
        span.add_event(name, attributes or {})


def set_span_error(error: Exception):
    """
    Marque le span actuel comme erreur.
    
    Args:
        error: Exception
    """
    span = trace.get_current_span()
    if span and span.is_recording():
        span.set_status(Status(StatusCode.ERROR, str(error)))
        span.record_exception(error)


# Décorateurs spécialisés pour différents types d'opérations
trace_database = lambda name=None: trace_method(
    span_name=name,
    kind=trace.SpanKind.CLIENT,
    attributes={"db.system": "postgresql"}
)

trace_cache = lambda name=None: trace_method(
    span_name=name,
    kind=trace.SpanKind.CLIENT,
    attributes={"cache.system": "redis"}
)

trace_http_client = lambda name=None: trace_method(
    span_name=name,
    kind=trace.SpanKind.CLIENT,
    attributes={"http.client": True}
)

trace_business = lambda name=None: trace_method(
    span_name=name,
    kind=trace.SpanKind.INTERNAL,
    attributes={"business.operation": True}
)


def setup_tracing():
    """Configure et initialise le tracing pour l'application."""
    from app.core.config.config import settings
    
    # Créer la configuration de tracing
    config = TracingConfig(
        service_name=settings.APP_NAME,
        service_version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        otlp_endpoint=getattr(settings, 'OTLP_ENDPOINT', None),
        jaeger_endpoint=getattr(settings, 'JAEGER_ENDPOINT', None),
        console_export=settings.DEBUG,
        sample_rate=getattr(settings, 'TRACING_SAMPLE_RATE', 1.0)
    )
    
    # Initialiser le tracer (l'initialisation se fait automatiquement dans __init__)
    tracer = TracingManager(config)
    
    safe_log("info", "Tracing configuré avec succès", 
             service_name=config.service_name,
             environment=config.environment)
    
    return tracer
