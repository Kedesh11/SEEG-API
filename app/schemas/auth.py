"""
Schémas Pydantic pour l'authentification
"""
from typing import Optional
from pydantic import BaseModel, Field, EmailStr


class LoginRequest(BaseModel):
    """Schéma pour la connexion"""
    email: EmailStr = Field(..., description="Adresse email")
    password: str = Field(..., min_length=1, description="Mot de passe")


class SignupRequest(BaseModel):
    """Schéma pour l'inscription"""
    email: EmailStr = Field(..., description="Adresse email")
    password: str = Field(..., min_length=8, description="Mot de passe")
    first_name: str = Field(..., min_length=1, max_length=100, description="Prénom")
    last_name: str = Field(..., min_length=1, max_length=100, description="Nom")
    matricule: Optional[str] = Field(None, max_length=20, description="Matricule SEEG")
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
