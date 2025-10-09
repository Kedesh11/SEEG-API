"""merge multiple heads to create single migration path

Revision ID: 20251009_merge_heads_final
Revises: 20251003_interview, add_perf_idx_001, 20251008_internal_external
Create Date: 2025-10-09

Fusionne toutes les branches de migrations pour créer un chemin unique.
"""
from alembic import op  # noqa: F401


# Révisions Alembic
revision = "20251009_merge_heads_final"
down_revision = ("add_perf_idx_001", "20251008_internal_external")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge uniquement, pas de changement de schéma
    pass


def downgrade() -> None:
    # Inversion du merge: pas d'action requise
    pass


