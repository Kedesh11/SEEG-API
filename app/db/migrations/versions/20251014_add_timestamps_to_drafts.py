"""add timestamps to application_drafts

Revision ID: 20251014_timestamps_drafts
Revises: 
Create Date: 2025-10-14 17:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251014_timestamps_drafts'
down_revision = None  # Mettre l'ID de la dernière migration ici
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Ajoute les colonnes created_at à la table application_drafts si elle n'existe pas déjà.
    La colonne updated_at existe déjà normalement.
    """
    # Vérifier et ajouter created_at si elle n'existe pas
    op.execute("""
        DO $$ 
        BEGIN
            -- Ajouter created_at si elle n'existe pas
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='application_drafts' AND column_name='created_at'
            ) THEN
                ALTER TABLE application_drafts 
                ADD COLUMN created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW();
            END IF;
            
            -- S'assurer que updated_at existe et a les bonnes propriétés
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='application_drafts' AND column_name='updated_at'
            ) THEN
                ALTER TABLE application_drafts 
                ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW();
            END IF;
        END $$;
    """)
    
    # Ajouter un commentaire sur les colonnes
    op.execute("""
        COMMENT ON COLUMN application_drafts.created_at IS 'Date et heure de création du brouillon';
        COMMENT ON COLUMN application_drafts.updated_at IS 'Date et heure de dernière modification du brouillon';
    """)


def downgrade() -> None:
    """
    Supprime les colonnes created_at de la table application_drafts.
    Note: updated_at existait déjà, donc on ne la supprime pas dans le downgrade.
    """
    # Supprimer created_at seulement si elle a été ajoutée par cette migration
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='application_drafts' AND column_name='created_at'
            ) THEN
                ALTER TABLE application_drafts DROP COLUMN created_at;
            END IF;
        END $$;
    """)

