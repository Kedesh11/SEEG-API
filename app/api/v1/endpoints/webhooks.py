from typing import Optional
import os
import logging
import uuid
from fastapi import APIRouter, Header, HTTPException, status, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import httpx
import structlog

from app.db.database import get_db
from app.services.blob_storage import BlobStorageService
from app.services.etl_data_warehouse import ETLDataWarehouseService
from app.models.application import Application as ApplicationModel
from app.models.candidate_profile import CandidateProfile
from app.core.config.config import settings

router = APIRouter()

logger = structlog.get_logger(__name__)


class ApplicationSubmittedPayload(BaseModel):
    application_id: str = Field(..., description="ID de la candidature (UUID)")
    last_watermark: Optional[str] = Field(
        default=None,
        description="Horodatage ISO8601 pour export incrémental (optionnel)"
    )


async def _call_azure_function_on_application_submitted(payload: ApplicationSubmittedPayload) -> None:
    """Appelle l'Azure Function HTTP on_application_submitted si configurée.
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
            logger.exception("Erreur lors de l'appel à l'Azure Function on_application_submitted", exc_info=exc)


@router.post(
    "/application-submitted",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Webhook: déclenche l'ETL temps réel vers Blob Storage pour une candidature",
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
    db: AsyncSession = Depends(get_db),
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
        
        # Récupérer l'application avec toutes les relations
        result = await db.execute(
            select(ApplicationModel)
            .options(
                selectinload(ApplicationModel.candidate),
                selectinload(ApplicationModel.job_offer),
                selectinload(ApplicationModel.documents)
            )
            .where(ApplicationModel.id == uuid.UUID(payload.application_id))
        )
        
        application = result.scalar_one_or_none()
        
        if not application:
            logger.warning(
                "Candidature introuvable pour export",
                application_id=payload.application_id
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidature introuvable"
            )
        
        # ========================================================================
        # ÉTAPE 2 : Récupérer le profil candidat complet
        # ========================================================================
        candidate_profile = None
        if application.candidate:
            profile_result = await db.execute(
                select(CandidateProfile).where(
                    CandidateProfile.user_id == application.candidate_id
                )
            )
            candidate_profile = profile_result.scalar_one_or_none()
        
        # ========================================================================
        # ÉTAPE 3 : Construire le dictionnaire complet avec TOUTES les infos
        # ========================================================================
        application_dict = {
            # Candidature
            "id": str(application.id),
            "candidate_id": str(application.candidate_id),
            "job_offer_id": str(application.job_offer_id),
            "status": application.status,
            "mtp_answers": application.mtp_answers,
            "has_been_manager": application.has_been_manager,
            "ref_entreprise": application.ref_entreprise,
            "ref_fullname": application.ref_fullname,
            "ref_mail": application.ref_mail,
            "ref_contact": application.ref_contact,
            "reference_contacts": application.reference_contacts,
            "availability_start": application.availability_start.isoformat() if application.availability_start is not None else None,
            "created_at": application.created_at.isoformat() if application.created_at is not None else None,
            "updated_at": application.updated_at.isoformat() if application.updated_at is not None else None,
            
            # Candidat (User complet)
            "candidate": {
                "id": str(application.candidate.id),
                "email": application.candidate.email,
                "first_name": application.candidate.first_name,
                "last_name": application.candidate.last_name,
                "phone": application.candidate.phone,
                "date_of_birth": application.candidate.date_of_birth.isoformat() if application.candidate.date_of_birth is not None else None,
                "sexe": application.candidate.sexe,
                "adresse": application.candidate.adresse,
                "matricule": application.candidate.matricule,
                "poste_actuel": application.candidate.poste_actuel,
                "annees_experience": application.candidate.annees_experience,
                "role": application.candidate.role,
                "candidate_status": application.candidate.candidate_status,
                "statut": application.candidate.statut,
                "is_internal_candidate": application.candidate.is_internal_candidate,
                "email_verified": application.candidate.email_verified,
                "is_active": application.candidate.is_active,
                "created_at": application.candidate.created_at.isoformat() if application.candidate.created_at is not None else None,
            } if application.candidate else None,
            
            # Profil Candidat (CandidateProfile complet)
            "candidate_profile": {
                "id": str(candidate_profile.id),
                "address": candidate_profile.address,
                "availability": candidate_profile.availability,
                "birth_date": str(candidate_profile.birth_date) if candidate_profile.birth_date is not None else None,
                "current_department": candidate_profile.current_department,
                "current_position": candidate_profile.current_position,
                "cv_url": candidate_profile.cv_url,
                "education": candidate_profile.education,
                "expected_salary_min": candidate_profile.expected_salary_min,
                "expected_salary_max": candidate_profile.expected_salary_max,
                "gender": candidate_profile.gender,
                "linkedin_url": candidate_profile.linkedin_url,
                "portfolio_url": candidate_profile.portfolio_url,
                "skills": candidate_profile.skills,
                "years_experience": candidate_profile.years_experience,
            } if candidate_profile else None,
            
            # Offre d'emploi
            "job_offer": {
                "id": str(application.job_offer.id),
                "title": application.job_offer.title,
                "description": application.job_offer.description,
                "location": application.job_offer.location,
                "contract_type": application.job_offer.contract_type,
                "department": application.job_offer.department,
                "offer_status": application.job_offer.offer_status,
                "questions_mtp": application.job_offer.questions_mtp,
                "created_at": application.job_offer.created_at.isoformat() if application.job_offer.created_at is not None else None,
            } if application.job_offer else None
        }
        
        logger.info(
            "Candidature complète récupérée pour export",
            application_id=payload.application_id,
            candidate_email=application_dict.get("candidate", {}).get("email") if application_dict.get("candidate") else None,
            has_profile=application_dict.get("candidate_profile") is not None,
            documents_count=len(application.documents) if hasattr(application, 'documents') and application.documents else 0
        )
        
        # ========================================================================
        # ÉTAPE 4 : Préparer les documents PDF (bytes depuis PostgreSQL)
        # ========================================================================
        documents_for_export = []
        if hasattr(application, 'documents') and application.documents:
            for doc in application.documents:
                documents_for_export.append({
                    "document_type": doc.document_type,
                    "file_name": doc.file_name,
                    "file_data": doc.file_data,  # bytes
                    "file_size": doc.file_size,
                    "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at is not None else None
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
