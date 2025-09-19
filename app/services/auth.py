"""
Service d'authentification
"""
import structlog
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.schemas.auth import (
    LoginRequest, CandidateSignupRequest, CreateUserRequest, 
    TokenResponse, PasswordResetRequest
)
from app.core.security.security import PasswordManager, TokenManager
from app.core.exceptions import UnauthorizedError, ValidationError, BusinessLogicError

logger = structlog.get_logger(__name__)

class AuthService:
    """Service d'authentification"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.password_manager = PasswordManager()
        self.token_manager = TokenManager()
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authentifier un utilisateur"""
        try:
            # Récupérer l'utilisateur par email
            result = await self.db.execute(
                select(User).where(User.email == email)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                logger.warning("Tentative de connexion avec email inexistant", email=email)
                return None
            
            # Vérifier le mot de passe
            if not self.password_manager.verify_password(password, user.hashed_password):
                logger.warning("Mot de passe incorrect", email=email, user_id=str(user.id))
                return None
            
            logger.info("Authentification réussie", email=email, user_id=str(user.id))
            return user
            
        except Exception as e:
            logger.error("Erreur lors de l'authentification", email=email, error=str(e))
            raise BusinessLogicError("Erreur lors de l'authentification")
    
    async def create_candidate(self, user_data: CandidateSignupRequest) -> User:
        """Créer un candidat (inscription publique)"""
        try:
            # Vérifier si l'email existe déjà
            result = await self.db.execute(
                select(User).where(User.email == user_data.email)
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                raise ValidationError("Un utilisateur avec cet email existe déjà")
            
            # Vérifier si le matricule existe déjà
            if user_data.matricule:
                result = await self.db.execute(
                    select(User).where(User.matricule == user_data.matricule)
                )
                existing_matricule = result.scalar_one_or_none()
                
                if existing_matricule:
                    raise ValidationError("Un utilisateur avec ce matricule existe déjà")
            
            # Hacher le mot de passe
            hashed_password = self.password_manager.hash_password(user_data.password)
            
            # Créer l'utilisateur
            user = User(
                email=user_data.email,
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                role="candidate",
                phone=user_data.phone,
                date_of_birth=user_data.date_of_birth,
                sexe=user_data.sexe.value if hasattr(user_data.sexe, 'value') else user_data.sexe,
                matricule=user_data.matricule,
                hashed_password=hashed_password
            )
            
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            
            logger.info("Candidat créé avec succès", user_id=str(user.id), email=user.email)
            return user
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error("Erreur lors de la création du candidat", error=str(e))
            raise BusinessLogicError("Erreur lors de la création du candidat")
    
    async def create_user(self, user_data: CreateUserRequest) -> User:
        """Créer un utilisateur (admin/recruteur) - admin seulement"""
        try:
            # Vérifier si l'email existe déjà
            result = await self.db.execute(
                select(User).where(User.email == user_data.email)
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                raise ValidationError("Un utilisateur avec cet email existe déjà")
            
            # Hacher le mot de passe
            hashed_password = self.password_manager.hash_password(user_data.password)
            
            # Créer l'utilisateur
            user = User(
                email=user_data.email,
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                role=user_data.role.value if hasattr(user_data.role, 'value') else user_data.role,
                phone=user_data.phone,
                hashed_password=hashed_password
            )
            
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            
            logger.info("Utilisateur créé avec succès", user_id=str(user.id), email=user.email, role=user.role)
            return user
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error("Erreur lors de la création de l'utilisateur", error=str(e))
            raise BusinessLogicError("Erreur lors de la création de l'utilisateur")
    
    async def create_access_token(self, user: User) -> TokenResponse:
        """Créer les tokens d'accès et de rafraîchissement"""
        try:
            # Créer le token d'accès
            access_token = self.token_manager.create_access_token(
                data={"sub": str(user.id), "email": user.email, "role": user.role}
            )
            
            # Créer le token de rafraîchissement
            refresh_token = self.token_manager.create_refresh_token(
                data={"sub": str(user.id)}
            )
            
            return TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=1800  # 30 minutes
            )
            
        except Exception as e:
            logger.error("Erreur lors de la création des tokens", user_id=str(user.id), error=str(e))
            raise BusinessLogicError("Erreur lors de la création des tokens")
    
    async def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """Rafraîchir le token d'accès"""
        try:
            # Vérifier le token de rafraîchissement
            payload = self.token_manager.verify_refresh_token(refresh_token)
            user_id = payload.get("sub")
            
            if not user_id:
                raise UnauthorizedError("Token de rafraîchissement invalide")
            
            # Récupérer l'utilisateur
            result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                raise UnauthorizedError("Utilisateur non trouvé")
            
            # Créer un nouveau token d'accès
            return await self.create_access_token(user)
            
        except Exception as e:
            logger.error("Erreur lors du rafraîchissement du token", error=str(e))
            raise UnauthorizedError("Erreur lors du rafraîchissement du token")
    
    async def reset_password_request(self, email: str) -> bool:
        """Demander une réinitialisation de mot de passe"""
        try:
            # Vérifier si l'utilisateur existe
            result = await self.db.execute(
                select(User).where(User.email == email)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                # Ne pas révéler si l'email existe ou non
                logger.info("Demande de réinitialisation pour email inexistant", email=email)
                return True
            
            # TODO: Implémenter l'envoi d'email de réinitialisation
            logger.info("Demande de réinitialisation de mot de passe", email=email, user_id=str(user.id))
            return True
            
        except Exception as e:
            logger.error("Erreur lors de la demande de réinitialisation", email=email, error=str(e))
            raise BusinessLogicError("Erreur lors de la demande de réinitialisation")
    
    async def reset_password_confirm(self, token: str, new_password: str) -> bool:
        """Confirmer la réinitialisation de mot de passe"""
        try:
            # TODO: Implémenter la vérification du token et la mise à jour du mot de passe
            logger.info("Réinitialisation de mot de passe confirmée", token=token[:10] + "...")
            return True
            
        except Exception as e:
            logger.error("Erreur lors de la confirmation de réinitialisation", error=str(e))
            raise BusinessLogicError("Erreur lors de la confirmation de réinitialisation")
