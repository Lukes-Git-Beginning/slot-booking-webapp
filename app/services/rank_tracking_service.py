# -*- coding: utf-8 -*-
"""
Rank Tracking Service - Taegliche Rang-Snapshots fuer Scoreboard

Speichert taegliche Rang-Positionen und berechnet Rang-Aenderungen.
Dual-Write: JSON + PostgreSQL (wenn verfuegbar).
"""

import os
import json
import logging
from datetime import datetime, timedelta

import pytz

logger = logging.getLogger(__name__)

TZ = pytz.timezone("Europe/Berlin")

# PostgreSQL dual-write support
USE_POSTGRES = os.getenv('USE_POSTGRES', 'true').lower() == 'true'

try:
    from app.models.gamification import RankHistory as RankHistoryModel
    from app.utils.db_utils import db_session_scope
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    USE_POSTGRES = False


class RankTrackingService:
    def __init__(self):
        persist_base = os.getenv("PERSIST_BASE", "data")
        self.history_file = os.path.join(persist_base, "persistent", "rank_history.json")
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)

        if not os.path.exists(self.history_file):
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump({}, f)

    def _load_history(self):
        """Load rank history — PG-first with JSON fallback"""
        if USE_POSTGRES and POSTGRES_AVAILABLE:
            try:
                with db_session_scope() as session:
                    rows = session.query(RankHistoryModel).order_by(RankHistoryModel.date).all()
                    history = {}
                    for row in rows:
                        if row.date not in history:
                            history[row.date] = {}
                        history[row.date][row.username] = row.rank_position
                    return history
            except Exception as e:
                logger.warning(f"PG rank history read failed: {e}")
        # JSON fallback
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_history(self, data):
        """Save rank history to JSON"""
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def record_daily_ranks(self, scores_list):
        """
        Speichert aktuelles Ranking als Tages-Snapshot.

        Args:
            scores_list: Liste von (username, points) Tuples, bereits sortiert
        """
        today = datetime.now(TZ).strftime("%Y-%m-%d")
        history = self._load_history()

        # Bereits fuer heute gespeichert? Ueberschreiben.
        rank_snapshot = {}
        for idx, (username, _points) in enumerate(scores_list, start=1):
            rank_snapshot[username] = idx

        history[today] = rank_snapshot
        self._save_history(history)

        # Dual-write to PostgreSQL
        self._pg_sync_ranks(today, rank_snapshot)

        logger.debug(f"Rank snapshot recorded for {today}: {len(rank_snapshot)} users")

    def get_rank_change(self, username, current_rank):
        """
        Berechnet Rang-Aenderung seit letztem Snapshot.

        Args:
            username: Username
            current_rank: Aktuelle Rang-Position (1-based)

        Returns:
            int: Delta (positiv = aufgestiegen, z.B. war 5 jetzt 3 = +2)
                 0 wenn kein vorheriger Snapshot oder gleich
        """
        history = self._load_history()
        today = datetime.now(TZ).strftime("%Y-%m-%d")

        # Finde den letzten Snapshot VOR heute
        previous_date = None
        for date_str in sorted(history.keys(), reverse=True):
            if date_str < today:
                previous_date = date_str
                break

        if not previous_date:
            return 0

        previous_ranks = history[previous_date]
        previous_rank = previous_ranks.get(username)

        if previous_rank is None:
            return 0

        # Positiv = aufgestiegen (war 5, jetzt 3 = +2)
        return previous_rank - current_rank

    def get_rank_changes(self, scores_list):
        """
        Batch-Berechnung der Rang-Aenderungen fuer alle User.

        Args:
            scores_list: Liste von (username, points) Tuples, bereits sortiert

        Returns:
            dict: {username: delta}
        """
        history = self._load_history()
        today = datetime.now(TZ).strftime("%Y-%m-%d")

        # Finde den letzten Snapshot VOR heute
        previous_date = None
        for date_str in sorted(history.keys(), reverse=True):
            if date_str < today:
                previous_date = date_str
                break

        changes = {}
        for idx, (username, _points) in enumerate(scores_list, start=1):
            if not previous_date:
                changes[username] = 0
                continue

            previous_ranks = history.get(previous_date, {})
            previous_rank = previous_ranks.get(username)

            if previous_rank is None:
                changes[username] = 0
            else:
                changes[username] = previous_rank - idx

        return changes

    def get_rank_history(self, username, days=30):
        """
        Rang-Historie fuer einen User.

        Args:
            username: Username
            days: Anzahl Tage zurueck

        Returns:
            list: [{date, rank}, ...] sortiert nach Datum
        """
        if USE_POSTGRES and POSTGRES_AVAILABLE:
            try:
                cutoff = (datetime.now(TZ) - timedelta(days=days)).strftime("%Y-%m-%d")
                with db_session_scope() as session:
                    rows = session.query(RankHistoryModel).filter(
                        RankHistoryModel.username == username,
                        RankHistoryModel.date >= cutoff
                    ).order_by(RankHistoryModel.date).all()
                    return [{"date": row.date, "rank": row.rank_position} for row in rows]
            except Exception as e:
                logger.warning(f"PG rank history query failed: {e}")

        # JSON fallback (bestehender Code)
        history = self._load_history()
        cutoff = (datetime.now(TZ) - timedelta(days=days)).strftime("%Y-%m-%d")

        user_history = []
        for date_str in sorted(history.keys()):
            if date_str < cutoff:
                continue
            rank = history[date_str].get(username)
            if rank is not None:
                user_history.append({"date": date_str, "rank": rank})

        return user_history

    def _pg_sync_ranks(self, date_str, rank_snapshot):
        """Dual-Write: Rang-Daten in PostgreSQL syncen (Model-basiert)"""
        if not USE_POSTGRES or not POSTGRES_AVAILABLE:
            return

        try:
            with db_session_scope() as session:
                for username, rank_pos in rank_snapshot.items():
                    existing = session.query(RankHistoryModel).filter_by(
                        date=date_str, username=username
                    ).first()
                    if existing:
                        existing.rank_position = rank_pos
                    else:
                        session.add(RankHistoryModel(
                            date=date_str,
                            username=username,
                            rank_position=rank_pos
                        ))
        except Exception as e:
            logger.debug(f"PG rank sync skipped: {e}")


# Global instance
rank_tracking_service = RankTrackingService()
