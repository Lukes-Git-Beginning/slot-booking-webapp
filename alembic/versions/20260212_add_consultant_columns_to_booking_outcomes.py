"""Add consultant columns to booking_outcomes

Revision ID: b3f4a2c1d5e7
Revises: a6c912049297
Create Date: 2026-02-12

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b3f4a2c1d5e7'
down_revision = 'a6c912049297'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('booking_outcomes', sa.Column('consultant', sa.String(100), nullable=True))
    op.add_column('booking_outcomes', sa.Column('consultant_email', sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column('booking_outcomes', 'consultant_email')
    op.drop_column('booking_outcomes', 'consultant')
