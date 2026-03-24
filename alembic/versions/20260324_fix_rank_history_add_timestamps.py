# -*- coding: utf-8 -*-
"""Fix rank_history: Add missing created_at/updated_at columns

Revision ID: fix_rank_ts_01
Revises: b4_cosmetics01
Create Date: 2026-03-24
"""

from alembic import op
import sqlalchemy as sa

revision = 'fix_rank_ts_01'
down_revision = 'b4_cosmetics01'
branch_labels = None
depends_on = None


def upgrade():
    # rank_history was created via raw SQL without timestamp columns
    # but the SQLAlchemy model inherits created_at/updated_at from Base
    op.execute("""
        ALTER TABLE rank_history
        ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT now()
    """)
    op.execute("""
        ALTER TABLE rank_history
        ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT now()
    """)


def downgrade():
    op.execute("ALTER TABLE rank_history DROP COLUMN IF EXISTS updated_at")
    op.execute("ALTER TABLE rank_history DROP COLUMN IF EXISTS created_at")
