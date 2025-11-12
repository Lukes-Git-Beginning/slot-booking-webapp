# -*- coding: utf-8 -*-
"""
Executive Reports System für CEO-taugliche Berichte
Professionelle Weekly & Monthly Reports für Telefonie-Punktesystem
"""

import json
import os
import pytz
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict

from app.services.weekly_points import (
    load_data, compute_week_stats, get_participants,
    get_week_key, list_recent_weeks, is_user_on_vacation
)

TZ = pytz.timezone("Europe/Berlin")

class ExecutiveReports:
    def __init__(self):
        self.data_dir = os.path.join("data", "persistent")
        self.reports_dir = os.path.join("data", "reports")
        os.makedirs(self.reports_dir, exist_ok=True)

    def generate_weekly_executive_report(self, week_key: Optional[str] = None) -> Dict[str, Any]:
        """Generiere professionellen Wochenbericht für CEO"""
        if week_key is None:
            week_key = get_week_key()

        participants = get_participants()
        stats = compute_week_stats(week_key, participants)

        # Parse week info
        year, week_num = week_key.split('-')
        week_start = datetime.strptime(f"{year}-W{week_num}-1", "%Y-W%W-%w")

        report = {
            "meta": {
                "report_type": "weekly_executive",
                "week": week_key,
                "year": int(year),
                "week_number": int(week_num),
                "week_start": week_start.strftime("%d.%m.%Y"),
                "week_end": (week_start + timedelta(days=6)).strftime("%d.%m.%Y"),
                "generated_at": datetime.now(TZ).strftime("%d.%m.%Y %H:%M"),
                "total_participants": len(participants)
            },

            "executive_summary": self._generate_executive_summary(stats, week_key),
            "performance_overview": self._generate_performance_overview(stats, participants, week_key),
            "absence_analysis": self._generate_absence_analysis(participants, week_key),
            "trends_analysis": self._generate_trends_analysis(week_key),
            "action_items": self._generate_action_items(stats, week_key),
            "detailed_breakdown": stats
        }

        # Save report
        report_file = os.path.join(self.reports_dir, f"weekly_executive_{week_key}.json")
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return report

    def generate_monthly_executive_report(self, year: Optional[int] = None, month: Optional[int] = None) -> Dict[str, Any]:
        """Generiere professionellen Monatsbericht für CEO"""
        now = datetime.now(TZ)
        if year is None:
            year = now.year
        if month is None:
            month = now.month

        # Get all weeks in this month
        weeks_in_month = self._get_weeks_in_month(year, month)
        participants = get_participants()

        monthly_stats = self._aggregate_monthly_stats(weeks_in_month, participants)

        report = {
            "meta": {
                "report_type": "monthly_executive",
                "year": year,
                "month": month,
                "month_name": datetime(year, month, 1).strftime("%B %Y"),
                "generated_at": datetime.now(TZ).strftime("%d.%m.%Y %H:%M"),
                "weeks_included": len(weeks_in_month),
                "total_participants": len(participants)
            },

            "executive_summary": self._generate_monthly_summary(monthly_stats, year, month),
            "monthly_performance": self._generate_monthly_performance(monthly_stats, weeks_in_month),
            "individual_analysis": self._generate_individual_monthly_analysis(monthly_stats, participants),
            "absence_impact": self._generate_monthly_absence_analysis(weeks_in_month, participants),
            "trends_forecast": self._generate_monthly_trends(year, month),
            "recommendations": self._generate_monthly_recommendations(monthly_stats),
            "detailed_data": monthly_stats
        }

        # Save report
        report_file = os.path.join(self.reports_dir, f"monthly_executive_{year}_{month:02d}.json")
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return report

    def _generate_executive_summary(self, stats: Dict, week_key: str) -> Dict:
        """Generate executive summary with traffic light system"""
        total_goal = stats["summary"]["total_goal"]
        total_achieved = stats["summary"]["total_achieved"]
        achievement_rate = (total_achieved / total_goal * 100) if total_goal > 0 else 0

        # Traffic light logic
        if achievement_rate >= 90:
            status = {"color": "green", "status": "Ausgezeichnet", "icon": "🟢"}
        elif achievement_rate >= 70:
            status = {"color": "yellow", "status": "Gut", "icon": "🟡"}
        else:
            status = {"color": "red", "status": "Aufmerksamkeit erforderlich", "icon": "🔴"}

        return {
            "overall_status": status,
            "key_metrics": {
                "achievement_rate": round(achievement_rate, 1),
                "total_points_goal": total_goal,
                "total_points_achieved": total_achieved,
                "points_remaining": stats["summary"]["total_remaining"],
                "team_performance": status["status"]
            },
            "highlights": [
                f"Team erreichte {total_achieved} von {total_goal} Punkten ({achievement_rate:.1f}%)",
                f"Leistungsstatus: {status['icon']} {status['status']}",
                f"{len([u for u in stats['users'] if u['balance'] >= 0])} von {len(stats['users'])} Teammitgliedern erfüllen/übertreffen Ziele"
            ]
        }

    def _generate_performance_overview(self, stats: Dict, participants: List[str], week_key: str) -> Dict:
        """Generate team performance breakdown with individual status"""
        performers = {"high": [], "medium": [], "low": []}

        for user_stat in stats["users"]:
            user = user_stat["user"]
            goal = user_stat["goal"]
            achieved = user_stat["achieved"]

            if goal == 0:
                category = "medium"  # Vacation or no goal set
            else:
                achievement_rate = (achieved / goal * 100) if goal > 0 else 0
                if achievement_rate >= 90:
                    category = "high"
                elif achievement_rate >= 70:
                    category = "medium"
                else:
                    category = "low"

            performers[category].append({
                "name": user,
                "goal": goal,
                "achieved": achieved,
                "rate": round((achieved / goal * 100) if goal > 0 else 0, 1),
                "on_vacation": user_stat.get("on_vacation", False)
            })

        return {
            "team_distribution": {
                "high_performers": len(performers["high"]),
                "medium_performers": len(performers["medium"]),
                "low_performers": len(performers["low"])
            },
            "performers": performers,
            "team_health": "Ausgezeichnet" if len(performers["low"]) == 0 else "Gut" if len(performers["low"]) <= 2 else "Aufmerksamkeit erforderlich"
        }

    def _generate_absence_analysis(self, participants: List[str], week_key: str) -> Dict:
        """Analyze absences and their impact"""
        absent_users = []
        total_absent = 0

        for user in participants:
            vacation_info = is_user_on_vacation(user, datetime.now(TZ))
            if vacation_info["on_vacation"]:
                absent_users.append({
                    "name": user,
                    "reason": vacation_info["reason"],
                    "period": vacation_info.get("period")
                })
                total_absent += 1

        absence_rate = (total_absent / len(participants) * 100) if participants else 0

        return {
            "total_absent": total_absent,
            "absence_rate": round(absence_rate, 1),
            "absent_users": absent_users,
            "impact": "Low" if absence_rate < 20 else "Medium" if absence_rate < 40 else "High",
            "operational_status": "Normal" if absence_rate < 30 else "Reduced capacity"
        }

    def _generate_trends_analysis(self, week_key: str) -> Dict:
        """Analyze performance trends over recent weeks"""
        recent_weeks = list_recent_weeks(4)  # Last 4 weeks
        participants = get_participants()

        weekly_performance = []
        for week in reversed(recent_weeks):  # Chronological order
            try:
                week_stats = compute_week_stats(week, participants)
                total_goal = week_stats["summary"]["total_goal"]
                total_achieved = week_stats["summary"]["total_achieved"]
                achievement_rate = (total_achieved / total_goal * 100) if total_goal > 0 else 0

                weekly_performance.append({
                    "week": week,
                    "achievement_rate": round(achievement_rate, 1),
                    "total_points": total_achieved,
                    "goal_points": total_goal
                })
            except:
                continue

        # Calculate trend
        if len(weekly_performance) >= 2:
            current_rate = weekly_performance[-1]["achievement_rate"]
            previous_rate = weekly_performance[-2]["achievement_rate"]
            trend_direction = "steigend" if current_rate > previous_rate else "fallend" if current_rate < previous_rate else "stabil"
            trend_change = round(current_rate - previous_rate, 1)
        else:
            trend_direction = "insufficient_data"
            trend_change = 0

        return {
            "trend_direction": trend_direction,
            "trend_change": trend_change,
            "weekly_data": weekly_performance,
            "average_performance": round(sum(w["achievement_rate"] for w in weekly_performance) / len(weekly_performance), 1) if weekly_performance else 0
        }

    def _generate_action_items(self, stats: Dict, week_key: str) -> List[str]:
        """Generate specific action items based on performance"""
        actions = []

        total_goal = stats["summary"]["total_goal"]
        total_achieved = stats["summary"]["total_achieved"]
        achievement_rate = (total_achieved / total_goal * 100) if total_goal > 0 else 0

        # Overall performance actions
        if achievement_rate < 70:
            actions.append("🎯 Teamziele überprüfen und bei Bedarf anpassen - aktuelle Erreichungsrate unter 70%")
            actions.append("🗣️ Individuelle Leistungsgespräche mit unterdurchschnittlichen Teammitgliedern planen")

        # Individual performance actions
        low_performers = [u for u in stats["users"] if u["goal"] > 0 and (u["achieved"] / u["goal"] * 100) < 60]
        if low_performers:
            actions.append(f"👥 Unterstützung auf {len(low_performers)} Teammitglieder fokussieren, die deutlich hinter den Zielen zurückliegen")

        # High performers recognition
        high_performers = [u for u in stats["users"] if u["goal"] > 0 and (u["achieved"] / u["goal"] * 100) >= 110]
        if high_performers:
            actions.append(f"🏆 {len(high_performers)} Top-Leister anerkennen und feiern, die Ziele übertreffen")

        # Goal setting
        users_without_goals = [u for u in stats["users"] if u["goal"] == 0 and not u.get("on_vacation")]
        if users_without_goals:
            actions.append(f"📋 Ziele für {len(users_without_goals)} Teammitglieder festlegen, die aktuell keine Ziele haben")

        return actions

    def _get_weeks_in_month(self, year: int, month: int) -> List[str]:
        """Get all ISO week keys that fall within the given month"""
        from calendar import monthrange

        # First and last day of month
        first_day = datetime(year, month, 1)
        last_day = datetime(year, month, monthrange(year, month)[1])

        weeks = set()
        current_date = first_day

        while current_date <= last_day:
            week_key = get_week_key(current_date)
            weeks.add(week_key)
            current_date += timedelta(days=1)

        return sorted(list(weeks))

    def _aggregate_monthly_stats(self, weeks: List[str], participants: List[str]) -> Dict:
        """Aggregate statistics across multiple weeks for monthly report"""
        monthly_data = {
            "total_goal": 0,
            "total_achieved": 0,
            "weeks_count": len(weeks),
            "user_totals": defaultdict(lambda: {"goal": 0, "achieved": 0, "weeks_active": 0}),
            "weekly_breakdown": []
        }

        for week in weeks:
            try:
                week_stats = compute_week_stats(week, participants)
                monthly_data["total_goal"] += week_stats["summary"]["total_goal"]
                monthly_data["total_achieved"] += week_stats["summary"]["total_achieved"]

                weekly_summary = {
                    "week": week,
                    "goal": week_stats["summary"]["total_goal"],
                    "achieved": week_stats["summary"]["total_achieved"],
                    "achievement_rate": round((week_stats["summary"]["total_achieved"] / week_stats["summary"]["total_goal"] * 100) if week_stats["summary"]["total_goal"] > 0 else 0, 1)
                }
                monthly_data["weekly_breakdown"].append(weekly_summary)

                for user_stat in week_stats["users"]:
                    user = user_stat["user"]
                    monthly_data["user_totals"][user]["goal"] += user_stat["goal"]
                    monthly_data["user_totals"][user]["achieved"] += user_stat["achieved"]
                    if user_stat["goal"] > 0 or user_stat["achieved"] > 0:
                        monthly_data["user_totals"][user]["weeks_active"] += 1

            except Exception as e:
                print(f"Warning: Could not process week {week}: {e}")
                continue

        return monthly_data

    def _generate_monthly_summary(self, monthly_stats: Dict, year: int, month: int) -> Dict:
        """Generate executive monthly summary"""
        total_goal = monthly_stats["total_goal"]
        total_achieved = monthly_stats["total_achieved"]
        achievement_rate = (total_achieved / total_goal * 100) if total_goal > 0 else 0

        # Monthly status
        if achievement_rate >= 85:
            status = {"color": "green", "status": "Ausgezeichneter Monat", "icon": "🟢"}
        elif achievement_rate >= 70:
            status = {"color": "yellow", "status": "Guter Monat", "icon": "🟡"}
        else:
            status = {"color": "red", "status": "Herausfordernder Monat", "icon": "🔴"}

        return {
            "overall_status": status,
            "key_metrics": {
                "monthly_achievement_rate": round(achievement_rate, 1),
                "total_monthly_goal": total_goal,
                "total_monthly_achieved": total_achieved,
                "weeks_analyzed": monthly_stats["weeks_count"],
                "average_weekly_performance": round(achievement_rate, 1)
            },
            "month_highlights": [
                f"Monatliche Teamleistung: {total_achieved} von {total_goal} Punkten ({achievement_rate:.1f}%)",
                f"Leistung über {monthly_stats['weeks_count']} Wochen: {status['icon']} {status['status']}",
                f"Durchschnittliche wöchentliche Erreichungsrate: {achievement_rate:.1f}%"
            ]
        }

    def _generate_monthly_performance(self, monthly_stats: Dict, weeks: List[str]) -> Dict:
        """Generate monthly performance analysis"""
        weekly_breakdown = monthly_stats["weekly_breakdown"]

        # Find best and worst weeks
        if weekly_breakdown:
            best_week = max(weekly_breakdown, key=lambda w: w["achievement_rate"])
            worst_week = min(weekly_breakdown, key=lambda w: w["achievement_rate"])
            avg_rate = sum(w["achievement_rate"] for w in weekly_breakdown) / len(weekly_breakdown)
        else:
            best_week = worst_week = {"week": "N/A", "achievement_rate": 0}
            avg_rate = 0

        return {
            "average_weekly_rate": round(avg_rate, 1),
            "best_week": {
                "week": best_week["week"],
                "rate": best_week["achievement_rate"],
                "points": best_week["achieved"]
            },
            "worst_week": {
                "week": worst_week["week"],
                "rate": worst_week["achievement_rate"],
                "points": worst_week["achieved"]
            },
            "consistency": "High" if (max(w["achievement_rate"] for w in weekly_breakdown) - min(w["achievement_rate"] for w in weekly_breakdown)) < 20 else "Medium" if (max(w["achievement_rate"] for w in weekly_breakdown) - min(w["achievement_rate"] for w in weekly_breakdown)) < 40 else "Low",
            "weekly_data": weekly_breakdown
        }

    def _generate_individual_monthly_analysis(self, monthly_stats: Dict, participants: List[str]) -> Dict:
        """Individual team member monthly analysis"""
        individual_analysis = {}

        for user in participants:
            user_data = monthly_stats["user_totals"][user]
            goal = user_data["goal"]
            achieved = user_data["achieved"]
            weeks_active = user_data["weeks_active"]

            achievement_rate = (achieved / goal * 100) if goal > 0 else 0
            avg_weekly_points = achieved / weeks_active if weeks_active > 0 else 0

            # Performance rating
            if achievement_rate >= 90:
                rating = {"level": "Ausgezeichnet", "icon": "🏆", "color": "green"}
            elif achievement_rate >= 75:
                rating = {"level": "Gut", "icon": "👍", "color": "yellow"}
            else:
                rating = {"level": "Verbesserungsbedarf", "icon": "📈", "color": "red"}

            individual_analysis[user] = {
                "monthly_goal": goal,
                "monthly_achieved": achieved,
                "achievement_rate": round(achievement_rate, 1),
                "weeks_active": weeks_active,
                "avg_weekly_points": round(avg_weekly_points, 1),
                "performance_rating": rating
            }

        return individual_analysis

    def _generate_monthly_absence_analysis(self, weeks: List[str], participants: List[str]) -> Dict:
        """Analyze monthly absence patterns"""
        # This would require more detailed vacation tracking
        # For now, return basic structure
        return {
            "total_absence_days": 0,
            "most_absent_reason": "Urlaub",
            "absence_impact": "Niedrig",
            "planning_insights": ["Abwesenheitsmuster für zukünftige Planung berücksichtigen"]
        }

    def _generate_monthly_trends(self, year: int, month: int) -> Dict:
        """Generate monthly trends and forecasting"""
        return {
            "trend_direction": "stabil",
            "predicted_next_month": "Ähnliche Leistung erwartet",
            "growth_opportunities": [
                "Fokus auf Konsistenz über alle Wochen",
                "Unterstützung für Teammitglieder mit variabler Leistung"
            ]
        }

    def _generate_monthly_recommendations(self, monthly_stats: Dict) -> List[str]:
        """Generate actionable monthly recommendations"""
        recommendations = []

        total_goal = monthly_stats["total_goal"]
        total_achieved = monthly_stats["total_achieved"]
        achievement_rate = (total_achieved / total_goal * 100) if total_goal > 0 else 0

        if achievement_rate < 80:
            recommendations.append("🎯 Monatlichen Zielsetzungsprozess überprüfen und anpassen")
            recommendations.append("📊 Wöchentliche Check-ins implementieren, um Fortschritt zu verfolgen")

        if monthly_stats["weeks_count"] < 4:
            recommendations.append("📅 Konsistente Zielsetzung über alle Wochen des Monats sicherstellen")

        recommendations.append("🏆 Top-Leister weiterhin anerkennen, um Motivation aufrechtzuerhalten")
        recommendations.append("📈 Fokus auf Unterstützung von Teammitgliedern mit variabler Leistung")

        return recommendations

# Convenience functions
def generate_current_weekly_report() -> Dict:
    """Generate report for current week"""
    reports = ExecutiveReports()
    return reports.generate_weekly_executive_report()

def generate_current_monthly_report() -> Dict:
    """Generate report for current month"""
    reports = ExecutiveReports()
    now = datetime.now(TZ)
    return reports.generate_monthly_executive_report(now.year, now.month)

def get_available_reports() -> Dict:
    """Get list of all available reports"""
    reports_dir = os.path.join("data", "reports")
    if not os.path.exists(reports_dir):
        return {"weekly": [], "monthly": []}

    weekly_reports = []
    monthly_reports = []

    for filename in os.listdir(reports_dir):
        if filename.startswith("weekly_executive_") and filename.endswith(".json"):
            week = filename.replace("weekly_executive_", "").replace(".json", "")
            weekly_reports.append(week)
        elif filename.startswith("monthly_executive_") and filename.endswith(".json"):
            month_part = filename.replace("monthly_executive_", "").replace(".json", "")
            monthly_reports.append(month_part)

    return {
        "weekly": sorted(weekly_reports, reverse=True),
        "monthly": sorted(monthly_reports, reverse=True)
    }
