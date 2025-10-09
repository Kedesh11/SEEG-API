"""add internal external system

Revision ID: 20251008_internal_external
Revises: 
Create Date: 2025-10-08

Ajout du système complet de gestion des candidats et offres INTERNES/EXTERNES :
- is_internal_candidate sur users (candidat interne si matricule présent)
- is_internal_only sur job_offers (offre réservée aux internes uniquement)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251008_internal_external'
down_revision = '20251003_interview'  # À ajuster selon votre dernière migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Ajoute le système complet de gestion INTERNES/EXTERNES.
    
    1. users.is_internal_candidate :
       - true = Employé SEEG (avec matricule)
       - false = Candidat externe (sans matricule)
    
    2. job_offers.is_internal_only :
       - true = Offre réservée aux employés SEEG uniquement
       - false = Offre accessible à tous (internes + externes)
    """
    
    # 1. Ajouter is_internal_candidate à la table users
    op.add_column('users', 
        sa.Column('is_internal_candidate', sa.Boolean(), nullable=False, server_default='false')
    )
    
    # 2. Ajouter is_internal_only à la table job_offers
    op.add_column('job_offers', 
        sa.Column('is_internal_only', sa.Boolean(), nullable=False, server_default='false')
    )
    
    # 3. Créer les indexes pour optimiser les requêtes de filtrage
    op.create_index(
        'ix_users_is_internal_candidate', 
        'users', 
        ['is_internal_candidate', 'role'],
        unique=False
    )
    
    op.create_index(
        'ix_job_offers_is_internal_only', 
        'job_offers', 
        ['is_internal_only', 'status'],
        unique=False
    )
    
    # 4. Mettre à jour les données existantes
    # Les candidats avec matricule deviennent automatiquement "internes"
    op.execute("""
        UPDATE users 
        SET is_internal_candidate = true 
        WHERE role = 'candidate' 
        AND matricule IS NOT NULL
    """)
    
    # Optionnel : Toutes les offres existantes sont accessibles à tous par défaut
    # (is_internal_only reste à false)


def downgrade() -> None:
    """Supprimer les colonnes et indexes ajoutés"""
    
    # Supprimer les indexes
    op.drop_index('ix_job_offers_is_internal_only', table_name='job_offers')
    op.drop_index('ix_users_is_internal_candidate', table_name='users')
    
    # Supprimer les colonnes
    op.drop_column('job_offers', 'is_internal_only')
    op.drop_column('users', 'is_internal_candidate')

