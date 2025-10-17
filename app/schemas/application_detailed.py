"""
Schémas enrichis pour les réponses détaillées de candidatures
Inclut les informations complètes du candidat et de l'offre
"""
from pydantic import BaseModel, UUID4
from typing import Optional, List, Dict, Any
from datetime import datetime


class CandidateProfileInfo(BaseModel):
    """Informations du profil candidat"""
    id: Optional[UUID4] = None
    years_experience: Optional[int] = None
    current_position: Optional[str] = None
    current_department: Optional[str] = None
    availability: Optional[str] = None
    skills: Optional[str] = None
    education: Optional[str] = None
    expected_salary_min: Optional[int] = None
    expected_salary_max: Optional[int] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None


class CandidateInfo(BaseModel):
    """Informations complètes du candidat"""
    id: UUID4
    email: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    date_of_birth: Optional[str] = None
    sexe: Optional[str] = None
    role: str
    is_active: bool = True
    candidate_status: Optional[str] = None
    created_at: Optional[datetime] = None
    
    # Profil candidat (si disponible)
    candidate_profile: Optional[CandidateProfileInfo] = None


class JobOfferInfo(BaseModel):
    """Informations de l'offre d'emploi"""
    id: UUID4
    title: str
    department: Optional[str] = None
    location: Optional[str] = None
    contract_type: Optional[str] = None
    description: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    status: Optional[str] = None


class ApplicationDetailed(BaseModel):
    """Candidature avec informations complètes (candidat + offre)"""
    # Informations de base de la candidature
    id: UUID4
    candidate_id: UUID4
    job_offer_id: UUID4
    status: str
    reference_contacts: Optional[str] = None
    availability_start: Optional[datetime] = None
    has_been_manager: bool = False
    ref_entreprise: Optional[str] = None
    ref_fullname: Optional[str] = None
    ref_mail: Optional[str] = None
    ref_contact: Optional[str] = None
    mtp_answers: Optional[Dict[str, List[str]]] = None
    created_at: datetime
    updated_at: datetime
    
    # Relations enrichies (uniquement pour admins/recruteurs)
    candidate: Optional[CandidateInfo] = None
    job_offer: Optional[JobOfferInfo] = None
    
    model_config = {"from_attributes": True}


class ApplicationDetailedResponse(BaseModel):
    """Réponse avec candidature détaillée"""
    success: bool
    message: str
    data: ApplicationDetailed

