"""
Schémas Pydantic pour les utilisateurs
======================================
Architecture: Type-Safe + Validation Stricte + Documentation Complète

Schémas principaux:
- UserBase/Response: Données utilisateur complètes
- UserUpdate: Mise à jour utilisateur
- CandidateProfile: Profil enrichi du candidat
- UserWithProfile: Utilisateur + profil candidat
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID
from app.core.enums.user_enums import UserRole
from app.schemas.auth import (
    ALLOWED_SEXES, ALLOWED_CANDIDATE_STATUS,
    SEXE_MALE, SEXE_FEMALE,
    CANDIDATE_STATUS_INTERNAL, CANDIDATE_STATUS_EXTERNAL
)

# ============================================================================
# CONSTANTES - Statuts et paramètres utilisateur
# ============================================================================

# Statuts de compte
USER_STATUS_ACTIVE = "actif"
USER_STATUS_PENDING = "en_attente"
USER_STATUS_BLOCKED = "bloqué"
ALLOWED_USER_STATUS = {USER_STATUS_ACTIVE, USER_STATUS_PENDING, USER_STATUS_BLOCKED}

# Disponibilités
AVAILABILITY_IMMEDIATE = "Immédiate"
AVAILABILITY_1_MONTH = "Dans 1 mois"
AVAILABILITY_2_MONTHS = "Dans 2 mois"
AVAILABILITY_3_MONTHS = "Dans 3 mois ou plus"
ALLOWED_AVAILABILITIES = {
    AVAILABILITY_IMMEDIATE,
    AVAILABILITY_1_MONTH,
    AVAILABILITY_2_MONTHS,
    AVAILABILITY_3_MONTHS
}

class UserBase(BaseModel):
    """
    Schéma de base pour un utilisateur.
    
    Contient toutes les informations communes à tous les types d'utilisateurs:
    - Candidats (internes et externes)
    - Recruteurs
    - Administrateurs
    """
    email: EmailStr = Field(..., description="Adresse email unique")
    first_name: str = Field(..., min_length=1, max_length=100, description="Prénom")
    last_name: str = Field(..., min_length=1, max_length=100, description="Nom de famille")
    role: UserRole = Field(..., description="Rôle: candidate, recruiter, ou admin")
    phone: Optional[str] = Field(None, max_length=20, description="Numéro de téléphone")
    date_of_birth: Optional[datetime] = Field(None, description="Date de naissance")
    sexe: Optional[str] = Field(None, description=f"Sexe: {SEXE_MALE} (Homme) ou {SEXE_FEMALE} (Femme)")
    matricule: Optional[int] = Field(None, description="Matricule SEEG (candidats internes uniquement)")
    email_verified: Optional[bool] = Field(False, description="Email vérifié")
    is_active: Optional[bool] = Field(True, description="Compte actif")
    is_internal_candidate: Optional[bool] = Field(False, description="Candidat interne SEEG")
    adresse: Optional[str] = Field(None, description="Adresse complète")
    candidate_status: Optional[str] = Field(None, description=f"Type: {CANDIDATE_STATUS_INTERNAL} ou {CANDIDATE_STATUS_EXTERNAL}")
    statut: Optional[str] = Field(USER_STATUS_ACTIVE, description=f"Statut du compte: {', '.join(ALLOWED_USER_STATUS)}")
    poste_actuel: Optional[str] = Field(None, description="Poste occupé actuellement")
    annees_experience: Optional[int] = Field(None, ge=0, le=50, description="Années d'expérience professionnelle")
    no_seeg_email: Optional[bool] = Field(False, description="Employé SEEG sans email @seeg-gabon.com")


class UserCreate(UserBase):
    """Schéma pour créer un nouvel utilisateur (inclut le mot de passe)."""
    password: str = Field(..., min_length=12, description="Mot de passe (minimum 12 caractères)")


class UserUpdate(BaseModel):
    """
    Schéma pour mettre à jour un utilisateur.
    
    Tous les champs sont optionnels. Seuls les champs fournis seront mis à jour.
    """
    email: Optional[EmailStr] = Field(None, description="Nouvelle adresse email")
    first_name: Optional[str] = Field(None, min_length=1, max_length=100, description="Nouveau prénom")
    last_name: Optional[str] = Field(None, min_length=1, max_length=100, description="Nouveau nom")
    role: Optional[UserRole] = Field(None, description="Nouveau rôle")
    phone: Optional[str] = Field(None, max_length=20, description="Nouveau téléphone")
    date_of_birth: Optional[datetime] = Field(None, description="Nouvelle date de naissance")
    sexe: Optional[str] = Field(None, description="Nouveau sexe")
    matricule: Optional[int] = Field(None, description="Nouveau matricule")
    adresse: Optional[str] = Field(None, description="Nouvelle adresse")
    candidate_status: Optional[str] = Field(None, description="Nouveau statut candidat")
    statut: Optional[str] = Field(None, description="Nouveau statut compte")
    poste_actuel: Optional[str] = Field(None, description="Nouveau poste")
    annees_experience: Optional[int] = Field(None, ge=0, le=50, description="Nouvelles années d'expérience")
    no_seeg_email: Optional[bool] = Field(None, description="Mise à jour flag email")
    is_internal_candidate: Optional[bool] = Field(None, description="Mise à jour flag interne")
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "description": "Mettre à jour le téléphone et l'adresse",
                    "value": {
                        "phone": "+241 07 99 88 77",
                        "adresse": "Nouvelle adresse, Libreville"
                    }
                },
                {
                    "description": "Mettre à jour l'expérience professionnelle",
                    "value": {
                        "poste_actuel": "Chef de projet IT",
                        "annees_experience": 10
                    }
                }
            ]
        }


class UserResponse(UserBase):
    """
    Schéma de réponse utilisateur avec métadonnées système.
    
    Inclut les timestamps et l'ID unique.
    """
    id: UUID = Field(..., description="Identifiant unique (UUID)")
    created_at: datetime = Field(..., description="Date de création du compte")
    updated_at: datetime = Field(..., description="Date de dernière modification")
    last_login: Optional[datetime] = Field(None, description="Date de dernière connexion")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "jean.dupont@seeg-gabon.com",
                "first_name": "Jean",
                "last_name": "Dupont",
                "role": "candidate",
                "phone": "+241 06 22 33 44",
                "date_of_birth": "1988-11-10T00:00:00Z",
                "sexe": "M",
                "matricule": 123456,
                "email_verified": True,
                "is_active": True,
                "is_internal_candidate": True,
                "adresse": "Quartier Batterie IV, Libreville",
                "candidate_status": "interne",
                "statut": "actif",
                "poste_actuel": "Technicien Réseau",
                "annees_experience": 8,
                "no_seeg_email": False,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-10-17T14:20:00Z",
                "last_login": "2024-10-17T09:15:00Z"
            }
        }

class CandidateProfileBase(BaseModel):
    """
    Schéma de base pour le profil enrichi d'un candidat.
    
    Complète les informations de User avec des détails professionnels,
    académiques et de préférences.
    """
    address: Optional[str] = Field(None, description="Adresse complète du candidat")
    availability: Optional[str] = Field(None, description=f"Disponibilité: {', '.join(ALLOWED_AVAILABILITIES)}")
    birth_date: Optional[datetime] = Field(None, description="Date de naissance (peut différer de User.date_of_birth)")
    current_department: Optional[str] = Field(None, description="Département actuel (si employé SEEG)")
    current_position: Optional[str] = Field(None, description="Poste actuel")
    cv_url: Optional[str] = Field(None, description="URL vers CV hébergé (obsolète, préférer documents PDF)")
    education: Optional[str] = Field(None, description="Formation académique détaillée")
    expected_salary_min: Optional[int] = Field(None, ge=0, description="Salaire minimum souhaité (FCFA)")
    expected_salary_max: Optional[int] = Field(None, ge=0, description="Salaire maximum souhaité (FCFA)")
    gender: Optional[str] = Field(None, description=f"Genre: {SEXE_MALE} ou {SEXE_FEMALE}")
    linkedin_url: Optional[str] = Field(None, description="URL profil LinkedIn")
    portfolio_url: Optional[str] = Field(None, description="URL portfolio professionnel")
    skills: Optional[List[str]] = Field(None, description="Liste des compétences techniques et métier")
    years_experience: Optional[int] = Field(None, ge=0, le=50, description="Années d'expérience totales")


class CandidateProfileCreate(CandidateProfileBase):
    """Schéma pour créer un profil candidat."""
    user_id: UUID = Field(..., description="ID de l'utilisateur associé")


class CandidateProfileUpdate(BaseModel):
    """
    Schéma pour mettre à jour un profil candidat.
    
    Tous les champs sont optionnels.
    """
    address: Optional[str] = Field(None, description="Nouvelle adresse")
    availability: Optional[str] = Field(None, description="Nouvelle disponibilité")
    birth_date: Optional[datetime] = Field(None, description="Nouvelle date de naissance")
    current_department: Optional[str] = Field(None, description="Nouveau département")
    current_position: Optional[str] = Field(None, description="Nouveau poste")
    cv_url: Optional[str] = Field(None, description="Nouvelle URL CV")
    education: Optional[str] = Field(None, description="Nouvelle formation")
    expected_salary_min: Optional[int] = Field(None, ge=0, description="Nouveau salaire min")
    expected_salary_max: Optional[int] = Field(None, ge=0, description="Nouveau salaire max")
    gender: Optional[str] = Field(None, description="Nouveau genre")
    linkedin_url: Optional[str] = Field(None, description="Nouvelle URL LinkedIn")
    portfolio_url: Optional[str] = Field(None, description="Nouvelle URL portfolio")
    skills: Optional[List[str]] = Field(None, description="Nouvelles compétences")
    years_experience: Optional[int] = Field(None, ge=0, le=50, description="Nouvelle expérience")
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "description": "Mettre à jour compétences et salaire",
                    "value": {
                        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Azure"],
                        "expected_salary_min": 800000,
                        "expected_salary_max": 1200000
                    }
                },
                {
                    "description": "Mettre à jour disponibilité et liens professionnels",
                    "value": {
                        "availability": "Immédiate",
                        "linkedin_url": "https://linkedin.com/in/jean-dupont-seeg",
                        "portfolio_url": "https://github.com/jeandupont"
                    }
                }
            ]
        }


class CandidateProfileResponse(CandidateProfileBase):
    """
    Schéma de réponse profil candidat avec métadonnées.
    """
    id: UUID = Field(..., description="ID unique du profil")
    user_id: UUID = Field(..., description="ID de l'utilisateur associé")
    created_at: datetime = Field(..., description="Date de création du profil")
    updated_at: datetime = Field(..., description="Date de dernière modification")
    
    @field_validator('skills', mode='before')
    @classmethod
    def parse_skills(cls, v):
        """Convertir JSON string vers List[str] si nécessaire."""
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except:
                return []
        return v
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "660e8400-e29b-41d4-a716-446655440000",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "address": "Quartier Nzeng-Ayong, Libreville",
                "availability": "Immédiate",
                "birth_date": "1995-03-20T00:00:00Z",
                "current_department": "IT",
                "current_position": "Développeuse Full Stack",
                "cv_url": None,
                "education": "Master Informatique - Université Omar Bongo",
                "expected_salary_min": 800000,
                "expected_salary_max": 1200000,
                "gender": "F",
                "linkedin_url": "https://linkedin.com/in/marie-kouamba",
                "portfolio_url": "https://github.com/mariekouamba",
                "skills": ["Python", "FastAPI", "React", "PostgreSQL", "Docker"],
                "years_experience": 5,
                "created_at": "2024-02-01T10:00:00Z",
                "updated_at": "2024-10-17T14:30:00Z"
            }
        }


class UserWithProfile(UserResponse):
    """
    Utilisateur avec son profil candidat enrichi.
    
    Combine les données User + CandidateProfile pour une vue complète du candidat.
    Utilisé dans les endpoints qui nécessitent toutes les informations du candidat.
    """
    candidate_profile: Optional[CandidateProfileResponse] = Field(
        None,
        description="Profil enrichi du candidat (null pour recruteurs/admins)"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "marie.kouamba@gmail.com",
                "first_name": "Marie",
                "last_name": "Kouamba",
                "role": "candidate",
                "phone": "+241 07 11 22 33",
                "candidate_status": "externe",
                "statut": "actif",
                "created_at": "2024-02-01T09:00:00Z",
                "updated_at": "2024-10-17T14:30:00Z",
                "candidate_profile": {
                    "id": "660e8400-e29b-41d4-a716-446655440000",
                    "user_id": "550e8400-e29b-41d4-a716-446655440000",
                    "skills": ["Python", "FastAPI", "React"],
                    "availability": "Immédiate",
                    "expected_salary_min": 800000,
                    "years_experience": 5
                }
            }
        }
    }
