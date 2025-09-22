"""
Enforce user roles: default 'candidate' and CHECK constraint

Revision ID: 20250922_000001_enforce_user_roles_default_and_check
Revises: 20250918_165241_improve_relations_and_performance
Create Date: 2025-09-22 00:00:01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20250922_roles_check'
down_revision: Union[str, None] = '5f5a6c00ca3a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Normaliser les valeurs NULL existantes en 'candidate'
    op.execute("UPDATE users SET role = 'candidate' WHERE role IS NULL")

    # 2) Définir la valeur par défaut à 'candidate'
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'candidate'")

    # 3) Ajouter une contrainte CHECK sur les rôles permis
    # Supprimer l'ancienne si elle existe (idempotence partielle)
    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'users_role_check'
        ) THEN
            ALTER TABLE users DROP CONSTRAINT users_role_check;
        END IF;
    END$$;
    """)
    op.execute(
        "ALTER TABLE users ADD CONSTRAINT users_role_check CHECK (role IN ('candidate','recruiter','admin','observer'))"
    )

    # 4) S'assurer que la colonne est NOT NULL
    op.execute("ALTER TABLE users ALTER COLUMN role SET NOT NULL")


def downgrade() -> None:
    # Revenir en arrière: enlever la contrainte CHECK et la valeur par défaut
    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'users_role_check'
        ) THEN
            ALTER TABLE users DROP CONSTRAINT users_role_check;
        END IF;
    END$$;
    """)
    op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT")
    # ne pas remettre les NULL automatiquement 