"""
Endpoints pour récupérer les informations complètes des candidats
Accessible uniquement aux admins et recruteurs
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import structlog

logger = structlog.get_logger(__name__)

from app.db.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.candidate_profile import CandidateProfile
from app.models.application import Application
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


@router.get("/candidates/{candidate_id}/complete", response_model=CandidateCompleteInfo)
async def get_candidate_complete_info(
    candidate_id: UUID4,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
    if current_user.role not in ["admin", "recruiter"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs et recruteurs"
        )
    
    try:
        logger.info("Récupération infos complètes candidat", 
                   candidate_id=str(candidate_id),
                   requester_id=str(current_user.id))
        
        # Récupérer l'utilisateur avec son profil candidat
        stmt = (
            select(User)
            .options(selectinload(User.candidate_profile))
            .where(User.id == candidate_id)
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidat {candidate_id} non trouvé"
            )
        
        # Vérifier que c'est bien un candidat
        if user.role not in ["candidate", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="L'utilisateur n'est pas un candidat"
            )
        
        # Récupérer les statistiques de candidatures
        applications_stmt = select(Application).where(Application.candidate_id == candidate_id)
        applications_result = await db.execute(applications_stmt)
        applications = applications_result.scalars().all()
        
        total_apps = len(applications)
        pending = sum(1 for app in applications if app.status == "pending")  # type: ignore
        submitted = sum(1 for app in applications if app.status == "submitted")  # type: ignore
        under_review = sum(1 for app in applications if app.status == "under_review")  # type: ignore
        accepted = sum(1 for app in applications if app.status in ["accepted", "hired"])
        rejected = sum(1 for app in applications if app.status in ["rejected", "withdrawn"])
        
        # Construire la réponse avec conversion explicite des types
        response = CandidateCompleteInfo(
            user_id=user.id,
            email=str(user.email),
            first_name=str(user.first_name),
            last_name=str(user.last_name),
            phone=str(user.phone) if user.phone is not None else None,
            date_of_birth=str(user.date_of_birth) if user.date_of_birth is not None else None,
            sexe=str(user.sexe) if user.sexe is not None else None,
            role=str(user.role),
            is_active=bool(user.is_active),
            candidate_status=str(user.candidate_status) if user.candidate_status is not None else None,
            created_at=user.created_at,
            profile=CandidateProfileResponse.model_validate(user.candidate_profile) if user.candidate_profile else None,
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
    application_id: UUID4,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Récupère les informations complètes du candidat à partir d'une candidature
    
    **Accessible uniquement aux admins et recruteurs**
    
    Pratique pour obtenir toutes les infos du candidat quand on consulte une candidature
    """
    # Vérifier que l'utilisateur est admin ou recruteur
    if current_user.role not in ["admin", "recruiter"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs et recruteurs"
        )
    
    try:
        # Récupérer la candidature
        stmt = select(Application).where(Application.id == application_id)
        result = await db.execute(stmt)
        application = result.scalar_one_or_none()
        
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidature {application_id} non trouvée"
            )
        
        # Utiliser l'endpoint principal pour récupérer les infos
        # Convertir explicitement UUID pour éviter les erreurs de type
        from uuid import UUID as UUID_Type
        candidate_uuid = UUID_Type(str(application.candidate_id))
        
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

