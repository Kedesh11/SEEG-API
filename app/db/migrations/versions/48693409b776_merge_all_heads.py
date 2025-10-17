"""merge_all_heads

Revision ID: 48693409b776
Revises: 20251010_add_updated_at, 20251013_add_offer_status, 20251014_timestamps_drafts
Create Date: 2025-10-17 08:36:40.590520

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '48693409b776'
down_revision = ('20251010_add_updated_at', '20251013_add_offer_status', '20251014_timestamps_drafts')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
