"""
Service d'authentification
"""
import structlog
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.user import User
from app.schemas.auth import (
    LoginRequest, CandidateSignupRequest, CreateUserRequest, 
    TokenResponse, PasswordResetRequest
)
from app.core.security.security import PasswordManager, TokenManager, create_password_reset_token, verify_password_reset_token
from app.core.exceptions import UnauthorizedError, ValidationError, BusinessLogicError
from app.services.email import EmailService

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
            
            # Vérifier que le compte est actif
            if not user.is_active:
                logger.warning("Tentative de connexion sur compte désactivé", email=email, user_id=str(user.id))
                return None
            
            # Vérifier le mot de passe
            if not self.password_manager.verify_password(password, user.hashed_password):
                logger.warning("Mot de passe incorrect", email=email, user_id=str(user.id))
                return None
            
            # Mettre à jour last_login
            await self.db.execute(
                update(User)
                .where(User.id == user.id)
                .values(last_login=datetime.now(timezone.utc))
            )
            await self.db.commit()
            await self.db.refresh(user)
            
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
            existing = result.scalar_one_or_none()
            if existing:
                raise ValidationError("Un utilisateur avec cet email existe déjà")
            
            hashed = self.password_manager.hash_password(user_data.password)
            user = User(
                email=user_data.email,
                hashed_password=hashed,
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                phone=user_data.phone,
                role="candidate",
            )
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            logger.info("Candidat créé", user_id=str(user.id), email=user.email)
            return user
        except ValidationError:
            raise
        except Exception as e:
            logger.error("Erreur création candidat", error=str(e))
            raise BusinessLogicError("Erreur lors de la création du candidat")

    async def create_access_token(self, user: User) -> TokenResponse:
        """Créer des tokens d'accès et refresh"""
        try:
            access = self.token_manager.create_access_token({"sub": str(user.id), "role": user.role})
            refresh = self.token_manager.create_refresh_token({"sub": str(user.id), "role": user.role})
            return TokenResponse(access_token=access, refresh_token=refresh, token_type="bearer", expires_in=3600)
        except Exception as e:
            logger.error("Erreur création token", error=str(e))
            raise BusinessLogicError("Erreur lors de la création du token")

    async def reset_password_request(self, email: str) -> bool:
        """Créer un token de réinitialisation et envoyer l'email."""
        try:
            result = await self.db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            if not user:
                # Ne pas révéler l'existence ou non de l'email
                logger.info("Demande de reset pour email inconnu", email=email)
                return True
            token = create_password_reset_token(email)
            reset_link = f"{''}/reset-password?token={token}"
            # Envoyer l'email
            email_service = EmailService(self.db)
            subject = "Réinitialisation de votre mot de passe"
            body = f"Utilisez ce lien pour réinitialiser votre mot de passe: {reset_link}"
            html = f"<p>Vous avez demandé une réinitialisation de mot de passe.</p><p>Cliquez sur ce lien: <a href=\"{reset_link}\">Réinitialiser</a></p>"
            try:
                await email_service.send_email(to=user.email, subject=subject, body=body, html_body=html)
            except Exception as e:
                # Log et continuer (la génération du token côté client peut suffire si l'email tombe en échec)
                logger.error("Echec envoi email reset", error=str(e))
            logger.info("Demande de réinitialisation de mot de passe", email=email, user_id=str(user.id))
            return True
        except Exception as e:
            logger.error("Erreur lors de la demande de réinitialisation", email=email, error=str(e))
            raise BusinessLogicError("Erreur lors de la demande de réinitialisation")
    
    async def reset_password_confirm(self, token: str, new_password: str) -> bool:
        """Vérifier le token et mettre à jour le mot de passe."""
        try:
            email = verify_password_reset_token(token)
            if not email:
                raise ValidationError("Token de réinitialisation invalide ou expiré")
            result = await self.db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            if not user:
                raise ValidationError("Utilisateur introuvable pour ce token")
            user.hashed_password = self.password_manager.hash_password(new_password)
            await self.db.commit()
            logger.info("Mot de passe réinitialisé", user_id=str(user.id), email=email)
            return True
        except ValidationError:
            raise
        except Exception as e:
            logger.error("Erreur lors de la confirmation de réinitialisation", error=str(e))
            raise BusinessLogicError("Erreur lors de la confirmation de réinitialisation")

    async def change_password(self, user_id: str, current_password: str, new_password: str) -> bool:
        """Changer le mot de passe pour l'utilisateur authentifié."""
        try:
            result = await self.db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user:
                raise ValidationError("Utilisateur introuvable")
            if not self.password_manager.verify_password(current_password, user.hashed_password):
                raise UnauthorizedError("Mot de passe actuel incorrect")
            user.hashed_password = self.password_manager.hash_password(new_password)
            await self.db.commit()
            logger.info("Mot de passe modifié", user_id=str(user.id))
            return True
        except (ValidationError, UnauthorizedError):
            raise
        except Exception as e:
            logger.error("Erreur changement mot de passe", error=str(e), user_id=user_id)
            raise BusinessLogicError("Erreur lors du changement de mot de passe")
