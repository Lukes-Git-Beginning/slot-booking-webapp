# -*- coding: utf-8 -*-
"""
Consultant Ranking Service
Kombiniert Tracking-Daten (Show-Rates) mit Telefonie-Daten (Weekly Points)
für ein vollständiges Berater-Performance-Ranking
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pytz

from app.config.base import consultant_config

logger = logging.getLogger(__name__)
TZ = pytz.timezone("Europe/Berlin")


class ConsultantRankingService:
    """
    Service für kombiniertes Berater-Ranking

    Kombiniert:
    - Show-Rates aus dem Tracking-System (Qualität)
    - Weekly Points aus dem Telefonie-System (Aktivität/Zielerreichung)
    """

    # Gewichtung für Combined Score
    WEIGHT_SHOW_RATE = 0.4        # Qualität (Erschienen-Quote)
    WEIGHT_ACHIEVEMENT = 0.3      # Zielerreichung (% vom Goal)
    WEIGHT_ACTIVITY = 0.2        # Aktivitätsvolumen (T1+T2+Tel)
    WEIGHT_CONSISTENCY = 0.1      # Konsistenz (niedrige Varianz)

    # Festvertrag-Telefonisten: Keine eigenen Ziele, daher Achievement/Consistency
    # nicht relevant. Score wird nur auf Show-Rate + Activity gewichtet.
    FIXED_CONTRACT = {"Ann-Kathrin", "Yasmine", "Ben"}

    def __init__(self):
        # Nur aktive Telefonisten im Ranking anzeigen (nicht alle Consultants)
        all_consultants = consultant_config.get_consultants()
        active_telefonists = consultant_config.get_active_telefonists()
        self.consultants = [name for name in active_telefonists if name in all_consultants]

    def get_combined_performance(self, start_date_str: str, end_date_str: str) -> List[Dict]:
        """
        Berechne kombinierte Performance aller Berater

        Args:
            start_date_str: Start-Datum (YYYY-MM-DD)
            end_date_str: End-Datum (YYYY-MM-DD)

        Returns:
            Liste von Berater-Performance-Dicts, sortiert nach Combined Score
        """
        try:
            # Import hier um zirkuläre Imports zu vermeiden
            from app.core.extensions import tracking_system
            from app.services import weekly_points

            # 1. Hole Show-Rates aus Tracking-System
            show_rates = {}
            bookings_created = {}
            if tracking_system:
                raw_show_rates = tracking_system.get_consultant_performance(start_date_str, end_date_str)
                # Case-insensitive mapping: Login-Namen können andere Gross-/Kleinschreibung haben
                show_rates = {k.lower(): v for k, v in raw_show_rates.items()}
                # Hole auch T1-Buchungen nach Erstellungsdatum
                bookings_data = tracking_system.get_bookings_by_creation_date(start_date_str, end_date_str)
                raw_bookings = bookings_data.get("by_user", {})
                # Case-insensitive mapping: Login-Namen können andere Gross-/Kleinschreibung haben
                bookings_created = {k.lower(): v for k, v in raw_bookings.items()}

            # 2. Hole Telefonie-Daten
            telefonie_data = self._get_telefonie_performance(start_date_str, end_date_str)

            # 3. Kombiniere Daten für alle Berater
            combined = []
            for consultant in self.consultants:
                show_data = show_rates.get(consultant.lower(), {})
                tel_data = telefonie_data.get(consultant, {})

                is_fixed = consultant in self.FIXED_CONTRACT

                consultant_perf = {
                    "name": consultant,
                    "fixed_contract": is_fixed,
                    # Show-Rate Daten
                    "show_rate": show_data.get("appearance_rate", 0.0),
                    "total_slots": show_data.get("total_slots", 0),
                    "completed": show_data.get("completed", 0),
                    "no_shows": show_data.get("no_shows", 0),
                    "cancelled": show_data.get("cancelled", 0),
                    "rescheduled": show_data.get("rescheduled", 0),
                    "overhang": show_data.get("overhang", 0),
                    # T1 Buchungen (nach Erstellungsdatum) - case-insensitive lookup
                    "t1_booked": bookings_created.get(consultant.lower(), 0),
                    # Telefonie Daten
                    "telefonie_achievement": tel_data.get("achievement_rate", 0.0),
                    "telefonie_points": tel_data.get("total_points", 0),
                    "telefonie_goal": tel_data.get("total_goal", 0),
                    "t1_count": tel_data.get("t1_activities", 0),
                    "t2_count": tel_data.get("t2_activities", 0),
                    "tel_count": tel_data.get("tel_activities", 0),
                    "total_activities": tel_data.get("total_activities", 0),
                    "consistency_score": tel_data.get("consistency_score", 50.0),
                    "weeks_analyzed": tel_data.get("weeks_analyzed", 0),
                }

                # Berechne Combined Score
                consultant_perf["combined_score"] = self._calculate_combined_score(
                    consultant_perf["show_rate"],
                    consultant_perf["telefonie_achievement"],
                    consultant_perf["total_activities"],
                    consultant_perf["consistency_score"],
                    is_fixed_contract=is_fixed
                )

                # Klassifiziere Performance
                consultant_perf["category"] = self._classify_performance(
                    consultant_perf["combined_score"]
                )

                combined.append(consultant_perf)

            # 4. Sortiere nach Combined Score (absteigend)
            combined.sort(key=lambda x: x["combined_score"], reverse=True)

            # 5. Füge Ranking hinzu
            for idx, consultant in enumerate(combined, 1):
                consultant["rank"] = idx

            return combined

        except Exception as e:
            logger.error(f"Fehler bei get_combined_performance: {e}")
            return []

    def _get_telefonie_performance(self, start_date_str: str, end_date_str: str) -> Dict:
        """
        Aggregiere Telefonie-Performance für einen Zeitraum

        Returns:
            Dict mit Performance pro Berater
        """
        try:
            from app.services import weekly_points

            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d")

            # Finde alle ISO-Wochen im Zeitraum
            weeks_in_range = []
            current = start_date
            while current <= end_date:
                week_key = weekly_points.get_week_key(current)
                if week_key not in weeks_in_range:
                    weeks_in_range.append(week_key)
                current += timedelta(days=7)

            # Aggregiere Daten pro Berater
            result = {}
            for consultant in self.consultants:
                total_points = 0
                total_goal = 0
                t1_activities = 0
                t2_activities = 0
                tel_activities = 0
                weeks_with_data = 0
                weekly_achievements = []

                for week_key in weeks_in_range:
                    try:
                        stats = weekly_points.compute_user_stats(week_key, consultant)
                        if stats["goal"] > 0 or stats["achieved"] > 0:
                            weeks_with_data += 1
                            total_points += stats["achieved"]
                            total_goal += stats["goal"]

                            if stats["goal"] > 0:
                                weekly_achievements.append(
                                    (stats["achieved"] / stats["goal"]) * 100
                                )

                            # Zähle Aktivitäten nach Typ
                            data = weekly_points.load_data()
                            if week_key in data["weeks"] and consultant in data["weeks"][week_key]["users"]:
                                user_data = data["weeks"][week_key]["users"][consultant]
                                for activity in user_data.get("activities", []):
                                    kind = activity.get("kind", "").lower()
                                    if kind == "t1":
                                        t1_activities += 1
                                    elif kind == "t2":
                                        t2_activities += 1
                                    elif kind == "telefonie":
                                        tel_activities += 1
                    except Exception:
                        continue

                # Berechne Achievement Rate
                achievement_rate = 0.0
                if total_goal > 0:
                    achievement_rate = round((total_points / total_goal) * 100, 1)

                # Berechne Consistency Score (basierend auf Varianz)
                consistency_score = 50.0  # Default
                if len(weekly_achievements) >= 2:
                    avg = sum(weekly_achievements) / len(weekly_achievements)
                    variance = sum((x - avg) ** 2 for x in weekly_achievements) / len(weekly_achievements)
                    std_dev = variance ** 0.5
                    # Niedrigere Varianz = höhere Konsistenz (max 100)
                    consistency_score = max(0, min(100, 100 - std_dev))

                result[consultant] = {
                    "total_points": total_points,
                    "total_goal": total_goal,
                    "achievement_rate": achievement_rate,
                    "t1_activities": t1_activities,
                    "t2_activities": t2_activities,
                    "tel_activities": tel_activities,
                    "total_activities": t1_activities + t2_activities + tel_activities,
                    "weeks_analyzed": weeks_with_data,
                    "consistency_score": round(consistency_score, 1)
                }

            return result

        except Exception as e:
            logger.error(f"Fehler bei _get_telefonie_performance: {e}")
            return {}

    def _calculate_combined_score(
        self,
        show_rate: float,
        achievement_rate: float,
        total_activities: int,
        consistency_score: float,
        is_fixed_contract: bool = False
    ) -> float:
        """
        Berechne gewichteten Combined Score

        Normale Telefonisten:
            Score = Show Rate * 0.4 + Achievement * 0.3 + Activity * 0.2 + Consistency * 0.1

        Festvertrag (kein eigenes Ziel):
            Score = Show Rate * 0.65 + Activity * 0.35
            Achievement und Consistency entfallen.

        Returns:
            Combined Score (0-100)
        """
        # Normalisiere Activity Volume auf 0-100 (max 30 Aktivitäten = 100%)
        activity_normalized = min(total_activities / 30 * 100, 100)

        if is_fixed_contract:
            # Festvertrag: Nur Show-Rate und Aktivität zählen
            score = (
                show_rate * 0.65 +
                activity_normalized * 0.35
            )
        else:
            # Cap achievement rate at 150% for scoring purposes
            achievement_capped = min(achievement_rate, 150)

            score = (
                show_rate * self.WEIGHT_SHOW_RATE +
                achievement_capped * self.WEIGHT_ACHIEVEMENT +
                activity_normalized * self.WEIGHT_ACTIVITY +
                consistency_score * self.WEIGHT_CONSISTENCY
            )

        return round(score, 1)

    def _classify_performance(self, score: float) -> str:
        """
        Klassifiziere Performance-Level

        Args:
            score: Combined Score

        Returns:
            'high', 'medium', oder 'low'
        """
        if score >= 70:
            return "high"
        elif score >= 45:
            return "medium"
        else:
            return "low"

    def get_ranking_summary(self, start_date_str: str, end_date_str: str) -> Dict:
        """
        Hole Ranking-Zusammenfassung mit Statistiken

        Returns:
            Dict mit Ranking und Zusammenfassungs-Statistiken
        """
        try:
            rankings = self.get_combined_performance(start_date_str, end_date_str)

            if not rankings:
                return {
                    "rankings": [],
                    "summary": {
                        "total_consultants": 0,
                        "high_performers": 0,
                        "medium_performers": 0,
                        "low_performers": 0,
                        "avg_show_rate": 0.0,
                        "avg_achievement": 0.0
                    }
                }

            # Berechne Zusammenfassung
            high_count = sum(1 for r in rankings if r["category"] == "high")
            medium_count = sum(1 for r in rankings if r["category"] == "medium")
            low_count = sum(1 for r in rankings if r["category"] == "low")

            avg_show_rate = sum(r["show_rate"] for r in rankings) / len(rankings)
            avg_achievement = sum(r["telefonie_achievement"] for r in rankings) / len(rankings)
            total_t1_booked = sum(r["t1_booked"] for r in rankings)

            return {
                "rankings": rankings,
                "period": {
                    "start_date": start_date_str,
                    "end_date": end_date_str
                },
                "summary": {
                    "total_consultants": len(rankings),
                    "high_performers": high_count,
                    "medium_performers": medium_count,
                    "low_performers": low_count,
                    "avg_show_rate": round(avg_show_rate, 1),
                    "avg_achievement": round(avg_achievement, 1),
                    "total_t1_booked": total_t1_booked
                }
            }

        except Exception as e:
            logger.error(f"Fehler bei get_ranking_summary: {e}")
            return {"rankings": [], "summary": {}}


# Singleton-Instanz für einfachen Import
consultant_ranking_service = ConsultantRankingService()
