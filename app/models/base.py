"""
Modèles de base pour tous les modèles SQLAlchemy.
Implémente les mixins communs et la configuration de base.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Column, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import as_declarative, declared_attr, Mapped, mapped_column


@as_declarative()
class Base:
    """Classe de base pour tous les modèles SQLAlchemy."""
    
    id: Any
    __name__: str
    
    # Générer automatiquement le nom de la table
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower()


class UUIDMixin:
    """Mixin pour ajouter un ID UUID à un modèle."""
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="Identifiant unique UUID"
    )


class TimestampMixin:
    """Mixin pour ajouter des timestamps de création et modification."""
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Date et heure de création"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Date et heure de dernière modification"
    )


class SoftDeleteMixin:
    """Mixin pour implémenter la suppression logique."""
    
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Date et heure de suppression logique"
    )
    
    is_deleted: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Indique si l'enregistrement est supprimé logiquement"
    )


class AuditMixin:
    """Mixin pour ajouter des informations d'audit."""
    
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="ID de l'utilisateur qui a créé l'enregistrement"
    )
    
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="ID de l'utilisateur qui a modifié l'enregistrement"
    )


class BaseModel(Base, UUIDMixin, TimestampMixin):
    """Modèle de base avec UUID et timestamps."""
    
    __abstract__ = True


class AuditableModel(BaseModel, AuditMixin):
    """Modèle de base avec audit complet."""
    
    __abstract__ = True


class SoftDeletableModel(BaseModel, SoftDeleteMixin):
    """Modèle de base avec suppression logique."""
    
    __abstract__ = True


class FullAuditModel(BaseModel, AuditMixin, SoftDeleteMixin):
    """Modèle de base avec audit complet et suppression logique."""
    
    __abstract__ = True
