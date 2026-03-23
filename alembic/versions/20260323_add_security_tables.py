# -*- coding: utf-8 -*-
"""Add security tables: account_lockouts, audit_logs

Revision ID: b1_security_01
Revises: f7a8b9c0d1e2
Create Date: 2026-03-23
"""

from alembic import op
import sqlalchemy as sa

revision = 'b1_security_01'
down_revision = 'f7a8b9c0d1e2'
branch_labels = None
depends_on = None


def upgrade():
    # account_lockouts table
    op.create_table(
        'account_lockouts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('username', sa.String(100), nullable=False),
        sa.Column('failed_attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('first_attempt', sa.DateTime(), nullable=True),
        sa.Column('last_attempt', sa.DateTime(), nullable=True),
        sa.Column('locked_until', sa.DateTime(), nullable=True),
        sa.Column('lockout_tier', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username', name='uq_account_lockouts_username')
    )
    op.create_index('ix_account_lockouts_username', 'account_lockouts', ['username'])
    op.create_index('idx_lockout_locked_until', 'account_lockouts', ['locked_until'])

    # audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('action', sa.String(500), nullable=False),
        sa.Column('user', sa.String(100), nullable=False),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('severity', sa.String(20), nullable=False, server_default='info'),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'])
    op.create_index('ix_audit_logs_event_type', 'audit_logs', ['event_type'])
    op.create_index('ix_audit_logs_user', 'audit_logs', ['user'])
    op.create_index('ix_audit_logs_severity', 'audit_logs', ['severity'])
    op.create_index('idx_audit_timestamp_desc', 'audit_logs', ['timestamp'])
    op.create_index('idx_audit_event_type_severity', 'audit_logs', ['event_type', 'severity'])


def downgrade():
    op.drop_index('idx_audit_event_type_severity', table_name='audit_logs')
    op.drop_index('idx_audit_timestamp_desc', table_name='audit_logs')
    op.drop_index('ix_audit_logs_severity', table_name='audit_logs')
    op.drop_index('ix_audit_logs_user', table_name='audit_logs')
    op.drop_index('ix_audit_logs_event_type', table_name='audit_logs')
    op.drop_index('ix_audit_logs_timestamp', table_name='audit_logs')
    op.drop_table('audit_logs')

    op.drop_index('idx_lockout_locked_until', table_name='account_lockouts')
    op.drop_index('ix_account_lockouts_username', table_name='account_lockouts')
    op.drop_table('account_lockouts')
