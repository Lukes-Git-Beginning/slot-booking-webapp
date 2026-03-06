# -*- coding: utf-8 -*-
"""
Finanzberatung Document Classification Service

Classifies extracted document text into contract types (Vertragsarten).

Mock mode (FINANZ_LLM_ENABLED=false):
- Keyword matching against finanz_checklist.py CLASSIFICATION_KEYWORDS
- Fast, no GPU required, good for development

Live mode (FINANZ_LLM_ENABLED=true):
- Sends document text to vLLM endpoint for classification
- Uses 8B model for fast classification
"""

import json
import logging
from typing import Optional

from app.config.base import FinanzConfig as finanz_config
from app.config.finanz_checklist import (
    CONTRACT_TYPES, CLASSIFICATION_KEYWORDS, get_all_type_keys,
)
from app.models import get_db_session
from app.models.finanzberatung import FinanzDocument, DocumentStatus, DocumentType

logger = logging.getLogger(__name__)


class FinanzClassificationService:
    """Classifies financial documents into contract types."""

    def classify_document(self, document_id: int) -> dict:
        """
        Classify a document's contract type based on its extracted text.

        Args:
            document_id: ID of the FinanzDocument (must be in EXTRACTED status)

        Returns:
            Dict with 'type_key', 'type_label', 'confidence'

        Raises:
            ValueError: If document not found or not in correct status
        """
        db = get_db_session()
        try:
            doc = db.query(FinanzDocument).filter(
                FinanzDocument.id == document_id
            ).first()
            if doc is None:
                raise ValueError(f"Document {document_id} not found")

            if doc.status != DocumentStatus.EXTRACTED:
                raise ValueError(
                    f"Document {document_id} not in EXTRACTED status (current: {doc.status})"
                )

            # Update status
            doc.status = DocumentStatus.CLASSIFYING
            db.commit()

            text = doc.extracted_text or ""

            use_llm = finanz_config.FINANZ_LLM_ENABLED

            try:
                if use_llm:
                    result = self._classify_llm(text)
                else:
                    result = self._classify_keywords(text)
            except Exception as e:
                doc.status = DocumentStatus.ERROR
                db.commit()
                raise RuntimeError(f"Classification failed for doc {document_id}: {e}") from e

            # Update document
            type_key = result["type_key"]
            if type_key and type_key != "sonstige":
                try:
                    doc.document_type = DocumentType(type_key)
                except ValueError:
                    doc.document_type = DocumentType.SONSTIGE
            else:
                doc.document_type = DocumentType.SONSTIGE

            doc.classification_confidence = result["confidence"]
            doc.status = DocumentStatus.CLASSIFIED
            db.commit()

            logger.info(
                "Document %s classified as '%s' (confidence: %.2f)",
                document_id, result["type_key"], result["confidence"],
            )
            return result

        except (ValueError, RuntimeError):
            raise
        except Exception as e:
            db.rollback()
            logger.error("Classification error for doc %s: %s", document_id, e, exc_info=True)
            raise
        finally:
            db.close()

    def _classify_keywords(self, text: str) -> dict:
        """
        Classify using keyword matching against CLASSIFICATION_KEYWORDS.

        Scores each contract type by counting keyword matches in the text.
        Returns the type with the highest score.
        """
        text_lower = text.lower()
        scores = {}

        for type_key, keywords in CLASSIFICATION_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                count = text_lower.count(keyword.lower())
                if count > 0:
                    score += count * len(keyword)  # Weight by keyword length
            if score > 0:
                scores[type_key] = score

        if not scores:
            return {
                "type_key": "sonstige",
                "type_label": "Sonstiges",
                "confidence": 0.1,
            }

        # Best match
        best_key = max(scores, key=scores.get)
        best_score = scores[best_key]

        # Compute relative confidence (0.3 - 0.9 range for keyword matching)
        total_score = sum(scores.values())
        relative = best_score / total_score if total_score > 0 else 0
        confidence = min(0.9, 0.3 + relative * 0.6)

        ct = CONTRACT_TYPES.get(best_key, {})
        return {
            "type_key": best_key,
            "type_label": ct.get("label", best_key),
            "confidence": round(confidence, 2),
        }

    def _classify_llm(self, text: str) -> dict:
        """
        Classify using LLM via vLLM API endpoint.

        Sends document text with list of contract types to the LLM
        and expects a structured JSON response.
        """
        import requests

        base_url = finanz_config.FINANZ_LLM_BASE_URL
        model = finanz_config.FINANZ_LLM_MODEL

        type_list = "\n".join(
            f"- {key}: {ct['label']}"
            for key, ct in CONTRACT_TYPES.items()
        )

        # Truncate text to avoid token limits
        max_chars = 8000
        truncated = text[:max_chars] if len(text) > max_chars else text

        prompt = f"""Klassifiziere das folgende Dokument. Gib den passenden Vertragstyp als JSON zurueck.

Verfuegbare Vertragstypen:
{type_list}

Dokument-Text:
{truncated}

Antworte NUR mit JSON im Format: {{"type": "<type_key>", "confidence": 0.0-1.0}}"""

        try:
            response = requests.post(
                f"{base_url}/chat/completions",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 100,
                },
                timeout=30,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]

            # Parse JSON from response
            result = json.loads(content.strip())
            type_key = result.get("type", "sonstige")
            confidence = float(result.get("confidence", 0.5))

            if type_key not in CONTRACT_TYPES:
                type_key = "sonstige"
                confidence = 0.2

            ct = CONTRACT_TYPES.get(type_key, {})
            return {
                "type_key": type_key,
                "type_label": ct.get("label", type_key),
                "confidence": round(confidence, 2),
            }

        except Exception as e:
            logger.error("LLM classification failed: %s", e, exc_info=True)
            # Fallback to keyword matching
            return self._classify_keywords(text)
