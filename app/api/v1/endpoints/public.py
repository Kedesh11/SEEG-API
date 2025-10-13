"""
Endpoints publics (sans authentification)
Pour permettre aux visiteurs de voir les offres d'emploi
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID

from app.db.database import get_db
from app.models.job_offer import JobOffer
from app.schemas.job import JobOfferPublicResponse, JobOfferDetailPublicResponse
import structlog

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("/jobs", response_model=List[JobOfferPublicResponse], summary="Liste des offres publiques (sans auth)")
async def get_public_jobs(
    skip: int = 0,
    limit: int = 100,
    location: Optional[str] = None,
    contract_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Récupérer la liste des offres d'emploi publiques (sans authentification).
    
    **Filtres automatiques :**
    - Offres avec offer_status = 'tous', 'externe' ou 'interne'
    - Uniquement les offres ACTIVES (status = 'active')
    
    **Filtres optionnels :**
    - location : Filtrer par localisation
    - contract_type : Filtrer par type de contrat (CDI, CDD, Stage, Alternance)
    
    **Pagination :**
    - skip : Nombre d'offres à ignorer (défaut: 0)
    - limit : Nombre maximum d'offres à retourner (défaut: 100, max: 100)
    """
    try:
        # Requête de base : offres publiques et actives
        # Afficher uniquement les offres "tous" et "externe" (jamais "interne" car pas d'authentification)
        query = select(JobOffer).where(
            JobOffer.offer_status.in_(["tous", "externe"]),
            JobOffer.status == "active"
        )
        
        # Filtres optionnels
        if location:
            query = query.where(JobOffer.location.ilike(f"%{location}%"))
        
        if contract_type:
            query = query.where(JobOffer.contract_type == contract_type)
        
        # Pagination
        query = query.offset(skip).limit(min(limit, 100))
        
        # Tri par date de création (plus récentes en premier)
        query = query.order_by(JobOffer.created_at.desc())
        
        # Exécution
        result = await db.execute(query)
        jobs = result.scalars().all()
        
        logger.info(
            "Liste des offres publiques récupérée",
            count=len(jobs),
            skip=skip,
            limit=limit,
            location=location,
            contract_type=contract_type
        )
        
        return jobs
        
    except Exception as e:
        logger.error("Erreur lors de la récupération des offres publiques", error=str(e), error_type=type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des offres"
        )


@router.get("/jobs/count", response_model=dict, summary="Compteur d'offres publiques (sans auth)")
async def get_public_jobs_count(
    db: AsyncSession = Depends(get_db),
):
    """
    Compter le nombre d'offres d'emploi publiques disponibles.
    
    **Retourne :**
    - total : Nombre total d'offres publiques actives
    """
    try:
        # Compter les offres "tous" et "externe"
        query = select(JobOffer).where(
            JobOffer.offer_status.in_(["tous", "externe"]),
            JobOffer.status == "active"
        )
        
        result = await db.execute(query)
        jobs = result.scalars().all()
        total = len(jobs)
        
        logger.info("Compteur d'offres publiques", total=total)
        
        return {
            "total": total,
            "status": "active",
            "type": "public"
        }
        
    except Exception as e:
        logger.error("Erreur lors du comptage des offres publiques", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors du comptage des offres"
        )


@router.get("/jobs/{job_id}", response_model=JobOfferDetailPublicResponse, summary="Détails d'une offre publique (sans auth)")
async def get_public_job_details(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Récupérer les détails complets d'une offre d'emploi publique (sans authentification).
    
    **Restrictions :**
    - Offres avec offer_status = 'tous', 'externe' ou 'interne'
    - Uniquement les offres ACTIVES (status = 'active')
    
    **Retourne :**
    - Tous les détails de l'offre (titre, description, localisation, etc.)
    - Les questions MTP si disponibles
    - Informations sur le recruteur (nom uniquement, pas d'infos sensibles)
    """
    try:
        # Requête avec vérifications de sécurité
        # Uniquement les offres "tous" et "externe"
        query = select(JobOffer).where(
            JobOffer.id == job_id,
            JobOffer.offer_status.in_(["tous", "externe"]),
            JobOffer.status == "active"
        )
        
        result = await db.execute(query)
        job = result.scalar_one_or_none()
        
        if not job:
            logger.warning("Offre publique non trouvée ou non accessible", job_id=str(job_id))
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Offre d'emploi non trouvée ou non accessible publiquement"
            )
        
        logger.info("Détails de l'offre publique récupérés", job_id=str(job_id), title=job.title)
        
        return job
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Erreur lors de la récupération des détails de l'offre publique",
            job_id=str(job_id),
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des détails de l'offre"
        )

