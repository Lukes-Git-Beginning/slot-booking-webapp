# -*- coding: utf-8 -*-
"""Add ON DELETE constraints to existing FKs + new FK for booking_outcomes.booking_id

Revision ID: add_fk_constr01
Revises: fix_finanz_st01
Create Date: 2026-03-28
"""

from alembic import op

revision = 'add_fk_constr01'
down_revision = 'fix_finanz_st01'
branch_labels = None
depends_on = None


# Finanzberatung FK upgrades: add ON DELETE CASCADE/SET NULL
FINANZ_FK_UPGRADES = [
    # (table, constraint_name, column, ref_table.ref_column, ondelete)
    ('finanz_upload_tokens', 'finanz_upload_tokens_session_id_fkey', 'session_id', 'finanz_sessions.id', 'CASCADE'),
    ('finanz_documents', 'finanz_documents_session_id_fkey', 'session_id', 'finanz_sessions.id', 'CASCADE'),
    ('finanz_documents', 'finanz_documents_token_id_fkey', 'token_id', 'finanz_upload_tokens.id', 'SET NULL'),
    ('finanz_extracted_data', 'finanz_extracted_data_document_id_fkey', 'document_id', 'finanz_documents.id', 'CASCADE'),
    ('finanz_scorecards', 'finanz_scorecards_session_id_fkey', 'session_id', 'finanz_sessions.id', 'CASCADE'),
    ('finanz_foerderfragebogen', 'finanz_foerderfragebogen_session_id_fkey', 'session_id', 'finanz_sessions.id', 'CASCADE'),
    ('finanz_tasks', 'finanz_tasks_session_id_fkey', 'session_id', 'finanz_sessions.id', 'CASCADE'),
]


def upgrade():
    # --- Finanzberatung: upgrade existing FKs with ON DELETE ---
    for table, constraint, column, ref, ondelete in FINANZ_FK_UPGRADES:
        ref_table, ref_col = ref.split('.')
        # Drop old FK (without ondelete)
        op.drop_constraint(constraint, table, type_='foreignkey')
        # Re-create with ondelete
        op.create_foreign_key(
            constraint, table, ref_table,
            [column], [ref_col],
            ondelete=ondelete
        )

    # --- BookingOutcome: add new FK to bookings.booking_id ---
    op.create_foreign_key(
        'booking_outcomes_booking_id_fkey',
        'booking_outcomes', 'bookings',
        ['booking_id'], ['booking_id'],
        ondelete='SET NULL'
    )


def downgrade():
    # Remove BookingOutcome FK
    op.drop_constraint('booking_outcomes_booking_id_fkey', 'booking_outcomes', type_='foreignkey')

    # Revert Finanzberatung FKs to without ondelete
    for table, constraint, column, ref, _ondelete in FINANZ_FK_UPGRADES:
        ref_table, ref_col = ref.split('.')
        op.drop_constraint(constraint, table, type_='foreignkey')
        op.create_foreign_key(
            constraint, table, ref_table,
            [column], [ref_col]
        )
