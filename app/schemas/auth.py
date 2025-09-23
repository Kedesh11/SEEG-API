"""
Schémas Pydantic pour l'authentification
"""
from typing import Optional
from pydantic import BaseModel, Field, EmailStr
from datetime import date
from app.core.enums.user_enums import UserRole


class LoginRequest(BaseModel):
    """Schéma pour la connexion"""
    email: EmailStr = Field(..., description="Adresse email")
    password: str = Field(..., min_length=1, description="Mot de passe")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "candidate@example.com",
                "password": "MotdepasseFort123!"
            }
        }


class CandidateSignupRequest(BaseModel):
    """Schéma pour l'inscription des candidats uniquement"""
    email: EmailStr = Field(..., description="Adresse email")
    password: str = Field(..., min_length=8, description="Mot de passe")
    first_name: str = Field(..., min_length=1, max_length=100, description="Prénom")
    last_name: str = Field(..., min_length=1, max_length=100, description="Nom")
    matricule: int = Field(..., description="Matricule SEEG (obligatoire pour les candidats)")
    phone: Optional[str] = Field(None, max_length=20, description="Numéro de téléphone")
    date_of_birth: date = Field(..., description="Date de naissance (obligatoire pour les candidats)")
    sexe: str = Field(..., description="Sexe (obligatoire pour les candidats)")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "new.candidate@seeg.ga",
                "password": "Password#2025",
                "first_name": "Aïcha",
                "last_name": "Mouketou",
                "matricule": 123456,
                "phone": "+24106223344",
                "date_of_birth": "1994-06-12",
                "sexe": "F"
            }
        }


class CreateUserRequest(BaseModel):
    """Schéma pour créer un utilisateur (admin/recruteur) - admin seulement"""
    email: EmailStr = Field(..., description="Adresse email")
    password: str = Field(..., min_length=8, description="Mot de passe")
    first_name: str = Field(..., min_length=1, max_length=100, description="Prénom")
    last_name: str = Field(..., min_length=1, max_length=100, description="Nom")
    role: UserRole = Field(..., description="Rôle de l'utilisateur")
    phone: Optional[str] = Field(None, max_length=20, description="Numéro de téléphone")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "recruteur@seeg.ga",
                "password": "Recrut3ur#2025",
                "first_name": "Jean",
                "last_name": "Mavoungou",
                "role": "recruiter",
                "phone": "+24107445566"
            }
        }


class TokenResponse(BaseModel):
    """Schéma de réponse pour les tokens"""
    access_token: str = Field(..., description="Token d'accès")
    refresh_token: str = Field(..., description="Token de rafraîchissement")
    token_type: str = Field(default="bearer", description="Type de token")
    expires_in: int = Field(..., description="Durée d'expiration en secondes")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIs...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
                "token_type": "bearer",
                "expires_in": 3600
            }
        }


class TokenResponseData(BaseModel):
    """Schéma de réponse pour les tokens avec données utilisateur"""
    access_token: str = Field(..., description="Token d'accès")
    refresh_token: str = Field(..., description="Token de rafraîchissement")
    token_type: str = Field(default="bearer", description="Type de token")
    expires_in: int = Field(..., description="Durée d'expiration en secondes")
    user: dict = Field(..., description="Données utilisateur")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIs...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
                "token_type": "bearer",
                "expires_in": 3600,
                "user": {"id": "uuid", "email": "candidate@example.com", "role": "candidate"}
            }
        }


class RefreshTokenRequest(BaseModel):
    """Schéma pour rafraîchir un token"""
    refresh_token: str = Field(..., description="Token de rafraîchissement")


class RefreshTokenResponseRequest(BaseModel):
    """Schéma pour la réponse de rafraîchissement de token"""
    access_token: str = Field(..., description="Nouveau token d'accès")
    token_type: str = Field(default="bearer", description="Type de token")
    expires_in: int = Field(..., description="Durée d'expiration en secondes")


class PasswordResetRequest(BaseModel):
    """Schéma pour demander une réinitialisation de mot de passe"""
    email: EmailStr = Field(..., description="Adresse email")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com"
            }
        }


class PasswordResetConfirm(BaseModel):
    """Schéma pour confirmer la réinitialisation de mot de passe"""
    token: str = Field(..., description="Token de réinitialisation")
    new_password: str = Field(..., min_length=8, description="Nouveau mot de passe")

    class Config:
        json_schema_extra = {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "new_password": "NouveauMotDePasse123!"
            }
        }


class ChangePasswordRequest(BaseModel):
    """Schéma pour changer le mot de passe"""
    current_password: str = Field(..., min_length=1, description="Mot de passe actuel")
    new_password: str = Field(..., min_length=8, description="Nouveau mot de passe")

    class Config:
        json_schema_extra = {
            "example": {
                "current_password": "Ancien123!",
                "new_password": "Nouveau123!"
            }
        }


class MatriculeVerificationResponse(BaseModel):
    """Résultat de la vérification du matricule contre la table seeg_agents"""
    valid: bool = Field(..., description="True si le matricule de l'utilisateur correspond à un agent SEEG")
    reason: Optional[str] = Field(None, description="Raison si non valide")
    agent_matricule: Optional[int] = Field(None, description="Matricule trouvé côté seeg_agents")
