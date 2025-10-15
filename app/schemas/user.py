"""
Schémas Pydantic pour les utilisateurs
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from app.core.enums.user_enums import UserRole

class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    role: UserRole
    phone: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    sexe: Optional[str] = None
    matricule: Optional[int] = None
    email_verified: Optional[bool] = False
    is_active: Optional[bool] = True
    is_internal_candidate: Optional[bool] = False  # True = interne, False = externe
    adresse: Optional[str] = None
    candidate_status: Optional[str] = None
    statut: Optional[str] = "actif"
    poste_actuel: Optional[str] = None
    annees_experience: Optional[int] = None
    no_seeg_email: Optional[bool] = False

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[UserRole] = None
    phone: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    sexe: Optional[str] = None
    matricule: Optional[int] = None
    adresse: Optional[str] = None
    candidate_status: Optional[str] = None
    statut: Optional[str] = None
    poste_actuel: Optional[str] = None
    annees_experience: Optional[int] = None
    no_seeg_email: Optional[bool] = None
    is_internal_candidate: Optional[bool] = None

class UserResponse(UserBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class CandidateProfileBase(BaseModel):
    address: Optional[str] = None
    availability: Optional[str] = None
    birth_date: Optional[datetime] = None
    current_department: Optional[str] = None
    current_position: Optional[str] = None
    cv_url: Optional[str] = None
    education: Optional[str] = None
    expected_salary_min: Optional[int] = None
    expected_salary_max: Optional[int] = None
    gender: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    skills: Optional[List[str]] = None
    years_experience: Optional[int] = None

class CandidateProfileCreate(CandidateProfileBase):
    user_id: UUID

class CandidateProfileUpdate(BaseModel):
    address: Optional[str] = None
    availability: Optional[str] = None
    birth_date: Optional[datetime] = None
    current_department: Optional[str] = None
    current_position: Optional[str] = None
    cv_url: Optional[str] = None
    education: Optional[str] = None
    expected_salary_min: Optional[int] = None
    expected_salary_max: Optional[int] = None
    gender: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    skills: Optional[List[str]] = None
    years_experience: Optional[int] = None

class CandidateProfileResponse(CandidateProfileBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    
    @field_validator('skills', mode='before')
    @classmethod
    def parse_skills(cls, v):
        """Convertir JSON string vers List[str] si nécessaire"""
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except:
                return []
        return v
    
    class Config:
        from_attributes = True

class UserWithProfile(UserResponse):
    """Utilisateur avec son profil candidat (si applicable)"""
    candidate_profile: Optional[CandidateProfileResponse] = None
