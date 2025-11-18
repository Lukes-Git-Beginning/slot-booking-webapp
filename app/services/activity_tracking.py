# -*- coding: utf-8 -*-
"""
Activity Tracking Service
Tracks user login activity and online status for admin monitoring
"""

from datetime import datetime, timedelta
import pytz
from typing import Dict, List, Optional
import logging

from app.services.data_persistence import data_persistence

logger = logging.getLogger(__name__)
TZ = pytz.timezone('Europe/Berlin')


class ActivityTrackingService:
    """Service für Login-Tracking und Online-Status-Verwaltung"""

    def __init__(self):
        self.login_history_file = 'login_history'
        self.online_sessions_file = 'online_sessions'

    def track_login(self, username: str, ip_address: str, user_agent: str, success: bool = True) -> None:
        """
        Trackt einen Login-Versuch

        Args:
            username: Benutzername
            ip_address: IP-Adresse des Users
            user_agent: Browser User-Agent String
            success: Ob der Login erfolgreich war
        """
        try:
            # Lade aktuelle Login-History
            login_history = data_persistence.load_data(self.login_history_file, default={})

            # Initialisiere User-History wenn nicht vorhanden
            if username not in login_history:
                login_history[username] = []

            # Erstelle Login-Entry
            login_entry = {
                'timestamp': datetime.now(TZ).isoformat(),
                'ip_address': ip_address,
                'user_agent': user_agent,
                'success': success,
                'browser': self._extract_browser(user_agent),
                'device': self._extract_device(user_agent)
            }

            # Füge zur History hinzu (neueste zuerst)
            login_history[username].insert(0, login_entry)

            # Behalte nur die letzten 100 Logins pro User
            login_history[username] = login_history[username][:100]

            # Speichere
            data_persistence.save_data(self.login_history_file, login_history)

            logger.info(f"Login tracked for {username} from {ip_address}")

        except Exception as e:
            logger.error(f"Error tracking login for {username}: {e}")

    def update_online_status(self, username: str, session_id: str, action: str = 'active') -> None:
        """
        Aktualisiert den Online-Status eines Users

        Args:
            username: Benutzername
            session_id: Flask Session-ID
            action: 'active' oder 'logout'
        """
        try:
            online_sessions = data_persistence.load_data(self.online_sessions_file, default={})

            if action == 'active':
                # Update/Create Session
                online_sessions[username] = {
                    'session_id': session_id,
                    'last_activity': datetime.now(TZ).isoformat(),
                    'status': 'online'
                }
            elif action == 'logout':
                # Entferne Session
                if username in online_sessions:
                    del online_sessions[username]

            # Speichere
            data_persistence.save_data(self.online_sessions_file, online_sessions)

        except Exception as e:
            logger.error(f"Error updating online status for {username}: {e}")

    def get_online_users(self, timeout_minutes: int = 15) -> List[Dict]:
        """
        Gibt Liste der aktuell online Users zurück

        Args:
            timeout_minutes: Nach wie vielen Minuten ohne Aktivität gilt ein User als offline

        Returns:
            Liste von Dicts mit User-Info und letzter Aktivität
        """
        try:
            online_sessions = data_persistence.load_data(self.online_sessions_file, default={})
            current_time = datetime.now(TZ)
            online_users = []

            # Cleanup alte Sessions und erstelle Online-Liste
            for username, session_data in list(online_sessions.items()):
                last_activity = datetime.fromisoformat(session_data['last_activity'])

                # Prüfe ob Session noch gültig ist
                time_diff = current_time - last_activity

                if time_diff.total_seconds() / 60 <= timeout_minutes:
                    # User ist online
                    online_users.append({
                        'username': username,
                        'last_activity': session_data['last_activity'],
                        'minutes_ago': int(time_diff.total_seconds() / 60),
                        'status': 'online'
                    })
                else:
                    # Session ist abgelaufen, entfernen
                    del online_sessions[username]

            # Speichere bereinigte Sessions
            data_persistence.save_data(self.online_sessions_file, online_sessions)

            # Sortiere nach letzter Aktivität (neueste zuerst)
            online_users.sort(key=lambda x: x['last_activity'], reverse=True)

            return online_users

        except Exception as e:
            logger.error(f"Error getting online users: {e}")
            return []

    def get_user_login_history(self, username: str, limit: int = 20) -> List[Dict]:
        """
        Gibt Login-History eines Users zurück

        Args:
            username: Benutzername
            limit: Anzahl der letzten Logins

        Returns:
            Liste von Login-Entries
        """
        try:
            login_history = data_persistence.load_data(self.login_history_file, default={})
            user_history = login_history.get(username, [])

            # Füge formatierte Timestamps hinzu
            for entry in user_history[:limit]:
                try:
                    dt = datetime.fromisoformat(entry['timestamp'])
                    entry['formatted_time'] = dt.strftime('%d.%m.%Y %H:%M:%S')
                    entry['time_ago'] = self._format_time_ago(dt)
                except:
                    entry['formatted_time'] = entry['timestamp']
                    entry['time_ago'] = 'Unbekannt'

            return user_history[:limit]

        except Exception as e:
            logger.error(f"Error getting login history for {username}: {e}")
            return []

    def get_all_login_activity(self, limit: int = 50) -> List[Dict]:
        """
        Gibt letzte Logins aller User zurück (für Admin-Dashboard)

        Args:
            limit: Anzahl der Einträge

        Returns:
            Liste von Login-Entries mit Usernames
        """
        try:
            login_history = data_persistence.load_data(self.login_history_file, default={})
            all_logins = []

            # Sammle alle Logins
            for username, user_logins in login_history.items():
                for login in user_logins:
                    login_copy = login.copy()
                    login_copy['username'] = username
                    all_logins.append(login_copy)

            # Sortiere nach Timestamp (neueste zuerst)
            all_logins.sort(key=lambda x: x['timestamp'], reverse=True)

            # Füge formatierte Timestamps hinzu
            for entry in all_logins[:limit]:
                try:
                    dt = datetime.fromisoformat(entry['timestamp'])
                    entry['formatted_time'] = dt.strftime('%d.%m.%Y %H:%M:%S')
                    entry['time_ago'] = self._format_time_ago(dt)
                except:
                    entry['formatted_time'] = entry['timestamp']
                    entry['time_ago'] = 'Unbekannt'

            return all_logins[:limit]

        except Exception as e:
            logger.error(f"Error getting all login activity: {e}")
            return []

    def get_login_stats(self, username: Optional[str] = None, days: int = 30) -> Dict:
        """
        Generiert Login-Statistiken

        Args:
            username: Optional - Stats für spezifischen User, sonst für alle
            days: Anzahl der Tage für Statistik

        Returns:
            Dict mit Statistiken
        """
        try:
            login_history = data_persistence.load_data(self.login_history_file, default={})
            cutoff_date = datetime.now(TZ) - timedelta(days=days)

            stats = {
                'total_logins': 0,
                'unique_users': set(),
                'failed_logins': 0,
                'success_logins': 0,
                'unique_ips': set(),
                'logins_by_day': {},
                'logins_by_hour': [0] * 24
            }

            # Filtere User wenn angegeben
            users_to_check = {username: login_history[username]} if username and username in login_history else login_history

            for user, user_logins in users_to_check.items():
                for login in user_logins:
                    try:
                        login_time = datetime.fromisoformat(login['timestamp'])

                        # Nur Logins innerhalb des Zeitraums
                        if login_time < cutoff_date:
                            continue

                        stats['total_logins'] += 1
                        stats['unique_users'].add(user)
                        stats['unique_ips'].add(login.get('ip_address', 'unknown'))

                        if login.get('success', True):
                            stats['success_logins'] += 1
                        else:
                            stats['failed_logins'] += 1

                        # Logins pro Tag
                        day_key = login_time.strftime('%Y-%m-%d')
                        stats['logins_by_day'][day_key] = stats['logins_by_day'].get(day_key, 0) + 1

                        # Logins pro Stunde
                        hour = login_time.hour
                        stats['logins_by_hour'][hour] += 1

                    except Exception as e:
                        logger.error(f"Error processing login entry: {e}")
                        continue

            # Konvertiere Sets zu Counts
            stats['unique_users'] = len(stats['unique_users'])
            stats['unique_ips'] = len(stats['unique_ips'])

            # Finde Peak-Hour
            peak_hour = max(range(24), key=lambda h: stats['logins_by_hour'][h])
            stats['peak_hour'] = f"{peak_hour:02d}:00-{(peak_hour+1):02d}:00"
            stats['peak_hour_logins'] = stats['logins_by_hour'][peak_hour]

            return stats

        except Exception as e:
            logger.error(f"Error calculating login stats: {e}")
            return {
                'total_logins': 0,
                'unique_users': 0,
                'failed_logins': 0,
                'success_logins': 0,
                'unique_ips': 0,
                'logins_by_day': {},
                'logins_by_hour': [0] * 24,
                'peak_hour': 'N/A',
                'peak_hour_logins': 0
            }

    # Helper Methods

    def _extract_browser(self, user_agent: str) -> str:
        """Extrahiert Browser-Namen aus User-Agent String"""
        user_agent_lower = user_agent.lower()

        if 'edg' in user_agent_lower:
            return 'Edge'
        elif 'chrome' in user_agent_lower:
            return 'Chrome'
        elif 'firefox' in user_agent_lower:
            return 'Firefox'
        elif 'safari' in user_agent_lower and 'chrome' not in user_agent_lower:
            return 'Safari'
        elif 'opera' in user_agent_lower or 'opr' in user_agent_lower:
            return 'Opera'
        else:
            return 'Unbekannt'

    def _extract_device(self, user_agent: str) -> str:
        """Extrahiert Device-Typ aus User-Agent String"""
        user_agent_lower = user_agent.lower()

        if 'mobile' in user_agent_lower or 'android' in user_agent_lower or 'iphone' in user_agent_lower:
            return 'Mobile'
        elif 'tablet' in user_agent_lower or 'ipad' in user_agent_lower:
            return 'Tablet'
        else:
            return 'Desktop'

    def _format_time_ago(self, dt: datetime) -> str:
        """Formatiert Zeit als 'vor X Minuten/Stunden/Tagen'"""
        now = datetime.now(TZ)

        # Ensure dt is timezone-aware
        if dt.tzinfo is None:
            dt = TZ.localize(dt)

        diff = now - dt

        seconds = diff.total_seconds()

        if seconds < 60:
            return 'gerade eben'
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f'vor {minutes} Min.'
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f'vor {hours} Std.'
        else:
            days = int(seconds / 86400)
            return f'vor {days} Tag(en)'


# Singleton instance
activity_tracking = ActivityTrackingService()
