"""
Endpoints de monitoring pour l'application SEEG-API.

Ce module fournit les endpoints pour exposer les métriques Prometheus
et autres informations de monitoring.
"""
from fastapi import APIRouter, Depends, Response
from app.core.dependencies import get_current_admin_user
from app.core.metrics import metrics_collector
from app.models.user import User
import structlog

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("/metrics", response_class=Response)
async def get_prometheus_metrics(
    current_user: User = Depends(get_current_admin_user)
):
    """
    Expose les métriques Prometheus.
    
    Nécessite les droits administrateur.
    """
    try:
        # Générer les métriques au format Prometheus
        metrics_data = metrics_collector.generate_metrics()
        
        return Response(
            content=metrics_data,
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )
    except Exception as e:
        logger.error("Erreur lors de la génération des métriques", error=str(e))
        return Response(
            content="# Erreur lors de la génération des métriques\n",
            media_type="text/plain; version=0.0.4; charset=utf-8",
            status_code=500
        )


@router.get("/stats")
async def get_application_stats(
    current_user: User = Depends(get_current_admin_user)
):
    """
    Retourne des statistiques détaillées sur l'application.
    
    Nécessite les droits administrateur.
    """
    try:
        stats = {
            "http_metrics": {
                "total_requests": metrics_collector.http_requests_total._value.sum(),
                "total_errors": metrics_collector.errors_total._value.sum(),
                "avg_request_duration": metrics_collector.get_average_request_duration()
            },
            "cache_metrics": {
                "hits": metrics_collector.cache_hits_total._value.sum(),
                "misses": metrics_collector.cache_misses_total._value.sum(),
                "hit_rate": metrics_collector.get_cache_hit_rate()
            },
            "business_metrics": {
                "applications_created": metrics_collector.applications_created_total._value.sum(),
                "documents_uploaded": metrics_collector.documents_uploaded_total._value.sum(),
                "auth_attempts": metrics_collector.auth_attempts_total._value.sum()
            }
        }
        
        return stats
    except Exception as e:
        logger.error("Erreur lors de la récupération des statistiques", error=str(e))
        return {"error": "Erreur lors de la récupération des statistiques"}