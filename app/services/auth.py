"""
Service d'authentification
"""
import structlog
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse, PasswordResetRequest
from app.core.security import PasswordManager, TokenManager
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
                return None
            
            # Vérifier le mot de passe
            if not self.password_manager.verify_password(password, user.hashed_password):
                return None
            
            return user
            
        except Exception as e:
            logger.error("Erreur d'authentification", error=str(e), email=email)
            raise UnauthorizedError("Erreur d'authentification")
    
    async def create_user(self, user_data: SignupRequest) -> User:
        """Créer un nouvel utilisateur"""
        try:
            # Vérifier si l'utilisateur existe déjà
            result = await self.db.execute(
                select(User).where(User.email == user_data.email)
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                raise ValidationError("Un utilisateur avec cet email existe déjà")
            
            # Créer le nouvel utilisateur
            hashed_password = self.password_manager.hash_password(user_data.password)
            
            user = User(
                email=user_data.email,
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                role="candidate",  # Par défaut
                matricule=user_data.matricule,
                phone=user_data.phone,
                hashed_password=hashed_password
            )
            
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            
            logger.info("Utilisateur créé", user_id=str(user.id), email=user.email)
            return user
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error("Erreur création utilisateur", error=str(e))
            raise BusinessLogicError("Erreur lors de la création de l'utilisateur")
    
    async def create_access_token(self, user: User) -> TokenResponse:
        """Créer un token d'accès"""
        try:
            access_token = self.token_manager.create_access_token(
                data={"sub": str(user.id), "email": user.email, "role": user.role}
            )
            
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
            logger.error("Erreur création token", error=str(e))
            raise BusinessLogicError("Erreur lors de la création du token")
