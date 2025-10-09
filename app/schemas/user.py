"""
Schémas Pydantic pour les utilisateurs
"""
from pydantic import BaseModel, EmailStr, Field
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

class UserResponse(UserBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class UserWithProfile(UserResponse):
    candidate_profile: Optional["CandidateProfileResponse"] = None

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
    
    class Config:
        from_attributes = True
