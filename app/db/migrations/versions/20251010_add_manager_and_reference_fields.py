"""Add manager and reference fields to applications table

Revision ID: 20251010_add_mgr_ref
Revises: 20251010_add_mtp_questions_to_job_offers
Create Date: 2025-10-10 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251010_add_mgr_ref'
down_revision = '20251010_add_mtp_questions_to_job_offers'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Ajoute les champs de gestion des candidatures internes/externes:
    - has_been_manager: indicateur de management pour candidats internes
    - ref_entreprise, ref_fullname, ref_mail, ref_contact: informations de recommandation pour candidats externes
    """
    # Champ pour les candidats internes
    op.add_column('applications', sa.Column(
        'has_been_manager',
        sa.Boolean(),
        nullable=False,
        server_default='false',
        comment='Indique si le candidat interne a déjà occupé un poste de chef/manager (pertinent pour candidats internes uniquement)'
    ))
    
    # Champs de référence/recommandation pour les candidats externes
    op.add_column('applications', sa.Column(
        'ref_entreprise',
        sa.String(255),
        nullable=True,
        comment='Nom de l\'entreprise/organisation recommandante (obligatoire pour candidats externes)'
    ))
    
    op.add_column('applications', sa.Column(
        'ref_fullname',
        sa.String(255),
        nullable=True,
        comment='Nom complet du référent (obligatoire pour candidats externes)'
    ))
    
    op.add_column('applications', sa.Column(
        'ref_mail',
        sa.String(255),
        nullable=True,
        comment='Adresse e-mail du référent (obligatoire pour candidats externes)'
    ))
    
    op.add_column('applications', sa.Column(
        'ref_contact',
        sa.String(50),
        nullable=True,
        comment='Numéro de téléphone du référent (obligatoire pour candidats externes)'
    ))


def downgrade() -> None:
    """Supprime les champs ajoutés pour les candidatures internes/externes."""
    op.drop_column('applications', 'ref_contact')
    op.drop_column('applications', 'ref_mail')
    op.drop_column('applications', 'ref_fullname')
    op.drop_column('applications', 'ref_entreprise')
    op.drop_column('applications', 'has_been_manager')

