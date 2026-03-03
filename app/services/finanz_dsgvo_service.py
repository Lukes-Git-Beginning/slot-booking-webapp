# -*- coding: utf-8 -*-
"""
Finanzberatung DSGVO Service - Data Protection Compliance

Handles GDPR-compliant data deletion for financial advisory sessions:
- Mark sessions for deletion (30-day retention period)
- Execute file deletion after retention expires
- Batch processing of expired deletion requests
- Preserves extracted data and embeddings for analytics

File-Deletion Logic:
1. Delete stored files from disk
2. Set original_filename to "[GELOESCHT]"
3. Set stored_filename to None
4. KEEP extracted_text (for analytics)
5. KEEP FinanzExtractedData rows
6. Transition session status to ARCHIVED
7. Set files_deleted_at timestamp
8. Log to audit service
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Optional

from app.models import get_db_session
from app.models.finanzberatung import (
    FinanzSession, FinanzDocument, SessionStatus,
)

logger = logging.getLogger(__name__)

# Retention period before files can be deleted
DELETION_RETENTION_DAYS = 30


class FinanzDSGVOService:
    """Manages GDPR-compliant data deletion for Finanzberatung sessions."""

    def mark_for_deletion(self, session_id: int, admin_user: str) -> dict:
        """
        Mark a session for DSGVO deletion.

        Sets deletion_requested_at and transitions status to DELETION_PENDING.
        Files are NOT deleted immediately — a 30-day retention period applies.

        Args:
            session_id: ID of the FinanzSession
            admin_user: Username of the admin requesting deletion

        Returns:
            Dict with session_id, status, deletion_date

        Raises:
            ValueError: If session not found or already marked
        """
        db = get_db_session()
        try:
            session = db.query(FinanzSession).filter(
                FinanzSession.id == session_id
            ).first()

            if session is None:
                raise ValueError(f"Session {session_id} not found")

            if session.deletion_requested_at is not None:
                raise ValueError(
                    f"Session {session_id} already marked for deletion "
                    f"on {session.deletion_requested_at.isoformat()}"
                )

            now = datetime.utcnow()
            session.deletion_requested_at = now
            session.deletion_requested_by = admin_user

            # Transition status
            try:
                session.transition_to(SessionStatus.DELETION_PENDING)
            except ValueError:
                # If current status doesn't allow transition, force it
                session.status = SessionStatus.DELETION_PENDING.value

            db.commit()

            deletion_date = now + timedelta(days=DELETION_RETENTION_DAYS)

            logger.info(
                "Session %s marked for deletion by %s (due: %s)",
                session_id, admin_user, deletion_date.isoformat(),
            )

            # Audit log
            try:
                from app.services.audit_service import audit_service
                audit_service.log(
                    'finanz_dsgvo_mark_deletion',
                    admin_user,
                    {
                        'session_id': session_id,
                        'customer_name': session.customer_name,
                        'deletion_due': deletion_date.isoformat(),
                    }
                )
            except Exception as e:
                logger.warning("Audit log failed: %s", e)

            return {
                'session_id': session_id,
                'status': 'deletion_pending',
                'deletion_requested_at': now.isoformat(),
                'deletion_due': deletion_date.isoformat(),
            }

        except ValueError:
            raise
        except Exception as e:
            db.rollback()
            logger.error("Error marking session %s for deletion: %s", session_id, e, exc_info=True)
            raise
        finally:
            db.close()

    def can_execute_deletion(self, session_id: int) -> bool:
        """
        Check if the 30-day retention period has expired.

        Args:
            session_id: ID of the FinanzSession

        Returns:
            True if deletion can be executed
        """
        db = get_db_session()
        try:
            session = db.query(FinanzSession).filter(
                FinanzSession.id == session_id
            ).first()

            if session is None:
                return False

            if session.deletion_requested_at is None:
                return False

            if session.files_deleted_at is not None:
                return False  # Already deleted

            elapsed = datetime.utcnow() - session.deletion_requested_at
            return elapsed >= timedelta(days=DELETION_RETENTION_DAYS)

        finally:
            db.close()

    def execute_deletion(self, session_id: int) -> dict:
        """
        Execute file deletion for a session after retention period.

        Deletes files from disk, anonymizes filenames, but preserves
        extracted text and structured data for analytics.

        Args:
            session_id: ID of the FinanzSession

        Returns:
            Dict with session_id, files_deleted count, status

        Raises:
            ValueError: If session not found or retention not expired
        """
        db = get_db_session()
        try:
            session = db.query(FinanzSession).filter(
                FinanzSession.id == session_id
            ).first()

            if session is None:
                raise ValueError(f"Session {session_id} not found")

            if session.deletion_requested_at is None:
                raise ValueError(f"Session {session_id} not marked for deletion")

            if session.files_deleted_at is not None:
                raise ValueError(f"Session {session_id} files already deleted")

            if not self.can_execute_deletion(session_id):
                remaining = (
                    session.deletion_requested_at
                    + timedelta(days=DELETION_RETENTION_DAYS)
                    - datetime.utcnow()
                )
                raise ValueError(
                    f"Retention period not expired. {remaining.days} days remaining."
                )

            # Get upload directory
            try:
                from flask import current_app
                upload_dir = current_app.config.get('FINANZ_UPLOAD_DIR', 'finanz_uploads')
                persist_base = current_app.config.get('PERSIST_BASE', 'data')
            except RuntimeError:
                upload_dir = 'finanz_uploads'
                persist_base = 'data'

            base_path = os.path.join(persist_base, 'persistent', upload_dir)

            # Delete files for each document
            documents = db.query(FinanzDocument).filter(
                FinanzDocument.session_id == session_id
            ).all()

            files_deleted = 0
            for doc in documents:
                if doc.stored_filename:
                    file_path = os.path.join(base_path, doc.stored_filename)
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            files_deleted += 1
                            logger.debug("Deleted file: %s", file_path)
                    except OSError as e:
                        logger.error("Failed to delete file %s: %s", file_path, e)

                # Anonymize filenames, keep extracted_text
                doc.original_filename = "[GELOESCHT]"
                doc.stored_filename = None

            # Update session
            session.files_deleted_at = datetime.utcnow()
            session.transition_to(SessionStatus.ARCHIVED)

            db.commit()

            logger.info(
                "Session %s: %d files deleted, status -> ARCHIVED",
                session_id, files_deleted,
            )

            # Audit log
            try:
                from app.services.audit_service import audit_service
                admin_user = session.deletion_requested_by or 'system'
                audit_service.log(
                    'finanz_dsgvo_execute_deletion',
                    admin_user,
                    {
                        'session_id': session_id,
                        'files_deleted': files_deleted,
                        'customer_name': session.customer_name,
                    }
                )
            except Exception as e:
                logger.warning("Audit log failed: %s", e)

            return {
                'session_id': session_id,
                'files_deleted': files_deleted,
                'status': 'archived',
            }

        except ValueError:
            raise
        except Exception as e:
            db.rollback()
            logger.error("Error executing deletion for session %s: %s", session_id, e, exc_info=True)
            raise
        finally:
            db.close()

    def get_deletion_queue(self) -> list[dict]:
        """
        Get all sessions marked for deletion with countdown info.

        Returns:
            List of dicts with session info and days_remaining
        """
        db = get_db_session()
        try:
            sessions = db.query(FinanzSession).filter(
                FinanzSession.deletion_requested_at.isnot(None),
                FinanzSession.files_deleted_at.is_(None),
            ).order_by(FinanzSession.deletion_requested_at.asc()).all()

            now = datetime.utcnow()
            queue = []
            for s in sessions:
                deletion_due = s.deletion_requested_at + timedelta(days=DELETION_RETENTION_DAYS)
                remaining = (deletion_due - now).days
                can_delete = remaining <= 0

                doc_count = db.query(FinanzDocument).filter(
                    FinanzDocument.session_id == s.id
                ).count()

                queue.append({
                    'session_id': s.id,
                    'customer_name': s.customer_name,
                    'opener_username': s.opener_username,
                    'deletion_requested_at': s.deletion_requested_at.isoformat(),
                    'deletion_requested_by': s.deletion_requested_by,
                    'deletion_due': deletion_due.isoformat(),
                    'days_remaining': max(0, remaining),
                    'can_delete': can_delete,
                    'document_count': doc_count,
                })

            return queue

        finally:
            db.close()

    def batch_delete_expired(self) -> dict:
        """
        Process all sessions whose retention period has expired.

        Returns:
            Dict with processed count and results
        """
        queue = self.get_deletion_queue()
        expired = [item for item in queue if item['can_delete']]

        results = []
        for item in expired:
            try:
                result = self.execute_deletion(item['session_id'])
                results.append({**result, 'success': True})
            except Exception as e:
                logger.error(
                    "Batch deletion failed for session %s: %s",
                    item['session_id'], e,
                )
                results.append({
                    'session_id': item['session_id'],
                    'success': False,
                    'error': str(e),
                })

        logger.info(
            "Batch deletion: %d/%d sessions processed",
            len([r for r in results if r.get('success')]),
            len(expired),
        )

        return {
            'total_expired': len(expired),
            'processed': len(results),
            'successful': len([r for r in results if r.get('success')]),
            'results': results,
        }
