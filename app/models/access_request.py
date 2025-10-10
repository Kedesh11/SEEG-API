"""
Modèle AccessRequest pour gérer les demandes d'accès à la plateforme.

Les candidats internes sans email @seeg-gabon.com doivent être approuvés 
par un recruteur avant de pouvoir se connecter.
"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.models.base import BaseModel


class AccessRequest(BaseModel):
    """
    Demande d'accès à la plateforme.
    
    Workflow:
    1. Candidat interne s'inscrit sans email @seeg-gabon.com
    2. Compte créé avec statut='en_attente'
    3. AccessRequest créée automatiquement avec status='pending'
    4. Recruteur voit la demande dans son dashboard
    5. Recruteur approuve → statut='actif', status='approved'
       OU
       Recruteur refuse → statut='bloqué', status='rejected'
    """
    __tablename__ = "access_requests"  # type: ignore[assignment]
    
    # Identifiant unique
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Référence vers l'utilisateur demandeur
    user_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False,
        comment="Référence vers l'utilisateur demandeur"
    )
    
    # Informations du demandeur (copiées de users pour faciliter l'affichage)
    email = Column(String, nullable=False, comment="Email du demandeur")
    first_name = Column(String, nullable=True, comment="Prénom du demandeur")
    last_name = Column(String, nullable=True, comment="Nom du demandeur")
    phone = Column(String, nullable=True, comment="Téléphone du demandeur")
    matricule = Column(String, nullable=True, comment="Matricule SEEG")
    
    # Type de demande
    request_type = Column(
        String,
        nullable=False,
        default="internal_no_seeg_email",
        comment="Type de demande: internal_no_seeg_email"
    )
    
    # Statut de la demande
    status = Column(
        String,
        nullable=False,
        default="pending",
        comment="Statut: pending, approved, rejected"
    )
    
    # Motif de refus (si status='rejected')
    rejection_reason = Column(
        Text,
        nullable=True,
        comment="Motif de refus saisi par le recruteur"
    )
    
    # Système de notification (badge)
    viewed = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Demande vue par un recruteur (pour le badge de notification)"
    )
    
    # Dates et traçabilité
    created_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        comment="Date de création de la demande"
    )  # type: ignore[assignment]
    
    reviewed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Date de traitement de la demande (approbation ou refus)"
    )
    
    # Recruteur qui a traité la demande
    reviewed_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Recruteur qui a traité la demande"
    )

    # Ajout d'un champ updated_at facultatif pour alignement avec certaines requêtes legacy
    updated_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Date de dernière mise à jour de la demande"
    )
    
    # Relations
    user = relationship("User", foreign_keys=[user_id], backref="access_request")
    reviewer = relationship("User", foreign_keys=[reviewed_by], backref="reviewed_access_requests")

