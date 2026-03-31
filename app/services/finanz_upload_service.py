# -*- coding: utf-8 -*-
"""
Finanzberatung Upload Service - Token, QR Code, File Validation & Storage

Provides business logic for the customer document upload flow:
- Crypto-secure token generation with configurable TTL
- QR code generation (base64 PNG) from upload URL
- File validation via magic bytes (python-magic), not extensions
- File storage with UUID filenames and SHA-256 hashing
- Deduplication within a session by file hash
- Token lifecycle (activate, deactivate, followup eligibility)

All database access through get_db_session() pattern.
"""

import base64
import hashlib
import io
import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

import magic
import qrcode
from sqlalchemy.orm import joinedload

from app.config.base import Config, FinanzConfig as finanz_config
from app.models import get_db_session
from app.models.finanzberatung import (
    FinanzDocument,
    FinanzUploadToken,
    DocumentStatus,
    TokenType,
)

logger = logging.getLogger(__name__)

# MIME type to file extension mapping
_MIME_TO_EXT = {
    'application/pdf': 'pdf',
    'image/jpeg': 'jpg',
    'image/png': 'png',
    'image/tiff': 'tiff',
    'image/heif': 'heif',
    'image/heic': 'heic',
}

# Allowed MIME types for upload
_ALLOWED_MIMES = set(_MIME_TO_EXT.keys())

# Token type to TTL config mapping
_TTL_MAP = {
    TokenType.T1: lambda: finanz_config.FINANZ_TOKEN_TTL_T1,
    TokenType.FOLLOWUP: lambda: finanz_config.FINANZ_TOKEN_TTL_FOLLOWUP,
    TokenType.T2: lambda: finanz_config.FINANZ_TOKEN_TTL_T2,
}


class FinanzUploadService:
    """Service for managing document upload tokens, validation, and storage."""

    def generate_token(
        self,
        session_id: int,
        token_type: TokenType,
        db_session=None,
    ) -> Tuple[FinanzUploadToken, str]:
        """
        Generate a crypto-secure upload token with QR code.

        Args:
            session_id: The session this token belongs to
            token_type: TokenType (T1, FOLLOWUP, T2)
            db_session: Optional existing DB session (for transactional use)

        Returns:
            Tuple of (FinanzUploadToken, qr_base64_string)
        """
        db = db_session or get_db_session()
        owns_session = db_session is None
        try:
            # Deactivate any existing active tokens for this session
            old_tokens = (
                db.query(FinanzUploadToken)
                .filter(
                    FinanzUploadToken.session_id == session_id,
                    FinanzUploadToken.is_active == True,
                )
                .all()
            )
            for old_token in old_tokens:
                old_token.is_active = False

            # Generate crypto-secure token
            token_value = secrets.token_urlsafe(48)

            # Calculate TTL from config
            ttl_getter = _TTL_MAP.get(token_type)
            if ttl_getter is None:
                raise ValueError(f"Unknown token type: {token_type}")
            ttl_seconds = ttl_getter()
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)

            # Create token record
            token = FinanzUploadToken(
                session_id=session_id,
                token=token_value,
                token_type=token_type,
                expires_at=expires_at,
                upload_count=0,
                max_uploads=finanz_config.FINANZ_MAX_UPLOADS_PER_TOKEN,
                is_active=True,
            )
            db.add(token)
            db.commit()
            db.refresh(token)

            # Build upload URL
            base_url = os.getenv(
                'FINANZ_UPLOAD_BASE_URL', 'https://berater.zfa.gmbh'
            ).rstrip('/')
            upload_url = f"{base_url}/finanzberatung/upload/{token_value}"

            # Generate QR code as base64 PNG
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(upload_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            qr_base64 = base64.b64encode(buffer.getvalue()).decode()

            logger.info(
                "Token generated: session=%s, type=%s, expires=%s",
                session_id, token_type.value, expires_at.isoformat(),
            )
            return token, qr_base64

        except Exception as e:
            if owns_session:
                db.rollback()
            logger.error(
                "Failed to generate token for session %s: %s",
                session_id, e, exc_info=True,
            )
            raise
        finally:
            if owns_session:
                db.close()

    def validate_token(
        self, token_value: str
    ) -> Tuple[bool, Optional[FinanzUploadToken], str]:
        """
        Validate an upload token.

        Args:
            token_value: The raw token string from the URL

        Returns:
            Tuple of (is_valid, token_or_none, error_message)
            Error messages are in German for end-user display.
        """
        db = get_db_session()
        try:
            token = db.query(FinanzUploadToken).options(
                joinedload(FinanzUploadToken.session)
            ).filter(
                FinanzUploadToken.token == token_value
            ).first()

            if token is None:
                return False, None, 'Token nicht gefunden'

            if not token.is_active:
                db.expunge(token)
                return False, token, 'Token deaktiviert'

            if token.is_expired:
                db.expunge(token)
                return False, token, 'Token abgelaufen'

            if token.is_exhausted:
                db.expunge(token)
                return False, token, 'Upload-Limit erreicht'

            db.expunge(token)
            return True, token, ''

        except Exception as e:
            logger.error("Failed to validate token: %s", e, exc_info=True)
            return False, None, 'Validierungsfehler'
        finally:
            db.close()

    def validate_file(self, file_storage) -> Tuple[bool, str, str]:
        """
        Validate an uploaded file via magic bytes.

        Uses python-magic to detect MIME type from file content,
        NOT from the file extension. Also checks file size.

        Args:
            file_storage: Werkzeug FileStorage object

        Returns:
            Tuple of (is_valid, detected_mime, error_message)
            Error messages are in German.
        """
        try:
            # Read header for magic byte detection
            header = file_storage.read(2048)
            file_storage.seek(0)

            if not header:
                return False, '', 'Leere Datei'

            # Detect MIME type from content
            detected_mime = magic.from_buffer(header, mime=True)

            # Check allowed MIME types
            if detected_mime not in _ALLOWED_MIMES:
                return (
                    False,
                    detected_mime,
                    f'Dateityp nicht erlaubt: {detected_mime}. '
                    f'Erlaubt: PDF, JPG, PNG, TIFF, HEIF/HEIC',
                )

            # Check file size
            file_storage.seek(0, os.SEEK_END)
            file_size = file_storage.tell()
            file_storage.seek(0)

            max_size = finanz_config.FINANZ_MAX_FILE_SIZE_MB * 1024 * 1024
            if file_size > max_size:
                return (
                    False,
                    detected_mime,
                    f'Datei zu gross: {file_size / (1024*1024):.1f} MB '
                    f'(max. {finanz_config.FINANZ_MAX_FILE_SIZE_MB} MB)',
                )

            return True, detected_mime, ''

        except Exception as e:
            logger.error("File validation error: %s", e, exc_info=True)
            return False, '', f'Validierungsfehler: {str(e)}'

    def store_file(
        self,
        file_storage,
        session_id: int,
        token_id: int,
        original_filename: str,
        mime_type: str,
    ) -> FinanzDocument:
        """
        Store an uploaded file with UUID filename and SHA-256 hash.

        Creates the storage directory if needed. Checks for duplicate
        files within the same session by comparing SHA-256 hashes.
        Increments the token's upload_count.

        Args:
            file_storage: Werkzeug FileStorage object
            session_id: The session this document belongs to
            token_id: The token used for this upload
            original_filename: The original filename from the client
            mime_type: Detected MIME type from validate_file()

        Returns:
            The created FinanzDocument record

        Raises:
            ValueError: If a duplicate file is detected in the session
        """
        db = get_db_session()
        try:
            # Read file content
            file_content = file_storage.read()
            file_storage.seek(0)
            file_size = len(file_content)

            # Compute SHA-256 hash
            file_hash = hashlib.sha256(file_content).hexdigest()

            # Check for duplicate in same session
            existing = db.query(FinanzDocument).filter(
                FinanzDocument.session_id == session_id,
                FinanzDocument.file_hash == file_hash,
            ).first()
            if existing is not None:
                raise ValueError(
                    f"Duplikat erkannt: Datei mit gleichem Inhalt bereits hochgeladen "
                    f"(Dokument {existing.id}: {existing.original_filename})"
                )

            # Generate UUID filename with proper extension
            ext = _MIME_TO_EXT.get(mime_type, 'bin')
            stored_filename = f"{uuid.uuid4()}.{ext}"

            # Build storage path: {PERSIST_BASE}/{FINANZ_UPLOAD_DIR}/{session_id}/
            upload_dir = finanz_config.get_upload_dir(session_id)
            os.makedirs(upload_dir, exist_ok=True)

            file_path = os.path.join(upload_dir, stored_filename)

            # Write file to disk
            with open(file_path, 'wb') as f:
                f.write(file_content)

            # Create document record
            document = FinanzDocument(
                session_id=session_id,
                token_id=token_id,
                original_filename=original_filename,
                stored_filename=stored_filename,
                file_hash=file_hash,
                file_size=file_size,
                mime_type=mime_type,
                status=DocumentStatus.UPLOADED,
            )
            db.add(document)

            # Increment token upload count
            token = db.query(FinanzUploadToken).filter(
                FinanzUploadToken.id == token_id
            ).first()
            if token is not None:
                token.upload_count += 1

            db.commit()
            db.refresh(document)

            logger.info(
                "File stored: session=%s, doc_id=%s, file=%s, hash=%s, size=%d",
                session_id, document.id, stored_filename, file_hash[:12], file_size,
            )
            return document

        except ValueError:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            logger.error(
                "Failed to store file for session %s: %s",
                session_id, e, exc_info=True,
            )
            raise
        finally:
            db.close()

    def get_active_token(
        self, session_id: int
    ) -> Optional[FinanzUploadToken]:
        """
        Get the currently active (valid) token for a session.

        Args:
            session_id: The session's primary key

        Returns:
            The active FinanzUploadToken or None
        """
        db = get_db_session()
        try:
            tokens = (
                db.query(FinanzUploadToken)
                .filter(
                    FinanzUploadToken.session_id == session_id,
                    FinanzUploadToken.is_active == True,
                )
                .order_by(FinanzUploadToken.created_at.desc())
                .all()
            )
            # Return the first one that is still valid (not expired, not exhausted)
            for token in tokens:
                if token.is_valid:
                    return token
            return None

        except Exception as e:
            logger.error(
                "Failed to get active token for session %s: %s",
                session_id, e, exc_info=True,
            )
            return None
        finally:
            db.close()

    def can_generate_followup(self, session_id: int) -> bool:
        """
        Check if a followup token can be generated for a session.

        Per CONTEXT.md: followup token is only available after the T1 token
        expires or is fully used. If any active T1 token exists, returns False.

        Args:
            session_id: The session's primary key

        Returns:
            True if followup generation is allowed
        """
        db = get_db_session()
        try:
            # Check for any active T1 token
            active_t1 = (
                db.query(FinanzUploadToken)
                .filter(
                    FinanzUploadToken.session_id == session_id,
                    FinanzUploadToken.token_type == TokenType.T1,
                    FinanzUploadToken.is_active == True,
                )
                .all()
            )
            # If any T1 token is still valid, followup is not allowed
            for token in active_t1:
                if token.is_valid:
                    return False
            return True

        except Exception as e:
            logger.error(
                "Failed to check followup eligibility for session %s: %s",
                session_id, e, exc_info=True,
            )
            return False
        finally:
            db.close()

    def deactivate_token(self, token_id: int) -> bool:
        """
        Deactivate an upload token.

        Args:
            token_id: The token's primary key

        Returns:
            True if deactivated successfully, False otherwise
        """
        db = get_db_session()
        try:
            token = db.query(FinanzUploadToken).filter(
                FinanzUploadToken.id == token_id
            ).first()
            if token is None:
                logger.warning("Token not found for deactivation: %s", token_id)
                return False

            token.is_active = False
            db.commit()
            logger.info("Token deactivated: id=%s", token_id)
            return True

        except Exception as e:
            db.rollback()
            logger.error(
                "Failed to deactivate token %s: %s", token_id, e, exc_info=True
            )
            return False
        finally:
            db.close()
