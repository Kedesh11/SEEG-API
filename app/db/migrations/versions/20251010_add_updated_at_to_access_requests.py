"""add_updated_at_to_access_requests

Revision ID: 20251010_add_updated_at
Revises: 20251010_access_requests
Create Date: 2025-10-10 22:32:05.284064

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251010_add_updated_at'
down_revision = '20251010_access_requests'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ajouter la colonne updated_at à la table access_requests
    op.add_column(
        'access_requests',
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='Date de dernière mise à jour de la demande')
    )


def downgrade() -> None:
    # Supprimer la colonne updated_at de la table access_requests
    op.drop_column('access_requests', 'updated_at')
