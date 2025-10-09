"""
Service de gestion des offres d'emploi
"""
import structlog
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from uuid import UUID

from app.models.job_offer import JobOffer
from app.models.application import Application
from app.schemas.job import JobOfferCreate, JobOfferUpdate
from app.core.exceptions import NotFoundError, ValidationError, BusinessLogicError

logger = structlog.get_logger(__name__)

class JobOfferService:
    """Service de gestion des offres d'emploi"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_job_offer(self, job_data: JobOfferCreate) -> JobOffer:
        """
        Créer une nouvelle offre d'emploi - LOGIQUE MÉTIER PURE.
        NE FAIT PAS de commit - c'est la responsabilité de l'endpoint.
        """
        try:
            job_offer = JobOffer(**job_data.dict())
            self.db.add(job_offer)
            # ✅ PAS de commit ici - c'est l'endpoint qui décide
            # ✅ PAS de refresh ici - sera fait après commit par l'endpoint
            
            logger.info("Offre d'emploi préparée", title=job_offer.title)
            return job_offer
        except Exception as e:
            logger.error("Erreur création offre d'emploi", error=str(e))
            raise BusinessLogicError("Erreur lors de la création de l'offre d'emploi")
    
    async def get_job_offer(self, job_id: UUID) -> Optional[JobOffer]:
        """Récupérer une offre d'emploi par son ID"""
        try:
            result = await self.db.execute(
                select(JobOffer).where(JobOffer.id == job_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Erreur récupération offre d'emploi", error=str(e), job_id=str(job_id))
            raise BusinessLogicError("Erreur lors de la récupération de l'offre d'emploi")
    
    async def get_job_offers(
        self, 
        skip: int = 0, 
        limit: int = 100,
        recruiter_id: Optional[UUID] = None,
        status: Optional[str] = None,
        current_user: Optional[Any] = None  # Pour filtrage interne/externe
    ) -> List[JobOffer]:
        """
        Récupérer la liste des offres d'emploi avec filtrage interne/externe.
        
        Logique de filtrage:
        - Candidat INTERNE (is_internal_candidate=true) : Voit TOUTES les offres
        - Candidat EXTERNE (is_internal_candidate=false) : Voit UNIQUEMENT les offres accessibles (is_internal_only=false)
        - Recruteur/Admin : Voit TOUTES les offres
        """
        try:
            query = select(JobOffer)
            
            # Filtrage par recruteur
            if recruiter_id:
                query = query.where(JobOffer.recruiter_id == recruiter_id)
            
            # Filtrage par statut
            if status:
                query = query.where(JobOffer.status == status)
            
            # Filtrage INTERNE/EXTERNE selon le type de candidat
            if current_user and current_user.role == "candidate":
                if not current_user.is_internal_candidate:
                    # Candidat EXTERNE : uniquement les offres non-internes
                    query = query.where(JobOffer.is_internal_only == False)
                    logger.debug("Filtrage offres pour candidat externe", user_id=str(current_user.id))
                else:
                    # Candidat INTERNE : toutes les offres
                    logger.debug("Affichage toutes offres pour candidat interne", user_id=str(current_user.id))
            
            query = query.offset(skip).limit(limit).order_by(JobOffer.created_at.desc())
            
            result = await self.db.execute(query)
            jobs = result.scalars().all()
            
            logger.info("Offres récupérées", count=len(jobs), 
                       is_internal_user=current_user.is_internal_candidate if current_user and hasattr(current_user, 'is_internal_candidate') else None)
            return jobs
            
        except Exception as e:
            logger.error("Erreur récupération liste offres d'emploi", error=str(e))
            raise BusinessLogicError("Erreur lors de la récupération des offres d'emploi")
    
    async def update_job_offer(self, job_id: UUID, job_data: JobOfferUpdate) -> JobOffer:
        """
        Mettre à jour une offre d'emploi - LOGIQUE MÉTIER PURE.
        NE FAIT PAS de commit - c'est la responsabilité de l'endpoint.
        """
        try:
            # Vérifier que l'offre existe
            job_offer = await self.get_job_offer(job_id)
            if not job_offer:
                raise NotFoundError("Offre d'emploi non trouvée")
            
            # Mettre à jour les champs fournis
            update_data = job_data.dict(exclude_unset=True)
            if update_data:
                await self.db.execute(
                    update(JobOffer)
                    .where(JobOffer.id == job_id)
                    .values(**update_data)
                )
                # ✅ PAS de commit ici
            
            logger.info("Offre d'emploi mise à jour", job_id=str(job_id))
            return job_offer
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Erreur mise à jour offre d'emploi", error=str(e), job_id=str(job_id))
            raise BusinessLogicError("Erreur lors de la mise à jour de l'offre d'emploi")
    
    async def delete_job_offer(self, job_id: UUID) -> bool:
        """
        Supprimer une offre d'emploi - LOGIQUE MÉTIER PURE.
        NE FAIT PAS de commit - c'est la responsabilité de l'endpoint.
        """
        try:
            # Vérifier que l'offre existe
            job_offer = await self.get_job_offer(job_id)
            if not job_offer:
                raise NotFoundError("Offre d'emploi non trouvée")
            
            await self.db.execute(
                delete(JobOffer).where(JobOffer.id == job_id)
            )
            # ✅ PAS de commit ici
            
            logger.info("Offre d'emploi préparée pour suppression", job_id=str(job_id))
            return True
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Erreur suppression offre d'emploi", error=str(e), job_id=str(job_id))
            raise BusinessLogicError("Erreur lors de la suppression de l'offre d'emploi")
    
    async def get_job_offer_with_applications(self, job_id: UUID) -> Optional[Dict[str, Any]]:
        """Récupérer une offre d'emploi avec ses candidatures"""
        try:
            # Récupérer l'offre
            job_offer = await self.get_job_offer(job_id)
            if not job_offer:
                return None
            
            # Récupérer les candidatures
            result = await self.db.execute(
                select(Application).where(Application.job_offer_id == job_id)
            )
            applications = result.scalars().all()
            
            return {
                "job_offer": job_offer,
                "applications": applications,
                "application_count": len(applications)
            }
        except Exception as e:
            logger.error("Erreur récupération offre avec candidatures", error=str(e), job_id=str(job_id))
            raise BusinessLogicError("Erreur lors de la récupération de l'offre d'emploi")
    
    async def get_recruiter_statistics(self, recruiter_id: UUID) -> Dict[str, Any]:
        """Récupérer les statistiques d'un recruteur"""
        try:
            # Nombre total d'offres
            total_jobs_result = await self.db.execute(
                select(func.count(JobOffer.id)).where(JobOffer.recruiter_id == recruiter_id)
            )
            total_jobs = total_jobs_result.scalar()
            
            # Nombre d'offres actives
            active_jobs_result = await self.db.execute(
                select(func.count(JobOffer.id)).where(
                    JobOffer.recruiter_id == recruiter_id,
                    JobOffer.status == "active"
                )
            )
            active_jobs = active_jobs_result.scalar()
            
            # Nombre total de candidatures
            total_applications_result = await self.db.execute(
                select(func.count(Application.id))
                .join(JobOffer, Application.job_offer_id == JobOffer.id)
                .where(JobOffer.recruiter_id == recruiter_id)
            )
            total_applications = total_applications_result.scalar()
            
            return {
                "total_jobs": total_jobs,
                "active_jobs": active_jobs,
                "total_applications": total_applications
            }
        except Exception as e:
            logger.error("Erreur récupération statistiques recruteur", error=str(e), recruiter_id=str(recruiter_id))
            raise BusinessLogicError("Erreur lors de la récupération des statistiques")
