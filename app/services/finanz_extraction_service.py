# -*- coding: utf-8 -*-
"""
Finanzberatung Document Extraction Service

Extracts text from uploaded documents:
- PDFs: pdfplumber for text-based extraction
- Images (JPG/PNG/TIFF/HEIC): pytesseract OCR with preprocessing
- Produces full text + page-level mapping

Gracefully degrades if ML dependencies are not installed.
"""

import logging
import os
from typing import Optional

from app.config.base import FinanzConfig as finanz_config
from app.models import get_db_session
from app.models.finanzberatung import FinanzDocument, DocumentStatus

logger = logging.getLogger(__name__)

# Optional ML imports
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False
    logger.info("pdfplumber not available — PDF extraction disabled")

try:
    import pytesseract
    from PIL import Image, ImageEnhance, ImageFilter
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False
    logger.info("pytesseract not available — OCR extraction disabled")


class FinanzExtractionService:
    """Extracts text content from uploaded financial documents."""

    def extract_document(self, document_id: int) -> dict:
        """
        Extract text from a document and update its status.

        Args:
            document_id: ID of the FinanzDocument to process

        Returns:
            Dict with 'text', 'page_count', 'pages' (list of page texts)

        Raises:
            ValueError: If document not found or file missing
            RuntimeError: If extraction fails
        """
        db = get_db_session()
        try:
            doc = db.query(FinanzDocument).filter(
                FinanzDocument.id == document_id
            ).first()
            if doc is None:
                raise ValueError(f"Document {document_id} not found")

            # Update status to EXTRACTING
            doc.status = DocumentStatus.EXTRACTING
            db.commit()

            # Resolve file path
            file_path = self._resolve_path(doc)
            if not os.path.exists(file_path):
                doc.status = DocumentStatus.ERROR
                db.commit()
                raise ValueError(f"File not found: {file_path}")

            # Extract based on MIME type
            try:
                if doc.mime_type == 'application/pdf':
                    result = self._extract_pdf(file_path)
                elif doc.mime_type.startswith('image/'):
                    result = self._extract_image(file_path)
                else:
                    result = {"text": "", "page_count": 0, "pages": []}
                    logger.warning(
                        "Unsupported MIME type for extraction: %s (doc %s)",
                        doc.mime_type, document_id,
                    )
            except Exception as e:
                doc.status = DocumentStatus.ERROR
                db.commit()
                raise RuntimeError(f"Extraction failed for doc {document_id}: {e}") from e

            # Save extracted text + page count
            doc.extracted_text = result["text"]
            doc.page_count = result["page_count"]
            doc.status = DocumentStatus.EXTRACTED
            db.commit()

            logger.info(
                "Document %s extracted: %d pages, %d chars",
                document_id, result["page_count"], len(result["text"]),
            )
            return result

        except (ValueError, RuntimeError):
            raise
        except Exception as e:
            db.rollback()
            logger.error("Extraction error for doc %s: %s", document_id, e, exc_info=True)
            raise
        finally:
            db.close()

    def _resolve_path(self, doc: FinanzDocument) -> str:
        """Resolve the full filesystem path for a document."""
        return finanz_config.get_file_path(doc.session_id, doc.stored_filename)

    def _extract_pdf(self, file_path: str) -> dict:
        """Extract text from a PDF file using pdfplumber."""
        if not HAS_PDFPLUMBER:
            logger.warning("pdfplumber not installed — returning empty extraction")
            return {"text": "", "page_count": 0, "pages": []}

        pages = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                pages.append(text)

        full_text = "\n\n".join(pages)
        return {
            "text": full_text,
            "page_count": len(pages),
            "pages": pages,
        }

    def _extract_image(self, file_path: str) -> dict:
        """Extract text from an image file using pytesseract OCR."""
        if not HAS_TESSERACT:
            logger.warning("pytesseract not installed — returning empty extraction")
            return {"text": "", "page_count": 1, "pages": [""]}

        img = Image.open(file_path)

        # Preprocessing for better OCR results
        img = img.convert('L')  # Grayscale
        img = ImageEnhance.Contrast(img).enhance(2.0)  # Increase contrast
        img = img.filter(ImageFilter.SHARPEN)  # Sharpen

        text = pytesseract.image_to_string(img, lang='deu')

        return {
            "text": text,
            "page_count": 1,
            "pages": [text],
        }
