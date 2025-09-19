"""
Schémas Pydantic pour les emails
"""
from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List
from datetime import datetime


class EmailBase(BaseModel):
    """Schéma de base pour les emails"""
    to: EmailStr = Field(..., description="Adresse email du destinataire")
    subject: str = Field(..., min_length=1, max_length=255, description="Sujet de l'email")
    body: str = Field(..., min_length=1, description="Corps de l'email (texte)")
    html_body: Optional[str] = Field(None, description="Corps de l'email (HTML)")


class EmailSend(EmailBase):
    """Schéma pour l'envoi d'email"""
    cc: Optional[List[EmailStr]] = Field(None, description="Copie carbone")
    bcc: Optional[List[EmailStr]] = Field(None, description="Copie carbone cachée")


class InterviewEmailRequest(BaseModel):
    """Schéma pour l'envoi d'email d'entretien"""
    to: EmailStr = Field(..., description="Email du destinataire")
    candidate_full_name: str = Field(..., min_length=1, description="Nom complet du candidat")
    job_title: str = Field(..., min_length=1, description="Titre du poste")
    date: str = Field(..., description="Date de l'entretien (YYYY-MM-DD)")
    time: str = Field(..., description="Heure de l'entretien (HH:MM)")
    location: Optional[str] = Field(
        "Salle de réunion du Président du Conseil d'Administration, 9ᵉ étage, siège SEEG, Libreville.",
        description="Lieu de l'entretien"
    )
    application_id: Optional[str] = Field(None, description="ID de la candidature")
    additional_notes: Optional[str] = Field(None, description="Notes additionnelles")

    @validator('date')
    def validate_date(cls, v):
        """Valider le format de date"""
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('La date doit être au format YYYY-MM-DD')

    @validator('time')
    def validate_time(cls, v):
        """Valider le format d'heure"""
        try:
            # Accepter HH:MM ou HH:MM:SS
            if len(v) == 5:  # HH:MM
                datetime.strptime(v, '%H:%M')
            elif len(v) == 8:  # HH:MM:SS
                datetime.strptime(v, '%H:%M:%S')
            else:
                raise ValueError('L\'heure doit être au format HH:MM ou HH:MM:SS')
            return v[:5]  # Retourner seulement HH:MM
        except ValueError:
            raise ValueError('L\'heure doit être au format HH:MM ou HH:MM:SS')


class EmailResponse(BaseModel):
    """Schéma de réponse pour l'envoi d'email"""
    success: bool = Field(..., description="Succès de l'envoi")
    message: str = Field(..., description="Message de retour")
    message_id: Optional[str] = Field(None, description="ID du message envoyé")


class EmailLogResponse(BaseModel):
    """Schéma pour les logs d'email"""
    id: str
    recipient_email: str
    subject: str
    status: str
    sent_at: datetime
    error_message: Optional[str] = None


class EmailLogsResponse(BaseModel):
    """Schéma pour la liste des logs d'email"""
    success: bool = True
    message: str = "Logs récupérés avec succès"
    data: List[EmailLogResponse]
    total: int
    skip: int
    limit: int
    has_more: bool
