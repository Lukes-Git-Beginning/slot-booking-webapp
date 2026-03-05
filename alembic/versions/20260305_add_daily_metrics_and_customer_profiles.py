# -*- coding: utf-8 -*-
"""Add daily_metrics and customer_profiles tables

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-03-05
"""

from alembic import op
import sqlalchemy as sa

revision = 'd5e6f7a8b9c0'
down_revision = 'c4d5e6f7a8b9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'daily_metrics',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('total_slots', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('no_shows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ghosts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cancelled', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rescheduled', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('overhang', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('no_show_rate', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('ghost_rate', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('completion_rate', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('cancellation_rate', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('by_hour', sa.Text(), nullable=True),
        sa.Column('by_user', sa.Text(), nullable=True),
        sa.Column('by_potential', sa.Text(), nullable=True),
        sa.Column('calculated_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('date')
    )
    op.create_index('idx_daily_metrics_date', 'daily_metrics', ['date'])

    op.create_table(
        'customer_profiles',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('customer', sa.String(255), nullable=False),
        sa.Column('first_seen', sa.String(10), nullable=True),
        sa.Column('last_seen', sa.String(10), nullable=True),
        sa.Column('total_appointments', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('no_shows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cancelled', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('reliability_score', sa.Float(), nullable=False, server_default='100.0'),
        sa.Column('risk_level', sa.String(20), nullable=False, server_default='low'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('customer')
    )
    op.create_index('idx_customer_profile_customer', 'customer_profiles', ['customer'])
    op.create_index('idx_customer_profile_risk', 'customer_profiles', ['risk_level'])


def downgrade():
    op.drop_index('idx_customer_profile_risk', table_name='customer_profiles')
    op.drop_index('idx_customer_profile_customer', table_name='customer_profiles')
    op.drop_table('customer_profiles')
    op.drop_index('idx_daily_metrics_date', table_name='daily_metrics')
    op.drop_table('daily_metrics')
