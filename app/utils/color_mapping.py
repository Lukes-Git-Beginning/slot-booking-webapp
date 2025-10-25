# -*- coding: utf-8 -*-
"""
Zentrale Color-Definition für das Slot Booking System
Vereinheitlicht alle Color-Mappings im System
"""

# Google Calendar Color IDs und ihre Bedeutung
CALENDAR_COLORS = {
    # Positive Outcomes (Berater verfügbar)
    "2": {
        "name": "Grün",
        "outcome": "completed",
        "potential_type": "normal",
        "blocks_availability": True,
        "description": "Normales Potential - Termin abgeschlossen"
    },
    "7": {
        "name": "Blau", 
        "outcome": "completed",
        "potential_type": "top",
        "blocks_availability": True,
        "description": "Top Potential - Termin abgeschlossen"
    },
    "5": {
        "name": "Gelb",
        "outcome": "completed", 
        "potential_type": "closer_needed",
        "blocks_availability": True,
        "description": "Closer nötig - Termin abgeschlossen"
    },
    "3": {
        "name": "Weintraube",
        "outcome": "completed",
        "potential_type": "recall", 
        "blocks_availability": True,
        "description": "Rückholung - Termin abgeschlossen"
    },
    "9": {
        "name": "Graphit",
        "outcome": "completed",
        "potential_type": "standard",
        "blocks_availability": True,
        "description": "Standard - Termin abgeschlossen"
    },
    "10": {
        "name": "Flamingo",
        "outcome": "completed",
        "potential_type": "standard",
        "blocks_availability": True,
        "description": "Standard - Termin abgeschlossen"
    },
    
    # Negative Outcomes (Berater NICHT verfügbar)
    "11": {
        "name": "Tomate",
        "outcome": "no_show",
        "potential_type": "no_show",
        "blocks_availability": False,  # WICHTIG: Blockiert NICHT die Verfügbarkeit
        "description": "No-Show - Kunde nicht erschienen"
    },
    "6": {
        "name": "Mandarine", 
        "outcome": "no_show",
        "potential_type": "cancelled",
        "blocks_availability": False,  # WICHTIG: Blockiert NICHT die Verfügbarkeit
        "description": "Abgesagt/Umgebucht - Zählt als No-Show"
    },
    
    # Häufige Berater-Änderungen (NICHT blockierend)
    "4": {
        "name": "Lavendel",
        "outcome": "no_show",
        "potential_type": "no_t1",
        "blocks_availability": False,
        "description": "Kein T1 bekommen - Berater-Änderung"
    },
    "8": {
        "name": "Pekoe",
        "outcome": "completed",
        "potential_type": "customer_name",
        "blocks_availability": False,
        "description": "Kundennamen eingetragen - Berater-Änderung"
    },
    "1": {
        "name": "Lavendel",
        "outcome": "completed", 
        "potential_type": "custom",
        "blocks_availability": False,
        "description": "Berater-Notiz - Blockiert nicht"
    }
}

# Farben die NICHT blockieren (für Availability Check)
NON_BLOCKING_COLORS = ["11", "6", "4", "8", "1"]

# Farben die blockieren (für Availability Check)  
BLOCKING_COLORS = ["2", "7", "5", "3", "9", "10"]

def get_outcome_from_color(color_id):
    """
    Bestimmt das Outcome basierend auf der Color ID
    """
    color_id = str(color_id)
    return CALENDAR_COLORS.get(color_id, {}).get("outcome", "completed")

def get_potential_type(color_id):
    """
    Bestimmt den Potential Type basierend auf der Color ID
    """
    color_id = str(color_id)
    return CALENDAR_COLORS.get(color_id, {}).get("potential_type", "unknown")

def blocks_availability(color_id):
    """
    Prüft ob eine Color ID die Verfügbarkeit blockiert
    """
    color_id = str(color_id)
    return CALENDAR_COLORS.get(color_id, {}).get("blocks_availability", True)

def get_color_info(color_id):
    """
    Gibt alle Informationen zu einer Color ID zurück
    """
    color_id = str(color_id)
    return CALENDAR_COLORS.get(color_id, {
        "name": "Unbekannt",
        "outcome": "completed",
        "potential_type": "unknown", 
        "blocks_availability": True,
        "description": "Unbekannte Farbe"
    })

def get_available_colors():
    """
    Gibt alle verfügbaren Color IDs zurück
    """
    return list(CALENDAR_COLORS.keys())

def get_completed_colors():
    """
    Gibt Color IDs zurück die als "abgeschlossen" gelten
    """
    return [cid for cid, info in CALENDAR_COLORS.items() if info["outcome"] == "completed"]

def get_no_show_colors():
    """
    Gibt Color IDs zurück die als "No-Show" gelten
    """
    return [cid for cid, info in CALENDAR_COLORS.items() if info["outcome"] == "no_show"]

def get_cancelled_colors():
    """
    Gibt Color IDs zurück die als "abgesagt" gelten
    """
    return [cid for cid, info in CALENDAR_COLORS.items() if info["outcome"] == "cancelled"]


# ============================================================================
# MY CALENDAR - CONSULTANT ANALYTICS FUNCTIONS
# ============================================================================

def get_booking_status(color_id, summary, event_date):
    """
    Bestimmt den Status eines Termins für My Calendar

    Args:
        color_id: Google Calendar Color ID
        summary: Event-Titel/Summary
        event_date: datetime.date object des Termins

    Returns:
        dict mit: status, label, badge_class, bg_class, status_icon, is_positive
    """
    from datetime import date

    color_id = str(color_id)
    summary_lower = summary.lower()
    today = date.today()
    is_future = event_date >= today

    # Status-Bestimmung (Priorität: Datum > Titel > Color)

    # 1. PENDING: Zukünftige Termine
    if is_future:
        return {
            'status': 'pending',
            'label': 'Ausstehend',
            'badge_class': 'badge-ghost',
            'bg_class': 'hover:bg-base-200',
            'status_icon': 'clock',
            'is_positive': None,
            'column': 'pending'
        }

    # 2. GHOST: Rot + "Ghost" im Titel
    if color_id == '11' and 'ghost' in summary_lower:
        return {
            'status': 'ghost',
            'label': 'Ghost',
            'badge_class': 'badge-error border-2 border-red-900',
            'bg_class': 'bg-red-900/10 hover:bg-red-900/20',
            'status_icon': 'user-x',
            'is_positive': False,
            'column': 'ghost'
        }

    # 3. NICHT ERSCHIENEN: Rot (11) ohne "Ghost"
    if color_id == '11':
        return {
            'status': 'nicht_erschienen',
            'label': 'Nicht erschienen',
            'badge_class': 'badge-error',
            'bg_class': 'bg-error/10 hover:bg-error/20',
            'status_icon': 'x-circle',
            'is_positive': False,
            'column': 'nicht_erschienen'
        }

    # 4. VERSCHOBEN/ABGESAGT: Orange (6)
    if color_id == '6':
        if 'verschoben' in summary_lower:
            label = 'Verschoben'
        elif 'abgesagt' in summary_lower:
            label = 'Abgesagt'
        else:
            label = 'Verschoben/Abgesagt'

        return {
            'status': 'verschoben',
            'label': label,
            'badge_class': 'badge-info',
            'bg_class': 'bg-info/10 hover:bg-info/20',
            'status_icon': 'calendar-x',
            'is_positive': False,
            'column': 'verschoben'
        }

    # 5. RÜCKHOLUNG: Weintraube (3)
    if color_id == '3':
        return {
            'status': 'rückholung',
            'label': 'Rückholung',
            'badge_class': 'badge-primary',
            'bg_class': 'bg-purple-500/10 hover:bg-purple-500/20',
            'status_icon': 'refresh-cw',
            'is_positive': True,
            'column': 'rückholung'
        }

    # 6. SONDERKUNDEN: Gelb (5)
    if color_id == '5':
        return {
            'status': 'sonderkunde',
            'label': 'Sonderkunde',
            'badge_class': 'badge-warning',
            'bg_class': 'bg-warning/10 hover:bg-warning/20',
            'status_icon': 'star',
            'is_positive': True,
            'column': 'sonderkunden'
        }

    # 7. ERSCHIENEN: Grün (2), Türkis (7), oder andere positive Farben
    if color_id in ['2', '7', '9', '10']:
        # Bestimme Potential-Typ für Label
        if color_id == '7':
            potential_label = ' (Top)'
        elif color_id == '2':
            potential_label = ' (Normal)'
        else:
            potential_label = ''

        return {
            'status': 'erschienen',
            'label': f'Erschienen{potential_label}',
            'badge_class': 'badge-success',
            'bg_class': 'bg-success/10 hover:bg-success/20',
            'status_icon': 'check-circle',
            'is_positive': True,
            'column': 'erschienen'
        }

    # Default: Erschienen
    return {
        'status': 'erschienen',
        'label': 'Erschienen',
        'badge_class': 'badge-success',
        'bg_class': 'bg-success/10 hover:bg-success/20',
        'status_icon': 'check-circle',
        'is_positive': True,
        'column': 'erschienen'
    }


def get_kanban_column(color_id, summary, event_date):
    """
    Bestimmt die Kanban-Spalte für ein Event

    Returns:
        str: column name (pending, erschienen, rückholung, sonderkunden,
             verschoben, nicht_erschienen, ghost)
    """
    status_info = get_booking_status(color_id, summary, event_date)
    return status_info['column']


def get_status_badge_class(status):
    """
    Gibt die Tailwind/DaisyUI Badge-Klasse für einen Status zurück

    Args:
        status: Status-String (pending, erschienen, etc.)

    Returns:
        str: CSS-Klassen für Badge
    """
    badge_map = {
        'pending': 'badge-ghost',
        'erschienen': 'badge-success',
        'rückholung': 'badge-primary',
        'sonderkunde': 'badge-warning',
        'verschoben': 'badge-info',
        'nicht_erschienen': 'badge-error',
        'ghost': 'badge-error border-2 border-red-900'
    }
    return badge_map.get(status, 'badge-ghost')


def get_row_background_class(status):
    """
    Gibt die Tailwind Background-Klasse für Tabellenzeilen zurück

    Args:
        status: Status-String

    Returns:
        str: CSS-Klassen für Background
    """
    bg_map = {
        'pending': 'hover:bg-base-200',
        'erschienen': 'bg-success/10 hover:bg-success/20',
        'rückholung': 'bg-purple-500/10 hover:bg-purple-500/20',
        'sonderkunde': 'bg-warning/10 hover:bg-warning/20',
        'verschoben': 'bg-info/10 hover:bg-info/20',
        'nicht_erschienen': 'bg-error/10 hover:bg-error/20',
        'ghost': 'bg-red-900/10 hover:bg-red-900/20'
    }
    return bg_map.get(status, 'hover:bg-base-200')


def get_column_stats(events_by_column):
    """
    Berechnet Statistiken für die Kanban-Spalten

    Args:
        events_by_column: dict mit Spalten als Keys und Event-Listen als Values

    Returns:
        dict mit Statistiken
    """
    total = sum(len(events) for events in events_by_column.values())

    # Abgeschlossene Termine (ohne pending)
    completed_statuses = ['erschienen', 'rückholung', 'sonderkunde', 'verschoben', 'nicht_erschienen', 'ghost']
    total_completed = sum(
        len(events_by_column.get(status, []))
        for status in completed_statuses
    )

    # Erfolgreiche Termine
    erschienen = len(events_by_column.get('erschienen', []))
    rückholung = len(events_by_column.get('rückholung', []))
    sonderkunde = len(events_by_column.get('sonderkunde', []))
    total_erfolg = erschienen + rückholung + sonderkunde

    # Nicht erfolgreiche Termine
    nicht_erschienen = len(events_by_column.get('nicht_erschienen', []))
    ghost = len(events_by_column.get('ghost', []))
    verschoben = len(events_by_column.get('verschoben', []))
    total_misserfolg = nicht_erschienen + ghost

    # Raten berechnen
    show_rate = (total_erfolg / total_completed * 100) if total_completed > 0 else 0
    no_show_rate = (total_misserfolg / total_completed * 100) if total_completed > 0 else 0

    return {
        'total': total,
        'pending': len(events_by_column.get('pending', [])),
        'erschienen': erschienen,
        'rückholung': rückholung,
        'sonderkunden': sonderkunde,
        'verschoben': verschoben,
        'nicht_erschienen': nicht_erschienen,
        'ghost': ghost,
        'total_completed': total_completed,
        'total_erfolg': total_erfolg,
        'total_misserfolg': total_misserfolg,
        'show_rate': round(show_rate, 1),
        'no_show_rate': round(no_show_rate, 1)
    }
