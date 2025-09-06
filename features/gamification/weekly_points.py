# -*- coding: utf-8 -*-
"""
Wochen-Punkte System - Optimiert
"""

import json
import os
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple
import pytz

TZ = pytz.timezone("Europe/Berlin")
DATA_DIR = os.path.join("data", "persistent")
DATA_FILE = os.path.join(DATA_DIR, "weekly_points.json")

DEFAULT_PARTICIPANTS = ["Christian", "Dominik", "Sara", "Patrick", "Tim", "Sonja"]

def _ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)

def _load_data() -> Dict:
    """Lade Daten mit Fallback"""
    _ensure_dirs()
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            data.setdefault("participants", DEFAULT_PARTICIPANTS)
            data.setdefault("weeks", {})
            return data
    except Exception:
        return {"participants": DEFAULT_PARTICIPANTS, "weeks": {}}

def _save_data(data: Dict):
    """Speichere Daten"""
    _ensure_dirs()
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _ensure_user_week(data: Dict, week_key: str, user: str):
    """Stelle User-Woche-Struktur sicher"""
    if week_key not in data["weeks"]:
        data["weeks"][week_key] = {
            "users": {},
            "created_at": datetime.now(TZ).isoformat(),
            "frozen": False
        }
    
    users = data["weeks"][week_key]["users"]
    if user not in users:
        users[user] = {
            "goal_points": 0,
            "on_vacation": False,
            "activities": [],
            "pending_activities": [],
            "pending_goal": None,
            "audit": []
        }

def get_week_key(dt: Optional[datetime] = None) -> str:
    """Generiere Wochenschlüssel (YYYY-WW)"""
    if dt is None:
        dt = datetime.now(TZ)
    iso_year, iso_week, _ = dt.isocalendar()
    return f"{iso_year}-{iso_week:02d}"

def list_recent_weeks(num_weeks: int = 8) -> List[str]:
    """Liste der letzten N Wochen"""
    now = datetime.now(TZ)
    weeks = []
    for i in range(num_weeks):
        dt = now - timedelta(weeks=i)
        week_key = get_week_key(dt)
        if week_key not in weeks:
            weeks.append(week_key)
    return weeks

def is_in_commit_window(check_dt: Optional[datetime] = None) -> bool:
    """Prüfe ob im Commit-Fenster (18:00-21:00)"""
    if check_dt is None:
        check_dt = datetime.now(TZ)
    local_time = check_dt.astimezone(TZ).time()
    return time(18, 0) <= local_time <= time(21, 0)

def set_participants(participants: List[str]):
    """Setze Teilnehmer"""
    data = _load_data()
    data["participants"] = participants
    _save_data(data)

def get_participants() -> List[str]:
    """Hole Teilnehmer"""
    return _load_data().get("participants", DEFAULT_PARTICIPANTS)

def set_on_vacation(week_key: str, user: str, on_vacation: bool):
    """Setze Urlaub-Status"""
    data = _load_data()
    _ensure_user_week(data, week_key, user)
    data["weeks"][week_key]["users"][user]["on_vacation"] = bool(on_vacation)
    _save_data(data)

def set_week_goal(week_key: str, user: str, goal_points: int, set_by: str):
    """Setze Wochenziel (pending wenn außerhalb Fenster)"""
    data = _load_data()
    _ensure_user_week(data, week_key, user)
    user_entry = data["weeks"][week_key]["users"][user]
    clamped = min(100, max(0, int(goal_points)))
    
    audit_entry = {
        "type": "goal_set",
        "points": clamped,
        "by": set_by,
        "ts": datetime.now(TZ).isoformat()
    }
    
    if is_in_commit_window():
        user_entry["goal_points"] = clamped
        user_entry["pending_goal"] = None
        user_entry.setdefault("audit", []).append(audit_entry)
    else:
        user_entry["pending_goal"] = clamped
    
    _save_data(data)

def record_activity(week_key: str, user: str, kind: str, points: int, set_by: str, note: str = ""):
    """Erfasse Aktivität (pending wenn außerhalb Fenster)"""
    assert kind in ("T1", "T2", "telefonie", "extra")
    points = min(100, max(0, int(points)))
    
    data = _load_data()
    _ensure_user_week(data, week_key, user)
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
    
    _save_data(data)

def apply_pending(week_key: str) -> Tuple[int, int]:
    """Verbuche pending Einträge (nur im Fenster)"""
    if not is_in_commit_window():
        return (0, 0)
    
    data = _load_data()
    if week_key not in data["weeks"]:
        return (0, 0)
    
    goals_applied = acts_applied = 0
    now_iso = datetime.now(TZ).isoformat()
    
    for user, udata in data["weeks"][week_key]["users"].items():
        # Pending Goal
        if udata.get("pending_goal") is not None:
            udata["goal_points"] = max(0, int(udata["pending_goal"]))
            udata["pending_goal"] = None
            goals_applied += 1
            udata.setdefault("audit", []).append({
                "type": "goal_applied",
                "points": udata["goal_points"],
                "by": "system",
                "ts": now_iso
            })
        
        # Pending Activities
        pending = udata.get("pending_activities", [])
        if pending:
            udata.setdefault("activities", []).extend(pending)
            acts_applied += len(pending)
            udata["pending_activities"] = []
            
            for p in pending:
                udata.setdefault("audit", []).append({
                    "type": "activity_applied",
                    "kind": p.get("kind"),
                    "points": int(p.get("points", 0)),
                    "note": p.get("note", ""),
                    "by": p.get("by", "unknown"),
                    "ts": now_iso
                })
    
    _save_data(data)
    return (goals_applied, acts_applied)

def compute_user_stats(week_key: str, user: str) -> Dict:
    """Berechne User-Statistik für Woche"""
    data = _load_data()
    _ensure_user_week(data, week_key, user)
    u = data["weeks"][week_key]["users"][user]
    
    goal = 0 if u.get("on_vacation") else int(u.get("goal_points", 0))
    achieved = sum(int(a.get("points", 0)) for a in u.get("activities", []))
    remaining = max(goal - achieved, 0)
    balance = achieved - goal
    
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
    """Berechne Wochen-Statistik für alle Teilnehmer"""
    data = _load_data()
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
    """Hole Audit-Log für Woche (neueste zuerst)"""
    data = _load_data()
    if week_key not in data["weeks"]:
        return []
    
    entries = []
    for user, u in data["weeks"][week_key]["users"].items():
        for a in u.get("audit", []):
            entry = dict(a)
            entry["user"] = user
            entries.append(entry)
    
    try:
        entries.sort(key=lambda x: x.get("ts", ""), reverse=True)
    except Exception:
        pass
    
    return entries

def add_participant(name: str):
    """Füge Teilnehmer hinzu"""
    name = (name or "").strip()
    if not name:
        return
    
    data = _load_data()
    participants = data.get("participants", DEFAULT_PARTICIPANTS)
    if name not in participants:
        participants.append(name)
        data["participants"] = participants
        _save_data(data)

def remove_participant(name: str):
    """Entferne Teilnehmer"""
    data = _load_data()
    participants = data.get("participants", DEFAULT_PARTICIPANTS)
    data["participants"] = [p for p in participants if p != name]
    _save_data(data)