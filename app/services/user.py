"""
Service de gestion des utilisateurs
"""
import structlog
from typing import Optional, List, Dict, Any
import structlog
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from uuid import UUID

from app.schemas.user import UserCreate, UserUpdate, CandidateProfileCreate, CandidateProfileUpdate
from app.core.exceptions import NotFoundError, ValidationError, BusinessLogicError

logger = structlog.get_logger(__name__)

class UserService:
    """Service de gestion des utilisateurs"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Récupérer un utilisateur par son ID (ObjectId ou UUID string) avec cache"""
        from app.core.cache import cache_user
        
        @cache_user(expire=3600)  # Cache 1 heure
        async def _get_user(uid: str):
            try:
                # Support ObjectId and plain strings
                query = {"_id": ObjectId(uid)} if len(uid) == 24 else {"_id": uid}
                user = await self.db.users.find_one(query)
                return user
            except Exception as e:
                logger.error("Erreur récupération utilisateur", error=str(e), user_id=uid)
                raise BusinessLogicError("Erreur lors de la récupération de l'utilisateur")
        
        return await _get_user(str(user_id))
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Récupérer un utilisateur par son email avec cache"""
        from app.core.cache import cache_key_wrapper
        
        @cache_key_wrapper("user:email", expire=1800)  # Cache 30 minutes
        async def _get_user_by_email(email: str):
            try:
                user = await self.db.users.find_one({"email": email})
                return user
            except Exception as e:
                logger.error("Erreur récupération utilisateur par email", error=str(e), email=email)
                raise BusinessLogicError("Erreur lors de la récupération de l'utilisateur")
        
        return await _get_user_by_email(email)
    
    async def get_users(self, skip: int = 0, limit: int = 100, role: Optional[str] = None, q: Optional[str] = None, sort: Optional[str] = None, order: Optional[str] = None) -> List[Dict[str, Any]]:
        """Récupérer la liste des utilisateurs avec filtres, recherche et tri."""
        try:
            # Construire mongo filter
            filter_query = {}
            if role:
                filter_query["role"] = role
            if q:
                filter_query["$or"] = [
                    {"first_name": {"$regex": q, "$options": "i"}},
                    {"last_name": {"$regex": q, "$options": "i"}},
                    {"email": {"$regex": q, "$options": "i"}}
                ]

            # Construire mongo sort
            sort_field = sort if sort in ["first_name", "last_name", "email", "created_at"] else "created_at"
            sort_dir = -1 if (order or "desc").lower() == "desc" else 1

            cursor = self.db.users.find(filter_query).sort(sort_field, sort_dir).skip(skip).limit(limit)
            users = await cursor.to_list(length=limit)
            return users
        except Exception as e:
            logger.error("Erreur récupération liste utilisateurs", error=str(e))
            raise BusinessLogicError("Erreur lors de la récupération des utilisateurs")
    
    async def update_user(self, user_id: str, user_data: UserUpdate) -> Dict[str, Any]:
        """Mettre à jour un utilisateur"""
        try:
            # Vérifier que l'utilisateur existe
            user = await self.get_user_by_id(user_id)
            if not user:
                raise NotFoundError("Utilisateur non trouvé")
            
            # Mettre à jour les champs fournis
            update_data = user_data.dict(exclude_unset=True)
            if update_data:
                query = {"_id": ObjectId(user_id)} if len(str(user_id)) == 24 else {"_id": str(user_id)}
                await self.db.users.update_one(query, {"$set": update_data})
                
                # Fetch updated
                user = await self.get_user_by_id(user_id)
            
            logger.info("Utilisateur mis à jour", user_id=str(user_id))
            return user
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Erreur mise à jour utilisateur", error=str(e), user_id=str(user_id))
            raise BusinessLogicError("Erreur lors de la mise à jour de l'utilisateur")
    
    async def delete_user(self, user_id: str) -> bool:
        """Supprimer un utilisateur"""
        try:
            # Vérifier que l'utilisateur existe
            user = await self.get_user_by_id(user_id)
            if not user:
                raise NotFoundError("Utilisateur non trouvé")
            
            query = {"_id": ObjectId(user_id)} if len(str(user_id)) == 24 else {"_id": str(user_id)}
            await self.db.users.delete_one(query)
            
            logger.info("Utilisateur préparé pour suppression", user_id=str(user_id))
            return True
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Erreur suppression utilisateur", error=str(e), user_id=str(user_id))
            raise BusinessLogicError("Erreur lors de la suppression de l'utilisateur")
    
    async def get_candidate_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Récupérer le profil candidat d'un utilisateur"""
        try:
            profile = await self.db.candidate_profiles.find_one({"user_id": str(user_id)})
            return profile
        except Exception as e:
            logger.error("Erreur récupération profil candidat", error=str(e), user_id=str(user_id))
            raise BusinessLogicError("Erreur lors de la récupération du profil candidat")
    
    async def create_candidate_profile(self, user_id: str, profile_data: CandidateProfileCreate) -> Dict[str, Any]:
        """Créer un profil candidat"""
        try:
            # Vérifier que l'utilisateur existe
            user = await self.get_user_by_id(user_id)
            if not user:
                raise NotFoundError("Utilisateur non trouvé")
            
            # Vérifier qu'il n'y a pas déjà un profil
            existing_profile = await self.get_candidate_profile(user_id)
            if existing_profile:
                raise ValidationError("Un profil candidat existe déjà pour cet utilisateur")
            
            # Créer le profil
            profile_dict = profile_data.model_dump()
            profile_dict['user_id'] = str(user_id)
            
            result = await self.db.candidate_profiles.insert_one(profile_dict)
            profile_dict["_id"] = result.inserted_id
            
            logger.info("Profil candidat préparé", user_id=str(user_id))
            return profile_dict
            
        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error("Erreur création profil candidat", error=str(e), user_id=str(user_id))
            raise BusinessLogicError("Erreur lors de la création du profil candidat")
    
    async def update_candidate_profile(self, user_id: str, profile_data: CandidateProfileUpdate) -> Dict[str, Any]:
        """Mettre à jour un profil candidat"""
        try:
            # Récupérer le profil existant
            profile = await self.get_candidate_profile(user_id)
            if not profile:
                raise NotFoundError("Profil candidat non trouvé")
            
            # Mettre à jour les champs fournis
            update_data = profile_data.dict(exclude_unset=True)
            if update_data:
                await self.db.candidate_profiles.update_one(
                    {"user_id": str(user_id)},
                    {"$set": update_data}
                )
                
                # Fetch updated
                profile = await self.get_candidate_profile(str(user_id))
            
            logger.info("Profil candidat mis à jour", user_id=str(user_id))
            return profile
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Erreur mise à jour profil candidat", error=str(e), user_id=str(user_id))
            raise BusinessLogicError("Erreur lors de la mise à jour du profil candidat")
