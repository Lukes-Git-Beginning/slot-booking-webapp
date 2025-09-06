# -*- coding: utf-8 -*-
"""
Persistenz und Logik für Wochen-Punkte (T1, T2, Telefonie, Extra)

Features:
- Ziele (goal_points) pro Nutzer und Woche (ISO: YYYY-WW)
- Aktivitäten (T1, T2, telefonie, extra) als Punkte
- Pending-Queues für Einträge außerhalb des Zeitfensters (18–21 Uhr, Europe/Berlin)
- Urlaub-Flag pro Nutzer/Woche (setzt Ziel rechnerisch auf 0)
- Aggregation/Statistik zur Darstellung (Ziel, erreicht, offen, Bilanz)
"""

import json
import os
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple

import pytz

TZ = pytz.timezone("Europe/Berlin")

DATA_DIR = os.path.join("data", "persistent")
DATA_FILE = os.path.join(DATA_DIR, "weekly_points.json")

# Standard-Teilnehmer (kann im UI erweitert werden)
DEFAULT_PARTICIPANTS = [
    "Christian", "Dominik", "Sara", "Patrick", "Tim", "Sonja"
]


def _ensure_dirs() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


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
    """Einträge zwischen 18:00 und 21:00 (inklusive 21:00) verbuchen."""
    if check_dt is None:
        check_dt = datetime.now(TZ)
    local = check_dt.astimezone(TZ)
    start = time(18, 0)
    end = time(21, 0)
    return start <= local.time() <= end


def load_data() -> Dict:
    _ensure_dirs()
    if not os.path.exists(DATA_FILE):
        return {
            "participants": DEFAULT_PARTICIPANTS,
            "weeks": {}
        }
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Backfill Standardfelder
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
    _ensure_dirs()
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


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


def set_week_goal(week_key: str, user: str, goal_points: int, set_by: str) -> None:
    """Setzt Wochenziel. Außerhalb des Fensters als pending gespeichert."""
    data = load_data()
    ensure_user_week(data, week_key, user)
    user_entry = data["weeks"][week_key]["users"][user]
    clamped = min(100, max(0, int(goal_points)))
    if is_in_commit_window():
        user_entry["goal_points"] = clamped
        user_entry["pending_goal"] = None
        user_entry.setdefault("audit", []).append({
            "type": "goal_set",
            "points": int(clamped),
            "by": set_by,
            "ts": datetime.now(TZ).isoformat()
        })
    else:
        user_entry["pending_goal"] = clamped
    save_data(data)


def record_activity(week_key: str, user: str, kind: str, points: int, set_by: str, note: str = "") -> None:
    """Erfasst Aktivität. Außerhalb des Fensters pending."""
    assert kind in ("T1", "T2", "telefonie", "extra")
    points = min(100, max(0, int(points)))
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
            udata["goal_points"] = max(0, int(udata["pending_goal"]))
            udata["pending_goal"] = None
            goals_applied += 1
            udata.setdefault("audit", []).append({
                "type": "goal_applied",
                "points": int(udata["goal_points"]),
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
                    "points": int(p.get("points", 0)),
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
    goal = 0 if u.get("on_vacation") else int(u.get("goal_points", 0))
    achieved = sum(int(a.get("points", 0)) for a in u.get("activities", []))
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


