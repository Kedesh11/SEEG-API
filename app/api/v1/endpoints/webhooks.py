import os
from fastapi import APIRouter, Header, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import Any, Optional
import httpx
import structlog

from app.db.database import get_db
from app.services.blob_storage import BlobStorageService
from app.services.etl_data_warehouse import ETLDataWarehouseService

from app.core.config.config import settings

router = APIRouter()

logger = structlog.get_logger(__name__)


class ApplicationSubmittedPayload(BaseModel):
    application_id: str = Field(..., description="ID de la candidature (UUID)")
    last_watermark: Optional[str] = Field(
        default=None,
        description="Horodatage ISO8601 pour export incrémental (optionnel)"
    )


async def _call_azure_function_on_application_submitted(
    payload: ApplicationSubmittedPayload
) -> None:
    """Appelle l'Azure Function on_application_submitted si configurée.
    - AZ_FUNC_ON_APP_SUBMITTED_URL: URL HTTP de la Function
    - AZ_FUNC_ON_APP_SUBMITTED_KEY: (optionnel) clé de fonction
    """
    func_url = os.environ.get("AZ_FUNC_ON_APP_SUBMITTED_URL", "").strip()
    func_key = os.environ.get("AZ_FUNC_ON_APP_SUBMITTED_KEY", "").strip()
    if not func_url:
        logger.warning("Azure Function URL non définie - appel ignoré")
        return

    params = {}
    if func_key:
        params["code"] = func_key

    timeout = httpx.Timeout(10.0, read=60.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.post(func_url, params=params, json=payload.model_dump())
            if resp.status_code >= 400:
                logger.error("Azure Function erreur",
                             extra={"status": resp.status_code,
                                    "text": resp.text[:500]})
            else:
                logger.info("Azure Function succès",
                            extra={"status": resp.status_code})
        except Exception as exc:
            logger.exception("Erreur appel Azure Function", exc_info=exc)


@router.post(
    "/application-submitted",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Webhook: ETL temps réel vers Blob Storage",
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
            "202": {"description": "Reçu - export vers Blob Storage en cours"},
            "401": {"description": "Non autorisé"},
            "404": {"description": "Candidature introuvable"},
            "500": {"description": "Erreur lors de l'export"}
        },
    },
)
async def on_application_submitted(
    payload: ApplicationSubmittedPayload,
    db: Any = Depends(get_db),
    x_webhook_token: Optional[str] = Header(default=None, alias="X-Webhook-Token"),
):
    """
    Réception d'un événement de soumission de candidature.
    Exporte en temps réel vers Azure Blob Storage (Data Lake).

    **Flow ETL Temps Réel:**
    1. Récupération des données complètes de la candidature depuis PostgreSQL
    2. Export JSON vers Blob Storage (conteneur 'raw')
    3. Export des PDF séparément (pour OCR)
    4. Optionnel: Appel Azure Function pour traitement supplémentaire

    **Sécurité:**
    - Header requis: X-Webhook-Token (si WEBHOOK_SECRET défini)

    **Format d'export:**
    ```
    raw/applications/ingestion_date=2025-10-17/json/{application_id}.json
    raw/applications/ingestion_date=2025-10-17/documents/{application_id}/cv_xxx.pdf
    ```
    """
    # Validation du webhook token
    secret = os.environ.get("WEBHOOK_SECRET", "").strip()

    if secret:
        if not x_webhook_token or x_webhook_token != secret:
            logger.warning(
                "Webhook non autorisé: token invalide ou absent",
                endpoint="application-submitted"
            )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Webhook non autorisé")
    else:
        logger.warning(
            "WEBHOOK_SECRET non défini - la validation du webhook est désactivée",
            endpoint="application-submitted"
        )

    logger.info(
        "Webhook reçu: application-submitted",
        application_id=payload.application_id,
        last_watermark=payload.last_watermark
    )

    try:
        # ========================================================================
        # ÉTAPE 1 : Récupérer la candidature avec TOUTES ses relations
        # ========================================================================
        from bson import ObjectId
        app_id = payload.application_id
        app_query = {"_id": ObjectId(app_id) if len(str(app_id)) == 24 else app_id}

        application_dict_raw = await db.applications.find_one(app_query)

        if not application_dict_raw:
            logger.warning(
                "Candidature introuvable pour export",
                application_id=payload.application_id
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidature introuvable"
            )

        candidate_id = application_dict_raw.get("candidate_id")
        job_offer_id = application_dict_raw.get("job_offer_id")

        candidate_query = {"_id": ObjectId(candidate_id) if len(str(candidate_id)) == 24 else candidate_id}
        candidate_dict = await db.users.find_one(candidate_query) if candidate_id else None

        offer_query = {"_id": ObjectId(job_offer_id) if len(str(job_offer_id)) == 24 else job_offer_id}
        job_offer_dict = await db.job_offers.find_one(offer_query) if job_offer_id else None

        doc_query = {"application_id": str(app_id)}
        documents_list = await db.documents.find(doc_query).to_list(length=None)

        # ========================================================================
        # ÉTAPE 2 : Récupérer le profil candidat complet
        # ========================================================================
        candidate_profile = None
        if candidate_id:
            profile_query = {"user_id": str(candidate_id)}
            candidate_profile = await db.candidate_profiles.find_one(profile_query)

        # ========================================================================
        # ÉTAPE 3 : Construire le dictionnaire complet avec TOUTES les infos
        # ========================================================================
        application_dict = {
            # Candidature
            "id": str(application_dict_raw.get("_id", application_dict_raw.get("id"))),
            "candidate_id": str(application_dict_raw.get("candidate_id")),
            "job_offer_id": str(application_dict_raw.get("job_offer_id")),
            "status": application_dict_raw.get("status"),
            "mtp_answers": application_dict_raw.get("mtp_answers"),
            "has_been_manager": application_dict_raw.get("has_been_manager"),
            "ref_entreprise": application_dict_raw.get("ref_entreprise"),
            "ref_fullname": application_dict_raw.get("ref_fullname"),
            "ref_mail": application_dict_raw.get("ref_mail"),
            "ref_contact": application_dict_raw.get("ref_contact"),
            "reference_contacts": application_dict_raw.get("reference_contacts"),
            "availability_start": str(application_dict_raw.get("availability_start")) if application_dict_raw.get("availability_start") else None,
            "created_at": str(application_dict_raw.get("created_at")) if application_dict_raw.get("created_at") else None,
            "updated_at": str(application_dict_raw.get("updated_at")) if application_dict_raw.get("updated_at") else None,

            # Candidat (User complet)
            "candidate": {
                "id": str(candidate_dict.get("_id", candidate_dict.get("id"))),
                "email": candidate_dict.get("email"),
                "first_name": candidate_dict.get("first_name"),
                "last_name": candidate_dict.get("last_name"),
                "phone": candidate_dict.get("phone"),
                "date_of_birth": candidate_dict.get("date_of_birth").isoformat() if candidate_dict.get("date_of_birth") is not None and hasattr(candidate_dict.get("date_of_birth"), "isoformat") else str(candidate_dict.get("date_of_birth")) if candidate_dict.get("date_of_birth") else None,
                "sexe": candidate_dict.get("sexe"),
                "adresse": candidate_dict.get("adresse"),
                "matricule": candidate_dict.get("matricule"),
                "poste_actuel": candidate_dict.get("poste_actuel"),
                "annees_experience": candidate_dict.get("annees_experience"),
                "role": candidate_dict.get("role"),
                "candidate_status": candidate_dict.get("candidate_status"),
                "statut": candidate_dict.get("statut"),
                "is_internal_candidate": candidate_dict.get("is_internal_candidate"),
                "email_verified": candidate_dict.get("email_verified"),
                "is_active": candidate_dict.get("is_active"),
                "created_at": candidate_dict.get("created_at").isoformat() if candidate_dict.get("created_at") is not None and hasattr(candidate_dict.get("created_at"), "isoformat") else str(candidate_dict.get("created_at")) if candidate_dict.get("created_at") else None,
            } if candidate_dict else None,

            # Profil Candidat (CandidateProfile complet)
            "candidate_profile": {
                "id": str(candidate_profile.get("_id", candidate_profile.get("id"))),
                "address": candidate_profile.get("address"),
                "availability": candidate_profile.get("availability"),
                "birth_date": candidate_profile.get("birth_date").isoformat() if candidate_profile.get("birth_date") is not None and hasattr(candidate_profile.get("birth_date"), "isoformat") else str(candidate_profile.get("birth_date")) if candidate_profile.get("birth_date") else None,
                "current_department": candidate_profile.get("current_department"),
                "current_position": candidate_profile.get("current_position"),
                "cv_url": candidate_profile.get("cv_url"),
                "education": candidate_profile.get("education"),
                "expected_salary_min": candidate_profile.get("expected_salary_min"),
                "expected_salary_max": candidate_profile.get("expected_salary_max"),
                "gender": candidate_profile.get("gender"),
                "linkedin_url": candidate_profile.get("linkedin_url"),
                "portfolio_url": candidate_profile.get("portfolio_url"),
                "skills": candidate_profile.get("skills"),
                "years_experience": candidate_profile.get("years_experience"),
            } if candidate_profile else None,

            # Offre d'emploi
            "job_offer": {
                "id": str(job_offer_dict.get("_id", job_offer_dict.get("id"))),
                "title": job_offer_dict.get("title"),
                "description": job_offer_dict.get("description"),
                "location": job_offer_dict.get("location"),
                "contract_type": job_offer_dict.get("contract_type"),
                "department": job_offer_dict.get("department"),
                "offer_status": job_offer_dict.get("offer_status"),
                "questions_mtp": job_offer_dict.get("questions_mtp"),
                "created_at": str(job_offer_dict.get("created_at")) if job_offer_dict.get("created_at") else None,
            } if job_offer_dict else None
        }

        logger.info(
            "Candidature complète récupérée pour export",
            application_id=payload.application_id,
            candidate_email=application_dict.get("candidate", {}).get("email") if application_dict.get("candidate") else None,
            has_profile=application_dict.get("candidate_profile") is not None,
            documents_count=len(documents_list)
        )

        # ========================================================================
        # ÉTAPE 4 : Préparer les documents PDF (bytes depuis PostgreSQL)
        # ========================================================================
        documents_for_export = []
        if documents_list:
            for doc in documents_list:
                documents_for_export.append({
                    "document_type": doc.get("document_type"),
                    "file_name": doc.get("file_name"),
                    "file_data": doc.get("file_data"),  # bytes
                    "file_size": doc.get("file_size"),
                    "uploaded_at": doc.get("uploaded_at").isoformat() if doc.get("uploaded_at") is not None and hasattr(doc.get("uploaded_at"), "isoformat") else str(doc.get("uploaded_at")) if doc.get("uploaded_at") else None
                })

        # ========================================================================
        # ÉTAPE 5 : Export vers Blob Storage (Architecture Star Schema)
        # ========================================================================
        connection_string = (settings.AZURE_STORAGE_CONNECTION_STRING or "").strip()
        export_result = None

        if connection_string:
            blob_service = BlobStorageService(connection_string, container_name="raw")
            etl_service = ETLDataWarehouseService(blob_service)

            # Export en Star Schema: dimensions + facts + documents PDF
            export_result = await etl_service.export_star_schema(
                application_dict,
                documents_for_export
            )

            logger.info(
                "Export Data Warehouse réussi (Star Schema)",
                application_id=payload.application_id,
                dim_candidate_exported=export_result["dim_candidate"] is not None,
                dim_job_offer_exported=export_result["dim_job_offer"] is not None,
                fact_exported=export_result["fact_application"] is not None,
                pdfs_exported=len(export_result["documents"]),
                total_size_mb=round(export_result["total_size_bytes"] / 1024 / 1024, 2)
            )
        else:
            logger.warning(
                "AZURE_STORAGE_CONNECTION_STRING non définie - export Blob Storage ignoré",
                application_id=payload.application_id
            )

        # ========================================================================
        # ÉTAPE 6 : Optionnel - Appel Azure Function pour traitement OCR
        # ========================================================================
        await _call_azure_function_on_application_submitted(payload)

        return {
            "success": True,
            "message": "Export ETL Data Warehouse effectué (Star Schema)",
            "data": {
                "application_id": payload.application_id,
                "exported_to_blob": connection_string != "",
                "tables_exported": {
                    "dim_candidates": export_result["dim_candidate"]["path"] if export_result and export_result.get("dim_candidate") else None,
                    "dim_job_offers": export_result["dim_job_offer"]["path"] if export_result and export_result.get("dim_job_offer") else None,
                    "fact_applications": export_result["fact_application"]["path"] if export_result and export_result.get("fact_application") else None,
                },
                "documents_count": len(export_result["documents"]) if export_result else 0,
                "total_size_mb": round(export_result["total_size_bytes"] / 1024 / 1024, 2) if export_result else 0
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Erreur critique lors de l'ETL temps réel",
            application_id=payload.application_id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'export: {str(e)}"
        )
