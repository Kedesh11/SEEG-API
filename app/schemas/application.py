"""
Schémas Pydantic pour les candidatures
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, BinaryIO
from datetime import datetime
from uuid import UUID
import base64
from app.core.validators import validate_pdf_field


class ApplicationBase(BaseModel):
    status: str = "pending"
    reference_contacts: Optional[str] = None
    availability_start: Optional[datetime] = None
    
    # Champ de qualification pour candidats internes
    has_been_manager: bool = Field(
        default=False,
        description="Indique si le candidat interne a déjà occupé un poste de chef/manager (obligatoire pour candidats internes)"
    )
    
    # Champs de recommandation pour candidats externes
    ref_entreprise: Optional[str] = Field(
        None,
        max_length=255,
        description="Nom de l'entreprise/organisation recommandante (obligatoire pour candidats externes)"
    )
    ref_fullname: Optional[str] = Field(
        None,
        max_length=255,
        description="Nom complet du référent (obligatoire pour candidats externes)"
    )
    ref_mail: Optional[str] = Field(
        None,
        max_length=255,
        description="Adresse e-mail du référent (obligatoire pour candidats externes)"
    )
    ref_contact: Optional[str] = Field(
        None,
        max_length=50,
        description="Numéro de téléphone du référent (obligatoire pour candidats externes)"
    )
    
    # Réponses MTP (format JSON auto-incrémenté)
    # Format: {"reponses_metier": ["R1", "R2", ...], "reponses_talent": [...], "reponses_paradigme": [...]}
    mtp_answers: Optional[Dict[str, List[str]]] = Field(
        None,
        description="Réponses MTP au format: {reponses_metier: [...], reponses_talent: [...], reponses_paradigme: [...]}"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "pending",
                "reference_contacts": "Mme X (+241...), M. Y (+241...)",
                "availability_start": "2025-10-01T00:00:00Z",
                "mtp_answers": {"q1": "réponse"},
                "has_been_manager": False,
                "ref_entreprise": "Entreprise ABC",
                "ref_fullname": "Jean Dupont",
                "ref_mail": "jean.dupont@abc.com",
                "ref_contact": "+241 01 02 03 04"
            }
        }


class ApplicationCreate(ApplicationBase):
    candidate_id: UUID
    job_offer_id: UUID

    class Config:
        json_schema_extra = {
            "example": {
                "candidate_id": "00000000-0000-0000-0000-000000000001",
                "job_offer_id": "00000000-0000-0000-0000-0000000000AA",
                "status": "pending"
            }
        }


class ApplicationUpdate(BaseModel):
    status: Optional[str] = None
    reference_contacts: Optional[str] = None
    availability_start: Optional[datetime] = None
    has_been_manager: Optional[bool] = None
    ref_entreprise: Optional[str] = Field(None, max_length=255)
    ref_fullname: Optional[str] = Field(None, max_length=255)
    ref_mail: Optional[str] = Field(None, max_length=255)
    ref_contact: Optional[str] = Field(None, max_length=50)
    # Réponses MTP (format JSON auto-incrémenté)
    mtp_answers: Optional[Dict[str, List[str]]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "status": "reviewed",
                "reference_contacts": "M. Kassa (+241...)",
                "has_been_manager": True,
                "ref_entreprise": "Entreprise XYZ",
                "ref_fullname": "Marie Martin",
                "ref_mail": "marie.martin@xyz.com",
                "ref_contact": "+241 05 06 07 08"
            }
        }


class ApplicationInDBBase(ApplicationBase):
    id: UUID
    candidate_id: UUID
    job_offer_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Application(ApplicationInDBBase):
    pass


class ApplicationInDB(ApplicationInDBBase):
    pass


# Schémas pour les documents avec fichiers binaires
class ApplicationDocumentBase(BaseModel):
    document_type: str = Field(..., description="Type de document: cover_letter, cv, certificats, diplome")
    file_name: str = Field(..., description="Nom du fichier PDF")
    file_data: str = Field(..., description="Contenu du fichier PDF encodé en base64")
    file_size: int = Field(..., description="Taille du fichier en octets")
    file_type: str = Field(default="application/pdf", description="Type MIME du fichier")

    # Utiliser le validateur PDF personnalisé
    _validate_pdf = validate_pdf_field(max_size_mb=10)

    class Config:
        json_schema_extra = {
            "example": {
                "document_type": "cv",
                "file_name": "cv_sevan.pdf",
                "file_data": "JVBERi0xLjQKJ... (base64)",
                "file_size": 245678,
                "file_type": "application/pdf"
            }
        }

    @validator('document_type')
    def validate_document_type(cls, v):
        """Valide le type de document."""
        allowed_types = ['cover_letter', 'cv', 'certificats', 'diplome']
        if v not in allowed_types:
            raise ValueError(f"Type de document invalide. Types autorisés: {allowed_types}")
        return v

    @validator('file_name')
    def validate_file_name(cls, v):
        """Valide que le nom de fichier se termine par .pdf."""
        if not v.lower().endswith('.pdf'):
            raise ValueError("Le nom de fichier doit se terminer par .pdf")
        return v

    @validator('file_data')
    def validate_file_data(cls, v):
        """Valide que les données sont en base64 valide."""
        try:
            # Décoder pour vérifier que c'est du base64 valide
            decoded = base64.b64decode(v)
            # Vérifier que c'est bien un PDF (magic number)
            if not decoded.startswith(b'%PDF'):
                raise ValueError("Le fichier n'est pas un PDF valide")
            return v
        except Exception as e:
            raise ValueError(f"Données base64 invalides: {str(e)}")

    @validator('file_type')
    def validate_file_type(cls, v):
        """Valide le type MIME."""
        if v != "application/pdf":
            raise ValueError("Le type de fichier doit être application/pdf")
        return v


class ApplicationDocumentCreate(ApplicationDocumentBase):
    application_id: UUID


class ApplicationDocumentUpdate(BaseModel):
    document_type: Optional[str] = None
    file_name: Optional[str] = None
    file_data: Optional[str] = None
    file_size: Optional[int] = None
    file_type: Optional[str] = None

    @validator('document_type')
    def validate_document_type(cls, v):
        """Valide le type de document."""
        if v is not None:
            allowed_types = ['cover_letter', 'cv', 'certificats', 'diplome']
            if v not in allowed_types:
                raise ValueError(f"Type de document invalide. Types autorisés: {allowed_types}")
        return v

    @validator('file_name')
    def validate_file_name(cls, v):
        """Valide que le nom de fichier se termine par .pdf."""
        if v is not None and not v.lower().endswith('.pdf'):
            raise ValueError("Le nom de fichier doit se terminer par .pdf")
        return v

    @validator('file_data')
    def validate_file_data(cls, v):
        """Valide que les données sont en base64 valide."""
        if v is not None:
            try:
                decoded = base64.b64decode(v)
                if not decoded.startswith(b'%PDF'):
                    raise ValueError("Le fichier n'est pas un PDF valide")
                return v
            except Exception as e:
                raise ValueError(f"Données base64 invalides: {str(e)}")
        return v

    @validator('file_type')
    def validate_file_type(cls, v):
        """Valide le type MIME."""
        if v is not None and v != "application/pdf":
            raise ValueError("Le type de fichier doit être application/pdf")
        return v


class ApplicationDocumentInDBBase(BaseModel):
    id: UUID
    application_id: UUID
    document_type: str
    file_name: str
    file_size: int
    file_type: str
    uploaded_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "00000000-0000-0000-0000-0000000000DD",
                "application_id": "00000000-0000-0000-0000-0000000000AA",
                "document_type": "cv",
                "file_name": "cv_sevan.pdf",
                "file_size": 245678,
                "file_type": "application/pdf",
                "uploaded_at": "2025-09-22T10:15:00Z"
            }
        }


class ApplicationDocument(ApplicationDocumentInDBBase):
    """Schéma pour la réponse API - n'inclut pas les données binaires pour des raisons de performance."""
    pass


class ApplicationDocumentWithData(ApplicationDocumentInDBBase):
    """Schéma pour inclure les données binaires du fichier."""
    file_data: str = Field(..., description="Contenu du fichier PDF encodé en base64")


class ApplicationDocumentInDB(ApplicationDocumentInDBBase):
    pass


# Schémas pour les brouillons
class ApplicationDraftBase(BaseModel):
    form_data: Optional[Dict[str, Any]] = None
    ui_state: Optional[Dict[str, Any]] = None


class ApplicationDraftCreate(ApplicationDraftBase):
    user_id: UUID
    job_offer_id: UUID


class ApplicationDraftUpdate(ApplicationDraftBase):
    pass


class ApplicationDraftInDBBase(ApplicationDraftBase):
    user_id: UUID
    job_offer_id: UUID
    updated_at: datetime

    class Config:
        from_attributes = True


class ApplicationDraft(ApplicationDraftInDBBase):
    pass


class ApplicationDraftInDB(ApplicationDraftInDBBase):
    pass


# Schémas pour l'historique
class ApplicationHistoryBase(BaseModel):
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    notes: Optional[str] = None


class ApplicationHistoryCreate(ApplicationHistoryBase):
    application_id: UUID
    changed_by: Optional[UUID] = None


class ApplicationHistoryInDBBase(ApplicationHistoryBase):
    id: UUID
    application_id: UUID
    changed_by: Optional[UUID] = None
    changed_at: datetime

    class Config:
        from_attributes = True


class ApplicationHistory(ApplicationHistoryInDBBase):
    pass


class ApplicationHistoryInDB(ApplicationHistoryInDBBase):
    pass


# Schémas pour les réponses API
class ApplicationResponse(BaseModel):
    """Réponse pour les endpoints d'application."""
    success: bool
    message: str
    data: Optional[Application] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Candidature créée avec succès",
                "data": {
                    "id": "00000000-0000-0000-0000-0000000000AA",
                    "candidate_id": "00000000-0000-0000-0000-000000000001",
                    "job_offer_id": "00000000-0000-0000-0000-0000000000BB",
                    "status": "pending",
                    "created_at": "2025-09-22T10:00:00Z",
                    "updated_at": "2025-09-22T10:00:00Z"
                }
            }
        }


class ApplicationListResponse(BaseModel):
    """Réponse pour la liste des applications."""
    success: bool
    message: str
    data: List[Application]
    total: int
    page: int
    per_page: int

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "1 candidature(s) trouvée(s)",
                "data": [
                    {
                        "id": "00000000-0000-0000-0000-0000000000AA",
                        "candidate_id": "00000000-0000-0000-0000-000000000001",
                        "job_offer_id": "00000000-0000-0000-0000-0000000000BB",
                        "status": "pending",
                        "created_at": "2025-09-22T10:00:00Z",
                        "updated_at": "2025-09-22T10:00:00Z"
                    }
                ],
                "total": 1,
                "page": 1,
                "per_page": 100
            }
        }


class ApplicationDocumentResponse(BaseModel):
    """Réponse pour les documents d'application."""
    success: bool
    message: str
    data: Optional[ApplicationDocument] = None


class ApplicationDocumentListResponse(BaseModel):
    """Réponse pour la liste des documents d'application."""
    success: bool
    message: str
    data: List[ApplicationDocument]
    total: int


class ApplicationDocumentWithDataResponse(BaseModel):
    """Réponse pour un document avec ses données binaires."""
    success: bool
    message: str
    data: Optional[ApplicationDocumentWithData] = None


# Schémas pour l'upload de fichiers
class FileUploadRequest(BaseModel):
    """Schéma pour l'upload d'un fichier PDF."""
    document_type: str = Field(..., description="Type de document: cover_letter, cv, certificats, diplome")
    file_name: str = Field(..., description="Nom du fichier PDF")
    file_data: str = Field(..., description="Contenu du fichier PDF encodé en base64")

    @validator('document_type')
    def validate_document_type(cls, v):
        allowed_types = ['cover_letter', 'cv', 'certificats', 'diplome']
        if v not in allowed_types:
            raise ValueError(f"Type de document invalide. Types autorisés: {allowed_types}")
        return v

    @validator('file_name')
    def validate_file_name(cls, v):
        if not v.lower().endswith('.pdf'):
            raise ValueError("Le nom de fichier doit se terminer par .pdf")
        return v

    @validator('file_data')
    def validate_file_data(cls, v):
        try:
            decoded = base64.b64decode(v)
            if not decoded.startswith(b'%PDF'):
                raise ValueError("Le fichier n'est pas un PDF valide")
            return v
        except Exception as e:
            raise ValueError(f"Données base64 invalides: {str(e)}")


class MultipleFileUploadRequest(BaseModel):
    """Schéma pour l'upload de plusieurs fichiers PDF."""
    files: List[FileUploadRequest] = Field(..., description="Liste des fichiers PDF à uploader")

    @validator('files')
    def validate_files_not_empty(cls, v):
        if not v:
            raise ValueError("Au moins un fichier doit être fourni")
        return v
