"""Create access_requests table for managing access approval workflow

Revision ID: 20251010_access_requests
Revises: 20251010_add_user_auth
Create Date: 2025-10-10 17:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = '20251010_access_requests'
down_revision = '20251010_add_user_auth'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Crée la table access_requests pour gérer les demandes d'accès.
    
    Cette table stocke les demandes d'accès des candidats internes sans email @seeg-gabon.com
    qui nécessitent une validation par un recruteur avant de pouvoir se connecter.
    """
    
    # Créer la table access_requests
    op.create_table(
        'access_requests',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, comment='Référence vers l\'utilisateur demandeur'),
        sa.Column('email', sa.String(), nullable=False, comment='Email du demandeur'),
        sa.Column('first_name', sa.String(), nullable=True, comment='Prénom du demandeur'),
        sa.Column('last_name', sa.String(), nullable=True, comment='Nom du demandeur'),
        sa.Column('phone', sa.String(), nullable=True, comment='Téléphone du demandeur'),
        sa.Column('matricule', sa.String(), nullable=True, comment='Matricule SEEG (candidats internes)'),
        sa.Column('request_type', sa.String(), nullable=False, server_default='internal_no_seeg_email', comment='Type de demande'),
        sa.Column('status', sa.String(), nullable=False, server_default='pending', comment='Statut de la demande: pending, approved, rejected'),
        sa.Column('rejection_reason', sa.Text(), nullable=True, comment='Motif de refus (si status=rejected)'),
        sa.Column('viewed', sa.Boolean(), nullable=False, server_default='false', comment='Demande vue par un recruteur'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()'), comment='Date de création de la demande'),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True, comment='Date de traitement de la demande'),
        sa.Column('reviewed_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, comment='Recruteur qui a traité la demande'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='Date de dernière mise à jour de la demande')
    )
    
    # Ajouter contrainte CHECK sur status
    op.create_check_constraint(
        'chk_access_requests_status',
        'access_requests',
        "status IN ('pending', 'approved', 'rejected')"
    )
    
    # Créer les index pour les performances
    op.create_index(
        'idx_access_requests_status',
        'access_requests',
        ['status'],
        unique=False
    )
    
    op.create_index(
        'idx_access_requests_user_id',
        'access_requests',
        ['user_id'],
        unique=False
    )
    
    op.create_index(
        'idx_access_requests_viewed',
        'access_requests',
        ['viewed'],
        unique=False
    )
    
    # Index composite pour filtrage (status, viewed)
    op.create_index(
        'idx_access_requests_status_viewed',
        'access_requests',
        ['status', 'viewed'],
        unique=False
    )
    
    # Index sur created_at pour tri par date (DESC)
    op.create_index(
        'idx_access_requests_created_at',
        'access_requests',
        [sa.text('created_at DESC')],
        unique=False
    )


def downgrade() -> None:
    """Supprime la table access_requests et ses index."""
    
    # Supprimer les index
    op.drop_index('idx_access_requests_created_at', table_name='access_requests')
    op.drop_index('idx_access_requests_status_viewed', table_name='access_requests')
    op.drop_index('idx_access_requests_viewed', table_name='access_requests')
    op.drop_index('idx_access_requests_user_id', table_name='access_requests')
    op.drop_index('idx_access_requests_status', table_name='access_requests')
    
    # Supprimer la contrainte CHECK
    op.drop_constraint('chk_access_requests_status', 'access_requests', type_='check')
    
    # Supprimer la table
    op.drop_table('access_requests')

