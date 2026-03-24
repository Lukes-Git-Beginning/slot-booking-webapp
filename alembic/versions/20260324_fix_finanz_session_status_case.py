# -*- coding: utf-8 -*-
"""Fix finanz_sessions status: normalize uppercase values to lowercase

Revision ID: fix_finanz_st01
Revises: fix_rank_ts_01
Create Date: 2026-03-24
"""

from alembic import op

revision = 'fix_finanz_st01'
down_revision = 'fix_rank_ts_01'
branch_labels = None
depends_on = None


def upgrade():
    # Some rows have uppercase status values (e.g. 'ACTIVE') but the
    # SQLAlchemy enum expects lowercase ('active'). Normalize them.
    op.execute("""
        UPDATE finanz_sessions
        SET status = LOWER(status)
        WHERE status != LOWER(status)
    """)


def downgrade():
    # No rollback needed — lowercase is the canonical format
    pass
