"""Add Booking and BookingOutcome models

Revision ID: a6c912049297
Revises: 12292c1c1ed7
Create Date: 2025-11-20 17:32:20.191779+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a6c912049297'
down_revision = '12292c1c1ed7'  # Depends on previous migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database to this revision"""
    pass


def downgrade() -> None:
    """Downgrade database from this revision"""
    pass
