"""
Schémas Pydantic pour les demandes d'accès (access_requests).
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID


class AccessRequestBase(BaseModel):
    """Schéma de base pour les demandes d'accès."""
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    matricule: Optional[str] = None
    request_type: str = "internal_no_seeg_email"
    status: str = "pending"
    viewed: bool = False


class AccessRequestCreate(AccessRequestBase):
    """Schéma pour créer une demande d'accès."""
    user_id: UUID
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "00000000-0000-0000-0000-000000000001",
                "email": "jean.perso@gmail.com",
                "first_name": "Jean",
                "last_name": "Dupont",
                "phone": "+24106223344",
                "matricule": "123456",
                "request_type": "internal_no_seeg_email",
                "status": "pending",
                "viewed": False
            }
        }


class AccessRequestUpdate(BaseModel):
    """Schéma pour mettre à jour une demande d'accès."""
    status: Optional[str] = None
    rejection_reason: Optional[str] = None
    viewed: Optional[bool] = None
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[UUID] = None
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        if v is not None and v not in ['pending', 'approved', 'rejected']:
            raise ValueError("Le status doit être 'pending', 'approved' ou 'rejected'")
        return v


class AccessRequestApprove(BaseModel):
    """Schéma pour approuver une demande d'accès."""
    request_id: UUID = Field(..., description="ID de la demande à approuver")
    
    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "00000000-0000-0000-0000-000000000001"
            }
        }


class AccessRequestReject(BaseModel):
    """Schéma pour refuser une demande d'accès."""
    request_id: UUID = Field(..., description="ID de la demande à refuser")
    rejection_reason: str = Field(..., min_length=20, description="Motif du refus (minimum 20 caractères)")
    
    @field_validator('rejection_reason')
    @classmethod
    def validate_rejection_reason(cls, v):
        if len(v.strip()) < 20:
            raise ValueError("Le motif de refus doit contenir au moins 20 caractères")
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "00000000-0000-0000-0000-000000000001",
                "rejection_reason": "Matricule invalide ou informations non vérifiables. Veuillez contacter le service RH."
            }
        }


class AccessRequestWithUser(AccessRequestBase):
    """Schéma pour une demande d'accès avec informations utilisateur complètes."""
    id: UUID
    user_id: UUID
    rejection_reason: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[UUID] = None
    
    # Informations utilisateur supplémentaires (via JOIN)
    user_date_of_birth: Optional[date] = Field(None, alias="date_of_birth")
    user_sexe: Optional[str] = Field(None, alias="sexe")
    user_adresse: Optional[str] = Field(None, alias="adresse")
    user_statut: Optional[str] = Field(None, alias="user_statut")
    
    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "id": "00000000-0000-0000-0000-000000000001",
                "user_id": "00000000-0000-0000-0000-000000000002",
                "email": "jean.perso@gmail.com",
                "first_name": "Jean",
                "last_name": "Dupont",
                "phone": "+24106223344",
                "matricule": "123456",
                "request_type": "internal_no_seeg_email",
                "status": "pending",
                "rejection_reason": None,
                "viewed": False,
                "created_at": "2025-01-10T10:30:00Z",
                "reviewed_at": None,
                "reviewed_by": None,
                "date_of_birth": "1990-05-15",
                "sexe": "M",
                "adresse": "123 Rue Example",
                "user_statut": "en_attente"
            }
        }
    }


class AccessRequestResponse(BaseModel):
    """Schéma de réponse pour une demande d'accès."""
    success: bool
    message: str
    data: Optional[AccessRequestWithUser] = None


class AccessRequestListResponse(BaseModel):
    """Schéma de réponse pour la liste des demandes d'accès."""
    success: bool
    message: str
    data: List[AccessRequestWithUser]
    total: int
    pending_count: int = Field(..., description="Nombre de demandes en attente")
    unviewed_count: int = Field(..., description="Nombre de demandes non vues (pour le badge)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "2 demande(s) d'accès trouvée(s)",
                "data": [],
                "total": 2,
                "pending_count": 1,
                "unviewed_count": 1
            }
        }


class MatriculeVerifyRequest(BaseModel):
    """Schéma pour vérifier un matricule."""
    matricule: int = Field(..., description="Matricule SEEG à vérifier")
    
    class Config:
        json_schema_extra = {
            "example": {
                "matricule": 123456
            }
        }


class MatriculeVerifyResponse(BaseModel):
    """Schéma de réponse pour la vérification de matricule."""
    valid: bool = Field(..., description="True si le matricule existe et est actif")
    message: str = Field(..., description="Message explicatif")
    agent_info: Optional[dict] = Field(None, description="Informations de l'agent SEEG (si trouvé)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "valid": True,
                "message": "Matricule valide",
                "agent_info": {
                    "matricule": "123456",
                    "first_name": "Jean",
                    "last_name": "Dupont",
                    "email": "jean.dupont@seeg-gabon.com"
                }
            }
        }

