# -*- coding: utf-8 -*-
"""
Advanced Analytics & Personal Insights System für Slot Booking Webapp
Detaillierte Statistiken, Verhaltensmuster und Zukunftsprognosen
"""

import os
import json
import pytz
import numpy as np
import logging
from datetime import datetime, timedelta, time
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Optional

# Logger setup
logger = logging.getLogger(__name__)

TZ = pytz.timezone("Europe/Berlin")

class AdvancedAnalytics:
    def __init__(self):
        self.analytics_file = "data/persistent/user_analytics.json"
        self.insights_file = "data/persistent/personal_insights.json"
        self.predictions_file = "data/persistent/user_predictions.json"
        self.patterns_file = "data/persistent/behavior_patterns.json"
        
        # Ensure directories exist
        os.makedirs("data/persistent", exist_ok=True)
        
        # Initialize files
        for file_path in [self.analytics_file, self.insights_file, self.predictions_file, self.patterns_file]:
            if not os.path.exists(file_path):
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump({}, f)
    
    def generate_user_analytics(self, user):
        """Generiere umfassende Analytics für einen User"""
        analytics = {
            "user": user,
            "generated_at": datetime.now(TZ).isoformat(),
            "overview": self._generate_overview_stats(user),
            "booking_patterns": self._analyze_booking_patterns(user),
            "performance_trends": self._analyze_performance_trends(user),
            "behavioral_insights": self._generate_behavioral_insights(user),
            "achievements_analysis": self._analyze_achievements(user),
            "predictions": self._generate_predictions(user),
            "recommendations": self._generate_recommendations(user),
            "comparisons": self._generate_peer_comparisons(user)
        }
        
        # Speichere generierte Analytics
        all_analytics = self.load_analytics()
        all_analytics[user] = analytics
        self.save_analytics(all_analytics)
        
        return analytics
    
    def _generate_overview_stats(self, user):
        """Generiere Überblicks-Statistiken"""
        stats = {
            "total_days_active": 0,
            "average_daily_bookings": 0,
            "peak_activity_day": "Montag",
            "peak_activity_time": "10:00",
            "total_points_earned": 0,
            "current_streak": 0,
            "longest_streak": 0,
            "efficiency_score": 0,
            "consistency_rating": "Gut",
            "activity_level": "Mittel"
        }
        
        try:
            # Lade User-Daten
            from achievement_system import achievement_system
            from tracking_system import BookingTracker
            
            daily_stats = achievement_system.load_daily_stats()
            user_stats = daily_stats.get(user, {})
            
            tracker = BookingTracker()
            user_bookings = tracker.load_all_bookings()
            user_bookings = [b for b in user_bookings if b.get("user") == user]
            
            if user_stats:
                stats["total_days_active"] = len([d for d, s in user_stats.items() if s.get("points", 0) > 0])
                
                # Berechne Durchschnitt
                if stats["total_days_active"] > 0:
                    total_bookings = sum(s.get("bookings", 0) for s in user_stats.values())
                    stats["average_daily_bookings"] = round(total_bookings / stats["total_days_active"], 2)
                
                # Finde Peak-Aktivität
                day_counts = defaultdict(int)
                hour_counts = defaultdict(int)
                
                for booking in user_bookings:
                    if booking.get("weekday"):
                        day_counts[booking["weekday"]] += 1
                    if booking.get("time"):
                        hour = booking["time"].split(":")[0] + ":00"
                        hour_counts[hour] += 1
                
                if day_counts:
                    stats["peak_activity_day"] = max(day_counts.items(), key=lambda x: x[1])[0]
                if hour_counts:
                    stats["peak_activity_time"] = max(hour_counts.items(), key=lambda x: x[1])[0]
                
                # Berechne Streaks
                streak_info = achievement_system.calculate_advanced_streak(user_stats)
                stats["current_streak"] = streak_info.get("work_streak", 0)
                stats["longest_streak"] = streak_info.get("best_streak", 0)
                
                # Efficiency Score basierend auf Buchungen/Zeit
                if len(user_bookings) > 0:
                    stats["efficiency_score"] = min(100, len(user_bookings) * 2)  # 2 Punkte pro Buchung
                
                # Aktivitätslevel bestimmen
                if stats["average_daily_bookings"] >= 5:
                    stats["activity_level"] = "Sehr Hoch"
                elif stats["average_daily_bookings"] >= 3:
                    stats["activity_level"] = "Hoch"
                elif stats["average_daily_bookings"] >= 1:
                    stats["activity_level"] = "Mittel"
                else:
                    stats["activity_level"] = "Niedrig"
                
                # Konsistenz bewerten
                if stats["current_streak"] >= 14:
                    stats["consistency_rating"] = "Exzellent"
                elif stats["current_streak"] >= 7:
                    stats["consistency_rating"] = "Sehr Gut"
                elif stats["current_streak"] >= 3:
                    stats["consistency_rating"] = "Gut"
                else:
                    stats["consistency_rating"] = "Verbesserungsfähig"
        
        except Exception as e:
            logger.error(f"Fehler bei Overview-Generierung für {user}", extra={'error': str(e)})
        
        return stats
    
    def _analyze_booking_patterns(self, user):
        """Analysiere Buchungsmuster und -gewohnheiten"""
        patterns = {
            "preferred_times": [],
            "preferred_days": [],
            "booking_velocity": "Normal",
            "advance_booking_days": 0,
            "seasonal_patterns": {},
            "weekly_distribution": {},
            "hourly_distribution": {},
            "booking_clusters": [],
            "consistency_score": 0
        }
        
        try:
            from tracking_system import BookingTracker
            tracker = BookingTracker()
            user_bookings = tracker.load_all_bookings()
            user_bookings = [b for b in user_bookings if b.get("user") == user]
            
            if not user_bookings:
                return patterns
            
            # Zeitanalyse
            hour_counts = Counter()
            day_counts = Counter()
            month_counts = Counter()
            advance_days = []
            
            for booking in user_bookings:
                # Stunde
                if booking.get("time"):
                    hour = int(booking["time"].split(":")[0])
                    hour_counts[hour] += 1
                
                # Wochentag
                if booking.get("weekday"):
                    day_counts[booking["weekday"]] += 1
                
                # Monat
                if booking.get("date"):
                    month = booking["date"][:7]  # YYYY-MM
                    month_counts[month] += 1
                
                # Vorlaufzeit
                lead_time = booking.get("booking_lead_time", 0)
                if lead_time >= 0:
                    advance_days.append(lead_time)
            
            # Top Zeiten und Tage
            patterns["preferred_times"] = [f"{h}:00" for h, _ in hour_counts.most_common(3)]
            patterns["preferred_days"] = [day for day, _ in day_counts.most_common(3)]
            
            # Durchschnittliche Vorlaufzeit
            if advance_days:
                patterns["advance_booking_days"] = round(sum(advance_days) / len(advance_days), 1)
            
            # Verteilungen
            patterns["hourly_distribution"] = dict(hour_counts)
            patterns["weekly_distribution"] = dict(day_counts)
            patterns["seasonal_patterns"] = dict(month_counts)
            
            # Buchungsgeschwindigkeit bewerten
            recent_bookings = [b for b in user_bookings 
                             if (datetime.now() - datetime.fromisoformat(b.get("timestamp", datetime.now().isoformat()))).days <= 30]
            
            if len(recent_bookings) >= 10:
                patterns["booking_velocity"] = "Hoch"
            elif len(recent_bookings) >= 5:
                patterns["booking_velocity"] = "Normal"
            else:
                patterns["booking_velocity"] = "Niedrig"
            
            # Konsistenz-Score berechnen
            if hour_counts and day_counts:
                # Entropy-basierte Konsistenz (niedrige Entropie = konsistent)
                hour_entropy = self._calculate_entropy(list(hour_counts.values()))
                day_entropy = self._calculate_entropy(list(day_counts.values()))
                patterns["consistency_score"] = max(0, 100 - (hour_entropy + day_entropy) * 10)
        
        except Exception as e:
            logger.error(f"Fehler bei Muster-Analyse für {user}", extra={'error': str(e)})
        
        return patterns
    
    def _analyze_performance_trends(self, user):
        """Analysiere Leistungstrends über Zeit"""
        trends = {
            "points_trend": "stable",
            "booking_trend": "stable", 
            "streak_trend": "stable",
            "weekly_performance": [],
            "monthly_performance": [],
            "improvement_areas": [],
            "strength_areas": [],
            "trend_predictions": {}
        }
        
        try:
            from achievement_system import achievement_system
            daily_stats = achievement_system.load_daily_stats()
            user_stats = daily_stats.get(user, {})
            
            if not user_stats:
                return trends
            
            # Sortiere Daten nach Datum
            sorted_dates = sorted(user_stats.keys())
            if len(sorted_dates) < 7:  # Brauchen mindestens eine Woche für Trends
                return trends
            
            # Wöchentliche Performance
            weekly_data = self._group_by_week(user_stats)
            for week, data in weekly_data.items():
                week_total = sum(d.get("points", 0) for d in data)
                week_bookings = sum(d.get("bookings", 0) for d in data)
                trends["weekly_performance"].append({
                    "week": week,
                    "points": week_total,
                    "bookings": week_bookings,
                    "avg_daily": round(week_total / len(data), 1) if data else 0
                })
            
            # Trend-Richtungen bestimmen
            if len(trends["weekly_performance"]) >= 3:
                recent_weeks = trends["weekly_performance"][-3:]
                older_weeks = trends["weekly_performance"][-6:-3] if len(trends["weekly_performance"]) >= 6 else []
                
                if older_weeks:
                    recent_avg = sum(w["points"] for w in recent_weeks) / len(recent_weeks)
                    older_avg = sum(w["points"] for w in older_weeks) / len(older_weeks)
                    
                    if recent_avg > older_avg * 1.1:
                        trends["points_trend"] = "improving"
                    elif recent_avg < older_avg * 0.9:
                        trends["points_trend"] = "declining"
            
            # Verbesserungs- und Stärkebereiche identifizieren
            patterns = self._analyze_booking_patterns(user)
            consistency_score = patterns.get("consistency_score", 0)
            
            if consistency_score < 50:
                trends["improvement_areas"].append("Buchungskonsistenz")
            else:
                trends["strength_areas"].append("Konstante Buchungen")
                
            if patterns.get("booking_velocity") == "Niedrig":
                trends["improvement_areas"].append("Buchungsfrequenz")
            else:
                trends["strength_areas"].append("Aktive Buchungstätigkeit")
        
        except Exception as e:
            logger.error(f"Fehler bei Trend-Analyse für {user}", extra={'error': str(e)})
        
        return trends
    
    def _generate_behavioral_insights(self, user):
        """Generiere Verhaltensinsights"""
        insights = {
            "user_type": "Balanced User",
            "motivation_drivers": [],
            "peak_productivity": {},
            "potential_blockers": [],
            "engagement_pattern": "Regular",
            "social_tendency": "Individual",
            "achievement_preference": "Balanced",
            "risk_tolerance": "Medium"
        }
        
        try:
            from achievement_system import achievement_system
            user_badges = achievement_system.get_user_badges(user)
            patterns = self._analyze_booking_patterns(user)
            
            # User-Typ bestimmen
            if patterns.get("booking_velocity") == "Hoch":
                insights["user_type"] = "Power User"
                insights["motivation_drivers"].extend(["Effizienz", "Hohe Aktivität"])
            elif patterns.get("consistency_score", 0) > 70:
                insights["user_type"] = "Steady Performer"  
                insights["motivation_drivers"].extend(["Konsistenz", "Zuverlässigkeit"])
            elif user_badges.get("total_badges", 0) > 10:
                insights["user_type"] = "Achievement Hunter"
                insights["motivation_drivers"].extend(["Sammlertrieb", "Zielerreichung"])
            
            # Peak Produktivität
            if patterns.get("preferred_times"):
                peak_time = patterns["preferred_times"][0]
                insights["peak_productivity"]["time"] = peak_time
                insights["peak_productivity"]["recommendation"] = f"Plane wichtige Termine um {peak_time}"
            
            if patterns.get("preferred_days"):
                peak_day = patterns["preferred_days"][0]
                insights["peak_productivity"]["day"] = peak_day
                insights["peak_productivity"]["recommendation"] = f"{peak_day} ist dein produktivster Tag"
            
            # Potentielle Blocker identifizieren
            if patterns.get("advance_booking_days", 0) < 1:
                insights["potential_blockers"].append("Spontane Buchungen - plane im Voraus für bessere Verfügbarkeit")
            
            if patterns.get("consistency_score", 0) < 40:
                insights["potential_blockers"].append("Unregelmäßige Muster - entwickle eine Routine")
            
            # Engagement Pattern
            overview = self._generate_overview_stats(user)
            if overview.get("current_streak", 0) >= 14:
                insights["engagement_pattern"] = "Highly Engaged"
            elif overview.get("current_streak", 0) >= 7:
                insights["engagement_pattern"] = "Consistent"
            elif overview.get("total_days_active", 0) > 30:
                insights["engagement_pattern"] = "Sporadic"
            else:
                insights["engagement_pattern"] = "New User"
            
            # Achievement Preference
            badges = user_badges.get("badges", [])
            badge_categories = [b.get("category", "") for b in badges]
            if badge_categories:
                most_common_category = Counter(badge_categories).most_common(1)[0][0]
                if most_common_category == "streak":
                    insights["achievement_preference"] = "Consistency Focused"
                elif most_common_category == "daily":
                    insights["achievement_preference"] = "Daily Goals"
                elif most_common_category == "mvp":
                    insights["achievement_preference"] = "Competition Driven"
        
        except Exception as e:
            logger.error(f"Fehler bei Insights-Generierung für {user}", extra={'error': str(e)})
        
        return insights
    
    def _analyze_achievements(self, user):
        """Analysiere Achievement-Performance"""
        analysis = {
            "completion_rate": 0,
            "favorite_categories": [],
            "rarity_distribution": {},
            "earning_velocity": "Medium",
            "next_recommendations": [],
            "milestone_progress": {},
            "comparative_performance": "Average"
        }
        
        try:
            from achievement_system import achievement_system
            user_badges = achievement_system.get_user_badges(user)
            all_definitions = achievement_system.get_all_badge_definitions()
            
            total_badges = user_badges.get("total_badges", 0)
            total_available = len(all_definitions)
            
            analysis["completion_rate"] = round((total_badges / total_available) * 100, 1) if total_available > 0 else 0
            
            # Rarity Distribution
            badges = user_badges.get("badges", [])
            rarity_counts = Counter(b.get("rarity", "common") for b in badges)
            analysis["rarity_distribution"] = dict(rarity_counts)
            
            # Favorite Categories
            category_counts = Counter(b.get("category", "") for b in badges)
            analysis["favorite_categories"] = [cat for cat, _ in category_counts.most_common(3)]
            
            # Badge-Earning Velocity
            recent_badges = [b for b in badges 
                           if (datetime.now() - datetime.fromisoformat(b.get("earned_date", datetime.now().isoformat()))).days <= 30]
            
            if len(recent_badges) >= 5:
                analysis["earning_velocity"] = "High"
            elif len(recent_badges) >= 2:
                analysis["earning_velocity"] = "Medium"
            else:
                analysis["earning_velocity"] = "Low"
            
            # Nächste Empfehlungen
            badge_progress = achievement_system.get_badge_progress(user)
            available_badges = [(bid, progress) for bid, progress in badge_progress.items() 
                              if not progress["earned"] and progress["progress_percent"] > 0]
            
            # Sortiere nach Fortschritt
            available_badges.sort(key=lambda x: x[1]["progress_percent"], reverse=True)
            
            for badge_id, progress in available_badges[:3]:
                badge_def = all_definitions.get(badge_id, {})
                analysis["next_recommendations"].append({
                    "badge_id": badge_id,
                    "name": badge_def.get("name", "Unbekannt"),
                    "description": badge_def.get("description", ""),
                    "progress_percent": progress["progress_percent"],
                    "remaining": progress["target"] - progress["current"]
                })
        
        except Exception as e:
            logger.error(f"Fehler bei Achievement-Analyse für {user}", extra={'error': str(e)})
        
        return analysis
    
    def _generate_predictions(self, user):
        """Generiere Zukunftsprognosen"""
        predictions = {
            "next_level_eta": "Unbekannt",
            "next_badge_eta": "Unbekannt", 
            "monthly_points_forecast": 0,
            "streak_survival_probability": 0,
            "achievement_completion_date": "Unbekannt",
            "performance_trajectory": "stable",
            "recommended_actions": []
        }
        
        try:
            # Lade historische Daten für Prediction
            from achievement_system import achievement_system
            daily_stats = achievement_system.load_daily_stats()
            user_stats = daily_stats.get(user, {})
            
            if not user_stats:
                return predictions
            
            # Berechne Durchschnittswerte der letzten 14 Tage
            recent_dates = sorted(user_stats.keys())[-14:]
            if not recent_dates:
                return predictions
            
            daily_avg_points = sum(user_stats[date].get("points", 0) for date in recent_dates) / len(recent_dates)
            
            # Monthly Forecast
            predictions["monthly_points_forecast"] = int(daily_avg_points * 30)
            
            # Next Level ETA (vereinfacht)
            try:
                from level_system import LevelSystem
                level_system = LevelSystem()
                user_level = level_system.calculate_user_level(user)
                
                xp_needed = user_level["next_level_xp"] - user_level["xp"]
                if daily_avg_points > 0:
                    days_needed = xp_needed / daily_avg_points
                    predictions["next_level_eta"] = f"{int(days_needed)} Tage"
            except (ImportError, AttributeError, ValueError, TypeError) as e:
                logger.warning(f"Error calculating level predictions for {user}", extra={'error': str(e)})
                pass
            
            # Streak Survival Probability
            current_streak = achievement_system.calculate_advanced_streak(user_stats).get("work_streak", 0)
            if current_streak > 0:
                # Vereinfachte Wahrscheinlichkeit basierend auf bisheriger Konsistenz
                consistency_days = len([d for d in user_stats.values() if d.get("points", 0) > 0])
                total_days = len(user_stats)
                consistency_rate = consistency_days / total_days if total_days > 0 else 0
                predictions["streak_survival_probability"] = int(consistency_rate * 100)
            
            # Performance Trajectory
            if len(recent_dates) >= 7:
                first_half = recent_dates[:7]
                second_half = recent_dates[7:]
                
                first_avg = sum(user_stats[d].get("points", 0) for d in first_half) / len(first_half)
                second_avg = sum(user_stats[d].get("points", 0) for d in second_half) / len(second_half)
                
                if second_avg > first_avg * 1.1:
                    predictions["performance_trajectory"] = "improving"
                elif second_avg < first_avg * 0.9:
                    predictions["performance_trajectory"] = "declining"
                else:
                    predictions["performance_trajectory"] = "stable"
            
            # Empfohlene Aktionen
            if predictions["performance_trajectory"] == "declining":
                predictions["recommended_actions"].append("🔄 Tägliche Routine wieder aufbauen")
            
            if current_streak < 3:
                predictions["recommended_actions"].append("🔥 Fokus auf Streak-Aufbau")
            
            if daily_avg_points < 5:
                predictions["recommended_actions"].append("📈 Mehr tägliche Aktivitäten")
        
        except Exception as e:
            logger.error(f"Fehler bei Predictions für {user}", extra={'error': str(e)})
        
        return predictions
    
    def _generate_recommendations(self, user):
        """Generiere personalisierte Empfehlungen"""
        recommendations = {
            "immediate_actions": [],
            "weekly_goals": [],
            "optimization_tips": [],
            "social_opportunities": [],
            "gamification_focus": []
        }
        
        try:
            insights = self._generate_behavioral_insights(user)
            patterns = self._analyze_booking_patterns(user)
            performance = self._analyze_performance_trends(user)
            
            # Immediate Actions
            if patterns.get("consistency_score", 0) < 50:
                recommendations["immediate_actions"].append({
                    "title": "⏰ Routine entwickeln",
                    "description": "Buche zur gleichen Zeit für mehr Konsistenz",
                    "priority": "high"
                })
            
            if insights.get("engagement_pattern") == "Sporadic":
                recommendations["immediate_actions"].append({
                    "title": "🎯 Tägliches Ziel setzen",
                    "description": "Plane mindestens eine Buchung pro Tag",
                    "priority": "medium"
                })
            
            # Weekly Goals
            current_level = insights.get("user_type", "")
            if current_level == "Power User":
                recommendations["weekly_goals"].append("🚀 Erreiche 50+ Punkte diese Woche")
            else:
                recommendations["weekly_goals"].append("📊 Steigere deine Punktzahl um 20%")
            
            # Optimization Tips
            if patterns.get("preferred_times"):
                peak_time = patterns["preferred_times"][0]
                recommendations["optimization_tips"].append(f"🕐 Nutze deine Peak-Zeit {peak_time} für wichtige Termine")
            
            if patterns.get("advance_booking_days", 0) < 2:
                recommendations["optimization_tips"].append("📅 Plane Termine 2-3 Tage im Voraus für bessere Verfügbarkeit")
            
            # Gamification Focus
            achievements = self._analyze_achievements(user)
            if achievements.get("completion_rate", 0) < 30:
                recommendations["gamification_focus"].append("🏆 Fokus auf Badge-Sammlung")
            
            if "streak" not in achievements.get("favorite_categories", []):
                recommendations["gamification_focus"].append("🔥 Baue längere Streaks auf")
        
        except Exception as e:
            logger.error(f"Fehler bei Recommendations für {user}", extra={'error': str(e)})
        
        return recommendations
    
    def _generate_peer_comparisons(self, user):
        """Generiere Vergleiche mit anderen Usern"""
        comparisons = {
            "ranking_position": 0,
            "percentile": 0,
            "above_average_areas": [],
            "improvement_opportunities": [],
            "similar_users": [],
            "competitive_metrics": {}
        }
        
        try:
            # Hole alle User-Daten für Vergleich
            from data_persistence import data_persistence
            scores = data_persistence.load_scores()
            current_month = datetime.now(TZ).strftime("%Y-%m")
            
            user_score = scores.get(user, {}).get(current_month, 0)
            all_scores = [s.get(current_month, 0) for s in scores.values()]
            all_scores = [s for s in all_scores if s > 0]  # Filter Nullwerte
            
            if all_scores:
                all_scores.sort(reverse=True)
                try:
                    ranking = all_scores.index(user_score) + 1
                    comparisons["ranking_position"] = ranking
                    comparisons["percentile"] = int((1 - (ranking - 1) / len(all_scores)) * 100)
                except ValueError:
                    comparisons["ranking_position"] = len(all_scores) + 1
                    comparisons["percentile"] = 0
                
                avg_score = sum(all_scores) / len(all_scores)
                if user_score > avg_score:
                    comparisons["above_average_areas"].append("Monatliche Punkte")
                else:
                    comparisons["improvement_opportunities"].append("Punkte-Performance steigern")
        
        except Exception as e:
            logger.error(f"Fehler bei Peer-Comparisons für {user}", extra={'error': str(e)})
        
        return comparisons
    
    # Helper Methods
    def _calculate_entropy(self, values):
        """Berechne Entropie für Konsistenz-Messung"""
        if not values:
            return 0
        total = sum(values)
        if total == 0:
            return 0
        probabilities = [v / total for v in values]
        entropy = -sum(p * np.log2(p) for p in probabilities if p > 0)
        return entropy
    
    def _group_by_week(self, user_stats):
        """Gruppiere Daten nach Kalenderwochen"""
        weekly_data = defaultdict(list)
        for date_str, stats in user_stats.items():
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                iso_year, iso_week, _ = date_obj.isocalendar()
                week_key = f"{iso_year}-W{iso_week:02d}"
                weekly_data[week_key].append(stats)
            except (ValueError, TypeError, AttributeError) as e:
                logger.warning(f"Invalid date format in weekly analytics: {date_str}", extra={'error': str(e)})
                continue
        return weekly_data
    
    # Persistence Methods
    def load_analytics(self):
        try:
            with open(self.analytics_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    
    def save_analytics(self, data):
        with open(self.analytics_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_user_analytics(self, user, force_refresh=False):
        """Hole Analytics für einen User (mit Caching)"""
        all_analytics = self.load_analytics()
        
        # Prüfe ob Refresh nötig ist
        user_analytics = all_analytics.get(user, {})
        generated_at = user_analytics.get("generated_at")
        
        needs_refresh = force_refresh or not generated_at
        if generated_at:
            try:
                last_generated = datetime.fromisoformat(generated_at)
                # Refresh wenn älter als 6 Stunden
                needs_refresh = (datetime.now(TZ) - last_generated).seconds > 21600
            except:
                needs_refresh = True
        
        if needs_refresh:
            return self.generate_user_analytics(user)
        else:
            return user_analytics

# Globale Instanz
analytics_system = AdvancedAnalytics()