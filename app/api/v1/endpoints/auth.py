"""
Endpoints d'authentification - Système unique et robuste
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Dict, Any
import structlog
from pydantic import ValidationError as PydanticValidationError
from uuid import UUID

from app.db.database import get_db
from app.schemas.auth import (
    LoginRequest, CandidateSignupRequest, CreateUserRequest, TokenResponse, TokenResponseData,
    RefreshTokenRequest, PasswordResetRequest, PasswordResetConfirm, ChangePasswordRequest,
    MatriculeVerificationResponse
)
from app.schemas.user import UserResponse
from app.services.auth import AuthService
from app.core.exceptions import UnauthorizedError
from app.core.dependencies import get_current_active_user, get_current_admin_user, get_current_user
from app.models.user import User
from app.models.seeg_agent import SeegAgent
from app.core.security.security import TokenManager
from app.core.rate_limit import limiter, AUTH_LIMITS, SIGNUP_LIMITS, DEFAULT_LIMITS
from app.core.exceptions import ValidationError
from sqlalchemy import select

logger = structlog.get_logger(__name__)
router = APIRouter()


def safe_log(level: str, message: str, **kwargs):
    """Log avec gestion d'erreur pour éviter les problèmes de handler."""
    try:
        getattr(logger, level)(message, **kwargs)
    except (TypeError, AttributeError):
        print(f"{level.upper()}: {message} - {kwargs}")


async def _login_core(email: str, password: str, db: AsyncSession) -> TokenResponseData:
    """
    Logique centrale de connexion - GESTION EXPLICITE DES TRANSACTIONS.
    
    Architecture propre : commit/rollback gérés ici, pas dans le service.
    Retourne les tokens + toutes les infos de l'utilisateur (sauf le mot de passe).
    """
    try:
        safe_log("debug", "🔵 Début _login_core", email=email)
        
        # Étape 1: Créer le service
        try:
            auth_service = AuthService(db)
            safe_log("debug", "✅ AuthService créé")
        except Exception as e:
            safe_log("error", "❌ Erreur création AuthService", error=str(e), error_type=type(e).__name__)
            raise
        
        # Étape 2: Authentifier l'utilisateur
        try:
            user = await auth_service.authenticate_user(email, password)
            safe_log("debug", "✅ authenticate_user terminé", user_found=user is not None)
        except Exception as e:
            safe_log("error", "❌ Erreur dans authenticate_user", error=str(e), error_type=type(e).__name__)
            raise
        
        if not user:
            safe_log("warning", "Tentative de connexion échouée", email=email)
            
            # Vérifier si l'utilisateur existe mais a un statut non actif
            try:
                user_check_result = await db.execute(
                    select(User).where(User.email == email)
                )
                user_check = user_check_result.scalar_one_or_none()
                
                if user_check and hasattr(user_check, 'statut'):
                    statut = str(user_check.statut) if user_check.statut is not None else None
                    
                    # Messages personnalisés selon le statut
                    if statut == 'en_attente':
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Votre compte est en attente de validation par notre équipe. Vous recevrez un email de confirmation une fois votre accès validé."
                        )
                    elif statut == 'bloqué':
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Votre compte a été bloqué. Veuillez contacter l'administrateur à support@seeg-talentsource.com"
                        )
                    elif statut == 'inactif':
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Votre compte a été désactivé. Veuillez contacter l'administrateur à support@seeg-talentsource.com"
                        )
                    elif statut == 'archivé':
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Votre compte a été archivé. Veuillez contacter l'administrateur à support@seeg-talentsource.com"
                        )
            except HTTPException:
                raise
            except Exception as e:
                safe_log("debug", "Erreur vérification statut", error=str(e))
            
            # Message générique si aucun statut spécifique
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou mot de passe incorrect",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Étape 3: Commit de la mise à jour last_login
        try:
            safe_log("debug", "🔄 Tentative de commit...")
            await db.commit()
            safe_log("debug", "✅ Commit réussi")
        except Exception as e:
            safe_log("error", "❌ Erreur lors du commit", error=str(e), error_type=type(e).__name__)
            raise
        
        # Étape 4: Refresh de l'utilisateur
        try:
            safe_log("debug", "🔄 Tentative de refresh...")
            await db.refresh(user)
            safe_log("debug", "✅ Refresh réussi")
        except Exception as e:
            safe_log("error", "❌ Erreur lors du refresh", error=str(e), error_type=type(e).__name__)
            raise
        
        # Étape 5: Créer les tokens
        try:
            safe_log("debug", "🔄 Création des tokens...")
            tokens = await auth_service.create_access_token(user)
            safe_log("debug", "✅ Tokens créés")
        except Exception as e:
            safe_log("error", "❌ Erreur création tokens", error=str(e), error_type=type(e).__name__)
            raise
        
        # Étape 6: Ajouter les informations utilisateur (sans le mot de passe)
        user_data = {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "phone": user.phone,
            "date_of_birth": user.date_of_birth.isoformat() if user.date_of_birth is not None else None,
            "sexe": user.sexe,
            "matricule": user.matricule,
            "email_verified": user.email_verified,
            "last_login": user.last_login.isoformat() if user.last_login is not None else None,
            "is_active": user.is_active,
            "is_internal_candidate": user.is_internal_candidate,
            "adresse": user.adresse,
            "candidate_status": user.candidate_status,
            "statut": user.statut,
            "poste_actuel": user.poste_actuel,
            "annees_experience": user.annees_experience,
            "no_seeg_email": user.no_seeg_email,
            "created_at": user.created_at.isoformat() if user.created_at is not None else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at is not None else None
        }
        
        safe_log(
            "info",
            "✅ Connexion réussie",
            user_id=str(user.id),
            email=user.email,
            role=user.role,
        )
        
        return TokenResponseData(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            token_type=tokens.token_type,
            expires_in=tokens.expires_in,
            user=user_data
        )
        
    except HTTPException:
        # HTTPException = erreurs métier, pas de rollback nécessaire
        raise
    except Exception as e:
        # Erreur technique = rollback automatique par get_db()
        safe_log("error", "❌ Erreur globale dans _login_core", error=str(e), error_type=type(e).__name__, email=email)
        import traceback
        safe_log("error", "Traceback complet", traceback=traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur interne du serveur: {str(e)}",
        )


@router.post("/token", response_model=TokenResponse, summary="Obtenir un token (déprécié)", include_in_schema=False)
async def login_token_deprecated(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Déprécié: utiliser /api/v1/auth/login
    Reste compatible pour les clients OAuth2 (form-urlencoded)
    """
    return await _login_core(form_data.username, form_data.password, db)


@router.post("/login", response_model=TokenResponseData, summary="Connexion utilisateur (JSON ou form)", openapi_extra={
    "requestBody": {
        "content": {
            "application/json": {
                "example": {"email": "candidate@example.com", "password": "MotdepasseFort123!"}
            },
            "application/x-www-form-urlencoded": {
                "schema": {"type": "object", "properties": {"username": {"type": "string"}, "password": {"type": "string"}}},
                "example": {"username": "candidate@example.com", "password": "MotdepasseFort123!"}
            }
        }
    },
    "responses": {
        "200": {
            "content": {"application/json": {"example": {
                "access_token": "<jwt>",
                "refresh_token": "<jwt>",
                "token_type": "bearer",
                "expires_in": 3600,
                "user": {
                    "id": "uuid",
                    "email": "candidate@example.com",
                    "first_name": "Jean",
                    "last_name": "Dupont",
                    "role": "candidate",
                    "statut": "actif",
                    "matricule": 12345
                }
            }}}
        },
        "401": {"description": "Email ou mot de passe incorrect"},
        "429": {"description": "Trop de tentatives de connexion"}
    }
})
# @limiter.limit(AUTH_LIMITS)  # ⚠️ TEMPORAIREMENT DÉSACTIVÉ - Problème avec slowapi
async def login(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Connexion d'un utilisateur via un unique endpoint qui accepte:
    - application/json: {"email": ..., "password": ...}
    - application/x-www-form-urlencoded: username=email, password=...
    """
    try:
        # 1) Si un Authorization: Bearer <token> est fourni et valide, retourner directement de nouveaux tokens
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            try:
                token = auth_header.split(" ", 1)[1].strip()
                payload = TokenManager.verify_token(token)
                if payload and payload.get("sub"):
                    user_id = payload["sub"]
                    result = await db.execute(select(User).where(User.id == user_id))
                    user = result.scalar_one_or_none()
                    if user:
                        auth_service = AuthService(db)
                        tokens = await auth_service.create_access_token(user)
                        # Construire la réponse complète avec les infos utilisateur
                        user_data = {
                            "id": str(user.id),
                            "email": user.email,
                            "first_name": user.first_name,
                            "last_name": user.last_name,
                            "role": user.role,
                            "phone": user.phone,
                            "date_of_birth": user.date_of_birth.isoformat() if user.date_of_birth is not None else None,
                            "sexe": user.sexe,
                            "matricule": user.matricule,
                            "email_verified": user.email_verified,
                            "last_login": user.last_login.isoformat() if user.last_login is not None else None,
                            "is_active": user.is_active,
                            "is_internal_candidate": user.is_internal_candidate,
                            "adresse": user.adresse,
                            "candidate_status": user.candidate_status,
                            "statut": user.statut,
                            "poste_actuel": user.poste_actuel,
                            "annees_experience": user.annees_experience,
                            "no_seeg_email": user.no_seeg_email,
                            "created_at": user.created_at.isoformat() if user.created_at is not None else None,
                            "updated_at": user.updated_at.isoformat() if user.updated_at is not None else None
                        }
                        return TokenResponseData(
                            access_token=tokens.access_token,
                            refresh_token=tokens.refresh_token,
                            token_type=tokens.token_type,
                            expires_in=tokens.expires_in,
                            user=user_data
                        )
            except Exception:
                # Ignore et poursuivre le flux normal (email/password)
                pass

        content_type = request.headers.get("content-type", "").lower()
        email = None
        password = None

        if content_type.startswith("application/x-www-form-urlencoded") or content_type.startswith("multipart/form-data"):
            form = await request.form()
            email = str(form.get("username") or form.get("email") or "").strip()
            password = str(form.get("password") or "").strip()
        else:
            body = await request.json()
            email = (body.get("email") or body.get("username") or "").strip()
            password = (body.get("password") or "").strip()

        if not email or not password:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="email/username et password requis")

        return await _login_core(email, password, db)
        
    except HTTPException:
        raise
    except Exception as e:
        safe_log("error", "Erreur lors de la connexion unifiée", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur",
        )


@router.post("/signup", response_model=UserResponse, summary="Inscription candidat", openapi_extra={
    "requestBody": {"content": {"application/json": {"example": {
        "email": "jean.dupont@seeg-gabon.com",
        "password": "Password#2025!Secure",
        "first_name": "Jean",
        "last_name": "Dupont",
        "phone": "+24106223344",
        "date_of_birth": "1990-05-15",
        "sexe": "M",
        "candidate_status": "interne",
        "matricule": 123456,
        "no_seeg_email": False,
        "adresse": "123 Rue de la Liberté, Libreville",
        "poste_actuel": "Technicien Réseau",
        "annees_experience": 5
    }}}},
    "responses": {
        "200": {"description": "Utilisateur créé", "content": {"application/json": {"example": {"id": "uuid", "email": "jean.dupont@seeg-gabon.com", "role": "candidate", "statut": "actif"}}}},
        "400": {"description": "Données invalides"},
        "429": {"description": "Trop de tentatives d'inscription"}
    }
})
# @limiter.limit(SIGNUP_LIMITS)  # ⚠️ TEMPORAIREMENT DÉSACTIVÉ - Problème avec slowapi
async def signup_candidate(
    request: Request,
    signup_data: CandidateSignupRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Inscription d'un candidat (public) - GESTION EXPLICITE DES TRANSACTIONS.
    
    Architecture propre : commit/rollback gérés ici, pas dans le service.
    
    Args:
        signup_data: Données d'inscription du candidat
        db: Session de base de données
        
    Returns:
        UserResponse: Informations du candidat créé
        
    Raises:
        HTTPException: Si l'inscription échoue
    """
    try:
        safe_log("debug", "🔵 Début signup_candidate", email=signup_data.email)
        
        # Étape 1: Créer le service
        try:
            auth_service = AuthService(db)
            safe_log("debug", "✅ AuthService créé")
        except Exception as e:
            safe_log("error", "❌ Erreur création AuthService", error=str(e), error_type=type(e).__name__)
            raise
        
        # Étape 2: Créer le candidat
        try:
            user = await auth_service.create_candidate(signup_data)
            safe_log("debug", "✅ Candidat préparé", email=user.email)
        except ValidationError as e:
            safe_log("warning", "Validation échouée", error=str(e))
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            safe_log("error", "❌ Erreur dans create_candidate", error=str(e), error_type=type(e).__name__)
            raise
        
        # Étape 3: Commit
        try:
            safe_log("debug", "🔄 Tentative de commit...")
            await db.commit()
            safe_log("debug", "✅ Commit réussi")
        except Exception as e:
            safe_log("error", "❌ Erreur lors du commit", error=str(e), error_type=type(e).__name__)
            raise
        
        # Étape 4: Refresh
        try:
            safe_log("debug", "🔄 Tentative de refresh...")
            await db.refresh(user)
            safe_log("debug", "✅ Refresh réussi", user_id=str(user.id))
        except Exception as e:
            safe_log("error", "❌ Erreur lors du refresh", error=str(e), error_type=type(e).__name__)
            raise
        
        # Étape 4.5: Envoyer email de bienvenue + notification (PATTERN UNIFIÉ)
        try:
            from app.services.notification_email_manager import NotificationEmailManager
            notif_email_manager = NotificationEmailManager(db)
            
            result = await notif_email_manager.notify_and_email_registration(
                user_id=user.id,
                email=str(user.email),
                first_name=str(user.first_name),
                last_name=str(user.last_name),
                sexe=str(user.sexe) if (user.sexe is not None and str(user.sexe)) else None
            )
            await db.commit()
            
            safe_log("info", "✅ Email + notification bienvenue envoyés", 
                    user_id=str(user.id),
                    email_sent=result["email_sent"],
                    notification_sent=result["notification_sent"])
        except Exception as e:
            safe_log("warning", "⚠️ Erreur email/notification bienvenue", error=str(e))
            # Ne pas bloquer l'inscription si email/notification échouent (fail-safe)
        
        # Étape 5: Créer une demande d'accès si statut='en_attente'
        if hasattr(user, 'statut') and str(getattr(user, 'statut', '')) == 'en_attente':
            try:
                from app.services.access_request import AccessRequestService
                from app.services.email import EmailService
                
                access_service = AccessRequestService(db)
                email_service = EmailService(db)
                
                safe_log("debug", "🔄 Création AccessRequest (statut=en_attente)...")
                await access_service.create_access_request(
                    user_id=user.id,
                    email=str(user.email),
                    first_name=str(user.first_name),
                    last_name=str(user.last_name),
                    phone=str(user.phone) if user.phone is not None else None,
                    matricule=str(user.matricule) if user.matricule is not None else None
                )
                
                # Commit de la demande d'accès
                await db.commit()
                safe_log("debug", "✅ AccessRequest créée", user_id=str(user.id))
                
                # Email 2 : Demande en Attente au candidat
                try:
                    await email_service.send_access_request_pending_email(
                        to_email=str(user.email),
                        first_name=str(user.first_name),
                        last_name=str(user.last_name),
                        sexe=str(user.sexe) if user.sexe is not None else None
                    )
                    safe_log("info", "Email demande en attente envoyé", user_id=str(user.id))
                except Exception as e:
                    safe_log("warning", "Erreur envoi email demande en attente", error=str(e))
                
                # Email 3 : Notification Admin à support@seeg-talentsource.com
                try:
                    date_birth_str = str(user.date_of_birth) if user.date_of_birth is not None else None
                    await email_service.send_access_request_notification_to_admin(
                        first_name=str(user.first_name),
                        last_name=str(user.last_name),
                        email=str(user.email),
                        phone=str(user.phone) if user.phone is not None else None,
                        matricule=str(user.matricule) if user.matricule is not None else None,
                        date_of_birth=date_birth_str,
                        sexe=str(user.sexe) if user.sexe is not None else None,
                        adresse=str(getattr(user, 'adresse', None)) if getattr(user, 'adresse', None) is not None else None
                    )
                    safe_log("info", "Email notification admin envoyé", user_id=str(user.id))
                except Exception as e:
                    safe_log("warning", "Erreur envoi notification admin", error=str(e))
                
                safe_log("info", "Candidat en attente de validation créé", user_id=str(user.id))
                
            except Exception as e:
                safe_log("error", "❌ Erreur création AccessRequest", error=str(e))
                await db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Erreur lors de la création de la demande d'accès"
                )
        else:
            # Email 1 : Bienvenue (statut=actif)
            try:
                from app.services.email import EmailService
                email_service = EmailService(db)
                
                await email_service.send_welcome_email(
                    to_email=str(user.email),
                    first_name=str(user.first_name),
                    last_name=str(user.last_name),
                    sexe=str(user.sexe) if user.sexe is not None else None
                )
                safe_log("info", "Email de bienvenue envoyé", user_id=str(user.id))
            except Exception as e:
                safe_log("warning", "Erreur envoi email bienvenue", error=str(e))
            
            safe_log("info", "Candidat actif créé (accès immédiat)", user_id=str(user.id))
        
        # Étape 6: Créer la réponse
        try:
            safe_log("debug", "🔄 Création UserResponse...")
            response = UserResponse.from_orm(user)
            safe_log("debug", "✅ UserResponse créé")
        except Exception as e:
            safe_log("error", "❌ Erreur création UserResponse", error=str(e), error_type=type(e).__name__)
            raise
        
        safe_log("info", "✅ Inscription candidat réussie", 
                user_id=str(user.id), 
                email=user.email,
                statut=getattr(user, 'statut', 'actif'))
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        # Erreur technique = rollback automatique par get_db()
        safe_log("error", "❌ Erreur globale signup_candidate", error=str(e), error_type=type(e).__name__)
        import traceback
        safe_log("error", "Traceback complet", traceback=traceback.format_exc())
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erreur interne du serveur: {str(e)}")


@router.post("/verify-matricule", summary="Vérifier un matricule SEEG", openapi_extra={
    "requestBody": {"content": {"application/json": {"example": {"matricule": 123456}}}},
    "responses": {
        "200": {"description": "Matricule valide", "content": {"application/json": {"example": {
            "valid": True,
            "message": "Matricule valide",
            "agent_info": {"matricule": "123456", "first_name": "Jean", "last_name": "Dupont", "email": "jean.dupont@seeg-gabon.com"}
        }}}},
        "200 (invalide)": {"description": "Matricule invalide", "content": {"application/json": {"example": {
            "valid": False,
            "message": "Matricule invalide ou inactif",
            "agent_info": None
        }}}}
    }
})
async def verify_matricule_endpoint(
    request: Request,
    matricule_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """
    Vérifier qu'un matricule SEEG existe et est actif.
    
    **Endpoint public** : Utilisé lors de l'inscription des candidats internes
    pour valider leur matricule en temps réel.
    
    **Retourne** :
    - `valid` : True si le matricule existe et est actif
    - `message` : Message explicatif
    - `agent_info` : Informations de l'agent si trouvé (matricule, nom, prénom, email)
    
    **Exemple de requête** :
    ```json
    {
        "matricule": 123456
    }
    ```
    """
    matricule = None  # Initialiser pour éviter unbound
    try:
        matricule = matricule_data.get("matricule")
        
        if not matricule:
            return {
                "valid": False,
                "message": "Matricule requis",
                "agent_info": None
            }
        
        # Vérifier dans la table seeg_agents
        result = await db.execute(
            select(SeegAgent).where(SeegAgent.matricule == int(matricule))
        )
        agent = result.scalar_one_or_none()
        
        if agent:
            return {
                "valid": True,
                "message": "Matricule valide",
                "agent_info": {
                    "matricule": str(agent.matricule),
                    "first_name": str(agent.prenom) if agent.prenom is not None else "",
                    "last_name": str(agent.nom) if agent.nom is not None else ""
                }
            }
        else:
            return {
                "valid": False,
                "message": "Matricule non trouvé dans la base SEEG. Veuillez vérifier votre matricule ou contacter le service RH.",
                "agent_info": None
            }
        
    except Exception as e:
        safe_log("error", "Erreur vérification matricule", matricule=str(matricule) if matricule else "unknown", error=str(e))
        return {
            "valid": False,
            "message": f"Erreur lors de la vérification: {str(e)}",
            "agent_info": None
        }


@router.post("/create-user", response_model=UserResponse, summary="Créer un utilisateur (admin/recruteur)")
async def create_user(
    user_data: CreateUserRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Créer un utilisateur (admin/recruteur) - admin seulement.
    GESTION EXPLICITE DES TRANSACTIONS.
    """
    try:
        auth_service = AuthService(db)
        user = await auth_service.create_user(user_data)
        
        # ✅ Commit explicite de la création
        await db.commit()
        await db.refresh(user)
        
        safe_log(
            "info",
            "Utilisateur créé par admin",
            user_id=str(user.id),
            email=user.email,
            role=user.role,
            created_by=str(current_admin.id),
        )
        return UserResponse.from_orm(user)
        
    except HTTPException:
        raise
    except ValidationError as e:
        safe_log("warning", "Erreur de validation lors de la création d'utilisateur", error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur lors de la création d'utilisateur", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur")


@router.post("/create-first-admin", response_model=UserResponse, summary="Créer le premier administrateur")
async def create_first_admin(
    db: AsyncSession = Depends(get_db)
):
    """
    Créer le premier administrateur - GESTION EXPLICITE DES TRANSACTIONS.
    """
    try:
        # Vérifier qu'aucun admin n'existe
        result = await db.execute(select(User).where(User.role == "admin"))
        existing_admin = result.scalar_one_or_none()
        if existing_admin:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Un administrateur existe déjà")
        
        # Créer l'admin
        auth_service = AuthService(db)
        hashed_password = auth_service.password_manager.hash_password("Sevan@Seeg")
        admin = User(
            email="sevankedesh11@gmail.com",  # type: ignore
            first_name="Sevan Kedesh",  # type: ignore
            last_name="IKISSA PENDY",  # type: ignore
            role="admin",  # type: ignore
            hashed_password=hashed_password,  # type: ignore
        )
        db.add(admin)
        
        # ✅ Commit explicite de la création
        await db.commit()
        await db.refresh(admin)
        
        safe_log("info", "Premier administrateur créé", user_id=str(admin.id), email=admin.email)
        return UserResponse.from_orm(admin)
        
    except HTTPException:
        # Erreur métier, rollback automatique par get_db()
        raise
    except Exception as e:
        # Erreur technique, rollback automatique par get_db()
        safe_log("error", "Erreur lors de la création du premier admin", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur")


@router.get("/me", response_model=UserResponse, summary="Obtenir le profil de l'utilisateur connecté", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {"id": "uuid", "email": "candidate@example.com", "role": "candidate"}}}}}
})
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """Retourne le profil de l'utilisateur connecté avec ses informations complètes"""
    safe_log("debug", "Profil utilisateur demandé", user_id=str(current_user.id), email=current_user.email)
    return UserResponse.from_orm(current_user)


@router.post("/refresh", response_model=TokenResponse, summary="Rafraîchir le token d'accès", openapi_extra={
    "requestBody": {
        "content": {
            "application/json": {
                "example": {"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}
            }
        }
    },
    "responses": {
        "200": {
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIs...",
                        "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
                        "token_type": "bearer",
                        "expires_in": 3600
                    }
                }
            }
        },
        "401": {"description": "Token de rafraîchissement invalide ou expiré"},
        "429": {"description": "Trop de tentatives de rafraîchissement"}
    }
})
# @limiter.limit(AUTH_LIMITS)  # ⚠️ TEMPORAIREMENT DÉSACTIVÉ - Problème avec slowapi
async def refresh_token(
    request: Request,
    payload: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Rafraîchir le token d'accès en utilisant le token de rafraîchissement
    
    - **refresh_token**: Token de rafraîchissement valide obtenu lors de la connexion
    
    Retourne un nouveau token d'accès et un nouveau token de rafraîchissement.
    """
    try:
        # Vérifier le refresh token
        token_manager = TokenManager()
        payload_data = token_manager.verify_token(payload.refresh_token)
        
        if not payload_data:
            safe_log("warning", "Tentative de refresh avec token invalide")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de rafraîchissement invalide",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Vérifier que c'est bien un refresh token
        if payload_data.get("type") != "refresh":
            safe_log("warning", "Tentative de refresh avec un token d'accès")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Type de token incorrect",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Récupérer l'utilisateur
        user_id = payload_data.get("sub")
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            safe_log("warning", "Utilisateur non trouvé lors du refresh", user_id=user_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Utilisateur non trouvé",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Vérifier que le compte est actif
        if not bool(user.is_active):
            safe_log("warning", "Tentative de refresh pour compte désactivé", user_id=user_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Compte désactivé",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Créer de nouveaux tokens
        auth_service = AuthService(db)
        tokens = await auth_service.create_access_token(user)
        
        safe_log("info", "Token rafraîchi avec succès", user_id=str(user.id), email=user.email)
        
        return tokens
        
    except HTTPException:
        raise
    except Exception as e:
        safe_log("error", "Erreur lors du rafraîchissement du token", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur",
        )


@router.post("/logout", summary="Déconnexion")
async def logout(current_user: User = Depends(get_current_user)):
    """
    Déconnexion de l'utilisateur actuel.
    Note: Avec JWT, la déconnexion se fait côté client en supprimant le token.
    """
    safe_log("info", "Déconnexion utilisateur", user_id=str(current_user.id))
    return {"message": "Déconnexion réussie", "user_id": str(current_user.id)}


@router.get("/verify-matricule", response_model=MatriculeVerificationResponse, summary="Vérifier le matricule de l'utilisateur connecté", openapi_extra={
    "responses": {
        "200": {
            "content": {
                "application/json": {
                    "examples": {
                        "valide": {"summary": "Matricule valide", "value": {"valid": True, "agent_matricule": "123456"}},
                        "invalide": {"summary": "Matricule invalide", "value": {"valid": False, "reason": "Matricule non trouvé dans seeg_agents"}}
                    }
                }
            }
        }
    }
})
async def verify_user_matricule(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Vérifie que le matricule de l'utilisateur connecté correspond à un agent actif dans la table seeg_agents.
    Autorise uniquement les rôles candidats.
    """
    if str(current_user.role) != "candidate":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accessible uniquement aux candidats")

    if current_user.matricule is None:
        return MatriculeVerificationResponse(valid=False, reason="Aucun matricule enregistré pour cet utilisateur")  # type: ignore

    try:
        # Cast matricule to integer to match seeg_agents.matricule type
        try:
            matricule_str = str(current_user.matricule).strip() if current_user.matricule is not None else ""
            matricule_int = int(matricule_str)
        except ValueError:
            return MatriculeVerificationResponse(valid=False, reason="Matricule invalide (doit être numérique)")  # type: ignore

        result = await db.execute(select(SeegAgent).where(SeegAgent.matricule == matricule_int))
        agent = result.scalar_one_or_none()
        if agent:
            return MatriculeVerificationResponse(valid=True, agent_matricule=str(getattr(agent, 'matricule', '')))  # type: ignore
        return MatriculeVerificationResponse(valid=False, reason="Matricule non trouvé dans seeg_agents")  # type: ignore
    except Exception as e:
        matricule_log = str(current_user.matricule) if current_user.matricule is not None else "None"
        safe_log("error", "Erreur de vérification de matricule", error=str(e), matricule=matricule_log)
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.post("/forgot-password", summary="Demander la réinitialisation du mot de passe", openapi_extra={
    "requestBody": {"content": {"application/json": {"example": {"email": "user@example.com"}}}},
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "message": "Email envoyé si l'adresse existe"}}}}}
})
async def forgot_password(
    payload: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Demande de réinitialisation du mot de passe.
    
    Pour des raisons de sécurité, retourne toujours un succès même si l'email n'existe pas.
    Cela empêche l'énumération des utilisateurs.
    """
    try:
        service = AuthService(db)
        await service.reset_password_request(payload.email)
        safe_log("info", "Demande de réinitialisation mot de passe", email=payload.email)
        return {"success": True, "message": "Email envoyé si l'adresse existe"}
    except Exception as e:
        safe_log("error", "Erreur demande réinitialisation mot de passe", error=str(e))
        # Retourner succès même en cas d'erreur pour éviter l'énumération
        return {"success": True, "message": "Email envoyé si l'adresse existe"}


@router.post("/reset-password", summary="Confirmer la réinitialisation du mot de passe", openapi_extra={
    "requestBody": {"content": {"application/json": {"example": {"token": "<token>", "new_password": "NouveauMotDePasse123!"}}}},
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "message": "Mot de passe réinitialisé"}}}}, "400": {"description": "Token invalide ou expiré"}}
})
async def reset_password(
    payload: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
):
    """
    Confirmer la réinitialisation du mot de passe avec le token reçu par email.
    GESTION EXPLICITE DES TRANSACTIONS.
    
    Le token a une durée de validité limitée (typiquement 1 heure).
    """
    try:
        service = AuthService(db)
        user = await service.reset_password_confirm(payload.token, payload.new_password)
        
        # ✅ Commit explicite du changement de mot de passe
        await db.commit()
        
        safe_log("info", "Mot de passe réinitialisé avec succès", user_id=str(user.id))
        
        # Envoyer email + notification de confirmation (non-bloquant)
        try:
            from app.services.notification_email_manager import NotificationEmailManager
            notif_email_manager = NotificationEmailManager(db)
            
            result = await notif_email_manager.notify_and_email_password_changed(
                user_id=user.id,
                email=str(user.email),
                first_name=str(user.first_name),
                last_name=str(user.last_name)
            )
            await db.commit()
            
            safe_log("info", "✅ Email + notification changement password envoyés",
                    user_id=str(user.id),
                    email_sent=result["email_sent"],
                    notification_sent=result["notification_sent"])
        except Exception as e:
            safe_log("warning", "⚠️ Erreur email/notification password change", 
                    user_id=str(user.id), error=str(e))
        return {"success": True, "message": "Mot de passe réinitialisé"}
        
    except (ValidationError, PydanticValidationError) as e:
        safe_log("warning", "Erreur validation réinitialisation mot de passe", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except UnauthorizedError as e:
        safe_log("warning", "Token de réinitialisation invalide")
        raise HTTPException(status_code=400, detail="Token invalide ou expiré")
    except Exception as e:
        safe_log("error", "Erreur réinitialisation mot de passe", error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.post("/change-password", summary="Changer le mot de passe (connecté)", openapi_extra={
    "requestBody": {"content": {"application/json": {"example": {"current_password": "Ancien123!", "new_password": "Nouveau123!"}}}},
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "message": "Mot de passe modifié"}}}}, "401": {"description": "Mot de passe actuel incorrect"}}
})
async def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Changer le mot de passe de l'utilisateur connecté.
    GESTION EXPLICITE DES TRANSACTIONS.
    
    Nécessite le mot de passe actuel pour confirmation.
    """
    try:
        service = AuthService(db)
        user = await service.change_password(str(current_user.id), payload.current_password, payload.new_password)
        
        # ✅ Commit explicite du changement de mot de passe
        await db.commit()
        
        safe_log("info", "Mot de passe changé avec succès", user_id=str(current_user.id))
        return {"success": True, "message": "Mot de passe modifié"}
        
    except UnauthorizedError as e:
        safe_log("warning", "Tentative de changement avec mauvais mot de passe", user_id=str(current_user.id))
        raise HTTPException(status_code=401, detail=str(e))
    except (ValidationError, PydanticValidationError) as e:
        safe_log("warning", "Erreur validation changement mot de passe", user_id=str(current_user.id), error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur changement mot de passe", user_id=str(current_user.id), error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

