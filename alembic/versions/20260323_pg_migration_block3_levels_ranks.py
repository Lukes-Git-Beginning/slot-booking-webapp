# -*- coding: utf-8 -*-
"""PG-Migration Block 3 — Level-System + Rank-Tracking Dual-Write

Revision ID: b3_levels_rk01
Revises: b2_notificat01
Create Date: 2026-03-23
"""

from alembic import op
import sqlalchemy as sa

revision = 'b3_levels_rk01'
down_revision = 'b2_notificat01'
branch_labels = None
depends_on = None


def upgrade():
    # user_levels table
    op.create_table(
        'user_levels',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(100), nullable=False),
        sa.Column('level', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('xp', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('level_title', sa.String(100), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username', name='uq_user_levels_username'),
    )
    op.create_index('ix_user_levels_username', 'user_levels', ['username'])

    # level_history table
    op.create_table(
        'level_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(100), nullable=False),
        sa.Column('old_level', sa.Integer(), nullable=False),
        sa.Column('new_level', sa.Integer(), nullable=False),
        sa.Column('old_xp', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('new_xp', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('xp_gained', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('leveled_up_at', sa.DateTime(), nullable=False),
        sa.Column('rewards_granted', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_level_history_username', 'level_history', ['username'])
    op.create_index('ix_level_history_leveled_up_at', 'level_history', ['leveled_up_at'])

    # rank_history table — CREATE IF NOT EXISTS wegen Raw-SQL in _pg_sync_ranks
    # Die Tabelle koennte bereits per Raw SQL existieren; daher IF NOT EXISTS via execute
    op.execute("""
        CREATE TABLE IF NOT EXISTS rank_history (
            id SERIAL PRIMARY KEY,
            date VARCHAR(10) NOT NULL,
            username VARCHAR(100) NOT NULL,
            rank_position INTEGER NOT NULL,
            CONSTRAINT uq_rank_history_date_username UNIQUE (date, username)
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_rank_date_username
        ON rank_history (date, username)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_rank_history_date
        ON rank_history (date)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_rank_history_username
        ON rank_history (username)
    """)


def downgrade():
    op.drop_table('level_history')
    op.drop_table('user_levels')
    # rank_history wird nicht gedroppt (koennte vor dieser Migration per Raw SQL erstellt worden sein)
