"""
Schémas Pydantic pour l'authentification
======================================
Architecture: Type-Safe + Validation Stricte + Documentation Complète

Schémas principaux:
- LoginRequest: Connexion utilisateur
- CandidateSignupRequest: Inscription candidat (interne/externe)
- CreateUserRequest: Création utilisateur par admin
- TokenResponse: Réponse avec tokens JWT
- PasswordReset*: Gestion mot de passe oublié
"""
from typing import Optional
from pydantic import BaseModel, Field, EmailStr, field_validator
from datetime import date
from app.core.enums.user_enums import UserRole
from app.core.validators import Validators

# ============================================================================
# CONSTANTES - Types de candidats et statuts
# ============================================================================

# Types de candidats autorisés
CANDIDATE_STATUS_INTERNAL = "interne"  # Employé SEEG
CANDIDATE_STATUS_EXTERNAL = "externe"  # Candidat externe
ALLOWED_CANDIDATE_STATUS = {CANDIDATE_STATUS_INTERNAL, CANDIDATE_STATUS_EXTERNAL}

# Sexes autorisés
SEXE_MALE = "M"      # Masculin
SEXE_FEMALE = "F"    # Féminin
ALLOWED_SEXES = {SEXE_MALE, SEXE_FEMALE}

# Contraintes mot de passe
PASSWORD_MIN_LENGTH_LOGIN = 8   # Pour connexion (lenient)
PASSWORD_MIN_LENGTH_SIGNUP = 12  # Pour inscription (strict)


class LoginRequest(BaseModel):
    """
    Schéma pour la connexion utilisateur.
    
    Utilisé par tous les types d'utilisateurs:
    - Candidats (internes et externes)
    - Recruteurs
    - Administrateurs
    
    **Validation**:
    - Email: Format valide requis
    - Password: Minimum 8 caractères (validation leniente pour compatibilité)
    """
    email: str = Field(
        ...,
        description="Adresse email de l'utilisateur",
        examples=["jean.dupont@seeg-gabon.com", "candidat@gmail.com"]
    )
    password: str = Field(
        ...,
        min_length=PASSWORD_MIN_LENGTH_LOGIN,
        description=f"Mot de passe (minimum {PASSWORD_MIN_LENGTH_LOGIN} caractères)",
        examples=["MonMotDePasse123!"]
    )

    # Validation de l'email
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        """Valide le format de l'email."""
        return Validators.validate_email(v)
    
    # Validation du mot de passe (lenient pour le login)
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        """Valide que le mot de passe respecte les critères minimums."""
        return Validators.validate_password(v, min_length=PASSWORD_MIN_LENGTH_LOGIN)

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "description": "Candidat externe",
                    "value": {
                        "email": "candidat.externe@gmail.com",
                        "password": "MotDePasse2024!"
                    }
                },
                {
                    "description": "Employé SEEG (candidat interne)",
                    "value": {
                        "email": "jean.dupont@seeg-gabon.com",
                        "password": "Password#SEEG2024"
                    }
                },
                {
                    "description": "Recruteur",
                    "value": {
                        "email": "recruteur@seeg.ga",
                        "password": "Recrut3ur#2024"
                    }
                }
            ]
        }


class CandidateSignupRequest(BaseModel):
    """
    Schéma pour l'inscription des candidats (internes et externes).
    
    Règles métier:
    - Candidats EXTERNES: matricule=None, no_seeg_email=False, n'importe quel email
    - Candidats INTERNES avec email SEEG: matricule requis, no_seeg_email=False, email @seeg-gabon.com
    - Candidats INTERNES sans email SEEG: matricule requis, no_seeg_email=True, n'importe quel email
    """
    email: str = Field(..., description="Adresse email")
    password: str = Field(..., min_length=12, description="Mot de passe (minimum 12 caractères)")
    first_name: str = Field(..., min_length=1, max_length=100, description="Prénom")
    last_name: str = Field(..., min_length=1, max_length=100, description="Nom")
    phone: Optional[str] = Field(None, max_length=20, description="Numéro de téléphone")
    date_of_birth: date = Field(..., description="Date de naissance")
    sexe: str = Field(..., min_length=1, max_length=1, description="Sexe: M (Homme) ou F (Femme)")
    
    # Champs pour déterminer le type de candidat
    candidate_status: str = Field(..., description="Type de candidat: 'interne' (employé SEEG) ou 'externe'")
    matricule: Optional[int] = Field(None, description="Matricule SEEG (OBLIGATOIRE pour candidats internes, NULL pour externes)")
    no_seeg_email: bool = Field(default=False, description="Candidat interne sans email professionnel @seeg-gabon.com")
    
    # Champs optionnels de profil
    adresse: Optional[str] = Field(None, description="Adresse complète")
    poste_actuel: Optional[str] = Field(None, description="Poste actuel (optionnel)")
    annees_experience: Optional[int] = Field(None, ge=0, description="Années d'expérience professionnelle")

    # Validation de l'email
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        return Validators.validate_email(v)
    
    # Validation du mot de passe
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        return Validators.validate_password(v, min_length=12)
    
    # Validation de la date de naissance
    @field_validator('date_of_birth')
    @classmethod
    def validate_date_of_birth(cls, v):
        return Validators.validate_date_of_birth(v)
    
    # Validation du sexe
    @field_validator('sexe')
    @classmethod
    def validate_sexe(cls, v):
        """Valide le sexe (M ou F)."""
        if v not in ALLOWED_SEXES:
            raise ValueError(f"Le sexe doit être '{SEXE_MALE}' (Homme) ou '{SEXE_FEMALE}' (Femme)")
        return v
    
    # Validation du candidate_status
    @field_validator('candidate_status')
    @classmethod
    def validate_candidate_status(cls, v):
        """Valide le type de candidat."""
        if v not in ALLOWED_CANDIDATE_STATUS:
            raise ValueError(f"Le candidate_status doit être '{CANDIDATE_STATUS_INTERNAL}' ou '{CANDIDATE_STATUS_EXTERNAL}'")
        return v

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "description": "Candidat EXTERNE (aucun lien avec SEEG)",
                    "value": {
                        "email": "marie.kouamba@gmail.com",
                        "password": "SecurePass2024!Marie",
                        "first_name": "Marie",
                        "last_name": "Kouamba",
                        "phone": "+241 07 11 22 33",
                        "date_of_birth": "1995-03-20",
                        "sexe": "F",
                        "candidate_status": "externe",
                        "matricule": None,
                        "no_seeg_email": False,
                        "adresse": "Quartier Nzeng-Ayong, Libreville",
                        "poste_actuel": "Développeuse Web",
                        "annees_experience": 3
                    }
                },
                {
                    "description": "Candidat INTERNE avec email SEEG (@seeg-gabon.com)",
                    "value": {
                        "email": "jean.dupont@seeg-gabon.com",
                        "password": "Password#SEEG2024",
                        "first_name": "Jean",
                        "last_name": "Dupont",
                        "phone": "+241 06 22 33 44",
                        "date_of_birth": "1988-11-10",
                        "sexe": "M",
                        "candidate_status": "interne",
                        "matricule": 123456,
                        "no_seeg_email": False,
                        "adresse": "Quartier Batavéa, Libreville",
                        "poste_actuel": "Technicien Réseau",
                        "annees_experience": 8
                    }
                },
                {
                    "description": "Candidat INTERNE SANS email SEEG (employé sans adresse professionnelle)",
                    "value": {
                        "email": "paul.mbina@hotmail.com",
                        "password": "MySecurePass123!",
                        "first_name": "Paul",
                        "last_name": "Mbina",
                        "phone": "+241 07 99 88 77",
                        "date_of_birth": "1992-07-15",
                        "sexe": "M",
                        "candidate_status": "interne",
                        "matricule": 789012,
                        "no_seeg_email": True,
                        "adresse": "PK8, Libreville",
                        "poste_actuel": "Agent technique",
                        "annees_experience": 5
                    }
                }
            ]
        }


class CreateUserRequest(BaseModel):
    """Schéma pour créer un utilisateur (admin/recruteur) - admin seulement"""
    email: str = Field(..., description="Adresse email")
    password: str = Field(..., description="Mot de passe")
    first_name: str = Field(..., min_length=1, max_length=100, description="Prénom")
    last_name: str = Field(..., min_length=1, max_length=100, description="Nom")
    role: UserRole = Field(..., description="Rôle de l'utilisateur")
    phone: Optional[str] = Field(None, max_length=20, description="Numéro de téléphone")
    
    # Champs optionnels (non pertinents pour admin/recruteur mais requis par le modèle User)
    date_of_birth: Optional[date] = Field(None, description="Date de naissance (optionnel pour admin/recruteur)")
    sexe: Optional[str] = Field(None, description="Sexe: M ou F (optionnel pour admin/recruteur)")
    candidate_status: Optional[str] = Field(None, description="Type de candidat (non applicable pour admin/recruteur)")

    # Validation de l'email
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        return Validators.validate_email(v)
    
    # Validation du mot de passe
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        return Validators.validate_password(v, min_length=12)
    
    # Validation du sexe (optionnel)
    @field_validator('sexe')
    @classmethod
    def validate_sexe(cls, v):
        """Valide le sexe si fourni."""
        if v is not None and v not in ALLOWED_SEXES:
            raise ValueError(f"Le sexe doit être '{SEXE_MALE}' ou '{SEXE_FEMALE}'")
        return v

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "description": "Créer un recruteur",
                    "value": {
                        "email": "recruteur.rh@seeg.ga",
                        "password": "Recrut3ur#Secure2024",
                        "first_name": "Sophie",
                        "last_name": "Mavoungou",
                        "role": "recruiter",
                        "phone": "+241 07 44 55 66"
                    }
                },
                {
                    "description": "Créer un administrateur",
                    "value": {
                        "email": "admin.systeme@seeg.ga",
                        "password": "AdminSecure#2024!",
                        "first_name": "Pierre",
                        "last_name": "Nzamba",
                        "role": "admin",
                        "phone": "+241 06 77 88 99"
                    }
                }
            ]
        }


class TokenResponse(BaseModel):
    """
    Schéma de réponse pour les tokens JWT.
    
    Contient:
    - access_token: Token d'accès (courte durée, 1h)
    - refresh_token: Token de rafraîchissement (longue durée, 7j)
    - token_type: Toujours "bearer" (standard OAuth2)
    - expires_in: Durée d'expiration du access_token en secondes
    """
    access_token: str = Field(..., description="Token d'accès JWT (valide 1 heure)")
    refresh_token: str = Field(..., description="Token de rafraîchissement JWT (valide 7 jours)")
    token_type: str = Field(default="bearer", description="Type de token (OAuth2)")
    expires_in: int = Field(..., description="Durée d'expiration du access_token en secondes (3600 = 1h)")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyQGV4YW1wbGUuY29tIn0...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyQGV4YW1wbGUuY29tIn0...",
                "token_type": "bearer",
                "expires_in": 3600
            }
        }


class TokenResponseData(BaseModel):
    """
    Schéma de réponse pour les tokens avec données utilisateur.
    
    Utilisé lors de:
    - Connexion réussie
    - Inscription réussie
    
    Inclut les tokens ET les informations de l'utilisateur connecté.
    """
    access_token: str = Field(..., description="Token d'accès JWT (valide 1 heure)")
    refresh_token: str = Field(..., description="Token de rafraîchissement JWT (valide 7 jours)")
    token_type: str = Field(default="bearer", description="Type de token (OAuth2)")
    expires_in: int = Field(..., description="Durée d'expiration du access_token en secondes")
    user: dict = Field(..., description="Données utilisateur (id, email, role, etc.)")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600,
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "email": "jean.dupont@seeg-gabon.com",
                    "first_name": "Jean",
                    "last_name": "Dupont",
                    "role": "candidate",
                    "candidate_status": "interne"
                }
            }
        }


class RefreshTokenRequest(BaseModel):
    """
    Schéma pour rafraîchir un token d'accès expiré.
    
    Utilise le refresh_token (longue durée) pour obtenir un nouveau access_token
    sans redemander les identifiants.
    """
    refresh_token: str = Field(..., description="Token de rafraîchissement JWT (reçu lors de la connexion)")


class RefreshTokenResponseRequest(BaseModel):
    """
    Schéma de réponse après rafraîchissement d'un token.
    
    Retourne uniquement le nouveau access_token (le refresh_token reste inchangé).
    """
    access_token: str = Field(..., description="Nouveau token d'accès JWT (valide 1 heure)")
    token_type: str = Field(default="bearer", description="Type de token (OAuth2)")
    expires_in: int = Field(..., description="Durée d'expiration en secondes (3600 = 1h)")


class PasswordResetRequest(BaseModel):
    """
    Schéma pour demander une réinitialisation de mot de passe.
    
    Envoie un email avec un lien de réinitialisation à l'utilisateur.
    """
    email: EmailStr = Field(..., description="Adresse email de l'utilisateur")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "jean.dupont@seeg-gabon.com"
            }
        }


class PasswordResetConfirm(BaseModel):
    """
    Schéma pour confirmer la réinitialisation de mot de passe.
    
    Utilise le token reçu par email pour définir un nouveau mot de passe.
    """
    token: str = Field(..., description="Token de réinitialisation (reçu par email)")
    new_password: str = Field(
        ...,
        min_length=PASSWORD_MIN_LENGTH_SIGNUP,
        description=f"Nouveau mot de passe (minimum {PASSWORD_MIN_LENGTH_SIGNUP} caractères)"
    )

    # Validation du nouveau mot de passe
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        """Valide que le nouveau mot de passe respecte les critères de sécurité."""
        return Validators.validate_password(v, min_length=PASSWORD_MIN_LENGTH_SIGNUP)

    class Config:
        json_schema_extra = {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyQGV4YW1wbGUuY29tIn0...",
                "new_password": "NouveauMotDePasse2024!"
            }
        }


class ChangePasswordRequest(BaseModel):
    """
    Schéma pour changer le mot de passe (utilisateur connecté).
    
    Requiert le mot de passe actuel pour vérification de sécurité.
    """
    current_password: str = Field(..., min_length=1, description="Mot de passe actuel (pour vérification)")
    new_password: str = Field(
        ...,
        min_length=PASSWORD_MIN_LENGTH_SIGNUP,
        description=f"Nouveau mot de passe (minimum {PASSWORD_MIN_LENGTH_SIGNUP} caractères)"
    )

    # Validation du nouveau mot de passe
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        """Valide que le nouveau mot de passe respecte les critères de sécurité."""
        return Validators.validate_password(v, min_length=PASSWORD_MIN_LENGTH_SIGNUP)

    class Config:
        json_schema_extra = {
            "example": {
                "current_password": "AncienMotDePasse2023!",
                "new_password": "NouveauMotDePasse2024!"
            }
        }


class MatriculeVerificationResponse(BaseModel):
    """Résultat de la vérification du matricule contre la table seeg_agents"""
    valid: bool = Field(..., description="True si le matricule de l'utilisateur correspond à un agent SEEG")
    reason: Optional[str] = Field(None, description="Raison si non valide")
    agent_matricule: Optional[int] = Field(None, description="Matricule trouvé côté seeg_agents")
