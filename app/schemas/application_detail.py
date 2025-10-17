"""
Schémas pour les détails complets d'une candidature
Inclut toutes les informations du candidat, offre, questions MTP et réponses
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


# ============================================================================
# Schémas pour le candidat
# ============================================================================

class CandidateDocumentDetail(BaseModel):
    """Document téléversé par le candidat"""
    id: UUID
    document_type: str = Field(description="Type de document (cv, cover_letter, diploma, etc.)")
    file_name: str = Field(description="Nom du fichier original")
    file_path: str = Field(description="Chemin du fichier")
    file_size: Optional[int] = Field(None, description="Taille du fichier en octets")
    uploaded_at: datetime = Field(description="Date de téléversement")
    
    model_config = {"from_attributes": True}


class CandidateProfileDetail(BaseModel):
    """Profil complet du candidat"""
    user_id: UUID
    email: str
    firstname: str
    lastname: str
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    birth_date: Optional[datetime] = None
    nationality: Optional[str] = None
    
    # Informations professionnelles
    current_job_title: Optional[str] = None
    years_of_experience: Optional[int] = None
    education_level: Optional[str] = None
    skills: Optional[List[str]] = Field(default_factory=list, description="Compétences du candidat")
    languages: Optional[List[str]] = Field(default_factory=list, description="Langues parlées")
    
    # Documents téléversés
    documents: List[CandidateDocumentDetail] = Field(
        default_factory=list,
        description="Liste des documents téléversés par le candidat"
    )
    
    model_config = {"from_attributes": True}


# ============================================================================
# Schémas pour l'offre d'emploi
# ============================================================================

class MTPQuestionsDetail(BaseModel):
    """Questions MTP d'une offre"""
    questions_metier: List[str] = Field(
        default_factory=list,
        description="Questions métier (M)"
    )
    questions_talent: List[str] = Field(
        default_factory=list,
        description="Questions talent (T)"
    )
    questions_paradigme: List[str] = Field(
        default_factory=list,
        description="Questions paradigme (P)"
    )
    
    model_config = {"from_attributes": True}


class JobOfferDetail(BaseModel):
    """Détails complets de l'offre d'emploi"""
    id: UUID
    title: str
    description: str
    location: str
    contract_type: str
    salary_range: Optional[str] = None
    requirements: List[str] = Field(default_factory=list, description="Prérequis du poste")
    responsibilities: List[str] = Field(default_factory=list, description="Responsabilités")
    benefits: List[str] = Field(default_factory=list, description="Avantages")
    
    # Statut et type d'offre
    status: str = Field(description="Statut de l'offre (draft, published, closed)")
    offer_status: str = Field(
        description="Type d'offre (interne_only, externe_only, tous)",
        default="tous"
    )
    
    # Questions MTP
    questions_mtp: Optional[MTPQuestionsDetail] = Field(
        None,
        description="Questions MTP rattachées à cette offre"
    )
    
    # Dates
    created_at: datetime
    updated_at: datetime
    deadline: Optional[datetime] = None
    
    model_config = {"from_attributes": True}


# ============================================================================
# Schémas pour les réponses MTP
# ============================================================================

class MTPAnswersDetail(BaseModel):
    """Réponses MTP du candidat"""
    reponses_metier: List[str] = Field(
        default_factory=list,
        description="Réponses aux questions métier"
    )
    reponses_talent: List[str] = Field(
        default_factory=list,
        description="Réponses aux questions talent"
    )
    reponses_paradigme: List[str] = Field(
        default_factory=list,
        description="Réponses aux questions paradigme"
    )
    
    model_config = {"from_attributes": True}


# ============================================================================
# Schéma principal - Détails complets de la candidature
# ============================================================================

class ApplicationCompleteDetail(BaseModel):
    """
    Détails complets d'une candidature
    Inclut : candidat + profil + documents, offre + questions MTP, réponses MTP
    """
    # Informations de la candidature
    application_id: UUID = Field(description="ID unique de la candidature")
    status: str = Field(description="Statut de la candidature (pending, reviewed, interview, etc.)")
    created_at: datetime = Field(description="Date de soumission de la candidature")
    updated_at: datetime = Field(description="Dernière mise à jour")
    
    # Informations complémentaires de la candidature
    reference_contacts: Optional[str] = Field(
        None,
        description="Contacts de référence"
    )
    availability_start: Optional[datetime] = Field(
        None,
        description="Date de disponibilité"
    )
    
    # Pour candidats internes
    has_been_manager: bool = Field(
        default=False,
        description="Le candidat a-t-il déjà été manager/chef ?"
    )
    
    # Pour candidats externes
    reference: Optional[Dict[str, str]] = Field(
        None,
        description="Informations du référent (externe uniquement)",
        json_schema_extra={
            "example": {
                "entreprise": "Entreprise XYZ",
                "fullname": "Marie Martin",
                "email": "marie.martin@xyz.com",
                "contact": "+241 05 06 07 08"
            }
        }
    )
    
    # Profil complet du candidat (avec documents)
    candidate: CandidateProfileDetail = Field(
        description="Profil complet du candidat avec documents téléversés"
    )
    
    # Détails de l'offre d'emploi (avec questions MTP)
    job_offer: JobOfferDetail = Field(
        description="Détails complets de l'offre d'emploi avec questions MTP"
    )
    
    # Réponses MTP du candidat
    mtp_answers: Optional[MTPAnswersDetail] = Field(
        None,
        description="Réponses MTP du candidat aux questions de l'offre"
    )
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "application_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "pending",
                "created_at": "2025-10-16T10:30:00Z",
                "updated_at": "2025-10-16T10:30:00Z",
                "reference_contacts": "M. Dupont (+241 01 02 03 04)",
                "availability_start": "2025-11-01T00:00:00Z",
                "has_been_manager": False,
                "reference": {
                    "entreprise": "Entreprise ABC",
                    "fullname": "Jean Dupont",
                    "email": "jean.dupont@abc.com",
                    "contact": "+241 01 02 03 04"
                },
                "candidate": {
                    "user_id": "123e4567-e89b-12d3-a456-426614174000",
                    "email": "candidat@example.com",
                    "firstname": "Marie",
                    "lastname": "Koukou",
                    "phone": "+241 06 07 08 09",
                    "current_job_title": "Développeur Full Stack",
                    "years_of_experience": 5,
                    "documents": [
                        {
                            "id": "doc-uuid-1",
                            "document_type": "cv",
                            "file_name": "CV_Marie_Koukou.pdf",
                            "file_path": "/uploads/cv/...",
                            "uploaded_at": "2025-10-15T09:00:00Z"
                        }
                    ]
                },
                "job_offer": {
                    "id": "job-uuid-1",
                    "title": "Développeur Full Stack Senior",
                    "description": "Nous recherchons...",
                    "location": "Libreville",
                    "contract_type": "CDI",
                    "questions_mtp": {
                        "questions_metier": [
                            "Décrivez votre expérience en développement backend",
                            "Quels frameworks maîtrisez-vous ?"
                        ],
                        "questions_talent": [
                            "Comment gérez-vous les priorités ?"
                        ],
                        "questions_paradigme": [
                            "Quelle est votre vision du travail en équipe ?"
                        ]
                    }
                },
                "mtp_answers": {
                    "reponses_metier": [
                        "J'ai 5 ans d'expérience en Python/Django...",
                        "Je maîtrise Django, FastAPI, Flask..."
                    ],
                    "reponses_talent": [
                        "J'utilise une matrice d'Eisenhower..."
                    ],
                    "reponses_paradigme": [
                        "Le travail en équipe est essentiel..."
                    ]
                }
            }
        }
    }


class ApplicationCompleteDetailResponse(BaseModel):
    """Réponse enveloppée pour les détails complets de la candidature"""
    success: bool = True
    message: str = "Détails de la candidature récupérés avec succès"
    data: ApplicationCompleteDetail
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Détails de la candidature récupérés avec succès",
                "data": {
                    "application_id": "550e8400-e29b-41d4-a716-446655440000",
                    "status": "pending",
                    "candidate": {
                        "email": "candidat@example.com",
                        "firstname": "Marie",
                        "lastname": "Koukou"
                    },
                    "job_offer": {
                        "title": "Développeur Full Stack Senior"
                    }
                }
            }
        }

