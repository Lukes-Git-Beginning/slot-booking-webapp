# -*- coding: utf-8 -*-
"""Add finanz_foerderfragebogen table (v2 — ZFA PDF schema)

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
    # Drop old table if exists (v1 schema)
    op.execute("DROP TABLE IF EXISTS finanz_foerderfragebogen CASCADE")

    op.create_table(
        'finanz_foerderfragebogen',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('session_id', sa.Integer(), sa.ForeignKey('finanz_sessions.id'), unique=True, nullable=False),

        # Stammdaten Mandant
        sa.Column('mandant_vorname', sa.String(100), nullable=True),
        sa.Column('mandant_nachname', sa.String(100), nullable=True),
        sa.Column('mandant_geburtsdatum', sa.String(10), nullable=True),
        sa.Column('mandant_beruf', sa.String(100), nullable=True),

        # Stammdaten Partner
        sa.Column('partner_vorname', sa.String(100), nullable=True),
        sa.Column('partner_nachname', sa.String(100), nullable=True),
        sa.Column('partner_geburtsdatum', sa.String(10), nullable=True),
        sa.Column('partner_beruf', sa.String(100), nullable=True),

        # Adresse
        sa.Column('anschrift', sa.String(300), nullable=True),

        # Kinder (JSON array)
        sa.Column('kinder', sa.Text(), nullable=True),
        sa.Column('anzahl_kindergeldberechtigt', sa.Integer(), nullable=True),

        # Einkuenfte
        sa.Column('brutto_mandant', sa.Float(), nullable=True),
        sa.Column('brutto_partner', sa.Float(), nullable=True),
        sa.Column('weitere_einkuenfte_mandant', sa.String(200), nullable=True),
        sa.Column('weitere_einkuenfte_partner', sa.String(200), nullable=True),
        sa.Column('staatsangehoerigkeit_mandant', sa.String(50), nullable=True),
        sa.Column('staatsangehoerigkeit_partner', sa.String(50), nullable=True),
        sa.Column('schufa_mandant', sa.Boolean(), nullable=True),
        sa.Column('schufa_partner', sa.Boolean(), nullable=True),

        # Flexible JSON answers for all subsidy questions
        sa.Column('answers', sa.Text(), nullable=True),

        # Notizen
        sa.Column('weitere_notizen', sa.Text(), nullable=True),

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
