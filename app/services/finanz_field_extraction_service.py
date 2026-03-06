# -*- coding: utf-8 -*-
"""
Finanzberatung Field Extraction Service

Extracts structured fields from classified documents based on the
checklist schema. Each extracted field includes a source reference
(page + text snippet) for traceability.

Mock mode (FINANZ_LLM_ENABLED=false):
- Regex/pattern matching for common formats (currency, dates, etc.)
- Known insurance company names matching
- Good enough for development and basic use

Live mode (FINANZ_LLM_ENABLED=true):
- Structured LLM extraction with JSON output
- Source references mandatory per field
"""

import json
import logging
import re
from typing import Optional

from app.config.base import FinanzConfig as finanz_config
from app.config.finanz_checklist import (
    CONTRACT_TYPES, get_fields_for_type, FIELD_TYPE_CURRENCY,
    FIELD_TYPE_DATE, FIELD_TYPE_NUMBER, FIELD_TYPE_PERCENT,
    FIELD_TYPE_TEXT,
)
from app.models import get_db_session
from app.models.finanzberatung import (
    FinanzDocument, FinanzExtractedData, DocumentStatus,
)

logger = logging.getLogger(__name__)

# Known German insurance companies for matching
KNOWN_COMPANIES = [
    "Allianz", "AXA", "Debeka", "DEVK", "ERGO", "Generali",
    "Gothaer", "HDI", "HUK-Coburg", "HUK24", "LVM",
    "Nuernberger", "R+V", "Signal Iduna", "VHV", "Wuerttembergische",
    "Zurich", "Alte Leipziger", "Continentale", "Cosmos Direkt",
    "CosmosDirekt", "Deutsche Familienversicherung", "DFV",
    "Die Bayerische", "Hannoversche", "Inter", "Janitos",
    "Provinzial", "SV SparkassenVersicherung", "Swiss Life",
    "Volkswohl Bund", "WWK", "Basler", "Condor", "Dialog",
    "Die Stuttgarter", "Stuttgarter", "Baloise", "Canada Life",
    "Standard Life", "Volkswohlbund", "Barmenia", "SDK",
    "DKV", "Hallesche", "Muenchener Verein", "ARAG",
    "Advocard", "Roland", "D.A.S.", "ADAC", "Kravag",
    "WGV", "BGV", "Oeffentliche", "Sparkassen", "Degussa",
    "Talanx", "HDI Global", "Helvetia", "Die Haftpflichtkasse",
]


class FinanzFieldExtractionService:
    """Extracts structured fields from classified financial documents."""

    def extract_fields(self, document_id: int) -> list[dict]:
        """
        Extract fields from a document based on its classified type.

        Args:
            document_id: ID of the FinanzDocument (must be CLASSIFIED)

        Returns:
            List of extracted field dicts with name, value, confidence,
            source_page, source_text

        Raises:
            ValueError: If document not found or wrong status
        """
        db = get_db_session()
        try:
            doc = db.query(FinanzDocument).filter(
                FinanzDocument.id == document_id
            ).first()
            if doc is None:
                raise ValueError(f"Document {document_id} not found")

            if doc.status != DocumentStatus.CLASSIFIED:
                raise ValueError(
                    f"Document {document_id} not in CLASSIFIED status (current: {doc.status})"
                )

            # Update status
            doc.status = DocumentStatus.ANALYZING
            db.commit()

            type_key = doc.document_type or "sonstige"
            text = doc.extracted_text or ""
            pages = self._split_pages(text)

            use_llm = finanz_config.FINANZ_LLM_ENABLED

            try:
                if use_llm:
                    results = self._extract_llm(type_key, text, pages)
                else:
                    results = self._extract_patterns(type_key, text, pages)
            except Exception as e:
                doc.status = DocumentStatus.ERROR
                db.commit()
                raise RuntimeError(
                    f"Field extraction failed for doc {document_id}: {e}"
                ) from e

            # Delete existing extracted data for this document (re-extraction)
            db.query(FinanzExtractedData).filter(
                FinanzExtractedData.document_id == document_id
            ).delete()

            # Save extracted fields
            for field_data in results:
                extracted = FinanzExtractedData(
                    document_id=document_id,
                    field_name=field_data["name"],
                    field_value=field_data.get("value"),
                    field_type=field_data.get("type", "text"),
                    confidence=field_data.get("confidence"),
                    source_page=field_data.get("source_page"),
                    source_text=field_data.get("source_text"),
                )
                db.add(extracted)

            doc.status = DocumentStatus.ANALYZED
            db.commit()

            logger.info(
                "Document %s: extracted %d fields for type '%s'",
                document_id, len(results), type_key,
            )
            return results

        except (ValueError, RuntimeError):
            raise
        except Exception as e:
            db.rollback()
            logger.error(
                "Field extraction error for doc %s: %s",
                document_id, e, exc_info=True,
            )
            raise
        finally:
            db.close()

    def _split_pages(self, text: str) -> list[str]:
        """Split full text into page-level segments."""
        if "\n\n" in text:
            pages = text.split("\n\n")
            return [p for p in pages if p.strip()]
        return [text] if text.strip() else []

    # -----------------------------------------------------------------------
    # Pattern-Based Extraction (Mock Mode)
    # -----------------------------------------------------------------------

    def _extract_patterns(
        self, type_key: str, text: str, pages: list[str]
    ) -> list[dict]:
        """Extract fields using regex patterns and heuristics."""
        fields = get_fields_for_type(type_key)
        if not fields:
            return []

        results = []
        for field_def in fields:
            name = field_def["name"]
            ftype = field_def["type"]

            match = None
            if name == "gesellschaft":
                match = self._find_company(text, pages)
            elif ftype == FIELD_TYPE_CURRENCY:
                match = self._find_currency(name, field_def["label"], text, pages)
            elif ftype == FIELD_TYPE_DATE:
                match = self._find_date(name, field_def["label"], text, pages)
            elif ftype == FIELD_TYPE_NUMBER:
                match = self._find_number(name, field_def["label"], text, pages)
            elif ftype == FIELD_TYPE_PERCENT:
                match = self._find_percent(name, field_def["label"], text, pages)
            else:
                match = self._find_text_field(name, field_def["label"], text, pages)

            if match:
                match["name"] = name
                match["type"] = ftype
                results.append(match)

        return results

    def _find_page(self, snippet: str, pages: list[str]) -> int | None:
        """Find which page contains a text snippet (1-indexed)."""
        if not pages or not snippet:
            return None
        snippet_lower = snippet.lower()
        for i, page in enumerate(pages):
            if snippet_lower in page.lower():
                return i + 1
        return 1

    def _extract_context(self, text: str, match_start: int, match_end: int, ctx_chars: int = 80) -> str:
        """Extract surrounding context around a match."""
        start = max(0, match_start - ctx_chars)
        end = min(len(text), match_end + ctx_chars)
        return text[start:end].strip()

    def _find_company(self, text: str, pages: list[str]) -> Optional[dict]:
        """Find insurance company name in text."""
        for company in KNOWN_COMPANIES:
            idx = text.find(company)
            if idx >= 0:
                ctx = self._extract_context(text, idx, idx + len(company))
                return {
                    "value": company,
                    "confidence": 0.85,
                    "source_page": self._find_page(company, pages),
                    "source_text": ctx,
                }
        return None

    def _find_currency(
        self, name: str, label: str, text: str, pages: list[str]
    ) -> Optional[dict]:
        """Find currency amounts near relevant labels."""
        # Patterns: 234,56 EUR | 234.56 € | EUR 234,56
        currency_re = re.compile(
            r'(\d{1,3}(?:[.\s]\d{3})*[,]\d{2})\s*(?:EUR|Euro|€)'
            r'|(?:EUR|Euro|€)\s*(\d{1,3}(?:[.\s]\d{3})*[,]\d{2})',
            re.IGNORECASE,
        )

        # Search near the label keywords
        label_words = label.lower().split()
        text_lower = text.lower()

        for word in label_words:
            if len(word) < 3:
                continue
            idx = text_lower.find(word)
            if idx >= 0:
                # Search in a window around the label
                window_start = max(0, idx - 50)
                window_end = min(len(text), idx + 300)
                window = text[window_start:window_end]
                m = currency_re.search(window)
                if m:
                    value = m.group(1) or m.group(2)
                    full_match = m.group(0)
                    abs_start = window_start + m.start()
                    ctx = self._extract_context(text, abs_start, abs_start + len(full_match))
                    return {
                        "value": value.replace('.', '').replace(' ', ''),
                        "confidence": 0.75,
                        "source_page": self._find_page(full_match, pages),
                        "source_text": ctx,
                    }

        # Fallback: find any currency amount
        m = currency_re.search(text)
        if m and name == "beitrag":
            value = m.group(1) or m.group(2)
            full_match = m.group(0)
            ctx = self._extract_context(text, m.start(), m.end())
            return {
                "value": value.replace('.', '').replace(' ', ''),
                "confidence": 0.5,
                "source_page": self._find_page(full_match, pages),
                "source_text": ctx,
            }

        return None

    def _find_date(
        self, name: str, label: str, text: str, pages: list[str]
    ) -> Optional[dict]:
        """Find dates in DD.MM.YYYY format near relevant labels."""
        date_re = re.compile(r'(\d{2}\.\d{2}\.\d{4})')

        label_words = label.lower().split()
        text_lower = text.lower()

        for word in label_words:
            if len(word) < 4:
                continue
            idx = text_lower.find(word)
            if idx >= 0:
                window = text[max(0, idx - 30):min(len(text), idx + 200)]
                m = date_re.search(window)
                if m:
                    ctx = self._extract_context(
                        text,
                        max(0, idx - 30) + m.start(),
                        max(0, idx - 30) + m.end(),
                    )
                    return {
                        "value": m.group(1),
                        "confidence": 0.8,
                        "source_page": self._find_page(m.group(1), pages),
                        "source_text": ctx,
                    }
        return None

    def _find_number(
        self, name: str, label: str, text: str, pages: list[str]
    ) -> Optional[dict]:
        """Find numeric values near relevant labels."""
        number_re = re.compile(r'(\d{1,6}(?:[.,]\d+)?)')

        label_words = label.lower().split()
        text_lower = text.lower()

        for word in label_words:
            if len(word) < 3:
                continue
            idx = text_lower.find(word)
            if idx >= 0:
                window = text[max(0, idx):min(len(text), idx + 200)]
                m = number_re.search(window)
                if m:
                    ctx = self._extract_context(
                        text,
                        max(0, idx) + m.start(),
                        max(0, idx) + m.end(),
                    )
                    return {
                        "value": m.group(1),
                        "confidence": 0.65,
                        "source_page": self._find_page(m.group(1), pages),
                        "source_text": ctx,
                    }
        return None

    def _find_percent(
        self, name: str, label: str, text: str, pages: list[str]
    ) -> Optional[dict]:
        """Find percentage values near relevant labels."""
        pct_re = re.compile(r'(\d{1,3}[.,]?\d*)\s*%')

        label_words = label.lower().split()
        text_lower = text.lower()

        for word in label_words:
            if len(word) < 3:
                continue
            idx = text_lower.find(word)
            if idx >= 0:
                window = text[max(0, idx):min(len(text), idx + 200)]
                m = pct_re.search(window)
                if m:
                    ctx = self._extract_context(
                        text,
                        max(0, idx) + m.start(),
                        max(0, idx) + m.end(),
                    )
                    return {
                        "value": m.group(1),
                        "confidence": 0.7,
                        "source_page": self._find_page(m.group(0), pages),
                        "source_text": ctx,
                    }
        return None

    def _find_text_field(
        self, name: str, label: str, text: str, pages: list[str]
    ) -> Optional[dict]:
        """Find text values near labels using colon/line patterns."""
        label_words = [w for w in label.lower().split() if len(w) >= 4]
        text_lower = text.lower()

        for word in label_words:
            idx = text_lower.find(word)
            if idx >= 0:
                # Look for "Label: Value" pattern
                after = text[idx:min(len(text), idx + 200)]
                colon_match = re.search(r':\s*(.+?)(?:\n|$)', after)
                if colon_match:
                    value = colon_match.group(1).strip()
                    if value and len(value) < 200:
                        ctx = self._extract_context(
                            text, idx, idx + colon_match.end()
                        )
                        return {
                            "value": value,
                            "confidence": 0.6,
                            "source_page": self._find_page(value, pages),
                            "source_text": ctx,
                        }
        return None

    # -----------------------------------------------------------------------
    # LLM-Based Extraction (Live Mode)
    # -----------------------------------------------------------------------

    def _extract_llm(
        self, type_key: str, text: str, pages: list[str]
    ) -> list[dict]:
        """Extract fields using LLM with structured JSON output."""
        import requests

        base_url = finanz_config.FINANZ_LLM_BASE_URL
        model = finanz_config.FINANZ_LLM_MODEL

        fields = get_fields_for_type(type_key)
        if not fields:
            return []

        ct = CONTRACT_TYPES.get(type_key, {})
        field_desc = "\n".join(
            f"- {f['name']}: {f['label']} (Typ: {f['type']}, Prioritaet: {f['priority']})"
            for f in fields
        )

        # Truncate text
        max_chars = 12000
        truncated = text[:max_chars] if len(text) > max_chars else text

        prompt = f"""Extrahiere die folgenden Felder aus dem Dokument (Vertragsart: {ct.get('label', type_key)}).

Gesuchte Felder:
{field_desc}

Dokument-Text:
{truncated}

Antworte NUR mit JSON im Format:
{{
  "fields": [
    {{"name": "feldname", "value": "wert", "confidence": 0.0-1.0, "source_page": 1, "source_text": "Originaltext-Ausschnitt"}}
  ]
}}

Regeln:
- Extrahiere NUR Felder die im Dokument vorkommen
- source_text MUSS der Originaltext-Ausschnitt sein der den Wert enthaelt
- confidence basiert auf Sicherheit der Extraktion
- Waehrungsbetraege als Dezimalzahl (z.B. "234.56")
- Daten als DD.MM.YYYY"""

        try:
            response = requests.post(
                f"{base_url}/chat/completions",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 2000,
                },
                timeout=60,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]

            result = json.loads(content.strip())
            extracted = result.get("fields", [])

            # Validate and enrich with page numbers
            valid_names = {f["name"] for f in fields}
            validated = []
            for item in extracted:
                if item.get("name") not in valid_names:
                    continue
                field_def = next(
                    (f for f in fields if f["name"] == item["name"]), None
                )
                if field_def:
                    item["type"] = field_def["type"]
                if not item.get("source_page"):
                    source = item.get("source_text", "")
                    item["source_page"] = self._find_page(source, pages) if source else 1
                validated.append(item)

            return validated

        except Exception as e:
            logger.error("LLM field extraction failed: %s", e, exc_info=True)
            # Fallback to pattern matching
            return self._extract_patterns(type_key, text, pages)
