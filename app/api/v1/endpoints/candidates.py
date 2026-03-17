"""
Endpoints pour récupérer les informations complètes des candidats
Accessible uniquement aux admins et recruteurs
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Any
from bson import ObjectId
import structlog

logger = structlog.get_logger(__name__)

from app.db.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.user import UserResponse
from app.schemas.candidate_profile import CandidateProfileResponse
from pydantic import BaseModel, UUID4
from datetime import datetime

router = APIRouter()


class CandidateCompleteInfo(BaseModel):
    """Informations complètes d'un candidat"""
    # Informations utilisateur
    user_id: UUID4
    email: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    date_of_birth: Optional[str] = None
    sexe: Optional[str] = None
    role: str
    is_active: bool
    candidate_status: Optional[str] = None
    created_at: datetime

    # Profil candidat
    profile: Optional[CandidateProfileResponse] = None

    # Statistiques de candidatures
    total_applications: int = 0
    pending_applications: int = 0
    accepted_applications: int = 0
    rejected_applications: int = 0

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True


@router.get("/candidates/{candidate_id}/complete", response_model=CandidateCompleteInfo)
async def get_candidate_complete_info(
    candidate_id: str,
    db: Any = Depends(get_db),
    current_user: Any = Depends(get_current_user)
):
    """
    Récupère les informations complètes d'un candidat (utilisateur + profil + statistiques)

    **Accessible uniquement aux admins et recruteurs**

    Retourne:
    - Informations utilisateur (nom, email, téléphone, etc.)
    - Profil candidat (compétences, formation, expérience, etc.)
    - Statistiques de candidatures
    """
    # Vérifier que l'utilisateur est admin ou recruteur
    if current_user.get("role") not in ["admin", "recruiter"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs et recruteurs"
        )

    try:
        logger.info("Récupération infos complètes candidat",
                   candidate_id=str(candidate_id),
                   requester_id=str(current_user.get("_id", current_user.get("id"))))

        # Récupérer l'utilisateur avec son profil candidat
        query = {"_id": ObjectId(candidate_id) if len(str(candidate_id)) == 24 else candidate_id}
        user = await db.users.find_one(query)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidat {candidate_id} non trouvé"
            )

        # Vérifier que c'est bien un candidat
        if user.get("role") not in ["candidate", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="L'utilisateur n'est pas un candidat"
            )

        # Récupérer les statistiques de candidatures
        app_query = {"candidate_id": str(candidate_id)}
        cursor = db.applications.find(app_query)
        applications = await cursor.to_list(length=None)

        total_apps = len(applications)
        pending = sum(1 for app in applications if app.get("status") == "pending")
        submitted = sum(1 for app in applications if app.get("status") == "submitted")
        under_review = sum(1 for app in applications if app.get("status") == "under_review")
        accepted = sum(1 for app in applications if app.get("status") in ["accepted", "hired"])
        rejected = sum(1 for app in applications if app.get("status") in ["rejected", "withdrawn"])

        # Construire la réponse avec conversion explicite des types
        response = CandidateCompleteInfo(
            user_id=str(user.get("_id", user.get("id"))),
            email=str(user.get("email", "")),
            first_name=str(user.get("first_name", "")),
            last_name=str(user.get("last_name", "")),
            phone=str(user.get("phone")) if user.get("phone") is not None else None,
            date_of_birth=str(user.get("date_of_birth")) if user.get("date_of_birth") is not None else None,
            sexe=str(user.get("sexe")) if user.get("sexe") is not None else None,
            role=str(user.get("role")),
            is_active=bool(user.get("is_active", True)),
            candidate_status=str(user.get("candidate_status")) if user.get("candidate_status") is not None else None,
            created_at=user.get("created_at", datetime.utcnow()),
            profile=CandidateProfileResponse.model_validate(user.get("candidate_profile")) if user.get("candidate_profile") else None,
            total_applications=total_apps,
            pending_applications=pending + submitted + under_review,
            accepted_applications=accepted,
            rejected_applications=rejected
        )

        logger.info("Infos candidat récupérées",
                   candidate_id=str(candidate_id),
                   total_applications=total_apps)

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur récupération infos candidat",
                    candidate_id=str(candidate_id),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des informations du candidat"
        )


@router.get("/applications/{application_id}/candidate-info", response_model=CandidateCompleteInfo)
async def get_candidate_info_from_application(
    application_id: str,
    db: Any = Depends(get_db),
    current_user: Any = Depends(get_current_user)
):
    """
    Récupère les informations complètes du candidat à partir d'une candidature

    **Accessible uniquement aux admins et recruteurs**

    Pratique pour obtenir toutes les infos du candidat quand on consulte une candidature
    """
    # Vérifier que l'utilisateur est admin ou recruteur
    if current_user.get("role") not in ["admin", "recruiter"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs et recruteurs"
        )

    try:
        # Récupérer la candidature
        query = {"_id": ObjectId(application_id) if len(str(application_id)) == 24 else application_id}
        application = await db.applications.find_one(query)

        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidature {application_id} non trouvée"
            )

        # Utiliser l'endpoint principal pour récupérer les infos
        candidate_uuid = str(application.get("candidate_id"))

        return await get_candidate_complete_info(
            candidate_id=candidate_uuid,
            db=db,
            current_user=current_user
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur récupération infos candidat depuis candidature",
                    application_id=str(application_id),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des informations du candidat"
        )

