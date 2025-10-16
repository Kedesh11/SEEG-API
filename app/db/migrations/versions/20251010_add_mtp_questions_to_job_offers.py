"""Add MTP questions to job_offers table

Revision ID: 20251010_add_mtp_questions_to_job_offers
Revises: add_perf_idx_001
Create Date: 2025-10-10 14:00:00.000000

Description:
    Ajout de trois colonnes pour les questions MTP (Métier, Talent, Paradigme)
    utilisées lors de l'évaluation des candidats pour les offres internes et externes.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251010_add_mtp_questions_to_job_offers'
down_revision = 'add_perf_idx_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Ajout des colonnes MTP au modèle JobOffer.
    
    Ces colonnes permettent aux recruteurs de définir trois types de questions
    lors de la création d'une offre :
    - question_metier : Évalue les compétences techniques et opérationnelles
    - question_talent : Évalue les aptitudes personnelles et le potentiel
    - question_paradigme : Évalue la vision, les valeurs et la compatibilité culturelle
    """
    
    # Ajouter question_metier (nullable pour permettre création sans ces questions)
    op.add_column(
        'job_offers',
        sa.Column('question_metier', sa.Text(), nullable=True,
                  comment='Question évaluant les compétences techniques et opérationnelles')
    )
    
    # Ajouter question_talent
    op.add_column(
        'job_offers',
        sa.Column('question_talent', sa.Text(), nullable=True,
                  comment='Question évaluant les aptitudes personnelles et le potentiel')
    )
    
    # Ajouter question_paradigme
    op.add_column(
        'job_offers',
        sa.Column('question_paradigme', sa.Text(), nullable=True,
                  comment='Question évaluant la vision, les valeurs et la compatibilité culturelle')
    )


def downgrade() -> None:
    """
    Suppression des colonnes MTP en cas de rollback.
    """
    
    op.drop_column('job_offers', 'question_paradigme')
    op.drop_column('job_offers', 'question_talent')
    op.drop_column('job_offers', 'question_metier')

