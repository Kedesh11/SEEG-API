"""update_interview_slots_add_is_available_location_notes

Revision ID: 20251003_interview
Revises: 20251002_add_user_fields
Create Date: 2025-10-03

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone


# revision identifiers, used by Alembic.
revision = '20251003_interview'
down_revision = '20251002_add_user_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Ajouter les champs is_available, location, et notes à la table interview_slots
    Rendre application_id, candidate_name, et job_title nullable
    Mettre à jour le format de time pour HH:mm:ss
    """
    # Ajouter les nouveaux champs
    op.add_column('interview_slots', sa.Column('is_available', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('interview_slots', sa.Column('location', sa.String(), nullable=True))
    op.add_column('interview_slots', sa.Column('notes', sa.Text(), nullable=True))
    
    # Rendre les champs nullable pour supporter les créneaux disponibles
    op.alter_column('interview_slots', 'application_id', nullable=True)
    op.alter_column('interview_slots', 'candidate_name', nullable=True)
    op.alter_column('interview_slots', 'job_title', nullable=True)
    
    # Mettre à jour les timestamps pour utiliser timezone UTC
    op.alter_column('interview_slots', 'created_at',
                   existing_type=sa.DateTime(timezone=True),
                   server_default=sa.text("timezone('utc'::text, now())"))
    op.alter_column('interview_slots', 'updated_at',
                   existing_type=sa.DateTime(timezone=True),
                   server_default=sa.text("timezone('utc'::text, now())"),
                   onupdate=sa.text("timezone('utc'::text, now())"))
    
    # Ajouter un index sur (date, time) pour améliorer les performances de recherche
    op.create_index('idx_interview_slots_date_time', 'interview_slots', ['date', 'time'])
    
    # Ajouter un index sur is_available
    op.create_index('idx_interview_slots_is_available', 'interview_slots', ['is_available'])


def downgrade() -> None:
    """
    Supprimer les champs ajoutés et restaurer l'état précédent
    """
    # Supprimer les index
    op.drop_index('idx_interview_slots_is_available', table_name='interview_slots')
    op.drop_index('idx_interview_slots_date_time', table_name='interview_slots')
    
    # Restaurer les colonnes non-nullable
    op.alter_column('interview_slots', 'application_id', nullable=False)
    op.alter_column('interview_slots', 'candidate_name', nullable=False)
    op.alter_column('interview_slots', 'job_title', nullable=False)
    
    # Supprimer les nouveaux champs
    op.drop_column('interview_slots', 'notes')
    op.drop_column('interview_slots', 'location')
    op.drop_column('interview_slots', 'is_available')

