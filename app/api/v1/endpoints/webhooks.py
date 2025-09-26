from typing import Optional
import os
import logging
from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter()

logger = logging.getLogger(__name__)


class ApplicationSubmittedPayload(BaseModel):
    application_id: str = Field(..., description="ID de la candidature (UUID)")
    last_watermark: Optional[str] = Field(
        default=None,
        description="Horodatage ISO8601 pour export incrémental (optionnel)"
    )


@router.post(
    "/application-submitted",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Webhook: déclenche l'orchestrateur ETL pour une candidature",
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "example": {
                        "application_id": "00000000-0000-0000-0000-000000000001",
                        "last_watermark": "2025-01-01T00:00:00Z"
                    }
                }
            }
        },
        "responses": {
            "202": {"description": "Reçu - traitement asynchrone déclenché"},
            "401": {"description": "Non autorisé"}
        },
    },
)
async def on_application_submitted(
    payload: ApplicationSubmittedPayload,
    x_webhook_token: Optional[str] = Header(default=None, alias="X-Webhook-Token"),
):
    """Réception d'un événement de soumission de candidature.

    - Valide un jeton simple via l'en-tête `X-Webhook-Token` si `WEBHOOK_SECRET` est défini.
    - Déclenche ensuite un traitement asynchrone (intégration Azure Function à brancher).
    - Retourne 202 immédiatement.
    """
    secret = os.environ.get("WEBHOOK_SECRET", "").strip()

    if secret:
        if not x_webhook_token or x_webhook_token != secret:
            logger.warning(
                "Webhook non autorisé: token invalide ou absent",
                extra={"endpoint": "application-submitted"}
            )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Webhook non autorisé")
    else:
        logger.warning(
            "WEBHOOK_SECRET non défini - la validation du webhook est désactivée",
            extra={"endpoint": "application-submitted"}
        )

    logger.info(
        "Webhook reçu: application-submitted",
        extra={
            "application_id": payload.application_id,
            "last_watermark": payload.last_watermark,
        },
    )

    # TODO: Intégration Azure Function HTTP à appeler ici (via requests/azure-identity)
    # Exemple (pseudo-code):
    # await call_azure_function_on_application_submitted(payload.application_id, payload.last_watermark)

    return {"success": True, "message": "Traitement en file", "data": {"application_id": payload.application_id}} 