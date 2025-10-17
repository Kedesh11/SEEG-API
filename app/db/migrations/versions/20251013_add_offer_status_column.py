"""Add offer_status column to job_offers

Revision ID: 20251013_add_offer_status
Revises: 20251013_add_mtp_questions_to_job_offers
Create Date: 2025-10-13 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251013_add_offer_status'
down_revision = '20251010_add_mtp_questions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Ajouter la colonne offer_status pour gérer 3 types d'offres:
    - 'tous': Accessible à tous (internes + externes) - PAR DÉFAUT
    - 'interne': Réservée aux candidats internes SEEG uniquement
    - 'externe': Réservée aux candidats externes uniquement
    
    Supprime l'ancienne colonne is_internal_only.
    """
    
    # Ajouter la nouvelle colonne offer_status
    op.add_column('job_offers', 
        sa.Column('offer_status', sa.String(), nullable=False, server_default='tous')
    )
    
    # Créer un index pour optimiser les requêtes
    op.create_index(
        'ix_job_offers_offer_status', 
        'job_offers', 
        ['offer_status', 'status'],
        unique=False
    )
    
    # Migrer les données existantes de is_internal_only vers offer_status
    # is_internal_only=true → offer_status='interne'
    # is_internal_only=false → offer_status='tous'
    op.execute("""
        UPDATE job_offers 
        SET offer_status = CASE 
            WHEN is_internal_only = true THEN 'interne'
            ELSE 'tous'
        END
    """)
    
    # Supprimer l'ancien index de is_internal_only (s'il existe)
    try:
        op.drop_index('ix_job_offers_is_internal_only', table_name='job_offers')
    except Exception:
        pass  # L'index n'existe peut-être pas
    
    # Supprimer l'ancienne colonne is_internal_only
    op.drop_column('job_offers', 'is_internal_only')


def downgrade() -> None:
    """Supprimer la colonne offer_status et restaurer is_internal_only"""
    
    # Recréer la colonne is_internal_only
    op.add_column('job_offers',
        sa.Column('is_internal_only', sa.Boolean(), nullable=False, server_default='false')
    )
    
    # Restaurer les données dans is_internal_only depuis offer_status
    op.execute("""
        UPDATE job_offers 
        SET is_internal_only = CASE 
            WHEN offer_status = 'interne' THEN true
            ELSE false
        END
    """)
    
    # Recréer l'index
    op.create_index(
        'ix_job_offers_is_internal_only', 
        'job_offers', 
        ['is_internal_only', 'status'],
        unique=False
    )
    
    # Supprimer l'index de offer_status
    op.drop_index('ix_job_offers_offer_status', table_name='job_offers')
    
    # Supprimer la colonne offer_status
    op.drop_column('job_offers', 'offer_status')

