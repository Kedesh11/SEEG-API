"""
Schémas Pydantic pour les candidatures
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

class ApplicationBase(BaseModel):
    status: str = "pending"
    cover_letter: Optional[str] = None
    motivation: Optional[str] = None
    reference_contacts: Optional[str] = None
    availability_start: Optional[datetime] = None
    url_idee_projet: Optional[str] = None
    url_lettre_integrite: Optional[str] = None
    
    # MTP Questions
    mtp_answers: Optional[Dict[str, Any]] = None
    mtp_metier_q1: Optional[str] = None
    mtp_metier_q2: Optional[str] = None
    mtp_metier_q3: Optional[str] = None
    mtp_paradigme_q1: Optional[str] = None
    mtp_paradigme_q2: Optional[str] = None
    mtp_paradigme_q3: Optional[str] = None
    mtp_talent_q1: Optional[str] = None
    mtp_talent_q2: Optional[str] = None
    mtp_talent_q3: Optional[str] = None

class ApplicationCreate(ApplicationBase):
    candidate_id: UUID
    job_offer_id: UUID

class ApplicationUpdate(BaseModel):
    status: Optional[str] = None
    cover_letter: Optional[str] = None
    motivation: Optional[str] = None
    reference_contacts: Optional[str] = None
    availability_start: Optional[datetime] = None
    url_idee_projet: Optional[str] = None
    url_lettre_integrite: Optional[str] = None
    mtp_answers: Optional[Dict[str, Any]] = None
    mtp_metier_q1: Optional[str] = None
    mtp_metier_q2: Optional[str] = None
    mtp_metier_q3: Optional[str] = None
    mtp_paradigme_q1: Optional[str] = None
    mtp_paradigme_q2: Optional[str] = None
    mtp_paradigme_q3: Optional[str] = None
    mtp_talent_q1: Optional[str] = None
    mtp_talent_q2: Optional[str] = None
    mtp_talent_q3: Optional[str] = None

class ApplicationResponse(ApplicationBase):
    id: UUID
    candidate_id: UUID
    job_offer_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ApplicationWithDetails(ApplicationResponse):
    candidate: Optional["UserResponse"] = None
    job_offer: Optional["JobOfferResponse"] = None
    documents: List["ApplicationDocumentResponse"] = []
    protocol1_evaluation: Optional["Protocol1EvaluationResponse"] = None
    protocol2_evaluation: Optional["Protocol2EvaluationResponse"] = None

class ApplicationDocumentBase(BaseModel):
    document_type: str
    file_name: str
    file_url: str
    file_size: Optional[int] = None

class ApplicationDocumentCreate(ApplicationDocumentBase):
    application_id: UUID

class ApplicationDocumentResponse(ApplicationDocumentBase):
    id: UUID
    application_id: UUID
    uploaded_at: datetime
    
    class Config:
        from_attributes = True

class ApplicationDraftBase(BaseModel):
    form_data: Optional[Dict[str, Any]] = None
    ui_state: Optional[Dict[str, Any]] = None

class ApplicationDraftCreate(ApplicationDraftBase):
    user_id: UUID
    job_offer_id: UUID

class ApplicationDraftUpdate(ApplicationDraftBase):
    pass

class ApplicationDraftResponse(ApplicationDraftBase):
    user_id: UUID
    job_offer_id: UUID
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ApplicationHistoryBase(BaseModel):
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    notes: Optional[str] = None

class ApplicationHistoryCreate(ApplicationHistoryBase):
    application_id: UUID
    changed_by: UUID

class ApplicationHistoryResponse(ApplicationHistoryBase):
    id: UUID
    application_id: UUID
    changed_by: UUID
    changed_at: datetime
    
    class Config:
        from_attributes = True
