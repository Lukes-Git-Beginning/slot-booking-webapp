# -*- coding: utf-8 -*-
"""
Zentrale Color-Definition für das Slot Booking System
"""

# Google Calendar Color IDs und ihre Bedeutung
CALENDAR_COLORS = {
    # Positive Outcomes (blockieren Verfügbarkeit)
    "2": {"name": "Grün", "outcome": "completed", "potential_type": "normal", "blocks_availability": True},
    "7": {"name": "Blau", "outcome": "completed", "potential_type": "top", "blocks_availability": True},
    "5": {"name": "Gelb", "outcome": "completed", "potential_type": "closer_needed", "blocks_availability": True},
    "3": {"name": "Weintraube", "outcome": "completed", "potential_type": "recall", "blocks_availability": True},
    "9": {"name": "Graphit", "outcome": "completed", "potential_type": "standard", "blocks_availability": True},
    "10": {"name": "Flamingo", "outcome": "completed", "potential_type": "standard", "blocks_availability": True},
    
    # Negative Outcomes (blockieren NICHT)
    "11": {"name": "Tomate", "outcome": "no_show", "potential_type": "no_show", "blocks_availability": False},
    "6": {"name": "Mandarine", "outcome": "cancelled", "potential_type": "cancelled", "blocks_availability": False},
    
    # Berater-Änderungen (blockieren NICHT)
    "4": {"name": "Lavendel", "outcome": "no_show", "potential_type": "no_t1", "blocks_availability": False},
    "8": {"name": "Pekoe", "outcome": "completed", "potential_type": "customer_name", "blocks_availability": False},
    "1": {"name": "Lavendel", "outcome": "completed", "potential_type": "custom", "blocks_availability": False}
}

# Quick Access Lists
NON_BLOCKING_COLORS = ["11", "6", "4", "8", "1"]
BLOCKING_COLORS = ["2", "7", "5", "3", "9", "10"]

def get_outcome_from_color(color_id):
    """Bestimmt das Outcome basierend auf der Color ID"""
    color_id = str(color_id)
    return CALENDAR_COLORS.get(color_id, {}).get("outcome", "completed")

def get_potential_type(color_id):
    """Bestimmt den Potential Type basierend auf der Color ID"""
    color_id = str(color_id)
    return CALENDAR_COLORS.get(color_id, {}).get("potential_type", "unknown")

def blocks_availability(color_id):
    """Prüft ob eine Color ID die Verfügbarkeit blockiert"""
    color_id = str(color_id)
    return CALENDAR_COLORS.get(color_id, {}).get("blocks_availability", True)

def get_color_info(color_id):
    """Gibt alle Informationen zu einer Color ID zurück"""
    color_id = str(color_id)
    return CALENDAR_COLORS.get(color_id, {
        "name": "Unbekannt",
        "outcome": "completed",
        "potential_type": "unknown", 
        "blocks_availability": True
    })

def get_available_colors():
    """Gibt alle verfügbaren Color IDs zurück"""
    return list(CALENDAR_COLORS.keys())

def get_colors_by_outcome(outcome):
    """Gibt Color IDs für ein bestimmtes Outcome zurück"""
    return [cid for cid, info in CALENDAR_COLORS.items() if info["outcome"] == outcome]

def get_colors_by_blocking(blocks=True):
    """Gibt Color IDs zurück basierend auf Blocking-Status"""
    return [cid for cid, info in CALENDAR_COLORS.items() if info["blocks_availability"] == blocks]

# Convenience functions für Rückwärtskompatibilität
def get_completed_colors():
    """Gibt Color IDs zurück die als 'abgeschlossen' gelten"""
    return get_colors_by_outcome("completed")

def get_no_show_colors():
    """Gibt Color IDs zurück die als 'No-Show' gelten"""
    return get_colors_by_outcome("no_show")

def get_cancelled_colors():
    """Gibt Color IDs zurück die als 'abgesagt' gelten"""
    return get_colors_by_outcome("cancelled")

def get_blocking_colors():
    """Gibt Color IDs zurück die die Verfügbarkeit blockieren"""
    return get_colors_by_blocking(True)

def get_non_blocking_colors():
    """Gibt Color IDs zurück die die Verfügbarkeit NICHT blockieren"""
    return get_colors_by_blocking(False)

# Validierungsfunktionen
def is_valid_color(color_id):
    """Prüft ob eine Color ID gültig ist"""
    return str(color_id) in CALENDAR_COLORS

def is_blocking_color(color_id):
    """Prüft ob eine Color ID blockierend ist"""
    return str(color_id) in BLOCKING_COLORS

def is_non_blocking_color(color_id):
    """Prüft ob eine Color ID nicht-blockierend ist"""
    return str(color_id) in NON_BLOCKING_COLORS

def get_color_summary():
    """Gibt eine Zusammenfassung aller Farben zurück"""
    return {
        "total_colors": len(CALENDAR_COLORS),
        "blocking_colors": len(BLOCKING_COLORS),
        "non_blocking_colors": len(NON_BLOCKING_COLORS),
        "outcomes": list(set(info["outcome"] for info in CALENDAR_COLORS.values()))
    }