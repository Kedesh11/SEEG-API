"""Convert users.matricule to INTEGER

Revision ID: 20250922_users_matricule_int
Revises: 20250922_roles_check
Create Date: 2025-09-22 11:20:00
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250922_users_matricule_int'
down_revision = '20250922_roles_check'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Drop unique index to allow type change
    op.drop_index(op.f('ix_users_matricule'), table_name='users')

    # 1) Normaliser: mettre NULL pour les matricules non numériques
    op.execute(
        """
        UPDATE users
        SET matricule = NULL
        WHERE matricule IS NOT NULL
          AND TRIM(matricule) <> ''
          AND matricule !~ '^[0-9]+$'
        """
    )

    # 2) Convert existing values using safe cast (blank -> NULL)
    op.execute(
        """
        ALTER TABLE users
        ALTER COLUMN matricule TYPE INTEGER
        USING NULLIF(TRIM(matricule), '')::INTEGER
        """
    )

    # Recreate unique index on integer column
    op.create_index(op.f('ix_users_matricule'), 'users', ['matricule'], unique=True)


def downgrade() -> None:
    # Drop index first
    op.drop_index(op.f('ix_users_matricule'), table_name='users')

    # Revert to VARCHAR
    op.execute(
        """
        ALTER TABLE users
        ALTER COLUMN matricule TYPE VARCHAR
        USING matricule::VARCHAR
        """
    )

    # Recreate unique index on varchar
    op.create_index(op.f('ix_users_matricule'), 'users', ['matricule'], unique=True) 