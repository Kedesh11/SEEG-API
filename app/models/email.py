"""
Modèles liés aux emails.
Respecte le principe de responsabilité unique (Single Responsibility Principle).
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import (
    Column, DateTime, ForeignKey, String, Text,
    Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class EmailLog(BaseModel):
    """
    Modèle des logs d'emails.
    Représente l'historique des emails envoyés.
    """
    
    __tablename__ = "email_logs"
    
    # Clé étrangère (optionnelle)
    application_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="SET NULL"),
        nullable=True,
        comment="ID de la candidature liée"
    )
    
    # Informations de l'email
    to: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Destinataire de l'email"
    )
    
    subject: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Sujet de l'email"
    )
    
    html: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Contenu HTML de l'email"
    )
    
    # Métadonnées
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Catégorie de l'email"
    )
    
    provider_message_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="ID du message du fournisseur d'email"
    )
    
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Date et heure d'envoi"
    )
    
    # Métadonnées supplémentaires
    metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Métadonnées supplémentaires"
    )
    
    # Relations
    application: Mapped[Optional["Application"]] = relationship("Application")
    
    # Contraintes
    __table_args__ = (
        Index("idx_email_logs_application", "application_id"),
        Index("idx_email_logs_category", "category"),
        Index("idx_email_logs_sent_at", "sent_at"),
        Index("idx_email_logs_to", "to"),
    )
    
    def __repr__(self) -> str:
        return f"<EmailLog(id={self.id}, to={self.to}, subject={self.subject}, sent_at={self.sent_at})>"
