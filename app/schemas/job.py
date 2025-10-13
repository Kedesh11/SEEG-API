"""
Schémas Pydantic pour les offres d'emploi
"""
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

class JobOfferBase(BaseModel):
    title: str
    description: str
    location: str
    contract_type: str
    department: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    requirements: Optional[List[str]] = None
    benefits: Optional[List[str]] = None
    responsibilities: Optional[List[str]] = None
    status: str = "active"
    
    # Statut de visibilité de l'offre
    offer_status: str = Field(
        default="tous",
        description="Visibilité de l'offre: 'tous' (internes+externes), 'interne' (employés SEEG uniquement), 'externe' (candidats externes uniquement)"
    )
    
    application_deadline: Optional[datetime] = None
    date_limite: Optional[datetime] = None
    reporting_line: Optional[str] = None
    salary_note: Optional[str] = None
    start_date: Optional[datetime] = None
    profile: Optional[str] = None
    categorie_metier: Optional[str] = None
    job_grade: Optional[str] = None
    
    # Questions MTP (format JSON auto-incrémenté)
    questions_mtp: Optional[Dict[str, List[str]]] = Field(
        None,
        description="Questions MTP au format: {questions_metier: [...], questions_talent: [...], questions_paradigme: [...]}"
    )
    
    @field_validator('questions_mtp')
    @classmethod
    def validate_mtp_questions(cls, v):
        """Valider que les questions MTP respectent les limites"""
        if v is None:
            return v
        
        # Vérifier les limites: 7 métier max, 3 talent max, 3 paradigme max
        if 'questions_metier' in v and len(v['questions_metier']) > 7:
            raise ValueError("Maximum 7 questions métier autorisées")
        if 'questions_talent' in v and len(v['questions_talent']) > 3:
            raise ValueError("Maximum 3 questions talent autorisées")
        if 'questions_paradigme' in v and len(v['questions_paradigme']) > 3:
            raise ValueError("Maximum 3 questions paradigme autorisées")
        
        return v

class JobOfferCreate(JobOfferBase):
    recruiter_id: Optional[UUID] = None  # Ajouté automatiquement depuis le token JWT
    
    # Champs legacy pour compatibilité avec le frontend (format string)
    question_metier: Optional[str] = Field(None, exclude=True)
    question_talent: Optional[str] = Field(None, exclude=True)
    question_paradigme: Optional[str] = Field(None, exclude=True)
    
    @model_validator(mode='after')
    def transform_mtp_questions(self):
        """
        Transformer les questions MTP du format legacy (strings) au format structuré (Dict[str, List[str]])
        
        Règle de transformation:
        - Si questions_mtp existe déjà → le garder tel quel
        - Sinon, si question_* existent → les transformer en questions_mtp structuré
        - Chaque question est séparée par un retour à la ligne (\n)
        """
        # Si questions_mtp est déjà fourni, ne rien faire
        if self.questions_mtp is not None:
            return self
        
        # Sinon, construire questions_mtp depuis les champs legacy
        questions_dict = {}
        
        # Transformer question_metier
        if self.question_metier:
            # Séparer les questions par retour à la ligne et nettoyer
            questions = [q.strip() for q in self.question_metier.split('\n') if q.strip()]
            if questions:
                questions_dict['questions_metier'] = questions
        
        # Transformer question_talent
        if self.question_talent:
            questions = [q.strip() for q in self.question_talent.split('\n') if q.strip()]
            if questions:
                questions_dict['questions_talent'] = questions
        
        # Transformer question_paradigme
        if self.question_paradigme:
            questions = [q.strip() for q in self.question_paradigme.split('\n') if q.strip()]
            if questions:
                questions_dict['questions_paradigme'] = questions
        
        # Assigner le dictionnaire structuré si non vide
        if questions_dict:
            self.questions_mtp = questions_dict
        
        return self

class JobOfferUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    contract_type: Optional[str] = None
    department: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    requirements: Optional[List[str]] = None
    benefits: Optional[List[str]] = None
    responsibilities: Optional[List[str]] = None
    status: Optional[str] = None
    offer_status: Optional[str] = Field(
        None,
        description="Visibilité de l'offre: 'tous', 'interne', 'externe'"
    )
    application_deadline: Optional[datetime] = None
    date_limite: Optional[datetime] = None
    reporting_line: Optional[str] = None
    salary_note: Optional[str] = None
    start_date: Optional[datetime] = None
    profile: Optional[str] = None
    categorie_metier: Optional[str] = None
    job_grade: Optional[str] = None
    
    # Questions MTP (format JSON auto-incrémenté)
    questions_mtp: Optional[Dict[str, List[str]]] = None
    
    # Champs legacy pour compatibilité avec le frontend (format string)
    question_metier: Optional[str] = Field(None, exclude=True)
    question_talent: Optional[str] = Field(None, exclude=True)
    question_paradigme: Optional[str] = Field(None, exclude=True)
    
    @model_validator(mode='after')
    def transform_mtp_questions(self):
        """
        Transformer les questions MTP du format legacy (strings) au format structuré (Dict[str, List[str]])
        
        Règle de transformation:
        - Si questions_mtp existe déjà → le garder tel quel
        - Sinon, si question_* existent → les transformer en questions_mtp structuré
        - Chaque question est séparée par un retour à la ligne (\n)
        """
        # Si questions_mtp est déjà fourni, ne rien faire
        if self.questions_mtp is not None:
            return self
        
        # Sinon, construire questions_mtp depuis les champs legacy
        questions_dict = {}
        
        # Transformer question_metier
        if self.question_metier:
            questions = [q.strip() for q in self.question_metier.split('\n') if q.strip()]
            if questions:
                questions_dict['questions_metier'] = questions
        
        # Transformer question_talent
        if self.question_talent:
            questions = [q.strip() for q in self.question_talent.split('\n') if q.strip()]
            if questions:
                questions_dict['questions_talent'] = questions
        
        # Transformer question_paradigme
        if self.question_paradigme:
            questions = [q.strip() for q in self.question_paradigme.split('\n') if q.strip()]
            if questions:
                questions_dict['questions_paradigme'] = questions
        
        # Assigner le dictionnaire structuré si non vide
        if questions_dict:
            self.questions_mtp = questions_dict
        
        return self

class JobOfferResponse(JobOfferBase):
    id: UUID
    recruiter_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# SCHÉMAS PUBLICS (sans authentification)
# ============================================================================

class JobOfferPublicResponse(BaseModel):
    """Schéma de réponse publique pour les offres (sans infos sensibles)"""
    id: UUID
    title: str
    description: str
    location: str
    contract_type: str
    department: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_note: Optional[str] = None
    requirements: Optional[List[str]] = None
    benefits: Optional[List[str]] = None
    responsibilities: Optional[List[str]] = None
    offer_status: str = Field(description="Visibilité: 'tous', 'interne', 'externe'")
    application_deadline: Optional[datetime] = None
    date_limite: Optional[datetime] = None
    start_date: Optional[datetime] = None
    profile: Optional[str] = None
    categorie_metier: Optional[str] = None
    job_grade: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class JobOfferDetailPublicResponse(BaseModel):
    """Schéma de réponse détaillée publique pour une offre (avec questions MTP)"""
    id: UUID
    title: str
    description: str
    location: str
    contract_type: str
    department: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_note: Optional[str] = None
    requirements: Optional[List[str]] = None
    benefits: Optional[List[str]] = None
    responsibilities: Optional[List[str]] = None
    offer_status: str = Field(description="Visibilité: 'tous', 'interne', 'externe'")
    application_deadline: Optional[datetime] = None
    date_limite: Optional[datetime] = None
    reporting_line: Optional[str] = None
    start_date: Optional[datetime] = None
    profile: Optional[str] = None
    categorie_metier: Optional[str] = None
    job_grade: Optional[str] = None
    
    # Questions MTP (si disponibles)
    questions_mtp: Optional[Dict[str, List[str]]] = Field(
        None,
        description="Questions MTP au format JSON"
    )
    
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
