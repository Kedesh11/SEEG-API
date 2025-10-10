"""
Service d'authentification
"""
import structlog
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from app.models.user import User
from app.schemas.auth import (
    LoginRequest, CandidateSignupRequest, CreateUserRequest, 
    TokenResponse, PasswordResetRequest
)
from app.core.security.security import PasswordManager, TokenManager, create_password_reset_token, verify_password_reset_token
from app.core.exceptions import UnauthorizedError, ValidationError, BusinessLogicError
from app.services.email import EmailService

logger = structlog.get_logger(__name__)


def safe_log(level: str, message: str, **kwargs):
    """Log avec gestion d'erreur pour éviter les problèmes de handler."""
    try:
        getattr(logger, level)(message, **kwargs)
    except (TypeError, AttributeError):
        print(f"{level.upper()}: {message} - {kwargs}")


class AuthService:
    """Service d'authentification"""
    
    SEEG_EMAIL_DOMAIN = "@seeg-gabon.com"  # Domaine email professionnel SEEG
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.password_manager = PasswordManager()
        self.token_manager = TokenManager()
    
    def determine_user_status(
        self,
        candidate_status: str,
        email: str,
        no_seeg_email: bool
    ) -> str:
        """
        Déterminer le statut de l'utilisateur selon les règles métier.
        
        Règles:
        1. Candidat EXTERNE → 'actif' (accès immédiat)
        2. Candidat INTERNE avec email @seeg-gabon.com → 'actif' (accès immédiat)
        3. Candidat INTERNE sans email @seeg-gabon.com → 'en_attente' (validation requise)
        
        Args:
            candidate_status: 'interne' ou 'externe'
            email: Adresse email du candidat
            no_seeg_email: True si candidat interne sans email SEEG
            
        Returns:
            str: 'actif' ou 'en_attente'
        """
        # Cas 1: Candidat externe → toujours actif
        if candidate_status == 'externe':
            return 'actif'
        
        # Cas 2: Candidat interne
        if candidate_status == 'interne':
            # Sous-cas 2.1: A un email @seeg-gabon.com → actif
            if not no_seeg_email and email.lower().endswith(self.SEEG_EMAIL_DOMAIN):
                return 'actif'
            
            # Sous-cas 2.2: N'a pas d'email SEEG → en_attente (validation requise)
            if no_seeg_email:
                return 'en_attente'
            
            # Sous-cas 2.3: Devrait avoir email SEEG mais ne l'a pas → en_attente
            return 'en_attente'
        
        # Défaut: actif
        return 'actif'
    
    async def verify_matricule_exists(self, matricule: int) -> bool:
        """
        Vérifier qu'un matricule existe dans la table seeg_agents.
        
        Args:
            matricule: Matricule à vérifier
            
        Returns:
            bool: True si le matricule existe dans la table seeg_agents
        """
        try:
            from app.models.seeg_agent import SeegAgent
            
            result = await self.db.execute(
                select(SeegAgent).where(SeegAgent.matricule == matricule)
            )
            agent = result.scalar_one_or_none()
            return agent is not None
            
        except Exception as e:
            safe_log("error", "Erreur vérification matricule", matricule=matricule, error=str(e))
            return False
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """
        Authentifier un utilisateur - LOGIQUE MÉTIER PURE.
        
        NE FAIT PAS de commit - c'est la responsabilité de l'endpoint.
        
        Args:
            email: Email de l'utilisateur
            password: Mot de passe en clair
            
        Returns:
            User si authentification réussie, None sinon
            
        Raises:
            BusinessLogicError: En cas d'erreur technique
        """
        try:
            # Récupérer l'utilisateur par email
            result = await self.db.execute(
                select(User).where(User.email == email)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                safe_log("warning", "Tentative de connexion avec email inexistant", email=email)
                return None
            
            # Vérifier le statut du compte (nouvelle logique)
            if hasattr(user, 'statut') and user.statut is not None:
                statut_str = str(user.statut)
                if statut_str != 'actif':
                    safe_log("warning", "Tentative de connexion avec compte non actif",
                            email=email, user_id=str(user.id), statut=statut_str)
                    # Retourner None et laisser l'endpoint gérer le message d'erreur selon le statut
                    return None
            
            # Vérifier que le compte est actif (legacy is_active field)
            if not bool(user.is_active):
                safe_log("warning", "Tentative de connexion sur compte désactivé (is_active=False)",
                        email=email, user_id=str(user.id))
                return None
            
            # Vérifier le mot de passe
            hashed_pwd = str(user.hashed_password) if user.hashed_password is not None else ""
            if not self.password_manager.verify_password(password, hashed_pwd):
                safe_log("warning", "Mot de passe incorrect", email=email, user_id=str(user.id))
                return None
            
            # Mettre à jour last_login (sera committé par l'endpoint)
            await self.db.execute(
                update(User)
                .where(User.id == user.id)
                .values(last_login=datetime.now(timezone.utc))
            )
            # ✅ PAS de commit ici - c'est l'endpoint qui décide
            # ✅ PAS de refresh ici - sera fait après commit par l'endpoint
            
            safe_log("info", "Authentification réussie", email=email, user_id=str(user.id))
            return user
            
        except Exception as e:
            # ✅ PAS de rollback ici - géré par get_db() automatiquement
            safe_log("error", "Erreur lors de l'authentification", email=email, error=str(e))
            raise BusinessLogicError("Erreur lors de l'authentification")
    
    async def create_candidate(self, user_data: CandidateSignupRequest) -> User:
        """
        Créer un candidat (inscription publique) - LOGIQUE MÉTIER PURE.
        
        NE FAIT PAS de commit - c'est la responsabilité de l'endpoint.
        
        Règles métier:
        1. Candidat EXTERNE (matricule=None) → statut='actif'
        2. Candidat INTERNE avec email @seeg-gabon.com → statut='actif'
        3. Candidat INTERNE sans email @seeg-gabon.com → statut='en_attente'
        
        Args:
            user_data: Données d'inscription du candidat
            
        Returns:
            User: Candidat créé (pas encore committé)
            
        Raises:
            ValidationError: Si validation échoue
            BusinessLogicError: En cas d'erreur technique
        """
        try:
            # Vérifier si l'email existe déjà
            result = await self.db.execute(
                select(User).where(User.email == user_data.email)
            )
            existing = result.scalar_one_or_none()
            if existing:
                raise ValidationError("Un utilisateur avec cet email existe déjà")
            
            # Validation métier: Candidat interne DOIT avoir un matricule
            if user_data.candidate_status == 'interne' and not user_data.matricule:
                raise ValidationError("Le matricule est obligatoire pour les candidats internes")
            
            # Validation métier: Vérifier que le matricule existe (si fourni)
            if user_data.matricule:
                is_valid = await self.verify_matricule_exists(user_data.matricule)
                if not is_valid:
                    raise ValidationError("Matricule SEEG non trouvé dans la base. Veuillez vérifier votre matricule.")

            # Validation métier: Empêcher la duplication de matricule côté users (renvoyer 400 plutôt que 500 DB)
            if user_data.matricule is not None:
                existing_mat_result = await self.db.execute(
                    select(User).where(User.matricule == user_data.matricule)
                )
                existing_with_same_matricule = existing_mat_result.scalar_one_or_none()
                if existing_with_same_matricule is not None:
                    raise ValidationError("Un utilisateur avec ce matricule existe déjà")
            
            # Validation métier: Si candidat interne sans no_seeg_email, l'email DOIT être @seeg-gabon.com
            if (user_data.candidate_status == 'interne' 
                and not user_data.no_seeg_email 
                and not user_data.email.lower().endswith(self.SEEG_EMAIL_DOMAIN)):
                raise ValidationError(
                    f"Les candidats internes doivent utiliser un email professionnel {self.SEEG_EMAIL_DOMAIN}. "
                    "Si vous n'avez pas d'email professionnel SEEG, veuillez cocher la case correspondante."
                )
            
            # Hasher le mot de passe
            hashed = self.password_manager.hash_password(user_data.password)
            
            # Déterminer le statut selon les règles métier
            statut = self.determine_user_status(
                candidate_status=user_data.candidate_status,
                email=user_data.email,
                no_seeg_email=user_data.no_seeg_email
            )
            
            # Déterminer si c'est un candidat interne
            is_internal = user_data.candidate_status == 'interne'
            
            # Créer l'utilisateur avec TOUS les nouveaux champs
            user = User(
                email=user_data.email,  # type: ignore
                hashed_password=hashed,  # type: ignore
                first_name=user_data.first_name,  # type: ignore
                last_name=user_data.last_name,  # type: ignore
                phone=user_data.phone,  # type: ignore
                role="candidate",  # type: ignore
                matricule=user_data.matricule,  # type: ignore
                date_of_birth=user_data.date_of_birth,  # type: ignore
                sexe=user_data.sexe,  # type: ignore
                is_internal_candidate=is_internal,  # type: ignore
                # Nouveaux champs
                adresse=user_data.adresse,  # type: ignore
                candidate_status=user_data.candidate_status,  # type: ignore
                statut=statut,  # type: ignore[assignment]
                poste_actuel=user_data.poste_actuel,  # type: ignore
                annees_experience=user_data.annees_experience,  # type: ignore
                no_seeg_email=user_data.no_seeg_email,  # type: ignore
                is_active=True,  # Legacy field  # type: ignore
                email_verified=False  # type: ignore
            )
            self.db.add(user)
            
            # ✅ PAS de commit ici - c'est l'endpoint qui décide
            # ✅ PAS de refresh ici - sera fait après commit par l'endpoint
            
            safe_log("info", "Candidat préparé pour création", 
                    email=user.email, 
                    candidate_status=user_data.candidate_status,
                    statut=statut,
                    has_matricule=user_data.matricule is not None,
                    no_seeg_email=user_data.no_seeg_email)
            return user
            
        except ValidationError:
            # ✅ PAS de rollback ici - géré par get_db() automatiquement
            raise
        except Exception as e:
            safe_log("error", "Erreur création candidat", error=str(e))
            raise BusinessLogicError("Erreur lors de la création du candidat")
    
    async def create_user(self, user_data: CreateUserRequest) -> User:
        """
        Créer un utilisateur (admin/recruteur) - LOGIQUE MÉTIER PURE.
        
        NE FAIT PAS de commit - c'est la responsabilité de l'endpoint.
        Réservé aux admins.
        
        Args:
            user_data: Données de l'utilisateur à créer
            
        Returns:
            User: Utilisateur créé (pas encore committé)
            
        Raises:
            ValidationError: Si validation échoue
            BusinessLogicError: En cas d'erreur technique
        """
        try:
            # Vérifier si l'email existe déjà
            result = await self.db.execute(
                select(User).where(User.email == user_data.email)
            )
            existing = result.scalar_one_or_none()
            if existing:
                raise ValidationError("Un utilisateur avec cet email existe déjà")
            
            # Hasher le mot de passe
            hashed = self.password_manager.hash_password(user_data.password)
            
            # Créer l'utilisateur
            user = User(
                email=user_data.email,  # type: ignore
                hashed_password=hashed,  # type: ignore
                first_name=user_data.first_name,  # type: ignore
                last_name=user_data.last_name,  # type: ignore
                phone=user_data.phone,  # type: ignore
                role=user_data.role,  # type: ignore
            )
            self.db.add(user)
            
            # ✅ PAS de commit ici - c'est l'endpoint qui décide
            # ✅ PAS de refresh ici - sera fait après commit par l'endpoint
            
            safe_log("info", "Utilisateur préparé pour création", email=user.email, role=user_data.role)
            return user
            
        except ValidationError:
            # ✅ PAS de rollback ici - géré par get_db() automatiquement
            raise
        except Exception as e:
            safe_log("error", "Erreur création utilisateur", error=str(e))
            raise BusinessLogicError("Erreur lors de la création de l'utilisateur")

    async def create_access_token(self, user: User) -> TokenResponse:
        """Créer des tokens d'accès et refresh"""
        try:
            access = self.token_manager.create_access_token({"sub": str(user.id), "role": user.role})
            refresh = self.token_manager.create_refresh_token({"sub": str(user.id), "role": user.role})
            return TokenResponse(access_token=access, refresh_token=refresh, token_type="bearer", expires_in=3600)
        except Exception as e:
            safe_log("error", "Erreur création token", error=str(e))
            raise BusinessLogicError("Erreur lors de la création du token")

    async def reset_password_request(self, email: str) -> bool:
        """Créer un token de réinitialisation et envoyer l'email."""
        try:
            result = await self.db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            if not user:
                # Ne pas révéler l'existence ou non de l'email
                safe_log("info", "Demande de reset pour email inconnu", email=email)
                return True
            token = create_password_reset_token(email)
            reset_link = f"{''}/reset-password?token={token}"
            # Envoyer l'email
            email_service = EmailService(self.db)
            subject = "Réinitialisation de votre mot de passe"
            body = f"Utilisez ce lien pour réinitialiser votre mot de passe: {reset_link}"
            html = f"<p>Vous avez demandé une réinitialisation de mot de passe.</p><p>Cliquez sur ce lien: <a href=\"{reset_link}\">Réinitialiser</a></p>"
            try:
                await email_service.send_email(to=str(user.email), subject=subject, body=body, html_body=html)
            except Exception as e:
                # Log et continuer (la génération du token côté client peut suffire si l'email tombe en échec)
                safe_log("error", "Echec envoi email reset", error=str(e))
            safe_log("info", "Demande de réinitialisation de mot de passe", email=email, user_id=str(user.id))
            return True
        except Exception as e:
            safe_log("error", "Erreur lors de la demande de réinitialisation", email=email, error=str(e))
            raise BusinessLogicError("Erreur lors de la demande de réinitialisation")
    
    async def reset_password_confirm(self, token: str, new_password: str) -> User:
        """
        Vérifier le token et préparer le changement de mot de passe.
        
        NE FAIT PAS de commit - c'est la responsabilité de l'endpoint.
        
        Args:
            token: Token de réinitialisation
            new_password: Nouveau mot de passe
            
        Returns:
            User: Utilisateur avec mot de passe modifié (pas encore committé)
            
        Raises:
            ValidationError: Si token invalide ou utilisateur introuvable
            BusinessLogicError: En cas d'erreur technique
        """
        try:
            email = verify_password_reset_token(token)
            if not email:
                raise ValidationError("Token de réinitialisation invalide ou expiré")
            
            result = await self.db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            if not user:
                raise ValidationError("Utilisateur introuvable pour ce token")
            
            # Modifier le mot de passe (sera committé par l'endpoint)
            user.hashed_password = self.password_manager.hash_password(new_password)  # type: ignore
            
            # ✅ PAS de commit ici - c'est l'endpoint qui décide
            
            safe_log("info", "Mot de passe préparé pour réinitialisation", user_id=str(user.id), email=email)
            return user
            
        except ValidationError:
            raise
        except Exception as e:
            safe_log("error", "Erreur lors de la confirmation de réinitialisation", error=str(e))
            raise BusinessLogicError("Erreur lors de la confirmation de réinitialisation")

    async def change_password(self, user_id: str, current_password: str, new_password: str) -> User:
        """
        Changer le mot de passe pour l'utilisateur authentifié.
        
        NE FAIT PAS de commit - c'est la responsabilité de l'endpoint.
        
        Args:
            user_id: ID de l'utilisateur
            current_password: Mot de passe actuel
            new_password: Nouveau mot de passe
            
        Returns:
            User: Utilisateur avec mot de passe modifié (pas encore committé)
            
        Raises:
            ValidationError: Si utilisateur introuvable
            UnauthorizedError: Si mot de passe actuel incorrect
            BusinessLogicError: En cas d'erreur technique
        """
        try:
            result = await self.db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user:
                raise ValidationError("Utilisateur introuvable")
            
            # Vérifier le mot de passe actuel
            hashed_pwd = str(user.hashed_password) if user.hashed_password is not None else ""
            if not self.password_manager.verify_password(current_password, hashed_pwd):
                raise UnauthorizedError("Mot de passe actuel incorrect")
            
            # Modifier le mot de passe (sera committé par l'endpoint)
            user.hashed_password = self.password_manager.hash_password(new_password)  # type: ignore
            
            # ✅ PAS de commit ici - c'est l'endpoint qui décide
            
            safe_log("info", "Mot de passe préparé pour modification", user_id=str(user.id))
            return user
            
        except (ValidationError, UnauthorizedError):
            raise
        except Exception as e:
            safe_log("error", "Erreur changement mot de passe", error=str(e), user_id=user_id)
            raise BusinessLogicError("Erreur lors du changement de mot de passe")
