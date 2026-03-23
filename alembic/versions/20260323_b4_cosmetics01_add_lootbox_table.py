# -*- coding: utf-8 -*-
"""Add lootbox_data table (Block 4 Cosmetics/Avatar/Lootbox migration)

Revision ID: b4_cosmetics01
Revises: f7a8b9c0d1e2
Create Date: 2026-03-23
"""

from alembic import op
import sqlalchemy as sa

revision = 'b4_cosmetics01'
down_revision = 'f7a8b9c0d1e2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'lootbox_data',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(100), nullable=False),
        sa.Column('crates', sa.JSON(), nullable=True),
        sa.Column('history', sa.JSON(), nullable=True),
        sa.Column('pity_counter', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_lootbox_data_username', 'lootbox_data', ['username'], unique=True)


def downgrade():
    op.drop_index('ix_lootbox_data_username', table_name='lootbox_data')
    op.drop_table('lootbox_data')
