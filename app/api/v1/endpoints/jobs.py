"""
Endpoints de gestion des offres d'emploi
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
import structlog

from app.db.session import get_async_session as get_async_db_session
from app.schemas.job import JobOfferResponse, JobOfferCreate, JobOfferUpdate
from app.services.job import JobOfferService
from app.core.dependencies import get_current_active_user, get_current_recruiter_user
from app.models.user import User

logger = structlog.get_logger(__name__)
router = APIRouter()

@router.get("/", response_model=List[JobOfferResponse], summary="Liste des offres d'emploi")
async def get_job_offers(
    skip: int = Query(0, ge=0, description="Nombre d'éléments à ignorer"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre d'éléments à retourner"),
    status: Optional[str] = Query(None, description="Filtrer par statut"),
    db: AsyncSession = Depends(get_async_db_session)
):
    """Récupérer la liste des offres d'emploi"""
    try:
        job_service = JobOfferService(db)
        job_offers = await job_service.get_job_offers(skip=skip, limit=limit, status=status)
        return [JobOfferResponse.from_orm(job) for job in job_offers]
    except Exception as e:
        logger.error("Erreur récupération offres d'emploi", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des offres d'emploi"
        )

@router.post("/", response_model=JobOfferResponse, summary="Créer une offre d'emploi")
async def create_job_offer(
    job_data: JobOfferCreate,
    db: AsyncSession = Depends(get_async_db_session),
    current_user: User = Depends(get_current_recruiter_user)
):
    """Créer une nouvelle offre d'emploi"""
    try:
        job_service = JobOfferService(db)
        
        # Ajouter l'ID du recruteur
        job_data.recruiter_id = current_user.id
        
        job_offer = await job_service.create_job_offer(job_data)
        return JobOfferResponse.from_orm(job_offer)
    except Exception as e:
        logger.error("Erreur création offre d'emploi", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la création de l'offre d'emploi"
        )

@router.get("/{job_id}", response_model=JobOfferResponse, summary="Détails d'une offre d'emploi")
async def get_job_offer(
    job_id: UUID,
    db: AsyncSession = Depends(get_async_db_session)
):
    """Récupérer les détails d'une offre d'emploi"""
    try:
        job_service = JobOfferService(db)
        job_offer = await job_service.get_job_offer(job_id)
        
        if not job_offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Offre d'emploi non trouvée"
            )
        
        return JobOfferResponse.from_orm(job_offer)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur récupération offre d'emploi", error=str(e), job_id=str(job_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération de l'offre d'emploi"
        )

@router.put("/{job_id}", response_model=JobOfferResponse, summary="Mettre à jour une offre d'emploi")
async def update_job_offer(
    job_id: UUID,
    job_data: JobOfferUpdate,
    db: AsyncSession = Depends(get_async_db_session),
    current_user: User = Depends(get_current_recruiter_user)
):
    """Mettre à jour une offre d'emploi"""
    try:
        job_service = JobOfferService(db)
        
        # Vérifier que l'offre appartient au recruteur
        job_offer = await job_service.get_job_offer(job_id)
        if not job_offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Offre d'emploi non trouvée"
            )
        
        if job_offer.recruiter_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Pas d'autorisation pour modifier cette offre d'emploi"
            )
        
        updated_job = await job_service.update_job_offer(job_id, job_data)
        return JobOfferResponse.from_orm(updated_job)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur mise à jour offre d'emploi", error=str(e), job_id=str(job_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la mise à jour de l'offre d'emploi"
        )

@router.delete("/{job_id}", summary="Supprimer une offre d'emploi")
async def delete_job_offer(
    job_id: UUID,
    db: AsyncSession = Depends(get_async_db_session),
    current_user: User = Depends(get_current_recruiter_user)
):
    """Supprimer une offre d'emploi"""
    try:
        job_service = JobOfferService(db)
        
        # Vérifier que l'offre appartient au recruteur
        job_offer = await job_service.get_job_offer(job_id)
        if not job_offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Offre d'emploi non trouvée"
            )
        
        if job_offer.recruiter_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Pas d'autorisation pour supprimer cette offre d'emploi"
            )
        
        success = await job_service.delete_job_offer(job_id)
        
        if success:
            return {"message": "Offre d'emploi supprimée avec succès"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur lors de la suppression de l'offre d'emploi"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur suppression offre d'emploi", error=str(e), job_id=str(job_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la suppression de l'offre d'emploi"
        )

@router.get("/{job_id}/applications", response_model=JobOfferResponse, summary="Candidatures d'une offre")
async def get_job_offer_applications(
    job_id: UUID,
    db: AsyncSession = Depends(get_async_db_session),
    current_user: User = Depends(get_current_recruiter_user)
):
    """Récupérer les candidatures d'une offre d'emploi"""
    try:
        job_service = JobOfferService(db)
        
        # Vérifier que l'offre appartient au recruteur
        job_offer = await job_service.get_job_offer(job_id)
        if not job_offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Offre d'emploi non trouvée"
            )
        
        if job_offer.recruiter_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Pas d'autorisation pour voir les candidatures de cette offre"
            )
        
        job_with_applications = await job_service.get_job_offer_with_applications(job_id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur récupération candidatures", error=str(e), job_id=str(job_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des candidatures"
        )

@router.get("/recruiter/my-jobs", response_model=List[JobOfferResponse], summary="Mes offres d'emploi")
async def get_my_job_offers(
    skip: int = Query(0, ge=0, description="Nombre d'éléments à ignorer"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre d'éléments à retourner"),
    db: AsyncSession = Depends(get_async_db_session),
    current_user: User = Depends(get_current_recruiter_user)
):
    """Récupérer les offres d'emploi du recruteur connecté"""
    try:
        job_service = JobOfferService(db)
        job_offers = await job_service.get_job_offers(
            skip=skip, 
            limit=limit, 
            recruiter_id=current_user.id
        )
        return [JobOfferResponse.from_orm(job) for job in job_offers]
    except Exception as e:
        logger.error("Erreur récupération mes offres d'emploi", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération de vos offres d'emploi"
        )

@router.get("/recruiter/statistics", summary="Statistiques du recruteur")
async def get_recruiter_statistics(
    db: AsyncSession = Depends(get_async_db_session),
    current_user: User = Depends(get_current_recruiter_user)
):
    """Récupérer les statistiques du recruteur connecté"""
    try:
        job_service = JobOfferService(db)
        stats = await job_service.get_recruiter_statistics(current_user.id)
        return stats
    except Exception as e:
        logger.error("Erreur récupération statistiques", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des statistiques"
        )
