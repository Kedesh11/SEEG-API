"""Add MTP questions columns to job_offers table

Revision ID: 20251013_add_mtp_questions
Revises: 20251010_add_updated_at
Create Date: 2025-10-13 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251013_add_mtp_questions'
down_revision = '20251010_add_updated_at'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ajouter la colonne JSON MTP aux offres d'emploi
    op.add_column('job_offers', sa.Column('questions_mtp', sa.JSON(), nullable=True, comment="Questions MTP sous forme de tableau auto-incremente"))
    
    # Supprimer les anciennes colonnes MTP individuelles de applications
    # (remplacées par le format JSON dans mtp_answers qui existe déjà)
    old_mtp_columns = [
        'mtp_metier_q1', 'mtp_metier_q2', 'mtp_metier_q3',
        'mtp_talent_q1', 'mtp_talent_q2', 'mtp_talent_q3',
        'mtp_paradigme_q1', 'mtp_paradigme_q2', 'mtp_paradigme_q3'
    ]
    
    for col_name in old_mtp_columns:
        try:
            op.drop_column('applications', col_name)
        except Exception:
            # Colonne peut-être déjà supprimée, continuer
            pass


def downgrade() -> None:
    # Supprimer la colonne MTP de job_offers
    op.drop_column('job_offers', 'questions_mtp')
    
    # Re-créer les anciennes colonnes individuelles de applications (optionnel pour downgrade complet)
    old_mtp_columns = [
        'mtp_metier_q1', 'mtp_metier_q2', 'mtp_metier_q3',
        'mtp_talent_q1', 'mtp_talent_q2', 'mtp_talent_q3',
        'mtp_paradigme_q1', 'mtp_paradigme_q2', 'mtp_paradigme_q3'
    ]
    
    for col_name in old_mtp_columns:
        op.add_column('applications', sa.Column(col_name, sa.Text(), nullable=True))

