# -*- coding: utf-8 -*-
"""Add finanz_foerderfragebogen table

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-03-14
"""

from alembic import op
import sqlalchemy as sa

revision = 'e6f7a8b9c0d1'
down_revision = 'd5e6f7a8b9c0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'finanz_foerderfragebogen',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('session_id', sa.Integer(), sa.ForeignKey('finanz_sessions.id'), unique=True, nullable=False),

        # Step 1: Persoenliche Daten
        sa.Column('geburtsdatum', sa.String(10), nullable=True),
        sa.Column('familienstand', sa.String(30), nullable=True),
        sa.Column('kinder_anzahl', sa.Integer(), nullable=True),
        sa.Column('kinder_geburtsjahre', sa.String(200), nullable=True),

        # Step 2: Berufliche Situation
        sa.Column('beschaeftigung', sa.String(30), nullable=True),
        sa.Column('rv_pflichtig', sa.Boolean(), nullable=True),
        sa.Column('bruttojahreseinkommen', sa.Float(), nullable=True),
        sa.Column('zve', sa.Float(), nullable=True),
        sa.Column('arbeitgeber_vl', sa.Boolean(), nullable=True),
        sa.Column('arbeitgeber_bav', sa.Boolean(), nullable=True),

        # Step 3: Kinder & Familie
        sa.Column('kinder_im_haushalt_u18', sa.Integer(), nullable=True),
        sa.Column('kinder_in_ausbildung', sa.Integer(), nullable=True),
        sa.Column('v0800_beantragt', sa.Boolean(), nullable=True),
        sa.Column('schwangerschaft_geplant', sa.Boolean(), nullable=True),

        # Step 4: Wohnsituation
        sa.Column('wohnsituation', sa.String(30), nullable=True),
        sa.Column('immobilie_geplant', sa.String(30), nullable=True),
        sa.Column('bausparvertrag', sa.Boolean(), nullable=True),

        # Step 5: Bestehende Vorsorge
        sa.Column('hat_riester', sa.Boolean(), nullable=True),
        sa.Column('hat_ruerup', sa.Boolean(), nullable=True),
        sa.Column('hat_bav', sa.Boolean(), nullable=True),
        sa.Column('hat_bu', sa.String(20), nullable=True),
        sa.Column('hat_pflegezusatz', sa.Boolean(), nullable=True),
        sa.Column('hat_vl_vertrag', sa.Boolean(), nullable=True),

        # Ergebnis
        sa.Column('eligible_foerderungen', sa.Text(), nullable=True),
        sa.Column('potential_yearly_benefit', sa.Float(), nullable=True),

        # Meta
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('completed_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_index('idx_finanz_ffb_session', 'finanz_foerderfragebogen', ['session_id'])


def downgrade():
    op.drop_index('idx_finanz_ffb_session')
    op.drop_table('finanz_foerderfragebogen')
