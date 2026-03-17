"""
Service d'authentification
"""

import structlog
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from app.schemas.auth import CandidateSignupRequest, CreateUserRequest, TokenResponse
from app.core.security.security import (
    PasswordManager,
    TokenManager,
    verify_password_reset_token,
)
from app.core.exceptions import (
    UnauthorizedError,
    ValidationError,
    BusinessLogicError,
    EmailError,
)
from app.core.config.config import settings
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

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.password_manager = PasswordManager()
        self.token_manager = TokenManager()

    def determine_user_status(
        self, candidate_status: str, email: str, no_seeg_email: bool
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
        if candidate_status == "externe":
            return "actif"

        # Cas 2: Candidat interne
        if candidate_status == "interne":
            # Sous-cas 2.1: A un email @seeg-gabon.com → actif
            if not no_seeg_email and email.lower().endswith(self.SEEG_EMAIL_DOMAIN):
                return "actif"

            # Sous-cas 2.2: N'a pas d'email SEEG → en_attente (validation requise)
            if no_seeg_email:
                return "en_attente"

            # Sous-cas 2.3: Devrait avoir email SEEG mais ne l'a pas → en_attente
            return "en_attente"

        # Défaut: actif
        return "actif"

    async def verify_matricule_exists(self, matricule: int) -> bool:
        """
        Vérifier qu'un matricule existe dans la table seeg_agents.

        Args:
            matricule: Matricule à vérifier

        Returns:
            bool: True si le matricule existe dans la table seeg_agents
        """
        try:
            agent = await self.db.seeg_agents.find_one({"matricule": matricule})
            return agent is not None

        except Exception as e:
            safe_log(
                "error",
                "Erreur vérification matricule",
                matricule=matricule,
                error=str(e),
            )
            return False

    async def authenticate_user(
        self, email: str, password: str
    ) -> Optional[Dict[str, Any]]:
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
            user = await self.db.users.find_one({"email": email})

            if not user:
                safe_log(
                    "warning",
                    "Tentative de connexion avec email inexistant",
                    email=email,
                )
                return None

            # Vérifier le statut du compte (nouvelle logique)
            if user.get("statut") is not None:
                statut_str = str(user.get("statut"))
                if statut_str != "actif":
                    safe_log(
                        "warning",
                        "Tentative de connexion avec compte non actif",
                        email=email,
                        user_id=str(user.get("_id", user.get("id"))),
                        statut=statut_str,
                    )
                    # Retourner None et laisser l'endpoint gérer le message d'erreur selon le statut
                    return None

            # Vérifier que le compte est actif (legacy is_active field)
            if not bool(user.get("is_active", True)):
                safe_log(
                    "warning",
                    "Tentative de connexion sur compte désactivé (is_active=False)",
                    email=email,
                    user_id=str(user.get("_id", user.get("id"))),
                )
                return None

            # Vérifier le mot de passe
            hashed_pwd = (
                str(user.get("hashed_password"))
                if user.get("hashed_password") is not None
                else ""
            )
            if not self.password_manager.verify_password(password, hashed_pwd):
                safe_log(
                    "warning",
                    "Mot de passe incorrect",
                    email=email,
                    user_id=str(user.get("_id", user.get("id"))),
                )
                return None

            # Mettre à jour last_login (sera committé par l'endpoint)
            user_id = user.get("_id", user.get("id"))
            query = (
                {"_id": ObjectId(user_id)}
                if len(str(user_id)) == 24
                else {"_id": user_id}
            )
            await self.db.users.update_one(
                query, {"$set": {"last_login": datetime.now(timezone.utc)}}
            )

            safe_log(
                "info", "Authentification réussie", email=email, user_id=str(user_id)
            )
            return user

        except Exception as e:
            # ✅ PAS de rollback ici - géré par get_db() automatiquement
            safe_log(
                "error", "Erreur lors de l'authentification", email=email, error=str(e)
            )
            raise BusinessLogicError("Erreur lors de l'authentification")

    async def create_candidate(
        self, user_data: CandidateSignupRequest
    ) -> Dict[str, Any]:
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
            if user_data.candidate_status == "interne" and not user_data.matricule:
                raise ValidationError(
                    "Le matricule est obligatoire pour les candidats internes"
                )

            # Validation métier: Vérifier que le matricule existe (si fourni)
            # ⚠️ WARNING au lieu de bloquer - Permet l'inscription même si matricule non trouvé dans seeg_agents
            # Justification: La table seeg_agents peut ne pas être à jour avec tous les employés
            if user_data.matricule:
                is_valid = await self.verify_matricule_exists(user_data.matricule)
                if not is_valid:
                    safe_log(
                        "warning",
                        "⚠️ Matricule non trouvé dans seeg_agents (inscription autorisée quand même)",
                        matricule=user_data.matricule,
                        email=user_data.email,
                    )
                    # Ne pas bloquer l'inscription - juste logger un warning
                    # L'admin pourra vérifier manuellement lors de l'approbation
                else:
                    safe_log(
                        "info",
                        "✅ Matricule validé dans seeg_agents",
                        matricule=user_data.matricule,
                    )

            # Validation métier: Empêcher la duplication de matricule côté users (renvoyer 400 plutôt que 500 DB)
            if user_data.matricule is not None:
                existing_with_same_matricule = await self.db.users.find_one(
                    {"matricule": user_data.matricule}
                )
                if existing_with_same_matricule is not None:
                    raise ValidationError(
                        "Un utilisateur avec ce matricule existe déjà"
                    )

            # Validation métier: Si candidat interne AVEC email SEEG déclaré, vérifier qu'il est @seeg-gabon.com
            # ⚠️ Si no_seeg_email=True, on accepte n'importe quel email (sera en attente de validation)
            if (
                user_data.candidate_status == "interne"
                and not user_data.no_seeg_email
                and not user_data.email.lower().endswith(self.SEEG_EMAIL_DOMAIN)
            ):
                raise ValidationError(
                    f"Les candidats internes doivent utiliser un email professionnel {self.SEEG_EMAIL_DOMAIN}. "
                    "Si vous n'avez pas d'email professionnel SEEG, veuillez cocher la case 'Je n'ai pas d'email SEEG'."
                )

            # Validation métier: Si no_seeg_email=True mais email se termine par @seeg-gabon.com, c'est incohérent
            if (
                user_data.candidate_status == "interne"
                and user_data.no_seeg_email
                and user_data.email.lower().endswith(self.SEEG_EMAIL_DOMAIN)
            ):
                raise ValidationError(
                    f"Incohérence détectée : vous avez coché 'Je n'ai pas d'email SEEG' mais votre email est {self.SEEG_EMAIL_DOMAIN}. "
                    "Veuillez décocher cette case ou utiliser un autre email."
                )

            # Hasher le mot de passe
            hashed = self.password_manager.hash_password(user_data.password)

            # Déterminer le statut selon les règles métier
            statut = self.determine_user_status(
                candidate_status=user_data.candidate_status,
                email=user_data.email,
                no_seeg_email=user_data.no_seeg_email,
            )

            # Déterminer si c'est un candidat interne
            is_internal = user_data.candidate_status == "interne"

            # Créer l'utilisateur avec TOUS les nouveaux champs
            import uuid

            user_id = str(uuid.uuid4())
            user = {
                "_id": user_id,
                "email": user_data.email,
                "hashed_password": hashed,
                "first_name": user_data.first_name,
                "last_name": user_data.last_name,
                "phone": user_data.phone,
                "role": "candidate",
                "matricule": user_data.matricule,
                "date_of_birth": user_data.date_of_birth,
                "sexe": user_data.sexe,
                "is_internal_candidate": is_internal,
                "adresse": user_data.adresse,
                "candidate_status": user_data.candidate_status,
                "statut": statut,
                "poste_actuel": user_data.poste_actuel,
                "annees_experience": user_data.annees_experience,
                "no_seeg_email": user_data.no_seeg_email,
                "is_active": True,
                "email_verified": False,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            await self.db.users.insert_one(user)

            # ✅ PAS de commit ici - c'est l'endpoint qui décide
            # ✅ PAS de refresh ici - sera fait après commit par l'endpoint
            # ℹ️ Le profil candidat sera créé lors de la première candidature

            safe_log(
                "info",
                "Utilisateur préparé pour création",
                email=user.get("email"),
                candidate_status=user_data.candidate_status,
                statut=statut,
                has_matricule=user_data.matricule is not None,
                no_seeg_email=user_data.no_seeg_email,
            )
            return user

        except ValidationError:
            # ✅ PAS de rollback ici - géré par get_db() automatiquement
            raise
        except Exception as e:
            safe_log("error", "Erreur création candidat", error=str(e))
            raise BusinessLogicError("Erreur lors de la création du candidat")

    async def create_user(self, user_data: CreateUserRequest) -> Dict[str, Any]:
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

            # Créer l'utilisateur avec valeurs par défaut pour champs optionnels
            import uuid

            user_id = str(uuid.uuid4())
            user = {
                "_id": user_id,
                "email": user_data.email,
                "hashed_password": hashed,
                "first_name": user_data.first_name,
                "last_name": user_data.last_name,
                "phone": user_data.phone,
                "role": user_data.role,
                "date_of_birth": user_data.date_of_birth,
                "sexe": user_data.sexe,
                "candidate_status": user_data.candidate_status,
                "statut": "actif",
                "no_seeg_email": False,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            await self.db.users.insert_one(user)

            # ✅ PAS de commit ici - c'est l'endpoint qui décide
            # ✅ PAS de refresh ici - sera fait après commit par l'endpoint

            safe_log(
                "info",
                "Utilisateur préparé pour création",
                email=user.get("email"),
                role=user_data.role,
            )
            return user

        except ValidationError:
            # ✅ PAS de rollback ici - géré par get_db() automatiquement
            raise
        except Exception as e:
            safe_log("error", "Erreur création utilisateur", error=str(e))
            raise BusinessLogicError("Erreur lors de la création de l'utilisateur")

    async def create_access_token(self, user: Dict[str, Any]) -> TokenResponse:
        """Créer des tokens d'accès et refresh"""
        try:
            user_id = user.get("_id", user.get("id"))
            access = self.token_manager.create_access_token(
                {"sub": str(user_id), "role": user.get("role")}
            )
            refresh = self.token_manager.create_refresh_token(
                {"sub": str(user_id), "role": user.get("role")}
            )
            return TokenResponse(
                access_token=access,
                refresh_token=refresh,
                token_type="bearer",
                expires_in=3600,
            )
        except Exception as e:
            safe_log("error", "Erreur création token", error=str(e))
            raise BusinessLogicError("Erreur lors de la création du token")

    async def reset_password_request(self, email: str) -> bool:
        """Créer un token de réinitialisation et envoyer l'email."""
        try:
            user = await self.db.users.find_one({"email": email})
            if not user:
                # Ne pas révéler l'existence ou non de l'email
                safe_log("info", "Demande de reset pour email inconnu", email=email)
                return True

            token = create_password_reset_token(email)
            reset_link = f"{settings.PUBLIC_APP_URL}/reset-password?token={token}"

            # Envoyer l'email avec template professionnel
            email_service = EmailService(self.db)
            subject = "🔑 Réinitialisation de votre mot de passe - OneHCM SEEG"

            # Déterminer la salutation
            salutation = "Bonjour"
            user_sexe = user.get("sexe")
            user_firstname = user.get("first_name")
            user_lastname = user.get("last_name")

            if user_sexe == "M":  # type: ignore[comparison-overlap]
                salutation = f"Monsieur {user_firstname} {user_lastname}"
            elif user_sexe == "F":  # type: ignore[comparison-overlap]
                salutation = f"Madame {user_firstname} {user_lastname}"
            elif user_firstname and user_lastname:  # type: ignore[truthy-bool]
                salutation = f"{user_firstname} {user_lastname}"

            # Email texte brut
            body = f"""
{salutation},

Vous avez demandé la réinitialisation de votre mot de passe pour votre compte OneHCM - SEEG Talent Source.

Pour créer un nouveau mot de passe, veuillez cliquer sur le lien ci-dessous :
{reset_link}

Ce lien est valide pendant 1 heure.

Si vous n'avez pas demandé cette réinitialisation, ignorez cet email. Votre mot de passe actuel reste inchangé.

Pour des raisons de sécurité :
- Ne partagez jamais ce lien
- Choisissez un mot de passe fort (8+ caractères, majuscules, minuscules, chiffres)

Besoin d'aide ?
Contact : support@seeg-talentsource.com

Cordialement,
L'équipe OneHCM - SEEG Talent Source
{settings.PUBLIC_APP_URL}
            """

            # Email HTML
            html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #FF9800 0%, #F57C00 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }}
        .warning-box {{ background: #FFF3E0; border-left: 4px solid #FF9800; padding: 15px; margin: 20px 0; border-radius: 4px; }}
        .security-box {{ background: #FFEBEE; border-left: 4px solid #F44336; padding: 15px; margin: 20px 0; border-radius: 4px; }}
        .button {{ display: inline-block; background: #FF9800; color: white; padding: 14px 35px; text-decoration: none; border-radius: 6px; margin: 20px 0; font-weight: bold; font-size: 16px; }}
        .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; }}
        ul {{ line-height: 2; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔑 Réinitialisation de mot de passe</h1>
        </div>
        <div class="content">
            <p><strong>{salutation},</strong></p>
            
            <p>Vous avez demandé la réinitialisation de votre mot de passe pour votre compte <strong>OneHCM - SEEG Talent Source</strong>.</p>
            
            <p style="text-align: center;">
                <a href="{reset_link}" class="button">Réinitialiser mon mot de passe</a>
            </p>
            
            <div class="warning-box">
                <p><strong>⏱️ Validité du lien</strong></p>
                <p>Ce lien est valide pendant <strong>1 heure</strong>. Passé ce délai, vous devrez refaire une demande.</p>
            </div>
            
            <div class="security-box">
                <p><strong>🔒 Consignes de sécurité</strong></p>
                <ul>
                    <li>Ne partagez jamais ce lien</li>
                    <li>Choisissez un mot de passe fort (8+ caractères)</li>
                    <li>Utilisez des majuscules, minuscules, chiffres et caractères spéciaux</li>
                </ul>
            </div>
            
            <p><strong>Vous n'avez pas demandé cette réinitialisation ?</strong><br>
            Ignorez cet email. Votre mot de passe actuel reste inchangé.</p>
            
            <p style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;">
            <strong>Besoin d'aide ?</strong><br>
            Contact : <a href="mailto:support@seeg-talentsource.com">support@seeg-talentsource.com</a></p>
            
            <p>Cordialement,<br>
            <strong>L'équipe OneHCM - SEEG Talent Source</strong><br>
            <a href="{settings.PUBLIC_APP_URL}">{settings.PUBLIC_APP_URL}</a></p>
        </div>
        <div class="footer">
            <p>&copy; 2025 SEEG - Société d'Énergie et d'Eau du Gabon</p>
            <p>Email automatique - Ne pas répondre directement</p>
        </div>
    </div>
</body>
</html>
            """

            try:
                await email_service.send_email(
                    to=str(user.get("email")),
                    subject=subject,
                    body=body,
                    html_body=html,
                )
                safe_log(
                    "info",
                    "Email de réinitialisation envoyé avec succès",
                    email=email,
                    user_id=str(user.get("_id", user.get("id"))),
                )
            except Exception as e:
                # Log l'erreur et la propager
                safe_log("error", "Echec envoi email reset", error=str(e), email=email)
                raise EmailError(
                    f"Impossible d'envoyer l'email de réinitialisation: {str(e)}"
                )

            safe_log(
                "info",
                "Demande de réinitialisation de mot de passe traitée",
                email=email,
                user_id=str(user.get("_id", user.get("id"))),
            )
            return True
        except EmailError:
            # Propager les erreurs d'email
            raise
        except Exception as e:
            safe_log(
                "error",
                "Erreur lors de la demande de réinitialisation",
                email=email,
                error=str(e),
            )
            raise BusinessLogicError("Erreur lors de la demande de réinitialisation")

    async def reset_password_confirm(
        self, token: str, new_password: str
    ) -> Dict[str, Any]:
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

            user = await self.db.users.find_one({"email": email})
            if not user:
                raise ValidationError("Utilisateur introuvable pour ce token")

            # Modifier le mot de passe (sera committé par l'endpoint)
            user_id = user.get("_id", user.get("id"))
            query = (
                {"_id": ObjectId(user_id)}
                if len(str(user_id)) == 24
                else {"_id": user_id}
            )
            hashed_password = self.password_manager.hash_password(new_password)

            await self.db.users.update_one(
                query,
                {
                    "$set": {
                        "hashed_password": hashed_password,
                        "updated_at": datetime.utcnow(),
                    }
                },
            )

            safe_log(
                "info",
                "Mot de passe préparé pour réinitialisation",
                user_id=str(user_id),
                email=email,
            )
            return user

        except ValidationError:
            raise
        except Exception as e:
            safe_log(
                "error",
                "Erreur lors de la confirmation de réinitialisation",
                error=str(e),
            )
            raise BusinessLogicError(
                "Erreur lors de la confirmation de réinitialisation"
            )

    async def change_password(
        self, user_id: str, current_password: str, new_password: str
    ) -> Dict[str, Any]:
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
            query = (
                {"_id": ObjectId(user_id)} if len(user_id) == 24 else {"_id": user_id}
            )
            user = await self.db.users.find_one(query)
            if not user:
                raise ValidationError("Utilisateur introuvable")

            # Vérifier le mot de passe actuel
            hashed_pwd = (
                str(user.get("hashed_password"))
                if user.get("hashed_password") is not None
                else ""
            )
            if not self.password_manager.verify_password(current_password, hashed_pwd):
                raise UnauthorizedError("Mot de passe actuel incorrect")

            # Modifier le mot de passe
            hashed_password = self.password_manager.hash_password(new_password)
            await self.db.users.update_one(
                query,
                {
                    "$set": {
                        "hashed_password": hashed_password,
                        "updated_at": datetime.utcnow(),
                    }
                },
            )

            safe_log(
                "info", "Mot de passe préparé pour modification", user_id=str(user_id)
            )
            return user

        except (ValidationError, UnauthorizedError):
            raise
        except Exception as e:
            safe_log(
                "error", "Erreur changement mot de passe", error=str(e), user_id=user_id
            )
            raise BusinessLogicError("Erreur lors du changement de mot de passe")
