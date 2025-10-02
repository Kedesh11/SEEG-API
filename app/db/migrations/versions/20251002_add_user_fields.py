"""Add email_verified, last_login, is_active to users table

Revision ID: 20251002_add_user_fields
Revises: 21bf595b762e
Create Date: 2025-10-02 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251002_add_user_fields'
down_revision = '21bf595b762e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Ajout des nouveaux champs au modèle User"""
    
    # Ajouter email_verified (par défaut False)
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='false'))
    
    # Ajouter last_login (nullable car peut être NULL)
    op.add_column('users', sa.Column('last_login', sa.DateTime(timezone=True), nullable=True))
    
    # Ajouter is_active (par défaut True)
    op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))


def downgrade() -> None:
    """Suppression des champs ajoutés"""
    
    op.drop_column('users', 'is_active')
    op.drop_column('users', 'last_login')
    op.drop_column('users', 'email_verified')

