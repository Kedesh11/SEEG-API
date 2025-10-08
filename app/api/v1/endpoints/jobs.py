"""
Endpoints de gestion des offres d'emploi
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
import structlog

from app.db.database import get_db
from app.schemas.job import JobOfferResponse, JobOfferCreate, JobOfferUpdate
from app.services.job import JobOfferService
from app.core.dependencies import get_current_active_user, get_current_recruiter_user
from app.models.user import User
from app.core.exceptions import NotFoundError, ValidationError, BusinessLogicError

logger = structlog.get_logger(__name__)
router = APIRouter()


def safe_log(level: str, message: str, **kwargs):
    """Log avec gestion d'erreur pour ÃƒÂ©viter les problÃƒÂ¨mes de handler."""
    try:
        getattr(logger, level)(message, **kwargs)
    except (TypeError, AttributeError):
        print(f"{level.upper()}: {message} - {kwargs}")

@router.get("/", response_model=List[JobOfferResponse], summary="Liste des offres d'emploi")
async def get_job_offers(
    skip: int = Query(0, ge=0, description="Nombre d'ÃƒÂ©lÃƒÂ©ments ÃƒÂ  ignorer"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre d'ÃƒÂ©lÃƒÂ©ments ÃƒÂ  retourner"),
    status_filter: Optional[str] = Query(None, description="Filtrer par statut"),
    db: AsyncSession = Depends(get_db)
):
    """RÃƒÂ©cupÃƒÂ©rer la liste des offres d'emploi"""
    try:
        job_service = JobOfferService(db)
        job_offers = await job_service.get_job_offers(skip=skip, limit=limit, status=status_filter)
        safe_log("info", "Offres d'emploi rÃƒÂ©cupÃƒÂ©rÃƒÂ©es", count=len(job_offers))
        return [JobOfferResponse.from_orm(job) for job in job_offers]
    except Exception as e:
        safe_log("error", "Erreur rÃƒÂ©cupÃƒÂ©ration offres d'emploi", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la rÃƒÂ©cupÃƒÂ©ration des offres d'emploi"
        )

@router.post("/", response_model=JobOfferResponse, summary="CrÃƒÂ©er une offre d'emploi")
async def create_job_offer(
    job_data: JobOfferCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
):
    """CrÃƒÂ©er une nouvelle offre d'emploi"""
    try:
        job_service = JobOfferService(db)
        
        # Ajouter l'ID du recruteur
        job_data.recruiter_id = current_user.id
        
        job_offer = await job_service.create_job_offer(job_data)
        safe_log("info", "Offre d'emploi crÃƒÂ©ÃƒÂ©e", job_id=str(job_offer.id), recruiter_id=str(current_user.id))
        return JobOfferResponse.from_orm(job_offer)
    except ValidationError as e:
        safe_log("warning", "Erreur validation crÃƒÂ©ation offre", error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur crÃƒÂ©ation offre d'emploi", error=str(e))
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la crÃƒÂ©ation de l'offre d'emploi"
        )

@router.get("/{job_id}", response_model=JobOfferResponse, summary="DÃƒÂ©tails d'une offre d'emploi")
async def get_job_offer(
    job_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """RÃƒÂ©cupÃƒÂ©rer les dÃƒÂ©tails d'une offre d'emploi"""
    try:
        job_service = JobOfferService(db)
        job_offer = await job_service.get_job_offer(job_id)
        
        if not job_offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Offre d'emploi non trouvÃƒÂ©e"
            )
        
        return JobOfferResponse.from_orm(job_offer)
    except HTTPException:
        raise
    except Exception as e:
        safe_log("error", "Erreur rÃƒÂ©cupÃƒÂ©ration offre d'emploi", error=str(e), job_id=str(job_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la rÃƒÂ©cupÃƒÂ©ration de l'offre d'emploi"
        )

@router.put("/{job_id}", response_model=JobOfferResponse, summary="Mettre ÃƒÂ  jour une offre d'emploi")
async def update_job_offer(
    job_id: UUID,
    job_data: JobOfferUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
):
    """Mettre ÃƒÂ  jour une offre d'emploi"""
    try:
        job_service = JobOfferService(db)
        
        # VÃƒÂ©rifier que l'offre appartient au recruteur
        job_offer = await job_service.get_job_offer(job_id)
        if not job_offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Offre d'emploi non trouvÃƒÂ©e"
            )
        
        if job_offer.recruiter_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Pas d'autorisation pour modifier cette offre d'emploi"
            )
        
        updated_job = await job_service.update_job_offer(job_id, job_data)
        safe_log("info", "Offre d'emploi mise ÃƒÂ  jour", job_id=str(job_id), recruiter_id=str(current_user.id))
        return JobOfferResponse.from_orm(updated_job)
    except HTTPException:
        raise
    except ValidationError as e:
        safe_log("warning", "Erreur validation MAJ offre", error=str(e), job_id=str(job_id))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur mise ÃƒÂ  jour offre d'emploi", error=str(e), job_id=str(job_id))
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la mise ÃƒÂ  jour de l'offre d'emploi"
        )

@router.delete("/{job_id}", summary="Supprimer une offre d'emploi")
async def delete_job_offer(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
):
    """Supprimer une offre d'emploi"""
    try:
        job_service = JobOfferService(db)
        
        # VÃƒÂ©rifier que l'offre appartient au recruteur
        job_offer = await job_service.get_job_offer(job_id)
        if not job_offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Offre d'emploi non trouvÃƒÂ©e"
            )
        
        if job_offer.recruiter_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Pas d'autorisation pour supprimer cette offre d'emploi"
            )
        
        success = await job_service.delete_job_offer(job_id)
        
        if success:
            safe_log("info", "Offre d'emploi supprimÃƒÂ©e", job_id=str(job_id), recruiter_id=str(current_user.id))
            return {"message": "Offre d'emploi supprimÃƒÂ©e avec succÃƒÂ¨s"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur lors de la suppression de l'offre d'emploi"
            )
    except HTTPException:
        raise
    except Exception as e:
        safe_log("error", "Erreur suppression offre d'emploi", error=str(e), job_id=str(job_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la suppression de l'offre d'emploi"
        )

@router.get("/{job_id}/applications", response_model=JobOfferResponse, summary="Candidatures d'une offre")
async def get_job_offer_applications(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
):
    """RÃƒÂ©cupÃƒÂ©rer les candidatures d'une offre d'emploi"""
    try:
        job_service = JobOfferService(db)
        
        # VÃƒÂ©rifier que l'offre appartient au recruteur
        job_offer = await job_service.get_job_offer(job_id)
        if not job_offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Offre d'emploi non trouvÃƒÂ©e"
            )
        
        if job_offer.recruiter_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Pas d'autorisation pour voir les candidatures de cette offre"
            )
        
        job_with_applications = await job_service.get_job_offer_with_applications(job_id)
        
        if not job_with_applications:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Offre d'emploi non trouvÃƒÂ©e"
            )
        
        safe_log("info", "Candidatures rÃƒÂ©cupÃƒÂ©rÃƒÂ©es pour offre", job_id=str(job_id), count=len(job_with_applications.applications) if hasattr(job_with_applications, 'applications') else 0)
        return JobOfferResponse.from_orm(job_with_applications)
        
    except HTTPException:
        raise
    except Exception as e:
        safe_log("error", "Erreur rÃƒÂ©cupÃƒÂ©ration candidatures", error=str(e), job_id=str(job_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la rÃƒÂ©cupÃƒÂ©ration des candidatures"
        )

@router.get("/recruiter/my-jobs", response_model=List[JobOfferResponse], summary="Mes offres d'emploi")
async def get_my_job_offers(
    skip: int = Query(0, ge=0, description="Nombre d'ÃƒÂ©lÃƒÂ©ments ÃƒÂ  ignorer"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre d'ÃƒÂ©lÃƒÂ©ments ÃƒÂ  retourner"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
):
    """RÃƒÂ©cupÃƒÂ©rer les offres d'emploi du recruteur connectÃƒÂ©"""
    try:
        job_service = JobOfferService(db)
        job_offers = await job_service.get_job_offers(
            skip=skip, 
            limit=limit, 
            recruiter_id=current_user.id
        )
        safe_log("info", "Mes offres d'emploi rÃƒÂ©cupÃƒÂ©rÃƒÂ©es", recruiter_id=str(current_user.id), count=len(job_offers))
        return [JobOfferResponse.from_orm(job) for job in job_offers]
    except Exception as e:
        safe_log("error", "Erreur rÃƒÂ©cupÃƒÂ©ration mes offres d'emploi", error=str(e), recruiter_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la rÃƒÂ©cupÃƒÂ©ration de vos offres d'emploi"
        )

@router.get("/recruiter/statistics", summary="Statistiques du recruteur")
async def get_recruiter_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
):
    """RÃƒÂ©cupÃƒÂ©rer les statistiques du recruteur connectÃƒÂ©"""
    try:
        job_service = JobOfferService(db)
        stats = await job_service.get_recruiter_statistics(current_user.id)
        safe_log("info", "Statistiques recruteur rÃƒÂ©cupÃƒÂ©rÃƒÂ©es", recruiter_id=str(current_user.id))
        return stats
    except Exception as e:
        safe_log("error", "Erreur rÃƒÂ©cupÃƒÂ©ration statistiques", error=str(e), recruiter_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la rÃƒÂ©cupÃƒÂ©ration des statistiques"
        )
