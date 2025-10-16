"""
Endpoints pour la gestion des emails
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
from datetime import datetime

from app.db.database import get_db
from app.services.email import EmailService
from app.schemas.email import (
    EmailSend, InterviewEmailRequest, EmailResponse, 
    EmailLogsResponse, EmailLogResponse
)
from app.core.dependencies import get_current_user
from app.models.user import User
from app.core.exceptions import EmailError

logger = structlog.get_logger(__name__)
router = APIRouter()


def safe_log(level: str, message: str, **kwargs):
    """Log avec gestion d'erreur pour Ã©viter les problÃ¨mes de handler."""
    try:
        getattr(logger, level)(message, **kwargs)
    except (TypeError, AttributeError):
        print(f"{level.upper()}: {message} - {kwargs}")


@router.post("/send", response_model=EmailResponse, status_code=status.HTTP_201_CREATED)  # Standard REST : 201 pour création de ressource
async def send_email(
    email_data: EmailSend,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Envoyer un email gÃ©nÃ©rique
    
    - **to**: Adresse email du destinataire
    - **subject**: Sujet de l'email
    - **body**: Corps de l'email (texte)
    - **html_body**: Corps de l'email (HTML, optionnel)
    - **cc**: Copie carbone (optionnel)
    - **bcc**: Copie carbone cachÃ©e (optionnel)
    """
    try:
        email_service = EmailService(db)
        
        success = await email_service.send_email(
            to=email_data.to,
            subject=email_data.subject,
            body=email_data.body,
            html_body=email_data.html_body,
            cc=email_data.cc,
            bcc=email_data.bcc
        )
        
        if success:
            safe_log("info", "Email envoyé avec succès", to=email_data.to, subject=email_data.subject)
            return EmailResponse(
                success=True,
                message="Email envoyé avec succès",
                message_id=None  # Azure Communication Services ne retourne pas de message_id
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ã‰chec de l'envoi de l'email"
            )
            
    except EmailError as e:
        safe_log("error", "Erreur lors de l'envoi de l'email", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'envoi de l'email: {str(e)}"
        )
    except Exception as e:
        safe_log("error", "Erreur inattendue lors de l'envoi de l'email", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur"
        )


@router.post("/send-interview-email", response_model=EmailResponse, status_code=status.HTTP_201_CREATED)  # Standard REST : 201 pour création de ressource
async def send_interview_email(
    email_data: InterviewEmailRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Envoyer un email d'invitation Ã  un entretien
    
    - **to**: Email du candidat
    - **candidate_full_name**: Nom complet du candidat
    - **job_title**: Titre du poste
    - **date**: Date de l'entretien (YYYY-MM-DD)
    - **time**: Heure de l'entretien (HH:MM)
    - **location**: Lieu de l'entretien (optionnel)
    - **application_id**: ID de la candidature (optionnel)
    - **additional_notes**: Notes additionnelles (optionnel)
    """
    try:
        email_service = EmailService(db)
        
        # Construire le HTML de l'email d'entretien
        date_obj = datetime.strptime(f"{email_data.date}T{email_data.time}", '%Y-%m-%dT%H:%M')
        formatted_date = date_obj.strftime('%d/%m/%Y')
        formatted_time = email_data.time
        
        subject = f"Convocation Ã  l'entretien â€“ {email_data.job_title}"
        
        # Corps texte
        body = f"""
Madame/Monsieur {email_data.candidate_full_name},

Nous avons le plaisir de vous informer que votre candidature pour le poste de {email_data.job_title} a retenu notre attention.

Nous vous invitons Ã  un entretien de recrutement qui se tiendra :

Date : {formatted_date}
Heure : {formatted_time}
Lieu : {email_data.location}

Nous vous prions de bien vouloir vous prÃ©senter 15 minutes avant l'heure de l'entretien, muni(e) de votre carte professionnelle, badge, ou de toute autre piÃ¨ce d'identitÃ© en cours de validitÃ©.

{f"Notes additionnelles: {email_data.additional_notes}" if email_data.additional_notes else ""}

Nous restons Ã  votre disposition pour toutes informations complÃ©mentaires.

Cordialement,
L'Ã©quipe RH - SEEG
        """
        
        # Corps HTML
        html_body = f"""
        <div style="font-family: ui-serif, Georgia, 'Times New Roman', serif; color:#000; max-width:760px; margin:0 auto;">
            <p>Madame/Monsieur {email_data.candidate_full_name},</p>
            <p>Nous avons le plaisir de vous informer que votre candidature pour le poste de <strong>{email_data.job_title}</strong> a retenu notre attention.</p>
            <p>Nous vous invitons Ã  un entretien de recrutement qui se tiendra :</p>
            <p><strong>Date :</strong> {formatted_date}<br/>
            <strong>Heure :</strong> {formatted_time}<br/>
            <strong>Lieu :</strong> {email_data.location}</p>
            <p>Nous vous prions de bien vouloir vous prÃ©senter <strong>15 minutes avant l'heure de l'entretien</strong>, muni(e) de votre carte professionnelle, badge, ou de toute autre piÃ¨ce d'identitÃ© en cours de validitÃ©.</p>
            {f"<p><strong>Notes additionnelles:</strong> {email_data.additional_notes}</p>" if email_data.additional_notes else ""}
            <p>Nous restons Ã  votre disposition pour toutes informations complÃ©mentaires.</p>
            <p>Cordialement,<br/>L'Ã©quipe RH - SEEG</p>
        </div>
        """
        
        success = await email_service.send_email(
            to=email_data.to,
            subject=subject,
            body=body,
            html_body=html_body
        )
        
        if success:
            safe_log(
                "info",
                "Email d'entretien envoyÃ© avec succÃ¨s", 
                to=email_data.to, 
                candidate=email_data.candidate_full_name,
                job_title=email_data.job_title,
                date=email_data.date,
                time=email_data.time
            )
            return EmailResponse(
                success=True,
                message="Email d'entretien envoyé avec succès",
                message_id=None  # Azure Communication Services ne retourne pas de message_id
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ã‰chec de l'envoi de l'email d'entretien"
            )
            
    except EmailError as e:
        safe_log("error", "Erreur lors de l'envoi de l'email d'entretien", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'envoi de l'email d'entretien: {str(e)}"
        )
    except ValueError as e:
        safe_log("warning", "Erreur de validation des donnÃ©es email", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur de validation: {str(e)}"
        )
    except Exception as e:
        safe_log("error", "Erreur inattendue lors de l'envoi de l'email d'entretien", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur"
        )


@router.get("/logs", response_model=EmailLogsResponse)
async def get_email_logs(
    skip: int = Query(0, ge=0, description="Nombre d'Ã©lÃ©ments Ã  ignorer"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre d'Ã©lÃ©ments Ã  retourner"),
    status_filter: Optional[str] = Query(None, description="Filtrer par statut (sent, failed)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    RÃ©cupÃ©rer les logs des emails envoyÃ©s
    
    - **skip**: Nombre d'Ã©lÃ©ments Ã  ignorer (pagination)
    - **limit**: Nombre d'Ã©lÃ©ments Ã  retourner (max 1000)
    - **status_filter**: Filtrer par statut (sent, failed)
    """
    try:
        email_service = EmailService(db)
        
        logs_data = await email_service.get_email_logs(
            skip=skip,
            limit=limit,
            category=status_filter
        )
        
        # Conversion des donnÃ©es pour le schÃ©ma de rÃ©ponse
        logs = [
            EmailLogResponse(
                id=log["id"],
                recipient_email=log["recipient_email"],
                subject=log["subject"],
                status=log["status"],
                sent_at=log["sent_at"],
                error_message=log["error_message"]
            )
            for log in logs_data["items"]
        ]
        
        return EmailLogsResponse(
            data=logs,
            total=logs_data["total"],
            skip=logs_data["skip"],
            limit=logs_data["limit"],
            has_more=logs_data["has_more"]
        )
        
    except Exception as e:
        safe_log("error", "Erreur lors de la rÃ©cupÃ©ration des logs d'email", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur"
        )
