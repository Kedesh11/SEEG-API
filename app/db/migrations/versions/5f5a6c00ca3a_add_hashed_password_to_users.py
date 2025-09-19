"""add_hashed_password_to_users

Revision ID: 5f5a6c00ca3a
Revises: improve_relations_perf
Create Date: 2025-09-19 14:48:15.730736

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5f5a6c00ca3a'
down_revision = 'improve_relations_perf'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ajouter le champ hashed_password à la table users
    op.add_column('users', sa.Column('hashed_password', sa.String(), nullable=False, server_default=''))


def downgrade() -> None:
    # Supprimer le champ hashed_password de la table users
    op.drop_column('users', 'hashed_password')
