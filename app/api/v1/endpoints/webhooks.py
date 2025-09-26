from typing import Optional
import os
import logging
from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field
import httpx

router = APIRouter()

logger = logging.getLogger(__name__)


class ApplicationSubmittedPayload(BaseModel):
    application_id: str = Field(..., description="ID de la candidature (UUID)")
    last_watermark: Optional[str] = Field(
        default=None,
        description="Horodatage ISO8601 pour export incrémental (optionnel)"
    )


async def _call_azure_function_on_application_submitted(payload: ApplicationSubmittedPayload) -> None:
    """Appelle l’Azure Function HTTP on_application_submitted si configurée.
    Lecture des variables d'environnement:
    - AZ_FUNC_ON_APP_SUBMITTED_URL: URL HTTP de la Function (ex: https://<func>.azurewebsites.net/api/on_application_submitted)
    - AZ_FUNC_ON_APP_SUBMITTED_KEY: (optionnel) clé de fonction à passer en query string `code`
    """
    func_url = os.environ.get("AZ_FUNC_ON_APP_SUBMITTED_URL", "").strip()
    func_key = os.environ.get("AZ_FUNC_ON_APP_SUBMITTED_KEY", "").strip()
    if not func_url:
        logger.warning("AZ_FUNC_ON_APP_SUBMITTED_URL non définie - appel Azure Function ignoré")
        return

    params = {}
    if func_key:
        params["code"] = func_key

    timeout = httpx.Timeout(10.0, read=60.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.post(func_url, params=params, json=payload.model_dump())
            if resp.status_code >= 400:
                logger.error("Azure Function on_application_submitted a renvoyé une erreur", extra={"status": resp.status_code, "text": resp.text[:500]})
            else:
                logger.info("Azure Function on_application_submitted appelée avec succès", extra={"status": resp.status_code})
        except Exception as exc:
            logger.exception("Erreur lors de l'appel à l’Azure Function on_application_submitted", exc_info=exc)


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
    """Réception d'un événement de soumission de candidature."""
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

    # Déléguer à l’Azure Function si configurée (asynchrone, non bloquant pour le client)
    await _call_azure_function_on_application_submitted(payload)

    return {"success": True, "message": "Traitement en file", "data": {"application_id": payload.application_id}} 