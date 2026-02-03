# -*- coding: utf-8 -*-
"""
Persistenz und Logik für Wochen-Punkte (T1, T2, Telefonie, Extra)

Features:
- Ziele (goal_points) pro Nutzer und Woche (ISO: YYYY-WW)
- Aktivitäten (T1, T2, telefonie, extra) als Punkte
- Pending-Queues für Einträge außerhalb des Zeitfensters (10–22 Uhr, Europe/Berlin)
- Urlaub-Flag pro Nutzer/Woche (setzt Ziel rechnerisch auf 0)
- Aggregation/Statistik zur Darstellung (Ziel, erreicht, offen, Bilanz)
"""

import csv
import json
import os
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple, Union

import pytz

TZ = pytz.timezone("Europe/Berlin")

# PostgreSQL dual-write support
import logging
_wp_logger = logging.getLogger(__name__)
USE_POSTGRES = os.getenv('USE_POSTGRES', 'true').lower() == 'true'

try:
    from app.models.weekly import WeeklyPoints as WeeklyPointsModel
    from app.models.base import get_db_session
    POSTGRES_AVAILABLE = True
except ImportError:
    _wp_logger.warning("PostgreSQL models not available for weekly_points, using JSON-only mode")
    POSTGRES_AVAILABLE = False
    USE_POSTGRES = False

# Use same persistence strategy as other data
PERSIST_BASE = os.getenv("PERSIST_BASE", "/opt/render/project/src/persist")
if not os.path.exists(PERSIST_BASE):
    PERSIST_BASE = "data"

DATA_DIR = os.path.join(PERSIST_BASE, "persistent")
DATA_FILE = os.path.join(DATA_DIR, "weekly_points.json")
STATIC_DIR = "static"
STATIC_FILE = os.path.join(STATIC_DIR, "weekly_points.json")

# Standard-Teilnehmer (kann im UI erweitert werden)
DEFAULT_PARTICIPANTS = [
    "Christian", "Dominik", "Sara", "Tim", "Sonja"
]


def _ensure_dirs() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(STATIC_DIR, exist_ok=True)


def get_week_key(dt: Optional[datetime] = None) -> str:
    if dt is None:
        dt = datetime.now(TZ)
    iso_year, iso_week, _ = dt.isocalendar()
    return f"{iso_year}-{iso_week:02d}"


def list_recent_weeks(num_weeks: int = 8) -> List[str]:
    now = datetime.now(TZ)
    weeks: List[str] = []
    for i in range(num_weeks):
        dt = now - timedelta(weeks=i)
        weeks.append(get_week_key(dt))
    # Duplikate entfernen und Reihenfolge beibehalten
    seen = set()
    unique_weeks = []
    for w in weeks:
        if w not in seen:
            seen.add(w)
            unique_weeks.append(w)
    return unique_weeks


def is_in_commit_window(check_dt: Optional[datetime] = None) -> bool:
    """Einträge sind jetzt 24/7 erlaubt (Zeitbeschränkung entfernt)."""
    # Zeitbeschränkung entfernt - Admin kann rund um die Uhr Einträge vornehmen
    return True


def load_data() -> Dict:
    """Lade Weekly Points (PostgreSQL-first, JSON-Fallback)"""
    _ensure_dirs()

    # 1. PostgreSQL-first
    if USE_POSTGRES and POSTGRES_AVAILABLE:
        try:
            session = get_db_session()
            try:
                rows = session.query(WeeklyPointsModel).all()
                if rows:
                    # Sammle participants aus DB
                    participants_set = set()
                    weeks: Dict = {}
                    for row in rows:
                        participants_set.add(row.participant_name)
                        if row.week_id not in weeks:
                            weeks[row.week_id] = {
                                "users": {},
                                "created_at": row.created_at.isoformat() if row.created_at else datetime.now(TZ).isoformat(),
                                "frozen": False,
                                "reset_info": {}
                            }
                        weeks[row.week_id]["users"][row.participant_name] = {
                            "goal_points": row.goal_points,
                            "on_vacation": row.on_vacation,
                            "activities": row.activities or [],
                            "pending_activities": row.pending_activities or [],
                            "pending_goal": row.pending_goal,
                            "vacation_periods": [],
                            "audit": row.audit or []
                        }
                    # Merge mit DEFAULT_PARTICIPANTS
                    all_participants = list(set(DEFAULT_PARTICIPANTS) | participants_set)
                    data = {"participants": all_participants, "weeks": weeks}
                    _wp_logger.debug(f"Loaded weekly points from PostgreSQL ({len(rows)} rows, {len(weeks)} weeks)")
                    return data
            finally:
                session.close()
        except Exception as e:
            _wp_logger.warning(f"PostgreSQL weekly points load failed: {e}, falling back to JSON")

    # 2. JSON-Fallback
    if not os.path.exists(DATA_FILE):
        return {
            "participants": DEFAULT_PARTICIPANTS,
            "weeks": {}
        }
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "participants" not in data:
                data["participants"] = DEFAULT_PARTICIPANTS
            if "weeks" not in data:
                data["weeks"] = {}
            return data
    except Exception:
        return {
            "participants": DEFAULT_PARTICIPANTS,
            "weeks": {}
        }


def save_data(data: Dict) -> None:
    """Speichere Weekly Points (Dual-Write: PostgreSQL + JSON)"""
    _ensure_dirs()

    # 1. PostgreSQL write
    if USE_POSTGRES and POSTGRES_AVAILABLE:
        try:
            session = get_db_session()
            try:
                for week_id, week_data in data.get("weeks", {}).items():
                    if not isinstance(week_data, dict):
                        continue
                    for participant, user_data in week_data.get("users", {}).items():
                        if not isinstance(user_data, dict):
                            continue
                        activities = user_data.get("activities", [])
                        total_pts = sum(a.get("points", 0) for a in activities if isinstance(a, dict))

                        existing = session.query(WeeklyPointsModel).filter_by(
                            week_id=week_id, participant_name=participant
                        ).first()
                        if existing:
                            existing.goal_points = user_data.get("goal_points", 0)
                            existing.on_vacation = user_data.get("on_vacation", False)
                            existing.activities = activities
                            existing.pending_activities = user_data.get("pending_activities", [])
                            existing.pending_goal = user_data.get("pending_goal")
                            existing.audit = user_data.get("audit", [])
                            existing.total_points = total_pts
                            existing.is_goal_set = user_data.get("goal_points", 0) > 0
                        else:
                            new_row = WeeklyPointsModel(
                                week_id=week_id,
                                participant_name=participant,
                                goal_points=user_data.get("goal_points", 0),
                                bonus_points=0,
                                total_points=total_pts,
                                on_vacation=user_data.get("on_vacation", False),
                                is_goal_set=user_data.get("goal_points", 0) > 0,
                                activities=activities,
                                pending_activities=user_data.get("pending_activities", []),
                                pending_goal=user_data.get("pending_goal"),
                                audit=user_data.get("audit", [])
                            )
                            session.add(new_row)
                session.commit()
                _wp_logger.debug("Weekly points saved to PostgreSQL")
            except Exception as e:
                session.rollback()
                _wp_logger.error(f"PostgreSQL weekly points save failed: {e}")
            finally:
                session.close()
        except Exception as e:
            _wp_logger.error(f"PostgreSQL connection failed for weekly points: {e}")

    # 2. JSON write (always, as backup)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Also write to static for compatibility/fallback
    try:
        with open(STATIC_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def ensure_week(data: Dict, week_key: str) -> None:
    if week_key not in data["weeks"]:
        data["weeks"][week_key] = {
            "users": {},
            "created_at": datetime.now(TZ).isoformat(),
            "frozen": False
        }


def ensure_user_week(data: Dict, week_key: str, user: str) -> None:
    ensure_week(data, week_key)
    users = data["weeks"][week_key]["users"]
    if user not in users:
        users[user] = {
            "goal_points": 0,
            "on_vacation": False,
            "activities": [],          # verbuchte Aktivitäten
            "pending_activities": [],  # wartende Aktivitäten
            "pending_goal": None,      # wartender Zielwert
            "audit": []                # Audit-Log pro Nutzer/Woche
        }


def set_participants(participants: List[str]) -> None:
    data = load_data()
    data["participants"] = participants
    save_data(data)


def get_participants() -> List[str]:
    data = load_data()
    return data.get("participants", DEFAULT_PARTICIPANTS)


def set_on_vacation(week_key: str, user: str, on_vacation: bool) -> None:
    data = load_data()
    ensure_user_week(data, week_key, user)
    data["weeks"][week_key]["users"][user]["on_vacation"] = bool(on_vacation)
    save_data(data)


def validate_participant(user: str) -> Dict[str, Union[bool, str]]:
    """Validates if participant exists in system."""
    participants = get_participants()
    if not user or not user.strip():
        return {"valid": False, "error": "User name cannot be empty"}
    if user not in participants:
        return {"valid": False, "error": f"User '{user}' not found in participants: {participants}"}
    return {"valid": True, "error": None}


def check_duplicate_activity(week_key: str, user: str, kind: str, points: float, window_minutes: int = 5) -> Dict[str, Union[bool, str]]:
    """Checks for duplicate activities within time window."""
    data = load_data()
    if week_key not in data["weeks"] or user not in data["weeks"][week_key]["users"]:
        return {"duplicate": False, "error": None}

    user_data = data["weeks"][week_key]["users"][user]
    activities = user_data.get("activities", []) + user_data.get("pending_activities", [])
    now = datetime.now(TZ)

    for activity in activities:
        try:
            activity_time = datetime.fromisoformat(activity.get("ts", ""))
            time_diff = abs((now - activity_time).total_seconds() / 60)

            if (activity.get("kind") == kind and
                activity.get("points") == points and
                time_diff < window_minutes):
                return {"duplicate": True, "error": f"Similar activity added {time_diff:.1f} minutes ago"}
        except Exception:
            continue

    return {"duplicate": False, "error": None}


def set_week_goal(week_key: str, user: str, goal_points: float, set_by: str) -> Dict[str, Union[bool, str]]:
    """Setzt Wochenziel. Außerhalb des Fensters als pending gespeichert."""
    # Validation
    validation = validate_participant(user)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    # Check if user is on vacation
    vacation_status = is_user_on_vacation(user)
    if vacation_status["on_vacation"]:
        return {"success": False, "error": f"User {user} is on vacation ({vacation_status['reason']}). Goal not set."}

    try:
        data = load_data()
        ensure_user_week(data, week_key, user)
        user_entry = data["weeks"][week_key]["users"][user]
        clamped = round(min(100.0, max(0.0, float(goal_points))), 1)

        if is_in_commit_window():
            user_entry["goal_points"] = clamped
            user_entry["pending_goal"] = None
            user_entry.setdefault("audit", []).append({
                "type": "goal_set",
                "points": clamped,
                "by": set_by,
                "ts": datetime.now(TZ).isoformat()
            })
        else:
            user_entry["pending_goal"] = clamped

        save_data(data)
        return {"success": True, "error": None}

    except Exception as e:
        return {"success": False, "error": f"Failed to set goal: {str(e)}"}


def record_activity(week_key: str, user: str, kind: str, points: float, set_by: str, note: str = "") -> Dict[str, Union[bool, str]]:
    """Erfasst Aktivität. Außerhalb des Fensters pending."""
    # Validation
    if kind not in ("T1", "T2", "telefonie", "extra"):
        return {"success": False, "error": f"Invalid activity kind '{kind}'. Must be one of: T1, T2, telefonie, extra"}

    validation = validate_participant(user)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    # Check if user is on vacation
    vacation_status = is_user_on_vacation(user)
    if vacation_status["on_vacation"]:
        return {"success": False, "error": f"Warning: User {user} is on vacation ({vacation_status['reason']}). Activity recorded but will not count toward goals."}

    # Duplicate-Check entfernt - Admin kann mehrere gleiche Termine für einen Berater eintragen

    try:
        points = round(min(100.0, max(0.0, float(points))), 1)
        data = load_data()
        ensure_user_week(data, week_key, user)
        user_entry = data["weeks"][week_key]["users"][user]

        entry = {
            "kind": kind,
            "points": points,
            "note": note or "",
            "by": set_by,
            "ts": datetime.now(TZ).isoformat()
        }

        if is_in_commit_window():
            user_entry["activities"].append(entry)
            user_entry.setdefault("audit", []).append({
                "type": "activity",
                "kind": kind,
                "points": points,
                "note": note or "",
                "by": set_by,
                "ts": entry["ts"]
            })
        else:
            user_entry["pending_activities"].append(entry)

        save_data(data)
        return {"success": True, "error": None}

    except Exception as e:
        return {"success": False, "error": f"Failed to record activity: {str(e)}"}


def delete_activity(week_key: str, user: str, activity_index: int, deleted_by: str) -> Dict[str, Union[bool, str]]:
    """
    Löscht eine Aktivität anhand des Index.

    Args:
        week_key: Woche im Format YYYY-WW
        user: Benutzername
        activity_index: Index der zu löschenden Aktivität im activities-Array
        deleted_by: Wer die Löschung durchführt (z.B. "admin")

    Returns:
        Dict mit success und optional error
    """
    try:
        data = load_data()

        # Check if week and user exist
        if week_key not in data["weeks"]:
            return {"success": False, "error": f"Week {week_key} not found"}

        if user not in data["weeks"][week_key]["users"]:
            return {"success": False, "error": f"User {user} not found in week {week_key}"}

        user_entry = data["weeks"][week_key]["users"][user]
        activities = user_entry.get("activities", [])

        # Check if index is valid
        if activity_index < 0 or activity_index >= len(activities):
            return {"success": False, "error": f"Invalid activity index {activity_index}"}

        # Get activity details before deletion for audit
        deleted_activity = activities[activity_index]

        # Delete the activity
        del activities[activity_index]

        # Add audit entry
        user_entry.setdefault("audit", []).append({
            "type": "activity_deleted",
            "kind": deleted_activity.get("kind", "unknown"),
            "points": deleted_activity.get("points", 0),
            "note": deleted_activity.get("note", ""),
            "original_by": deleted_activity.get("by", "unknown"),
            "deleted_by": deleted_by,
            "ts": datetime.now(TZ).isoformat()
        })

        save_data(data)
        return {"success": True, "error": None}

    except Exception as e:
        return {"success": False, "error": f"Failed to delete activity: {str(e)}"}


def apply_pending(week_key: str) -> Tuple[int, int]:
    """Verbucht alle pending Ziele/Aktivitäten, nur im Fenster zugelassen.
    Returns: (num_goals_applied, num_activities_applied)
    """
    if not is_in_commit_window():
        return (0, 0)
    data = load_data()
    ensure_week(data, week_key)
    users = data["weeks"][week_key]["users"]
    goals_applied = 0
    acts_applied = 0
    for user, udata in users.items():
        # pending goal
        if udata.get("pending_goal") is not None:
            udata["goal_points"] = round(max(0.0, float(udata["pending_goal"])), 1)
            udata["pending_goal"] = None
            goals_applied += 1
            udata.setdefault("audit", []).append({
                "type": "goal_applied",
                "points": udata["goal_points"],
                "by": "system",
                "ts": datetime.now(TZ).isoformat()
            })
        # pending activities
        pending = udata.get("pending_activities", [])
        if pending:
            udata.setdefault("activities", []).extend(pending)
            acts_applied += len(pending)
            udata["pending_activities"] = []
            # Audit pro pending-Activity
            now_iso = datetime.now(TZ).isoformat()
            for p in pending:
                udata.setdefault("audit", []).append({
                    "type": "activity_applied",
                    "kind": p.get("kind"),
                    "points": float(p.get("points", 0)),
                    "note": p.get("note", ""),
                    "by": p.get("by", "unknown"),
                    "ts": now_iso
                })
    save_data(data)
    return (goals_applied, acts_applied)


def compute_user_stats(week_key: str, user: str) -> Dict:
    data = load_data()
    ensure_user_week(data, week_key, user)
    u = data["weeks"][week_key]["users"][user]
    goal = 0 if u.get("on_vacation") else float(u.get("goal_points", 0))
    achieved = sum(float(a.get("points", 0)) for a in u.get("activities", []))
    remaining = max(goal - achieved, 0)
    balance = achieved - goal  # negativ = Ziel verfehlt
    return {
        "user": user,
        "goal": goal,
        "achieved": achieved,
        "remaining": remaining,
        "balance": balance,
        "on_vacation": bool(u.get("on_vacation")),
        "pending_goal": u.get("pending_goal"),
        "pending_count": len(u.get("pending_activities", []))
    }


def compute_week_stats(week_key: str, participants: Optional[List[str]] = None) -> Dict:
    data = load_data()
    ensure_week(data, week_key)
    if participants is None:
        participants = data.get("participants", DEFAULT_PARTICIPANTS)
    stats = [compute_user_stats(week_key, p) for p in participants]
    summary = {
        "total_goal": sum(s["goal"] for s in stats),
        "total_achieved": sum(s["achieved"] for s in stats),
        "total_remaining": sum(s["remaining"] for s in stats),
        "total_balance": sum(s["balance"] for s in stats)
    }
    return {"users": stats, "summary": summary}


def get_week_audit(week_key: str) -> List[Dict]:
    """Aggregiertes Audit-Log aller Nutzer für eine Woche (neueste zuerst)."""
    data = load_data()
    ensure_week(data, week_key)
    entries: List[Dict] = []
    for user, u in data["weeks"][week_key]["users"].items():
        for a in u.get("audit", []):
            e = dict(a)
            e["user"] = user
            entries.append(e)
    # Sortiere nach ts absteigend
    try:
        entries.sort(key=lambda x: x.get("ts", ""), reverse=True)
    except Exception:
        pass
    return entries


def add_participant(name: str) -> None:
    name = (name or "").strip()
    if not name:
        return
    data = load_data()
    participants = data.get("participants", DEFAULT_PARTICIPANTS)
    if name not in participants:
        participants.append(name)
    data["participants"] = participants
    save_data(data)


def remove_participant(name: str) -> None:
    data = load_data()
    participants = data.get("participants", DEFAULT_PARTICIPANTS)
    data["participants"] = [p for p in participants if p != name]
    save_data(data)


def reset_week_for_all_users(week_key: Optional[str] = None) -> Dict:
    """
    Automatischer Wochen-Reset für alle Teilnehmer.
    Archiviert aktuelle Woche und initialisiert neue Woche.
    """
    if week_key is None:
        week_key = get_week_key()
    
    data = load_data()
    participants = data.get("participants", DEFAULT_PARTICIPANTS)
    
    # Archive current week data if it exists
    archive_data = {}
    if week_key in data["weeks"]:
        archive_data = {
            "archived_week": week_key,
            "archived_at": datetime.now(TZ).isoformat(),
            "participants_count": len(participants),
            "week_data": data["weeks"][week_key]
        }
    
    # Initialize new week for all participants
    ensure_week(data, week_key)
    reset_count = 0
    
    for participant in participants:
        ensure_user_week(data, week_key, participant)
        user_data = data["weeks"][week_key]["users"][participant]
        
        # Reset to clean state
        user_data.update({
            "goal_points": 0,
            "on_vacation": False,
            "vacation_periods": [],  # New: time-based vacation system
            "activities": [],
            "pending_activities": [],
            "pending_goal": None,
            "audit": [{
                "type": "week_reset",
                "by": "system",
                "ts": datetime.now(TZ).isoformat(),
                "note": f"Automated weekly reset for week {week_key}"
            }]
        })
        reset_count += 1
    
    # Add reset metadata to week (without circular reference)
    data["weeks"][week_key]["reset_info"] = {
        "reset_at": datetime.now(TZ).isoformat(),
        "reset_by": "system",
        "participants_reset": reset_count,
        "archive_created": bool(archive_data)
    }
    
    save_data(data)
    
    return {
        "success": True,
        "week": week_key,
        "participants_reset": reset_count,
        "archive_created": bool(archive_data),
        "reset_timestamp": datetime.now(TZ).isoformat()
    }


def set_vacation_period(user: str, start_date: str, end_date: str, reason: str = "Urlaub") -> Dict:
    """
    Setzt Urlaubszeitraum für einen User (neue zeitbasierte Logik).
    
    Args:
        user: Username
        start_date: Start-Datum im Format "YYYY-MM-DD"
        end_date: End-Datum im Format "YYYY-MM-DD" 
        reason: Grund der Abwesenheit (Urlaub, Arzt/Zahnarzt, Krankheit, etc.)
    """
    try:
        # Validate dates
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        if start > end:
            return {"success": False, "message": "Start-Datum muss vor End-Datum liegen"}
        
        data = load_data()
        
        # Get all affected weeks
        current_date = start
        affected_weeks = []
        
        while current_date <= end:
            week_key = get_week_key(datetime.combine(current_date, time()))
            affected_weeks.append(week_key)
            current_date += timedelta(days=7 - current_date.weekday())  # Next Monday
        
        # Remove duplicates
        affected_weeks = list(set(affected_weeks))
        
        # Update each affected week
        for week_key in affected_weeks:
            ensure_user_week(data, week_key, user)
            user_data = data["weeks"][week_key]["users"][user]
            
            # Initialize vacation_periods if not exists (backward compatibility)
            if "vacation_periods" not in user_data:
                user_data["vacation_periods"] = []
            
            # Add new vacation period
            vacation_period = {
                "start": start_date,
                "end": end_date,
                "reason": reason,
                "created_at": datetime.now(TZ).isoformat()
            }
            user_data["vacation_periods"].append(vacation_period)
            
            # Set legacy on_vacation flag for backward compatibility
            user_data["on_vacation"] = True
            
            # Add audit entry
            user_data.setdefault("audit", []).append({
                "type": "vacation_set",
                "start_date": start_date,
                "end_date": end_date,
                "reason": reason,
                "by": "admin",
                "ts": datetime.now(TZ).isoformat()
            })
        
        save_data(data)
        
        return {
            "success": True,
            "message": f"Urlaubszeitraum für {user} gesetzt: {start_date} bis {end_date}",
            "affected_weeks": affected_weeks,
            "reason": reason
        }
        
    except ValueError as e:
        return {"success": False, "message": f"Ungültiges Datumsformat: {e}"}
    except Exception as e:
        return {"success": False, "message": f"Fehler beim Setzen des Urlaubs: {e}"}


def is_user_on_vacation(user: str, check_date: Optional[datetime] = None) -> Dict:
    """
    Prüft ob User an einem bestimmten Datum im Urlaub ist.
    
    Returns: {
        "on_vacation": bool,
        "reason": str,
        "period": dict or None
    }
    """
    if check_date is None:
        check_date = datetime.now(TZ)
    
    check_date_str = check_date.strftime("%Y-%m-%d")
    week_key = get_week_key(check_date)
    
    data = load_data()
    ensure_user_week(data, week_key, user)
    user_data = data["weeks"][week_key]["users"][user]
    
    # Check new vacation_periods system
    vacation_periods = user_data.get("vacation_periods", [])
    for period in vacation_periods:
        if period["start"] <= check_date_str <= period["end"]:
            return {
                "on_vacation": True,
                "reason": period["reason"],
                "period": period
            }
    
    # Fallback to legacy on_vacation flag
    if user_data.get("on_vacation", False):
        return {
            "on_vacation": True,
            "reason": "Urlaub",
            "period": None
        }
    
    return {
        "on_vacation": False,
        "reason": None,
        "period": None
    }


def get_user_vacation_periods(user: str) -> List[Dict]:
    """Gibt alle Urlaubszeiträume eines Users zurück."""
    data = load_data()
    all_periods = []

    # Sammle Urlaubsperioden aus allen Wochen
    for week_key, week_data in data["weeks"].items():
        if user in week_data["users"]:
            user_data = week_data["users"][user]
            periods = user_data.get("vacation_periods", [])
            for period in periods:
                # Verhindere Duplikate (gleiche Periode kann in mehreren Wochen stehen)
                if not any(p["start"] == period["start"] and p["end"] == period["end"] for p in all_periods):
                    all_periods.append(period)

    # Sortiere nach Start-Datum
    all_periods.sort(key=lambda x: x["start"])
    return all_periods


# Enhanced Audit & Reporting Functions
def get_weekly_stats_summary(week_key: str) -> Dict:
    """Quick overview of who's ahead/behind goals."""
    stats = compute_week_stats(week_key)
    behind = [u for u in stats["users"] if u["balance"] < 0 and not u["on_vacation"]]
    ahead = [u for u in stats["users"] if u["balance"] > 0]

    return {
        "week": week_key,
        "behind_goal": sorted(behind, key=lambda x: x["balance"]),
        "ahead_of_goal": sorted(ahead, key=lambda x: x["balance"], reverse=True),
        "on_vacation": [u["user"] for u in stats["users"] if u["on_vacation"]],
        "pending_items": sum(u["pending_count"] for u in stats["users"])
    }


def export_audit_to_csv(week_key: str, filename: Optional[str] = None) -> str:
    """Export audit log to CSV file."""
    if filename is None:
        filename = f"audit_{week_key}.csv"

    audit_entries = get_week_audit(week_key)

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        if not audit_entries:
            return filename

        fieldnames = audit_entries[0].keys()
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(audit_entries)

    return filename


# UI/Admin Helper Functions
def get_commit_window_status() -> Dict:
    """Check current commit window status."""
    now = datetime.now(TZ)
    in_window = is_in_commit_window(now)

    if in_window:
        # Calculate time until window closes
        end_time = now.replace(hour=22, minute=0, second=0, microsecond=0)
        time_left = end_time - now
        hours, remainder = divmod(time_left.seconds, 3600)
        minutes = remainder // 60

        return {
            "in_window": True,
            "message": f"Commit window OPEN - closes in {hours}h {minutes}m",
            "time_left_minutes": time_left.seconds // 60
        }
    else:
        # Calculate time until window opens
        if now.hour < 10:
            open_time = now.replace(hour=10, minute=0, second=0, microsecond=0)
        else:
            open_time = (now + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)

        time_until = open_time - now
        hours = time_until.seconds // 3600
        minutes = (time_until.seconds % 3600) // 60

        return {
            "in_window": False,
            "message": f"Commit window CLOSED - opens in {hours}h {minutes}m",
            "opens_in_minutes": time_until.seconds // 60
        }


def get_pending_summary() -> Dict:
    """Count pending items across all users."""
    data = load_data()
    current_week = get_week_key()
    summary = {"total_pending_goals": 0, "total_pending_activities": 0, "users_with_pending": []}

    if current_week not in data["weeks"]:
        return summary

    for user, user_data in data["weeks"][current_week]["users"].items():
        pending_goal = user_data.get("pending_goal") is not None
        pending_activities = len(user_data.get("pending_activities", []))

        if pending_goal:
            summary["total_pending_goals"] += 1
        if pending_activities > 0:
            summary["total_pending_activities"] += pending_activities

        if pending_goal or pending_activities > 0:
            summary["users_with_pending"].append({
                "user": user,
                "pending_goal": pending_goal,
                "pending_activities": pending_activities
            })

    return summary


# Data Management Utilities
def archive_old_weeks(weeks_to_keep: int = 8) -> Dict:
    """Archive weeks older than specified number to separate file."""
    data = load_data()
    current_week = get_week_key()
    recent_weeks = set(list_recent_weeks(weeks_to_keep))

    archived_weeks = {}
    weeks_to_archive = []

    for week_key in data["weeks"].keys():
        if week_key not in recent_weeks and week_key != current_week:
            archived_weeks[week_key] = data["weeks"][week_key]
            weeks_to_archive.append(week_key)

    if not archived_weeks:
        return {"archived_count": 0, "message": "No weeks to archive"}

    # Save archived data
    archive_file = os.path.join(DATA_DIR, f"weekly_points_archive_{datetime.now(TZ).strftime('%Y%m%d')}.json")
    try:
        with open(archive_file, "w", encoding="utf-8") as f:
            json.dump(archived_weeks, f, ensure_ascii=False, indent=2)

        # Remove archived weeks from main data
        for week_key in weeks_to_archive:
            del data["weeks"][week_key]

        save_data(data)

        return {
            "archived_count": len(weeks_to_archive),
            "archived_weeks": weeks_to_archive,
            "archive_file": archive_file,
            "message": f"Archived {len(weeks_to_archive)} weeks to {archive_file}"
        }
    except Exception as e:
        return {"archived_count": 0, "error": f"Failed to archive: {str(e)}"}


def backup_weekly_data(backup_name: Optional[str] = None) -> str:
    """Create backup of current weekly data."""
    if backup_name is None:
        backup_name = f"weekly_points_backup_{datetime.now(TZ).strftime('%Y%m%d_%H%M%S')}.json"

    backup_file = os.path.join(DATA_DIR, backup_name)
    data = load_data()

    with open(backup_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return backup_file


def restore_from_backup(backup_file: str) -> Dict:
    """Restore data from backup file."""
    try:
        if not os.path.exists(backup_file):
            return {"success": False, "error": f"Backup file not found: {backup_file}"}

        with open(backup_file, "r", encoding="utf-8") as f:
            backup_data = json.load(f)

        # Validate backup data structure
        if "participants" not in backup_data or "weeks" not in backup_data:
            return {"success": False, "error": "Invalid backup file structure"}

        save_data(backup_data)
        return {"success": True, "message": f"Data restored from {backup_file}"}

    except Exception as e:
        return {"success": False, "error": f"Failed to restore: {str(e)}"}


def validate_data_integrity() -> Dict:
    """Check data for corruption or inconsistencies."""
    try:
        data = load_data()
        issues = []

        # Check participants
        if not data.get("participants"):
            issues.append("No participants defined")

        # Check weeks structure
        for week_key, week_data in data.get("weeks", {}).items():
            if not isinstance(week_data, dict):
                issues.append(f"Week {week_key}: Invalid structure")
                continue

            # Check users in week
            for user, user_data in week_data.get("users", {}).items():
                if not isinstance(user_data, dict):
                    issues.append(f"Week {week_key}, User {user}: Invalid user data structure")
                    continue

                # Check required fields
                required_fields = ["goal_points", "on_vacation", "activities", "pending_activities", "audit"]
                for field in required_fields:
                    if field not in user_data:
                        issues.append(f"Week {week_key}, User {user}: Missing field '{field}'")

                # Check activities structure
                for activity in user_data.get("activities", []):
                    if not all(key in activity for key in ["kind", "points", "by", "ts"]):
                        issues.append(f"Week {week_key}, User {user}: Invalid activity structure")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "total_weeks": len(data.get("weeks", {})),
            "total_participants": len(data.get("participants", []))
        }

    except Exception as e:
        return {"valid": False, "issues": [f"Failed to validate: {str(e)}"]}


def repair_data_structure() -> Dict:
    """Fix common data structure issues."""
    try:
        data = load_data()
        repairs = []

        # Ensure participants exist
        if not data.get("participants"):
            data["participants"] = DEFAULT_PARTICIPANTS
            repairs.append("Added default participants")

        # Fix weeks structure
        for week_key, week_data in data.get("weeks", {}).items():
            if "users" not in week_data:
                week_data["users"] = {}
                repairs.append(f"Week {week_key}: Added users structure")

            # Fix user structures
            for user, user_data in week_data["users"].items():
                defaults = {
                    "goal_points": 0,
                    "on_vacation": False,
                    "activities": [],
                    "pending_activities": [],
                    "pending_goal": None,
                    "audit": []
                }

                for field, default_value in defaults.items():
                    if field not in user_data:
                        user_data[field] = default_value
                        repairs.append(f"Week {week_key}, User {user}: Added missing field '{field}'")

        if repairs:
            save_data(data)

        return {
            "success": True,
            "repairs_made": len(repairs),
            "repairs": repairs
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to repair: {str(e)}"}


# Smart Defaults
def suggest_goals_from_history(user: str, weeks_back: int = 4) -> Dict:
    """Suggest goal based on historical performance."""
    data = load_data()
    current_week = get_week_key()
    recent_weeks = list_recent_weeks(weeks_back + 1)

    # Remove current week from analysis
    analysis_weeks = [w for w in recent_weeks if w != current_week]

    performances = []
    for week_key in analysis_weeks:
        if week_key in data["weeks"] and user in data["weeks"][week_key]["users"]:
            user_data = data["weeks"][week_key]["users"][user]
            if not user_data.get("on_vacation", False):
                achieved = sum(a.get("points", 0) for a in user_data.get("activities", []))
                performances.append(achieved)

    if not performances:
        return {"suggested_goal": 15, "reason": "No historical data, using default"}

    avg_performance = sum(performances) / len(performances)
    # Suggest slightly above average to encourage growth
    suggested = max(5, min(50, int(avg_performance * 1.1)))

    return {
        "suggested_goal": suggested,
        "reason": f"Based on {len(performances)} weeks avg ({avg_performance:.1f})",
        "historical_performance": performances
    }


def detect_vacation_periods(user: str, consecutive_days: int = 3) -> List[Dict]:
    """Auto-detect potential vacation periods based on zero activity."""
    data = load_data()
    potential_vacations = []

    # Get last 8 weeks for analysis
    recent_weeks = list_recent_weeks(8)
    zero_activity_weeks = []

    for week_key in recent_weeks:
        if week_key in data["weeks"] and user in data["weeks"][week_key]["users"]:
            user_data = data["weeks"][week_key]["users"][user]
            total_points = sum(a.get("points", 0) for a in user_data.get("activities", []))

            if total_points == 0 and not user_data.get("on_vacation", False):
                zero_activity_weeks.append(week_key)

    if len(zero_activity_weeks) >= 2:  # 2+ weeks of zero activity
        potential_vacations.append({
            "user": user,
            "weeks_with_zero_activity": zero_activity_weeks,
            "recommendation": "Consider marking as vacation periods",
            "confidence": "medium" if len(zero_activity_weeks) < 3 else "high"
        })

    return potential_vacations


def recommend_point_adjustments(week_key: str) -> Dict:
    """Recommend point adjustments based on team performance."""
    stats = compute_week_stats(week_key)
    recommendations = []

    team_avg_goal = stats["summary"]["total_goal"] / len(stats["users"]) if stats["users"] else 0
    team_avg_achieved = stats["summary"]["total_achieved"] / len(stats["users"]) if stats["users"] else 0

    for user_stat in stats["users"]:
        if user_stat["on_vacation"]:
            continue

        user = user_stat["user"]
        goal = user_stat["goal"]
        achieved = user_stat["achieved"]

        # Recommendations based on performance patterns
        if goal == 0:
            suggestions = suggest_goals_from_history(user)
            recommendations.append({
                "user": user,
                "type": "set_goal",
                "current": goal,
                "suggested": suggestions["suggested_goal"],
                "reason": f"No goal set. {suggestions['reason']}"
            })
        elif achieved > goal * 1.5:  # Consistently over-achieving
            recommendations.append({
                "user": user,
                "type": "increase_goal",
                "current": goal,
                "suggested": min(50, int(goal * 1.2)),
                "reason": "Consistently exceeding goals, consider increasing challenge"
            })
        elif achieved < goal * 0.5 and goal > team_avg_goal * 0.8:  # Under-achieving with high goal
            recommendations.append({
                "user": user,
                "type": "reduce_goal",
                "current": goal,
                "suggested": max(5, int(goal * 0.8)),
                "reason": "Goal may be too ambitious, consider reducing"
            })

    return {
        "week": week_key,
        "team_stats": {
            "avg_goal": round(team_avg_goal, 1),
            "avg_achieved": round(team_avg_achieved, 1)
        },
        "recommendations": recommendations
    }


def auto_set_reasonable_goals(week_key: Optional[str] = None) -> Dict:
    """Auto-set reasonable goals for users with no goals."""
    if week_key is None:
        week_key = get_week_key()

    if not is_in_commit_window():
        return {"success": False, "error": "Can only auto-set goals during commit window"}

    data = load_data()
    participants = get_participants()
    goals_set = []

    for user in participants:
        ensure_user_week(data, week_key, user)
        user_data = data["weeks"][week_key]["users"][user]

        # Only set if no goal exists and not on vacation
        if user_data.get("goal_points", 0) == 0 and not user_data.get("on_vacation", False):
            suggestion = suggest_goals_from_history(user)

            user_data["goal_points"] = suggestion["suggested_goal"]
            user_data.setdefault("audit", []).append({
                "type": "goal_auto_set",
                "points": suggestion["suggested_goal"],
                "reason": suggestion["reason"],
                "by": "auto_system",
                "ts": datetime.now(TZ).isoformat()
            })

            goals_set.append({
                "user": user,
                "goal_set": suggestion["suggested_goal"],
                "reason": suggestion["reason"]
            })

    if goals_set:
        save_data(data)

    return {
        "success": True,
        "goals_set": len(goals_set),
        "details": goals_set
    }

