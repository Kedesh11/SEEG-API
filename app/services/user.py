"""
Service de gestion des utilisateurs
"""
import structlog
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, or_, asc, desc
from sqlalchemy.orm import selectinload
from uuid import UUID

from app.models.user import User
from app.models.candidate_profile import CandidateProfile
from app.schemas.user import UserCreate, UserUpdate, CandidateProfileCreate, CandidateProfileUpdate
from app.core.exceptions import NotFoundError, ValidationError, BusinessLogicError

logger = structlog.get_logger(__name__)

class UserService:
    """Service de gestion des utilisateurs"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Récupérer un utilisateur par son ID avec cache"""
        from app.core.cache import cache_user
        from app.db.query_optimizer import QueryOptimizer
        
        @cache_user(expire=3600)  # Cache 1 heure
        async def _get_user(user_id: str):
            try:
                query = select(User).where(User.id == user_id)
                query = QueryOptimizer.optimize_user_query(query)
                
                result = await self.db.execute(query)
                return result.scalar_one_or_none()
            except Exception as e:
                logger.error("Erreur récupération utilisateur", error=str(e), user_id=user_id)
                raise BusinessLogicError("Erreur lors de la récupération de l'utilisateur")
        
        return await _get_user(str(user_id))
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Récupérer un utilisateur par son email avec cache"""
        from app.core.cache import cache_key_wrapper
        from app.db.query_optimizer import QueryOptimizer
        
        @cache_key_wrapper("user:email", expire=1800)  # Cache 30 minutes
        async def _get_user_by_email(email: str):
            try:
                query = select(User).where(User.email == email)
                query = QueryOptimizer.optimize_user_query(query)
                
                result = await self.db.execute(query)
                return result.scalar_one_or_none()
            except Exception as e:
                logger.error("Erreur récupération utilisateur par email", error=str(e), email=email)
                raise BusinessLogicError("Erreur lors de la récupération de l'utilisateur")
        
        return await _get_user_by_email(email)
    
    async def get_users(self, skip: int = 0, limit: int = 100, role: Optional[str] = None, q: Optional[str] = None, sort: Optional[str] = None, order: Optional[str] = None) -> List[User]:
        """Récupérer la liste des utilisateurs avec filtres, recherche et tri."""
        from app.db.query_optimizer import QueryOptimizer
        
        try:
            query = select(User)
            # Optimiser la requête
            query = QueryOptimizer.optimize_user_query(query)
            # Filtres
            if role:
                query = query.where(User.role == role)
            if q:
                like = f"%{q}%"
                query = query.where(or_(User.first_name.ilike(like), User.last_name.ilike(like), User.email.ilike(like)))
            # Tri
            if sort in {"first_name", "last_name", "email", "created_at"}:
                direction = desc if (order or "desc").lower() == "desc" else asc
                query = query.order_by(direction(getattr(User, sort)))
            else:
                query = query.order_by(desc(User.created_at))
            # Pagination
            query = query.offset(skip).limit(limit)
            result = await self.db.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logger.error("Erreur récupération liste utilisateurs", error=str(e))
            raise BusinessLogicError("Erreur lors de la récupération des utilisateurs")
    
    async def update_user(self, user_id: UUID, user_data: UserUpdate) -> User:
        """Mettre à jour un utilisateur"""
        try:
            # Vérifier que l'utilisateur existe
            user = await self.get_user_by_id(user_id)
            if not user:
                raise NotFoundError("Utilisateur non trouvé")
            
            # Mettre à jour les champs fournis
            update_data = user_data.dict(exclude_unset=True)
            if update_data:
                await self.db.execute(
                    update(User)
                    .where(User.id == user_id)
                    .values(**update_data)
                )
                # ✅ PAS de commit ici
            
            logger.info("Utilisateur mis à jour", user_id=str(user_id))
            return user
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Erreur mise à jour utilisateur", error=str(e), user_id=str(user_id))
            raise BusinessLogicError("Erreur lors de la mise à jour de l'utilisateur")
    
    async def delete_user(self, user_id: UUID) -> bool:
        """Supprimer un utilisateur"""
        try:
            # Vérifier que l'utilisateur existe
            user = await self.get_user_by_id(user_id)
            if not user:
                raise NotFoundError("Utilisateur non trouvé")
            
            await self.db.execute(
                delete(User).where(User.id == user_id)
            )
            # ✅ PAS de commit ici
            
            logger.info("Utilisateur préparé pour suppression", user_id=str(user_id))
            return True
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Erreur suppression utilisateur", error=str(e), user_id=str(user_id))
            raise BusinessLogicError("Erreur lors de la suppression de l'utilisateur")
    
    async def get_candidate_profile(self, user_id: UUID) -> Optional[CandidateProfile]:
        """Récupérer le profil candidat d'un utilisateur"""
        try:
            result = await self.db.execute(
                select(CandidateProfile).where(CandidateProfile.user_id == user_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Erreur récupération profil candidat", error=str(e), user_id=str(user_id))
            raise BusinessLogicError("Erreur lors de la récupération du profil candidat")
    
    async def create_candidate_profile(self, user_id: UUID, profile_data: CandidateProfileCreate) -> CandidateProfile:
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
            profile_dict['user_id'] = user_id
            profile = CandidateProfile(**profile_dict)
            
            self.db.add(profile)
            # ✅ PAS de commit ici
            # ✅ PAS de refresh ici
            
            logger.info("Profil candidat préparé", user_id=str(user_id))
            return profile
            
        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error("Erreur création profil candidat", error=str(e), user_id=str(user_id))
            raise BusinessLogicError("Erreur lors de la création du profil candidat")
    
    async def update_candidate_profile(self, user_id: UUID, profile_data: CandidateProfileUpdate) -> CandidateProfile:
        """Mettre à jour un profil candidat"""
        try:
            # Récupérer le profil existant
            profile = await self.get_candidate_profile(user_id)
            if not profile:
                raise NotFoundError("Profil candidat non trouvé")
            
            # Mettre à jour les champs fournis
            update_data = profile_data.dict(exclude_unset=True)
            if update_data:
                # Convertir skills de List[str] vers JSON string si présent
                if 'skills' in update_data and update_data['skills'] is not None:
                    import json
                    update_data['skills'] = json.dumps(update_data['skills'])
                
                await self.db.execute(
                    update(CandidateProfile)
                    .where(CandidateProfile.user_id == user_id)
                    .values(**update_data)
                )
                # ✅ PAS de commit ici
                
                # 🔄 Rafraîchir l'objet pour avoir les nouvelles valeurs
                await self.db.refresh(profile)
            
            logger.info("Profil candidat mis à jour", user_id=str(user_id))
            return profile
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Erreur mise à jour profil candidat", error=str(e), user_id=str(user_id))
            raise BusinessLogicError("Erreur lors de la mise à jour du profil candidat")
