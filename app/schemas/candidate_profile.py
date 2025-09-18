"""
Schémas Pydantic pour les profils candidats
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.base import BaseSchema


class CandidateProfileBase(BaseModel):
    """Schéma de base pour les profils candidats"""
    user_id: str = Field(..., description="ID de l'utilisateur")
    address: Optional[str] = Field(None, description="Adresse")
    birth_date: Optional[datetime] = Field(None, description="Date de naissance")
    gender: Optional[str] = Field(None, description="Genre")
    phone: Optional[str] = Field(None, max_length=20, description="Numéro de téléphone")
    
    # Informations professionnelles
    current_position: Optional[str] = Field(None, description="Poste actuel")
    current_department: Optional[str] = Field(None, description="Département actuel")
    years_experience: Optional[int] = Field(None, ge=0, description="Années d'expérience")
    
    # Éducation et compétences
    education: Optional[str] = Field(None, description="Formation")
    skills: Optional[List[str]] = Field(None, description="Compétences")
    
    # Informations financières
    expected_salary_min: Optional[float] = Field(None, ge=0, description="Salaire minimum attendu")
    expected_salary_max: Optional[float] = Field(None, ge=0, description="Salaire maximum attendu")
    
    # Disponibilité
    availability: Optional[str] = Field(None, description="Disponibilité")
    
    # Liens et documents
    cv_url: Optional[str] = Field(None, description="URL du CV")
    linkedin_url: Optional[str] = Field(None, description="URL LinkedIn")
    portfolio_url: Optional[str] = Field(None, description="URL du portfolio")


class CandidateProfileCreate(CandidateProfileBase):
    """Schéma pour créer un profil candidat"""
    pass


class CandidateProfileUpdate(BaseModel):
    """Schéma pour mettre à jour un profil candidat"""
    address: Optional[str] = None
    birth_date: Optional[datetime] = None
    gender: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=20)
    current_position: Optional[str] = None
    current_department: Optional[str] = None
    years_experience: Optional[int] = Field(None, ge=0)
    education: Optional[str] = None
    skills: Optional[List[str]] = None
    expected_salary_min: Optional[float] = Field(None, ge=0)
    expected_salary_max: Optional[float] = Field(None, ge=0)
    availability: Optional[str] = None
    cv_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None


class CandidateProfileResponse(CandidateProfileBase, BaseSchema):
    """Schéma de réponse pour les profils candidats"""
    pass
