# -*- coding: utf-8 -*-
"""Add campaign column to bookings table

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-03-23
"""

from alembic import op
import sqlalchemy as sa

revision = 'f7a8b9c0d1e2'
down_revision = 'e6f7a8b9c0d1'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('bookings', sa.Column('campaign', sa.String(100), nullable=True))
    op.create_index('idx_bookings_campaign', 'bookings', ['campaign'])


def downgrade():
    op.drop_index('idx_bookings_campaign', table_name='bookings')
    op.drop_column('bookings', 'campaign')
