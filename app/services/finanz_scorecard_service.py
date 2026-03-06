# -*- coding: utf-8 -*-
"""
Finanzberatung Scorecard Service

Generates traffic-light scorecards for 4 categories based on extracted data:
- Altersvorsorge: Savings products, contributions, diversification
- Absicherung: BU, RLV, existential coverage gaps
- Vermoegen & Kosten: Total premiums, cost/benefit ratio, duplicates
- Steueroptimierung: Riester/Ruerup/bAV usage, subsidies

Mock mode: Rule-based decision tree
Live mode: LLM generates qualitative assessments (stub)
"""

import logging
from typing import Optional

from app.config.finanz_checklist import (
    CONTRACT_TYPES, CHECKLIST_CATEGORIES, get_fields_for_type,
    compute_completeness, PRIORITY_MUSS,
)
from app.models import get_db_session
from app.models.finanzberatung import (
    FinanzSession, FinanzDocument, FinanzExtractedData, FinanzScorecard,
    ScorecardCategory, TrafficLight, DocumentStatus,
)

logger = logging.getLogger(__name__)


class FinanzScorecardService:
    """Generates financial advisory scorecards."""

    def generate_scorecard(self, session_id: int) -> list[dict]:
        """
        Generate scorecards for all 4 categories + overall for a session.

        Args:
            session_id: ID of the FinanzSession

        Returns:
            List of scorecard dicts with category, rating, assessment, details
        """
        db = get_db_session()
        try:
            session = db.query(FinanzSession).filter(
                FinanzSession.id == session_id
            ).first()
            if session is None:
                raise ValueError(f"Session {session_id} not found")

            # Gather all extracted data for this session
            docs = db.query(FinanzDocument).filter(
                FinanzDocument.session_id == session_id,
                FinanzDocument.status == DocumentStatus.ANALYZED,
            ).all()

            contracts = self._gather_contracts(db, docs)

            # Generate per-category scorecards
            results = []
            for cat in ScorecardCategory:
                result = self._evaluate_category(cat, contracts)
                results.append(result)

            # Overall score
            overall = self._compute_overall(results)
            results.append(overall)

            # Delete existing scorecards for this session
            db.query(FinanzScorecard).filter(
                FinanzScorecard.session_id == session_id
            ).delete()

            # Save scorecards
            for sc_data in results:
                scorecard = FinanzScorecard(
                    session_id=session_id,
                    category=sc_data["category"],
                    rating=sc_data["rating"],
                    assessment=sc_data.get("assessment"),
                    details=sc_data.get("details"),
                    is_overall=sc_data.get("is_overall", False),
                )
                db.add(scorecard)

            db.commit()
            logger.info("Scorecards generated for session %s", session_id)
            return results

        except ValueError:
            raise
        except Exception as e:
            db.rollback()
            logger.error(
                "Scorecard generation error for session %s: %s",
                session_id, e, exc_info=True,
            )
            raise
        finally:
            db.close()

    def _gather_contracts(self, db, docs: list) -> dict:
        """
        Gather all contracts with their extracted fields.

        Returns:
            Dict mapping document_type -> list of {doc, fields: {name: {value, confidence, ...}}}
        """
        contracts = {}
        for doc in docs:
            dtype = doc.document_type or "sonstige"
            extracted = db.query(FinanzExtractedData).filter(
                FinanzExtractedData.document_id == doc.id
            ).all()

            fields = {}
            for ed in extracted:
                fields[ed.field_name] = {
                    "value": ed.field_value,
                    "confidence": ed.confidence,
                    "source_page": ed.source_page,
                    "source_text": ed.source_text,
                    "verified": ed.verified,
                }

            if dtype not in contracts:
                contracts[dtype] = []
            contracts[dtype].append({
                "doc": doc,
                "fields": fields,
            })

        return contracts

    def _evaluate_category(self, category: ScorecardCategory, contracts: dict) -> dict:
        """Evaluate a single scorecard category."""
        if category == ScorecardCategory.ALTERSVORSORGE:
            return self._eval_altersvorsorge(contracts)
        elif category == ScorecardCategory.ABSICHERUNG:
            return self._eval_absicherung(contracts)
        elif category == ScorecardCategory.VERMOEGEN_KOSTEN:
            return self._eval_vermoegen(contracts)
        elif category == ScorecardCategory.STEUEROPTIMIERUNG:
            return self._eval_steueroptimierung(contracts)
        return {
            "category": category.value,
            "rating": TrafficLight.YELLOW,
            "assessment": "Bewertung nicht verfuegbar.",
        }

    def _eval_altersvorsorge(self, contracts: dict) -> dict:
        """Evaluate Altersvorsorge category."""
        av_types = CHECKLIST_CATEGORIES["altersvorsorge"]["types"]
        found = [t for t in av_types if t in contracts]
        issues = []
        positives = []

        if not found:
            return {
                "category": ScorecardCategory.ALTERSVORSORGE,
                "rating": TrafficLight.RED,
                "assessment": "Keine Altersvorsorge-Produkte erkannt.",
                "details": "Es wurden keine Vertraege zur Altersvorsorge gefunden. "
                           "Eine umfassende Altersvorsorge-Beratung wird empfohlen.",
            }

        # Check diversification
        if len(found) >= 3:
            positives.append(f"Gute Diversifikation: {len(found)} Produkte")
        elif len(found) == 1:
            issues.append("Geringe Diversifikation: Nur 1 Produkt")

        # Check for key products
        if "riester" in found or "basisrente" in found:
            positives.append("Staatlich gefoerderte Vorsorge vorhanden")
        if "bav" in found:
            positives.append("Betriebliche Altersvorsorge vorhanden")
        if "depotanlagen" in found or "fondsgebundene_rv" in found:
            positives.append("Kapitalmarkt-basierte Vorsorge vorhanden")

        # Completeness check
        missing_muss = []
        for t in found:
            for contract in contracts.get(t, []):
                comp = compute_completeness(t, contract["fields"])
                if comp["percent_muss"] < 100:
                    ct = CONTRACT_TYPES.get(t, {})
                    missing_muss.append(ct.get("label", t))

        if missing_muss:
            issues.append(f"Fehlende Pflichtangaben bei: {', '.join(missing_muss)}")

        # Rating
        if issues and not positives:
            rating = TrafficLight.RED
        elif issues:
            rating = TrafficLight.YELLOW
        else:
            rating = TrafficLight.GREEN

        assessment_parts = positives + [f"Achtung: {i}" for i in issues]
        return {
            "category": ScorecardCategory.ALTERSVORSORGE,
            "rating": rating,
            "assessment": f"{len(found)} Altersvorsorge-Produkte erkannt.",
            "details": " | ".join(assessment_parts) if assessment_parts else None,
        }

    def _eval_absicherung(self, contracts: dict) -> dict:
        """Evaluate Absicherung category."""
        abs_types = CHECKLIST_CATEGORIES["absicherung"]["types"]
        found = [t for t in abs_types if t in contracts]
        critical_missing = []
        positives = []

        # BU is critical
        if "bu" in found:
            positives.append("BU-Versicherung vorhanden")
        else:
            critical_missing.append("Berufsunfaehigkeitsversicherung (BU)")

        # RLV important for families
        if "rlv" in found:
            positives.append("Risikolebensversicherung vorhanden")

        # Unfallversicherung
        if "unfallversicherung" in found:
            positives.append("Unfallversicherung vorhanden")

        # Sachversicherungen
        sach_types = CHECKLIST_CATEGORIES["sachversicherung"]["types"]
        sach_found = [t for t in sach_types if t in contracts]
        if "privathaftpflicht" not in sach_found:
            critical_missing.append("Privathaftpflichtversicherung")
        else:
            positives.append("Privathaftpflicht vorhanden")

        # Rating
        if len(critical_missing) >= 2:
            rating = TrafficLight.RED
        elif critical_missing:
            rating = TrafficLight.YELLOW
        else:
            rating = TrafficLight.GREEN

        assessment = f"{len(found)} Absicherungs-Produkte erkannt."
        if critical_missing:
            assessment += f" Fehlend: {', '.join(critical_missing)}."

        return {
            "category": ScorecardCategory.ABSICHERUNG,
            "rating": rating,
            "assessment": assessment,
            "details": " | ".join(positives) if positives else None,
        }

    def _eval_vermoegen(self, contracts: dict) -> dict:
        """Evaluate Vermoegen & Kosten category."""
        total_beitrag = 0.0
        contract_count = 0
        issues = []

        for type_key, contract_list in contracts.items():
            for contract in contract_list:
                contract_count += 1
                fields = contract["fields"]
                # Sum up premiums
                for fname in ("beitrag", "beitrag_netto", "sparbeitrag",
                              "eigenbeitrag", "arbeitnehmerbeitrag", "sparrate"):
                    if fname in fields and fields[fname].get("value"):
                        try:
                            val = str(fields[fname]["value"]).replace(',', '.')
                            total_beitrag += float(val)
                        except (ValueError, TypeError):
                            pass

        # Check for duplicates (same type, multiple contracts)
        duplicates = [t for t, cl in contracts.items() if len(cl) > 1 and t != "sonstige"]
        if duplicates:
            labels = [CONTRACT_TYPES.get(t, {}).get("label", t) for t in duplicates]
            issues.append(f"Moegliche Doppelversicherung: {', '.join(labels)}")

        if contract_count == 0:
            return {
                "category": ScorecardCategory.VERMOEGEN_KOSTEN,
                "rating": TrafficLight.YELLOW,
                "assessment": "Keine Vertraege zur Bewertung vorhanden.",
            }

        # Simple assessment
        if total_beitrag > 0:
            assessment = f"Gesamtbeitraege: ca. {total_beitrag:,.2f} EUR/Monat ({contract_count} Vertraege)."
        else:
            assessment = f"{contract_count} Vertraege erkannt. Beitraege konnten nicht ermittelt werden."

        if issues:
            rating = TrafficLight.YELLOW
        else:
            rating = TrafficLight.GREEN

        return {
            "category": ScorecardCategory.VERMOEGEN_KOSTEN,
            "rating": rating,
            "assessment": assessment,
            "details": " | ".join(issues) if issues else None,
        }

    def _eval_steueroptimierung(self, contracts: dict) -> dict:
        """Evaluate Steueroptimierung category."""
        positives = []
        suggestions = []

        if "riester" in contracts:
            positives.append("Riester-Rente genutzt")
        else:
            suggestions.append("Riester-Foerderung pruefen")

        if "basisrente" in contracts:
            positives.append("Basisrente (Ruerup) genutzt")
        else:
            suggestions.append("Basisrente als Steuerspar-Option pruefen")

        if "bav" in contracts:
            positives.append("bAV genutzt (Entgeltumwandlung)")
        else:
            suggestions.append("Betriebliche Altersvorsorge pruefen")

        if len(positives) >= 2:
            rating = TrafficLight.GREEN
            assessment = "Gute steuerliche Optimierung."
        elif positives:
            rating = TrafficLight.YELLOW
            assessment = "Teilweise steuerlich optimiert."
        else:
            rating = TrafficLight.RED
            assessment = "Keine steuerlich gefoerderten Produkte erkannt."

        details_parts = positives + [f"Empfehlung: {s}" for s in suggestions]
        return {
            "category": ScorecardCategory.STEUEROPTIMIERUNG,
            "rating": rating,
            "assessment": assessment,
            "details": " | ".join(details_parts) if details_parts else None,
        }

    def _compute_overall(self, category_results: list[dict]) -> dict:
        """Compute overall score from category results."""
        rating_scores = {
            TrafficLight.GREEN: 3,
            TrafficLight.YELLOW: 2,
            TrafficLight.RED: 1,
        }

        total = sum(rating_scores.get(r["rating"], 2) for r in category_results)
        avg = total / len(category_results) if category_results else 2

        if avg >= 2.5:
            overall_rating = TrafficLight.GREEN
            assessment = "Gute finanzielle Gesamtaufstellung."
        elif avg >= 1.5:
            overall_rating = TrafficLight.YELLOW
            assessment = "Finanzielle Aufstellung mit Optimierungspotenzial."
        else:
            overall_rating = TrafficLight.RED
            assessment = "Deutlicher Handlungsbedarf bei der finanziellen Absicherung."

        red_cats = [r for r in category_results if r["rating"] == TrafficLight.RED]
        if red_cats:
            cat_labels = {
                ScorecardCategory.ALTERSVORSORGE: "Altersvorsorge",
                ScorecardCategory.ABSICHERUNG: "Absicherung",
                ScorecardCategory.VERMOEGEN_KOSTEN: "Vermoegen & Kosten",
                ScorecardCategory.STEUEROPTIMIERUNG: "Steueroptimierung",
            }
            names = [cat_labels.get(r["category"], r["category"]) for r in red_cats]
            assessment += f" Kritisch: {', '.join(names)}."

        return {
            "category": "overall",
            "rating": overall_rating,
            "assessment": assessment,
            "is_overall": True,
        }
