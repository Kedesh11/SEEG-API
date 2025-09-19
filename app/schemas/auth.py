"""
Schémas Pydantic pour l'authentification
"""
from typing import Optional
from pydantic import BaseModel, Field, EmailStr
from datetime import date


class LoginRequest(BaseModel):
    """Schéma pour la connexion"""
    email: EmailStr = Field(..., description="Adresse email")
    password: str = Field(..., min_length=1, description="Mot de passe")


class CandidateSignupRequest(BaseModel):
    """Schéma pour l'inscription des candidats uniquement"""
    email: EmailStr = Field(..., description="Adresse email")
    password: str = Field(..., min_length=8, description="Mot de passe")
    first_name: str = Field(..., min_length=1, max_length=100, description="Prénom")
    last_name: str = Field(..., min_length=1, max_length=100, description="Nom")
    matricule: str = Field(..., min_length=1, max_length=20, description="Matricule SEEG (obligatoire pour les candidats)")
    phone: Optional[str] = Field(None, max_length=20, description="Numéro de téléphone")
    date_of_birth: date = Field(..., description="Date de naissance (obligatoire pour les candidats)")
    sexe: str = Field(..., description="Sexe (obligatoire pour les candidats)")


class CreateUserRequest(BaseModel):
    """Schéma pour créer un utilisateur (admin/recruteur) - admin seulement"""
    email: EmailStr = Field(..., description="Adresse email")
    password: str = Field(..., min_length=8, description="Mot de passe")
    first_name: str = Field(..., min_length=1, max_length=100, description="Prénom")
    last_name: str = Field(..., min_length=1, max_length=100, description="Nom")
    role: str = Field(..., description="Rôle: admin ou recruiter")
    phone: Optional[str] = Field(None, max_length=20, description="Numéro de téléphone")


class TokenResponse(BaseModel):
    """Schéma de réponse pour les tokens"""
    access_token: str = Field(..., description="Token d'accès")
    refresh_token: str = Field(..., description="Token de rafraîchissement")
    token_type: str = Field(default="bearer", description="Type de token")
    expires_in: int = Field(..., description="Durée d'expiration en secondes")


class TokenResponseData(BaseModel):
    """Schéma de réponse pour les tokens avec données utilisateur"""
    access_token: str = Field(..., description="Token d'accès")
    refresh_token: str = Field(..., description="Token de rafraîchissement")
    token_type: str = Field(default="bearer", description="Type de token")
    expires_in: int = Field(..., description="Durée d'expiration en secondes")
    user: dict = Field(..., description="Données utilisateur")


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


class PasswordResetConfirm(BaseModel):
    """Schéma pour confirmer la réinitialisation de mot de passe"""
    token: str = Field(..., description="Token de réinitialisation")
    new_password: str = Field(..., min_length=8, description="Nouveau mot de passe")


class ChangePasswordRequest(BaseModel):
    """Schéma pour changer le mot de passe"""
    current_password: str = Field(..., min_length=1, description="Mot de passe actuel")
    new_password: str = Field(..., min_length=8, description="Nouveau mot de passe")
