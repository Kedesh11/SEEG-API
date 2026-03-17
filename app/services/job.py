"""
Service de gestion des offres d'emploi
"""
import structlog
from typing import Optional, List, Dict, Any
import structlog
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from uuid import UUID
from datetime import datetime

from app.schemas.job import JobOfferCreate, JobOfferUpdate
from app.core.exceptions import NotFoundError, ValidationError, BusinessLogicError

logger = structlog.get_logger(__name__)

class JobOfferService:
    """Service de gestion des offres d'emploi"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def get_job_offers(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        current_user: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Récupérer les offres d'emploi avec filtrage automatique selon le type de candidat.
        """
        try:
            filter_query = {}
            
            # Filtrer par statut si fourni
            if status:
                filter_query["status"] = status
            
            # Filtrage intelligent selon le type d'utilisateur
            # Utiliser get() ou getattr() selon l'objet current_user
            user_role = getattr(current_user, 'role', None) or (current_user.get('role') if isinstance(current_user, dict) else None)
            if user_role == "candidate":
                # Candidat interne (employé SEEG avec matricule)
                is_internal = getattr(current_user, 'is_internal_candidate', False) or (current_user.get('is_internal_candidate') if isinstance(current_user, dict) else False)
                if is_internal:
                    # Voit toutes les offres (internes et externes)
                    pass
                else:
                    # Candidat externe : voit seulement les offres 'tous' et 'externe'
                    filter_query["offer_status"] = {"$in": ["tous", "externe"]}
            
            # Pagination & Tri
            cursor = self.db.job_offers.find(filter_query).sort("created_at", -1).skip(skip).limit(limit)
            job_offers = await cursor.to_list(length=limit)
            
            logger.info("Offres d'emploi récupérées", count=len(job_offers), user_role=user_role or "anonymous")
            
            return job_offers
        except Exception as e:
            logger.error("Erreur récupération offres d'emploi", error=str(e))
            raise
    
    async def get_job_offer_by_id(self, job_offer_id: str) -> Dict[str, Any]:
        """
        Récupérer une offre d'emploi par son ID.
        """
        try:
            query = {"_id": ObjectId(job_offer_id)} if len(str(job_offer_id)) == 24 else {"_id": str(job_offer_id)}
            job_offer = await self.db.job_offers.find_one(query)
            
            if not job_offer:
                raise NotFoundError(f"Offre d'emploi {job_offer_id} introuvable")
            
            logger.info("Offre d'emploi récupérée", job_offer_id=str(job_offer_id))
            return job_offer
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Erreur récupération offre d'emploi", job_offer_id=str(job_offer_id), error=str(e))
            raise
    
    async def create_job_offer(
        self,
        job_data: JobOfferCreate,
        recruiter_id: str
    ) -> Dict[str, Any]:
        """
        Créer une nouvelle offre d'emploi.
        """
        try:
            job_offer_dict = job_data.model_dump(exclude_unset=True)
            job_offer_dict["recruiter_id"] = str(recruiter_id)
            job_offer_dict["created_at"] = datetime.utcnow()
            job_offer_dict["updated_at"] = datetime.utcnow()
            
            # Gérer les champs JSONB
            for field in ["requirements", "benefits", "responsibilities", "questions_mtp"]:
                if field in job_offer_dict:
                    value = job_offer_dict[field]
                    if value == {} or value == []:
                        job_offer_dict[field] = None
                        
            result = await self.db.job_offers.insert_one(job_offer_dict)
            job_offer_dict["_id"] = result.inserted_id
            
            logger.info("Offre d'emploi créée", job_offer_id=str(result.inserted_id), title=job_offer_dict.get("title"))
            return job_offer_dict
            
        except Exception as e:
            logger.error("Erreur création offre d'emploi", error=str(e), error_type=type(e).__name__)
            raise
    
    async def update_job_offer(
        self,
        job_offer_id: str,
        job_data: JobOfferUpdate
    ) -> Dict[str, Any]:
        """
        Mettre à jour une offre d'emploi.
        """
        try:
            job_offer = await self.get_job_offer_by_id(job_offer_id)
            update_data = job_data.model_dump(exclude_unset=True)
            
            for field in ["requirements", "benefits", "responsibilities", "questions_mtp"]:
                if field in update_data:
                    value = update_data[field]
                    if value == {} or value == []:
                        update_data[field] = None
                        
            update_data["updated_at"] = datetime.utcnow()
            
            query = {"_id": ObjectId(job_offer_id)} if len(str(job_offer_id)) == 24 else {"_id": str(job_offer_id)}
            await self.db.job_offers.update_one(query, {"$set": update_data})
            
            job_offer = await self.get_job_offer_by_id(job_offer_id)
            logger.info("Offre d'emploi mise à jour", job_offer_id=str(job_offer_id))
            return job_offer
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Erreur mise à jour offre d'emploi", job_offer_id=str(job_offer_id), error=str(e))
            raise
    
    async def delete_job_offer(self, job_offer_id: str) -> bool:
        """
        Supprimer une offre d'emploi.
        """
        try:
            job_offer = await self.get_job_offer_by_id(job_offer_id)
            
            # Vérifier qu'il n'y a pas de candidatures associées
            applications_count = await self.db.applications.count_documents({"job_offer_id": str(job_offer_id)})
            
            if applications_count > 0:
                raise BusinessLogicError(f"Impossible de supprimer l'offre : {applications_count} candidature(s) associée(s)")
            
            query = {"_id": ObjectId(job_offer_id)} if len(str(job_offer_id)) == 24 else {"_id": str(job_offer_id)}
            await self.db.job_offers.delete_one(query)
            
            logger.info("Offre d'emploi supprimée", job_offer_id=str(job_offer_id))
            return True
            
        except (NotFoundError, BusinessLogicError):
            raise
        except Exception as e:
            logger.error("Erreur suppression offre d'emploi", job_offer_id=str(job_offer_id), error=str(e))
            raise
    
    async def get_job_offers_count(
        self,
        status: Optional[str] = None,
        current_user: Optional[Any] = None
    ) -> int:
        """
        Compter le nombre d'offres d'emploi.
        """
        try:
            filter_query = {}
            if status:
                filter_query["status"] = status
                
            user_role = getattr(current_user, 'role', None) or (current_user.get('role') if isinstance(current_user, dict) else None)
            if user_role == "candidate":
                is_internal = getattr(current_user, 'is_internal_candidate', False) or (current_user.get('is_internal_candidate') if isinstance(current_user, dict) else False)
                if not is_internal:
                    filter_query["offer_status"] = {"$in": ["tous", "externe"]}
            
            count = await self.db.job_offers.count_documents(filter_query)
            logger.info("Nombre d'offres d'emploi compté", count=count, user_role=user_role or "anonymous")
            
            return count
            
        except Exception as e:
            logger.error("Erreur comptage offres d'emploi", error=str(e))
            raise
