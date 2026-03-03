# -*- coding: utf-8 -*-
"""Finanzberatung Phase 6: DSGVO fields + ExtractedData verification columns

Revision ID: c4d5e6f7a8b9
Revises: b3f4a2c1d5e7
Create Date: 2026-03-03

New columns on finanz_sessions:
- deletion_requested_at (DateTime, nullable)
- deletion_requested_by (String(100), nullable)
- files_deleted_at (DateTime, nullable)

New columns on finanz_extracted_data:
- verified (Boolean, default False)
- verified_by (String(100), nullable)
- verified_at (DateTime, nullable)

Note: Enum extensions (DocumentType, DocumentStatus, SessionStatus) use
native_enum=False (VARCHAR-backed), so no DDL changes needed for enum values.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4d5e6f7a8b9'
down_revision = 'b3f4a2c1d5e7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # FinanzSession: DSGVO deletion tracking
    op.add_column('finanz_sessions', sa.Column(
        'deletion_requested_at', sa.DateTime(), nullable=True
    ))
    op.add_column('finanz_sessions', sa.Column(
        'deletion_requested_by', sa.String(100), nullable=True
    ))
    op.add_column('finanz_sessions', sa.Column(
        'files_deleted_at', sa.DateTime(), nullable=True
    ))

    # FinanzExtractedData: verification fields
    op.add_column('finanz_extracted_data', sa.Column(
        'verified', sa.Boolean(), nullable=False, server_default=sa.text('false')
    ))
    op.add_column('finanz_extracted_data', sa.Column(
        'verified_by', sa.String(100), nullable=True
    ))
    op.add_column('finanz_extracted_data', sa.Column(
        'verified_at', sa.DateTime(), nullable=True
    ))


def downgrade() -> None:
    # FinanzExtractedData
    op.drop_column('finanz_extracted_data', 'verified_at')
    op.drop_column('finanz_extracted_data', 'verified_by')
    op.drop_column('finanz_extracted_data', 'verified')

    # FinanzSession
    op.drop_column('finanz_sessions', 'files_deleted_at')
    op.drop_column('finanz_sessions', 'deletion_requested_by')
    op.drop_column('finanz_sessions', 'deletion_requested_at')
