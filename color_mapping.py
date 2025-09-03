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
        "outcome": "cancelled",
        "potential_type": "cancelled",
        "blocks_availability": False,  # WICHTIG: Blockiert NICHT die Verfügbarkeit
        "description": "Abgesagt - Termin storniert"
    }
}

# Farben die NICHT blockieren (für Availability Check)
NON_BLOCKING_COLORS = ["11", "6"]

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
