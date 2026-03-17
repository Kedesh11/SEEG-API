"""
Endpoints d'authentification - Système unique et robuste
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from typing import Dict, Any, Optional
from bson import ObjectId
import structlog
from pydantic import ValidationError as PydanticValidationError

from app.db.database import get_db
from app.schemas.auth import (
    LoginRequest, CandidateSignupRequest, CreateUserRequest, TokenResponse,
    TokenResponseData, RefreshTokenRequest, PasswordResetRequest,
    PasswordResetConfirm, ChangePasswordRequest, MatriculeVerificationResponse
)
from app.schemas.user import UserResponse, UserWithProfile
from app.services.auth import AuthService
from app.core.exceptions import ValidationError, UnauthorizedError
from app.core.dependencies import get_current_active_user, get_current_admin_user, get_current_user
from app.core.security.security import TokenManager

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["🔐 Authentification"])


def safe_log(level: str, message: str, **kwargs):
    """Log avec gestion d'erreur pour éviter les problèmes de handler."""
    try:
        getattr(logger, level)(message, **kwargs)
    except (TypeError, AttributeError):
        print(f"{level.upper()}: {message} - {kwargs}")


async def _login_core(email: str, password: str, db: Any) -> TokenResponseData:
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
            statut = None
            try:
                user_check = await db.users.find_one({"email": email})
                if user_check:
                    statut = user_check.get('statut')
            except Exception as e:
                safe_log("debug", "Erreur vérification statut", error=str(e))

            # Messages personnalisés selon le statut
            m_base = "Votre compte a été {}. Veuillez contacter le support."
            if statut == 'en_attente':
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Compte en attente de validation."
                )
            elif statut in ['bloqué', 'inactif', 'archivé']:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=m_base.format(statut)
                )

            # Message générique si aucun statut spécifique
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou mot de passe incorrect",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # MongoDB n'a pas besoin de commit ou de refresh dans ce contexte

        # Étape 5: Créer les tokens
        try:
            safe_log("debug", "🔄 Création des tokens...")
            tokens = await auth_service.create_access_token(user)
            safe_log("debug", "✅ Tokens créés")
        except Exception as e:
            safe_log("error", "❌ Erreur création tokens", error=str(e), error_type=type(e).__name__)
            raise

        # Étape 6: Récupérer le profil candidat si c'est un candidat
        candidate_profile = None
        if user.get("role") == "candidate":
            try:
                from app.services.user import UserService
                user_service = UserService(db)
                user_id = user.get("_id", user.get("id"))
                candidate_profile = await user_service.get_candidate_profile(str(user_id))
                safe_log("debug", "✅ Profil candidat récupéré",
                        user_id=str(user.get("_id", user.get("id"))),
                        has_profile=candidate_profile is not None)
            except Exception as e:
                safe_log("warning", "⚠️ Erreur récupération profil candidat lors du login",
                        user_id=str(user.get("_id", user.get("id"))),
                        error=str(e))

        # Étape 7: Ajouter les informations utilisateur complètes (avec profil candidat)
        dob = user.get("date_of_birth")
        last_login = user.get("last_login")
        created_at = user.get("created_at")
        updated_at = user.get("updated_at")

        user_data = {
            "id": str(user.get("_id", user.get("id"))),
            "email": user.get("email"),
            "first_name": user.get("first_name"),
            "last_name": user.get("last_name"),
            "role": user.get("role"),
            "phone": user.get("phone"),
            "date_of_birth": dob.isoformat() if hasattr(dob, "isoformat") else dob,
            "sexe": user.get("sexe"),
            "matricule": user.get("matricule"),
            "email_verified": user.get("email_verified"),
            "last_login": last_login.isoformat() if hasattr(last_login, "isoformat") else last_login,
            "is_active": user.get("is_active"),
            "is_internal_candidate": user.get("is_internal_candidate"),
            "adresse": user.get("adresse"),
            "candidate_status": user.get("candidate_status"),
            "statut": user.get("statut"),
            "poste_actuel": user.get("poste_actuel"),
            "annees_experience": user.get("annees_experience"),
            "no_seeg_email": user.get("no_seeg_email"),
            "created_at": created_at.isoformat() if hasattr(
                created_at, "isoformat") else created_at,
            "updated_at": updated_at.isoformat() if hasattr(
                updated_at, "isoformat") else updated_at,
            "candidate_profile": None
        }

        # Ajouter le profil candidat s'il existe
        if candidate_profile:
            from app.schemas.user import CandidateProfileResponse
            dump = CandidateProfileResponse.model_validate(
                candidate_profile
            ).model_dump()
            user_data["candidate_profile"] = dump

        safe_log(
            "info",
            "✅ Connexion réussie",
            user_id=str(user.get("_id", user.get("id"))),
            email=user.get("email"),
            role=user.get("role"),
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
        safe_log("error", "❌ Erreur globale login", error=str(e),
                 error_type=type(e).__name__, email=email)
        import traceback
        safe_log("error", "Traceback complet", traceback=traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur interne du serveur: {str(e)}",
        )


@router.post("/token",
             response_model=TokenResponse,
             summary="Token (déprécié)",
             include_in_schema=False)
async def login_token_deprecated(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Any = Depends(get_db),
):
    """
    Déprécié: utiliser /api/v1/auth/login
    Reste compatible pour les clients OAuth2 (form-urlencoded)
    """
    return await _login_core(form_data.username, form_data.password, db)


@router.post("/login",
             response_model=TokenResponseData,
             summary="Connexion utilisateur",
             openapi_extra={
    "responses": {
        "200": {"description": "Connexion réussie"},
        "401": {"description": "Email ou mot de passe incorrect"}
    }
})
# @limiter.limit(AUTH_LIMITS)  # ⚠️ TEMPORAIREMENT DÉSACTIVÉ - Problème avec slowapi
async def login(
    request: Request,
    db: Any = Depends(get_db),
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
                    user_query = {"_id": ObjectId(user_id)} if len(
                        str(user_id)) == 24 else {"_id": str(user_id)}
                    user = await db.users.find_one(user_query)
                    if user:
                        auth_service = AuthService(db)
                        tokens = await auth_service.create_access_token(user)
                        dob = user.get("date_of_birth")
                        last_login = user.get("last_login")
                        created_at = user.get("created_at")
                        updated_at = user.get("updated_at")
                        user_data = {
                            "id": str(user.get("_id", user.get("id"))),
                            "email": user.get("email"),
                            "first_name": user.get("first_name"),
                            "last_name": user.get("last_name"),
                            "role": user.get("role"),
                            "phone": user.get("phone"),
                            "date_of_birth": dob.isoformat() if hasattr(dob, "isoformat") else dob,
                            "sexe": user.get("sexe"),
                            "matricule": user.get("matricule"),
                            "email_verified": user.get("email_verified"),
                            "last_login": last_login.isoformat() if hasattr(last_login, "isoformat") else last_login,
                            "is_active": user.get("is_active"),
                            "is_internal_candidate": user.get("is_internal_candidate"),
                            "adresse": user.get("adresse"),
                            "candidate_status": user.get("candidate_status"),
                            "statut": user.get("statut"),
                            "poste_actuel": user.get("poste_actuel"),
                            "annees_experience": user.get("annees_experience"),
                            "no_seeg_email": user.get("no_seeg_email"),
                            "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else created_at,
                            "updated_at": updated_at.isoformat() if hasattr(updated_at, "isoformat") else updated_at
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
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="email et password requis"
            )

        return await _login_core(email, password, db)

    except HTTPException:
        raise
    except Exception as e:
        safe_log("error", "Erreur connexion", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne"
        )


@router.post(
    "/signup",
    response_model=UserWithProfile,
    status_code=status.HTTP_201_CREATED,  # Standard REST : 201 pour création de ressource
    summary="Inscription candidat",
    openapi_extra={
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
            "201": {"description": "Utilisateur créé avec succès", "content": {"application/json": {"example": {"id": "uuid", "email": "jean.dupont@seeg-gabon.com", "role": "candidate", "statut": "actif"}}}},
            "400": {"description": "Données invalides"},
            "429": {"description": "Trop de tentatives d'inscription"}
        }
    }
)
# @limiter.limit(SIGNUP_LIMITS)  # ⚠️ TEMPORAIREMENT DÉSACTIVÉ - Problème avec slowapi
async def signup_candidate(
    request: Request,
    signup_data: CandidateSignupRequest,
    db: Any = Depends(get_db)
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
        u_email = signup_data.email
        safe_log("debug", "🔵 Début signup", email=u_email)

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

        # MongoDB ne nécessite pas de commit ou refresh explicite
        u_id = str(user.get("_id", user.get("id")))
        safe_log("debug", "✅ Candidat enregistré", user_id=u_id)

        # Étape 4.5: Envoyer email de bienvenue + notification (PATTERN UNIFIÉ)
        try:
            from app.services.notification_email_manager import NotificationEmailManager
            notif_email_manager = NotificationEmailManager(db)

            result = await notif_email_manager.notify_and_email_registration(
                user_id=user.get("_id", user.get("id")),
                email=str(user.get("email")),
                first_name=str(user.get("first_name")),
                last_name=str(user.get("last_name")),
                sexe=str(user.get("sexe")) if user.get("sexe") else None
            )

            safe_log("info", "✅ Mail bienvenue envoyé",
                    user_id=str(user.get("_id", user.get("id"))),
                    email_sent=result["email_sent"])
        except Exception as e:
            safe_log("warning", "⚠️ Erreur email/notification bienvenue", error=str(e))
            # Ne pas bloquer l'inscription si email/notification échouent (fail-safe)

        # Étape 5: Créer une demande d'accès si statut='en_attente'
        if str(user.get('statut', '')) == 'en_attente':
            try:
                from app.services.access_request import AccessRequestService
                from app.services.email import EmailService

                access_service = AccessRequestService(db)
                email_service = EmailService(db)

                safe_log("debug", "🔄 Création AccessRequest (statut=en_attente)...")
                await access_service.create_access_request(
                    user_id=user.get("_id", user.get("id")),
                    email=str(user.get("email")),
                    first_name=str(user.get("first_name")),
                    last_name=str(user.get("last_name")),
                    phone=str(user.get("phone")) if user.get("phone") else None,
                    matricule=str(user.get("matricule")) if user.get("matricule") else None
                )

                safe_log("debug", "✅ AccessRequest créée", user_id=str(user.get("_id", user.get("id"))))

                # Email 2 : Demande en Attente au candidat
                try:
                    u_id = str(user.get("_id", user.get("id")))
                    await email_service.send_access_request_pending_email(
                        to_email=str(user.get("email")),
                        first_name=str(user.get("first_name")),
                        last_name=str(user.get("last_name")),
                        sexe=str(user.get("sexe")) if user.get("sexe") else None
                    )
                    safe_log("info", "Email en attente envoyé", user_id=u_id)
                except Exception as e:
                    safe_log("warning", "Erreur envoi email demande en attente", error=str(e))

                # Email 3 : Notification Admin
                try:
                    u_id = str(user.get("_id", user.get("id")))
                    await email_service.\
                        send_access_request_notification_to_admin(
                            first_name=str(user.get("first_name")),
                            last_name=str(user.get("last_name")),
                            email=str(user.get("email")),
                            phone=str(user.get("phone")) if user.get("phone") else None,
                            matricule=str(user.get("matricule")) if user.get("matricule") else None,
                            date_of_birth=str(user.get("date_of_birth")) if user.get("date_of_birth") else None,
                            sexe=str(user.get("sexe")) if user.get("sexe") else None,
                            adresse=str(user.get("adresse")) if user.get("adresse") else None
                        )
                    safe_log("info", "Email notif admin envoyé", user_id=u_id)
                except Exception as e:
                    safe_log("warning", "Erreur envoi notification admin", error=str(e))

            except Exception as e:
                safe_log("error", "❌ Erreur création AccessRequest", error=str(e))
        else:
            # Email 1 : Bienvenue (statut=actif)
            try:
                from app.services.email import EmailService
                email_service = EmailService(db)

                await email_service.send_welcome_email(
                    to_email=str(user.get("email")),
                    first_name=str(user.get("first_name")),
                    last_name=str(user.get("last_name")),
                    sexe=str(user.get("sexe")) if user.get("sexe") else None
                )
                safe_log("info", "Email bienvenue envoyé",
                         user_id=str(user.get("_id", user.get("id"))))
            except Exception as e:
                safe_log("warning", "Erreur envoi email bienvenue", error=str(e))

        # Étape 6: Créer la réponse complète avec profil candidat (null pour le moment)
        try:
            safe_log("debug", "🔄 Création UserWithProfile...")
            user_dict = UserResponse.model_validate(user).model_dump()
            user_dict["candidate_profile"] = None  # Profil créé lors de la première candidature
            safe_log("debug", "✅ UserWithProfile créé")
        except PydanticValidationError as e:
            safe_log("error", "❌ Erreur validation Pydantic UserWithProfile", error=str(e), error_type=type(e).__name__)
            import traceback
            safe_log("error", "Traceback Pydantic", traceback=traceback.format_exc())
            # L'utilisateur est déjà créé, retourner une réponse manuelle
            safe_log("warning", "⚠️ Retour réponse manuelle (bypass Pydantic)")
            user_dict = {
                "id": str(user.get("_id", user.get("id"))),
                "email": str(user.get("email")),
                "first_name": str(user.get("first_name")),
                "last_name": str(user.get("last_name")),
                "role": str(user.get("role")),
                "phone": str(user.get("phone")) if user.get("phone") else None,
                "date_of_birth": user.get("date_of_birth").isoformat() if hasattr(user.get("date_of_birth"), "isoformat") else user.get("date_of_birth"),
                "sexe": str(user.get("sexe")) if user.get("sexe") else None,
                "matricule": int(user.get("matricule")) if user.get("matricule") else None,
                "email_verified": bool(user.get("email_verified", False)),
                "is_active": bool(user.get("is_active", True)),
                "is_internal_candidate": bool(user.get("is_internal_candidate", False)),
                "adresse": str(user.get("adresse")) if user.get("adresse") else None,
                "candidate_status": str(user.get("candidate_status")) if user.get("candidate_status") else None,
                "statut": str(user.get("statut", "actif")),
                "poste_actuel": str(user.get("poste_actuel")) if user.get("poste_actuel") else None,
                "annees_experience": int(user.get("annees_experience")) if user.get("annees_experience") else None,
                "no_seeg_email": bool(user.get("no_seeg_email", False)),
                "created_at": user.get("created_at").isoformat() if hasattr(user.get("created_at"), "isoformat") else user.get("created_at"),
                "updated_at": user.get("updated_at").isoformat() if hasattr(user.get("updated_at"), "isoformat") else user.get("updated_at"),
                "last_login": user.get("last_login").isoformat() if hasattr(user.get("last_login"), "isoformat") else user.get("last_login"),
                "candidate_profile": None
            }
        except Exception as e:
            safe_log("error", "❌ Erreur création UserWithProfile", error=str(e), error_type=type(e).__name__)
            import traceback
            safe_log("error", "Traceback complet", traceback=traceback.format_exc())
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Utilisateur créé mais erreur lors de la génération de la réponse"
            )

        safe_log("info", "✅ Inscription candidat réussie",
                user_id=str(user.get("_id", user.get("id"))),
                email=user.get("email"),
                statut=user.get("statut", "actif"))
        return user_dict

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
    db: Any = Depends(get_db)
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
        agent = await db.seeg_agents.find_one({"matricule": int(matricule)})

        if agent:
            return {
                "valid": True,
                "message": "Matricule valide",
                "agent_info": {
                    "matricule": str(agent.get("matricule")),
                    "first_name": str(agent.get("prenom")) if agent.get("prenom") else "",
                    "last_name": str(agent.get("nom")) if agent.get("nom") else ""
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
    db: Any = Depends(get_db),
    current_admin: Any = Depends(get_current_admin_user)
):
    """
    Créer un utilisateur (admin/recruteur) - admin seulement.
    GESTION EXPLICITE DES TRANSACTIONS.
    """
    try:
        auth_service = AuthService(db)
        user = await auth_service.create_user(user_data)

        # MongoDB auto-commit


        safe_log(
            "info",
            "Utilisateur créé par admin",
            user_id=str(user.get("_id", user.get("id"))),
            email=user.get("email"),
            role=user.get("role"),
            created_by=str(current_admin.id) if hasattr(current_admin, 'id') else str(current_admin.get('_id')),
        )
        return UserResponse.model_validate(user)

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
    db: Any = Depends(get_db)
):
    """
    Créer le premier administrateur - GESTION EXPLICITE DES TRANSACTIONS.
    """
    try:
        # Vérifier qu'aucun admin n'existe
        existing_admin = await db.users.find_one({"role": "admin"})
        if existing_admin:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Un administrateur existe déjà")

        # Créer l'admin
        auth_service = AuthService(db)
        hashed_password = auth_service.password_manager.hash_password("Sevan@Seeg")
        from datetime import datetime, timezone
        admin = {
            "email": "sevankedesh11@gmail.com",
            "first_name": "Sevan Kedesh",
            "last_name": "IKISSA PENDY",
            "role": "admin",
            "hashed_password": hashed_password,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "is_active": True,
            "email_verified": True
        }

        result = await db.users.insert_one(admin)
        admin["_id"] = result.inserted_id
        admin["id"] = str(result.inserted_id)

        safe_log("info", "Premier administrateur créé", user_id=str(admin.get("_id")), email=admin.get("email"))
        return UserResponse.model_validate(admin)

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
    current_user: Any = Depends(get_current_active_user)
):
    """Retourne le profil de l'utilisateur connecté avec ses informations complètes"""
    user_id = str(current_user.id) if hasattr(current_user, 'id') else str(current_user.get('_id', current_user.get('id')))
    email = current_user.email if hasattr(current_user, 'email') else current_user.get('email')
    safe_log("debug", "Profil utilisateur demandé", user_id=user_id, email=email)

    # Si UserMock est renvoyé, on cherche les vraies données. Autrement on sérialise.
    if hasattr(current_user, 'get'):
        return UserResponse.model_validate(current_user)
    elif hasattr(current_user, '__dict__'):
        return UserResponse.model_validate(current_user.__dict__)
    return UserResponse.model_validate(current_user)


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
    db: Any = Depends(get_db),
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
        user = await db.users.find_one({"_id": ObjectId(user_id) if len(str(user_id)) == 24 else user_id})

        if not user:
            safe_log("warning", "Utilisateur non trouvé lors du refresh", user_id=user_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Utilisateur non trouvé",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Vérifier que le compte est actif
        if not bool(user.get("is_active")):
            safe_log("warning", "Tentative de refresh pour compte désactivé", user_id=user_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Compte désactivé",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Créer de nouveaux tokens
        auth_service = AuthService(db)
        tokens = await auth_service.create_access_token(user)

        user_id_str = str(user.get("_id", user.get("id")))
        user_email = user.get("email")
        safe_log("info", "Token rafraîchi avec succès", user_id=user_id_str, email=user_email)

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
async def logout(current_user: Any = Depends(get_current_user)):
    """
    Déconnexion de l'utilisateur actuel.
    Note: Avec JWT, la déconnexion se fait côté client en supprimant le token.
    """
    user_id = str(current_user.get("_id", current_user.get("id")))
    safe_log("info", "Déconnexion utilisateur", user_id=user_id)
    return {"message": "Déconnexion réussie", "user_id": user_id}


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
    current_user: Any = Depends(get_current_active_user),
    db: Any = Depends(get_db)
):
    """
    Vérifie que le matricule de l'utilisateur connecté correspond à un agent actif dans la table seeg_agents.
    Autorise uniquement les rôles candidats.
    """
    if str(current_user.role) != "candidate":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accessible uniquement aux candidats")

    matricule_str = str(current_user.get("matricule")).strip() if current_user.get("matricule") is not None else ""
    if not matricule_str:
        return MatriculeVerificationResponse(valid=False, reason="Aucun matricule enregistré pour cet utilisateur")

    try:
        matricule_int = int(matricule_str)
    except ValueError:
        return MatriculeVerificationResponse(
            valid=False,
            reason="Matricule invalide (doit être numérique)",
        )

    try:
        agent = await db.seeg_agents.find_one({"matricule": matricule_int})
        if agent:
            return MatriculeVerificationResponse(
                valid=True,
                agent_matricule=str(agent.get("matricule", "")),
            )
        return MatriculeVerificationResponse(
            valid=False,
            reason="Matricule non trouvé dans seeg_agents",
        )
    except Exception as e:
        m_val = current_user.get("matricule")
        m_log = str(m_val) if m_val is not None else "None"
        safe_log("error", "Erreur matricule", error=str(e), matricule=m_log)
        raise HTTPException(status_code=500, detail="Erreur interne")


@router.post("/forgot-password", summary="Demander la réinitialisation du mot de passe", openapi_extra={
    "requestBody": {"content": {"application/json": {"example": {"email": "user@example.com"}}}},
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "message": "Email envoyé si l'adresse existe"}}}}}
})
async def forgot_password(
    payload: PasswordResetRequest,
    db: Any = Depends(get_db),
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
    db: Any = Depends(get_db),
):
    """
    Confirmer la réinitialisation du mot de passe avec le token reçu par email.
    GESTION EXPLICITE DES TRANSACTIONS.

    Le token a une durée de validité limitée (typiquement 1 heure).
    """
    try:
        service = AuthService(db)
        user = await service.reset_password_confirm(payload.token, payload.new_password)

        # MongoDB auto-commit

        user_id_str = str(user.get("_id", user.get("id")))
        safe_log("info", "Mot de passe réinitialisé avec succès", user_id=user_id_str)

        # Envoyer email + notification de confirmation (non-bloquant)
        try:
            from app.services.notification_email_manager import NotificationEmailManager
            notif_email_manager = NotificationEmailManager(db)

            result = await notif_email_manager.notify_and_email_password_changed(
                user_id=user_id_str,
                email=str(user.get("email")),
                first_name=str(user.get("first_name")),
                last_name=str(user.get("last_name"))
            )

            safe_log("info", "✅ Email + notification changement password envoyés",
                    user_id=user_id_str,
                    email_sent=result["email_sent"],
                    notification_sent=result["notification_sent"])
        except Exception as e:
            safe_log("warning", "⚠️ Erreur email/notification password change",
                    user_id=user_id_str, error=str(e))
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
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db),
):
    """
    Changer le mot de passe de l'utilisateur connecté.
    GESTION EXPLICITE DES TRANSACTIONS.

    Nécessite le mot de passe actuel pour confirmation.
    """
    try:
        service = AuthService(db)
        user_id_str = str(current_user.get("_id", current_user.get("id")))
        user = await service.change_password(user_id_str, payload.current_password, payload.new_password)

        # MongoDB auto-commit

        safe_log("info", "Mot de passe changé avec succès", user_id=user_id_str)
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

