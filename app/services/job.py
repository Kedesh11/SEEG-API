"""
Service de gestion des offres d'emploi
"""
import structlog
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_, desc
from sqlalchemy.orm import selectinload
from uuid import UUID
from datetime import datetime

from app.models.job_offer import JobOffer
from app.models.user import User
from app.schemas.job import JobOfferCreate, JobOfferUpdate
from app.core.exceptions import NotFoundError, ValidationError, BusinessLogicError

logger = structlog.get_logger(__name__)

class JobOfferService:
    """Service de gestion des offres d'emploi"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_job_offers(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        current_user: Optional[User] = None
    ) -> List[JobOffer]:
        """
        Récupérer les offres d'emploi avec filtrage automatique selon le type de candidat.
        
        Args:
            skip: Nombre d'éléments à ignorer
            limit: Nombre d'éléments à retourner
            status: Filtrer par statut
            current_user: Utilisateur courant pour filtrage intelligent
            
        Returns:
            Liste des offres d'emploi
        """
        try:
            query = select(JobOffer).options(
                selectinload(JobOffer.recruiter)
            )
            
            # Filtrer par statut si fourni
            if status:
                query = query.where(JobOffer.status == status)
            
            # Filtrage intelligent selon le type d'utilisateur
            # Utiliser getattr pour éviter les warnings SQLAlchemy
            if current_user and getattr(current_user, 'role', None) == "candidate":
                # Candidat interne (employé SEEG avec matricule)
                is_internal = getattr(current_user, 'is_internal_candidate', False)
                if is_internal:
                    # Voit toutes les offres (internes et externes)
                    pass
                else:
                    # Candidat externe : voit seulement les offres 'tous' et 'externe'
                    query = query.where(
                        JobOffer.offer_status.in_(["tous", "externe"])
                    )
            
            # Tri par date de création décroissante
            query = query.order_by(desc(JobOffer.created_at))
            
            # Pagination
            query = query.offset(skip).limit(limit)
            
            result = await self.db.execute(query)
            job_offers = result.scalars().all()
            
            logger.info("Offres d'emploi récupérées", 
                       count=len(job_offers),
                       user_role=current_user.role if current_user else "anonymous")
            
            return list(job_offers)
            
        except Exception as e:
            logger.error("Erreur récupération offres d'emploi", error=str(e))
            raise
    
    async def get_job_offer_by_id(self, job_offer_id: UUID) -> JobOffer:
        """
        Récupérer une offre d'emploi par son ID.
        
        Args:
            job_offer_id: UUID de l'offre d'emploi
            
        Returns:
            Offre d'emploi
            
        Raises:
            NotFoundError: Si l'offre n'existe pas
        """
        try:
            query = select(JobOffer).where(JobOffer.id == job_offer_id).options(
                selectinload(JobOffer.recruiter)
            )
            
            result = await self.db.execute(query)
            job_offer = result.scalar_one_or_none()
            
            if not job_offer:
                raise NotFoundError(f"Offre d'emploi {job_offer_id} introuvable")
            
            logger.info("Offre d'emploi récupérée", job_offer_id=str(job_offer_id))
            
            return job_offer
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Erreur récupération offre d'emploi", 
                        job_offer_id=str(job_offer_id),
                        error=str(e))
            raise
    
    async def create_job_offer(
        self,
        job_data: JobOfferCreate,
        recruiter_id: UUID
    ) -> JobOffer:
        """
        Créer une nouvelle offre d'emploi.
        
        Args:
            job_data: Données de l'offre d'emploi
            recruiter_id: UUID du recruteur
            
        Returns:
            Offre d'emploi créée
        """
        try:
            # Créer l'objet en mémoire
            job_offer_dict = job_data.model_dump(exclude_unset=True)
            job_offer_dict["recruiter_id"] = recruiter_id
            
            # Gérer les champs JSONB - s'assurer qu'ils sont None ou dict, jamais {}
            for field in ["requirements", "benefits", "responsibilities", "questions_mtp"]:
                if field in job_offer_dict:
                    value = job_offer_dict[field]
                    if value == {} or value == []:
                        job_offer_dict[field] = None
            
            job_offer = JobOffer(**job_offer_dict)
            
            # Ajouter à la session
            self.db.add(job_offer)
            
            # Flush pour obtenir l'ID avant le commit
            await self.db.flush()
            
            logger.info("Offre d'emploi créée en mémoire", 
                       job_offer_id=str(job_offer.id),
                       title=job_offer.title,
                       offer_status=job_offer.offer_status)
            
            return job_offer
            
        except Exception as e:
            logger.error("Erreur création offre d'emploi", 
                        error=str(e),
                        error_type=type(e).__name__)
            raise
    
    async def update_job_offer(
        self,
        job_offer_id: UUID,
        job_data: JobOfferUpdate
    ) -> JobOffer:
        """
        Mettre à jour une offre d'emploi.
        
        Args:
            job_offer_id: UUID de l'offre d'emploi
            job_data: Données de mise à jour
            
        Returns:
            Offre d'emploi mise à jour
            
        Raises:
            NotFoundError: Si l'offre n'existe pas
        """
        try:
            # Récupérer l'offre existante
            job_offer = await self.get_job_offer_by_id(job_offer_id)
            
            # Mettre à jour les champs fournis
            update_data = job_data.model_dump(exclude_unset=True)
            
            # Gérer les champs JSONB - s'assurer qu'ils sont None ou dict, jamais {}
            for field in ["requirements", "benefits", "responsibilities", "questions_mtp"]:
                if field in update_data:
                    value = update_data[field]
                    if value == {} or value == []:
                        update_data[field] = None
            
            for field, value in update_data.items():
                setattr(job_offer, field, value)
            
            # Mettre à jour la date de modification
            job_offer.updated_at = datetime.utcnow()
            
            # Flush pour persister avant refresh
            await self.db.flush()
            
            # Rafraîchir l'objet pour récupérer les valeurs actuelles
            await self.db.refresh(job_offer)
            
            logger.info("Offre d'emploi mise à jour", 
                       job_offer_id=str(job_offer_id),
                       updated_fields=list(update_data.keys()))
            
            return job_offer
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Erreur mise à jour offre d'emploi", 
                        job_offer_id=str(job_offer_id),
                        error=str(e),
                        error_type=type(e).__name__)
            raise
    
    async def delete_job_offer(self, job_offer_id: UUID) -> bool:
        """
        Supprimer une offre d'emploi.
        
        Args:
            job_offer_id: UUID de l'offre d'emploi
            
        Returns:
            True si suppression réussie
            
        Raises:
            NotFoundError: Si l'offre n'existe pas
            BusinessLogicError: Si l'offre a des candidatures associées
        """
        try:
            # Vérifier que l'offre existe
            job_offer = await self.get_job_offer_by_id(job_offer_id)
            
            # Vérifier qu'il n'y a pas de candidatures associées
            from app.models.application import Application
            
            applications_query = select(func.count(Application.id)).where(
                Application.job_offer_id == job_offer_id
            )
            result = await self.db.execute(applications_query)
            applications_count = result.scalar_one()
            
            if applications_count > 0:
                raise BusinessLogicError(
                    f"Impossible de supprimer l'offre : {applications_count} candidature(s) associée(s)"
                )
            
            # Supprimer l'offre
            await self.db.delete(job_offer)
            await self.db.flush()
            
            logger.info("Offre d'emploi supprimée", job_offer_id=str(job_offer_id))
            
            return True
            
        except (NotFoundError, BusinessLogicError):
            raise
        except Exception as e:
            logger.error("Erreur suppression offre d'emploi", 
                        job_offer_id=str(job_offer_id),
                        error=str(e))
            raise
    
    async def get_job_offers_count(
        self,
        status: Optional[str] = None,
        current_user: Optional[User] = None
    ) -> int:
        """
        Compter le nombre d'offres d'emploi.
        
        Args:
            status: Filtrer par statut
            current_user: Utilisateur courant pour filtrage intelligent
            
        Returns:
            Nombre d'offres d'emploi
        """
        try:
            query = select(func.count(JobOffer.id))
            
            # Filtrer par statut si fourni
            if status:
                query = query.where(JobOffer.status == status)
            
            # Filtrage intelligent selon le type d'utilisateur
            # Utiliser getattr pour éviter les warnings SQLAlchemy
            if current_user and getattr(current_user, 'role', None) == "candidate":
                is_internal = getattr(current_user, 'is_internal_candidate', False)
                if not is_internal:
                    # Candidat externe : voit seulement les offres 'tous' et 'externe'
                    query = query.where(
                        JobOffer.offer_status.in_(["tous", "externe"])
                    )
            
            result = await self.db.execute(query)
            count = result.scalar_one()
            
            logger.info("Nombre d'offres d'emploi compté", 
                       count=count,
                       user_role=current_user.role if current_user else "anonymous")
            
            return count
            
        except Exception as e:
            logger.error("Erreur comptage offres d'emploi", error=str(e))
            raise
