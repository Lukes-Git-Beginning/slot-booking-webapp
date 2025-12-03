# -*- coding: utf-8 -*-
"""
Error Messages
User-friendly error message templates for different error categories
"""

ERROR_MESSAGES = {
    "VALIDATION": {
        "title": "Eingabefehler",
        "message": "{details}",
        "severity": "LOW",
        "show_error_id": False,
        "show_support": False
    },

    "SLOT_FULL": {
        "title": "Slot bereits belegt",
        "message": "Dieser Zeitslot ist bereits vollständig gebucht. Bitte wählen Sie einen anderen Zeitpunkt.",
        "severity": "LOW",
        "show_error_id": False,
        "show_support": False
    },

    "SLOT_LOCKED": {
        "title": "Slot wird gerade bearbeitet",
        "message": "Ein anderer Benutzer bearbeitet gerade diesen Slot. Bitte warten Sie einen Moment.",
        "severity": "LOW",
        "show_error_id": False,
        "show_support": False
    },

    "HOLIDAY_BLOCKED": {
        "title": "Datum gesperrt",
        "message": "Dieser Tag ist gesperrt: {reason}",
        "severity": "LOW",
        "show_error_id": False,
        "show_support": False
    },

    # Calendar API errors
    "CALENDAR_QUOTA": {
        "title": "Kalender-Limit erreicht",
        "message": "Das tägliche API-Limit wurde erreicht. Das System nutzt Cache-Daten.",
        "severity": "MEDIUM",
        "show_error_id": True,
        "show_support": True
    },

    "CALENDAR_RATE_LIMIT": {
        "title": "Zu viele Anfragen",
        "message": "Zu viele Kalender-Anfragen. Das System wartet automatisch und versucht es erneut.",
        "severity": "MEDIUM",
        "show_error_id": False,
        "show_support": False
    },

    "CALENDAR_NETWORK": {
        "title": "Netzwerk-Problem",
        "message": "Verbindung zum Google Calendar fehlgeschlagen. Das System versucht es automatisch erneut.",
        "severity": "MEDIUM",
        "show_error_id": True,
        "show_support": True
    },

    "CALENDAR_INVALID_DATA": {
        "title": "Ungültige Termin-Daten",
        "message": "Die Termin-Daten konnten nicht validiert werden. Bitte überprüfen Sie Ihre Eingaben.",
        "severity": "MEDIUM",
        "show_error_id": True,
        "show_support": True
    },

    "CALENDAR_UNAVAILABLE": {
        "title": "Kalender-Service nicht verfügbar",
        "message": "Der Google Calendar Service ist momentan nicht erreichbar. Ihre Buchung wurde NICHT erstellt.",
        "severity": "HIGH",
        "show_error_id": True,
        "show_support": True
    },

    # Tracking errors
    "TRACKING_FAILED": {
        "title": "Tracking-Warnung",
        "message": "Ihr Termin wurde im Kalender erstellt, aber das Tracking ist fehlgeschlagen. Bitte informieren Sie einen Administrator.",
        "severity": "MEDIUM",
        "show_error_id": True,
        "show_support": True
    },

    # Authentication errors
    "CSRF_TOKEN": {
        "title": "Sicherheits-Token fehlt",
        "message": "Die Sicherheitsprüfung ist fehlgeschlagen. Bitte laden Sie die Seite neu und versuchen Sie es erneut.",
        "severity": "MEDIUM",
        "show_error_id": False,
        "show_support": False
    },

    "SESSION_EXPIRED": {
        "title": "Sitzung abgelaufen",
        "message": "Ihre Sitzung ist abgelaufen. Bitte melden Sie sich erneut an.",
        "severity": "LOW",
        "show_error_id": False,
        "show_support": False
    },

    # System errors
    "DATABASE": {
        "title": "Datenbank-Fehler",
        "message": "Es ist ein Datenbankfehler aufgetreten. Das Entwicklungsteam wurde benachrichtigt.",
        "severity": "HIGH",
        "show_error_id": True,
        "show_support": True
    },

    "CONFIGURATION": {
        "title": "Konfigurationsfehler",
        "message": "Der Service ist nicht korrekt konfiguriert. Das Entwicklungsteam wurde benachrichtigt.",
        "severity": "CRITICAL",
        "show_error_id": True,
        "show_support": True
    },

    "INTERNAL": {
        "title": "Interner Server-Fehler",
        "message": "Ein unerwarteter Fehler ist aufgetreten. Das Entwicklungsteam wurde automatisch benachrichtigt.",
        "severity": "CRITICAL",
        "show_error_id": True,
        "show_support": True
    }
}


def get_error_message(category: str) -> dict:
    """
    Get error message template by category

    Args:
        category: Error category string (e.g., 'CALENDAR_QUOTA', 'TRACKING_FAILED')

    Returns:
        dict: Error message template with title, message, severity, show_error_id, show_support
    """
    return ERROR_MESSAGES.get(category, ERROR_MESSAGES["INTERNAL"])
