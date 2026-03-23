# -*- coding: utf-8 -*-
"""Add notifications table

Revision ID: a1b2c3d4e5f6
Revises: f7a8b9c0d1e2
Create Date: 2026-03-23
"""

from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = 'f7a8b9c0d1e2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('notification_id', sa.String(100), nullable=False),
        sa.Column('username', sa.String(100), nullable=False),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('notification_type', sa.String(50), nullable=False, server_default='info'),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_dismissed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('show_popup', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('roles', sa.JSON(), nullable=True),
        sa.Column('actions', sa.JSON(), nullable=True),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('notification_id', name='uq_notification_id'),
    )

    # Indexes
    op.create_index('ix_notifications_notification_id', 'notifications', ['notification_id'])
    op.create_index('ix_notifications_username', 'notifications', ['username'])
    op.create_index('ix_notifications_is_read', 'notifications', ['is_read'])
    op.create_index('idx_notification_username_read', 'notifications', ['username', 'is_read'])
    op.create_index('idx_notification_username_dismissed', 'notifications', ['username', 'is_dismissed'])


def downgrade():
    op.drop_index('idx_notification_username_dismissed', table_name='notifications')
    op.drop_index('idx_notification_username_read', table_name='notifications')
    op.drop_index('ix_notifications_is_read', table_name='notifications')
    op.drop_index('ix_notifications_username', table_name='notifications')
    op.drop_index('ix_notifications_notification_id', table_name='notifications')
    op.drop_table('notifications')
