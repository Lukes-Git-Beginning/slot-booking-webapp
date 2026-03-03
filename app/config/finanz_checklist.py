# -*- coding: utf-8 -*-
"""
Finanzberatung Checklist Schema - Central Config for all Contract Types

Defines ~30 Vertragsarten (insurance/financial contract types) with their
required fields, priorities (MUSS/SOLL/KANN), field types, and categorization.

Used by:
- Dashboard (field display, Ampel-Status, completeness)
- Pipeline (extraction schema per contract type)
- Export (Excel/PDF field mapping with source references)
"""

# ---------------------------------------------------------------------------
# Priority Levels
# ---------------------------------------------------------------------------
PRIORITY_MUSS = "muss"      # Pflichtangabe — must have
PRIORITY_SOLL = "soll"      # Sehr empfohlen — should have
PRIORITY_KANN = "kann"      # Optional — nice to have

PRIORITY_LABELS = {
    PRIORITY_MUSS: "Pflicht",
    PRIORITY_SOLL: "Empfohlen",
    PRIORITY_KANN: "Optional",
}

PRIORITY_ORDER = {
    PRIORITY_MUSS: 0,
    PRIORITY_SOLL: 1,
    PRIORITY_KANN: 2,
}

# ---------------------------------------------------------------------------
# Field Types
# ---------------------------------------------------------------------------
FIELD_TYPE_TEXT = "text"
FIELD_TYPE_CURRENCY = "currency"
FIELD_TYPE_NUMBER = "number"
FIELD_TYPE_DATE = "date"
FIELD_TYPE_PERCENT = "percent"
FIELD_TYPE_BOOLEAN = "boolean"

# ---------------------------------------------------------------------------
# Categories — grouping of contract types
# ---------------------------------------------------------------------------
CHECKLIST_CATEGORIES = {
    "sachversicherung": {
        "label": "Sachversicherungen",
        "icon": "home",
        "types": [
            "privathaftpflicht", "hausrat", "glasbruch", "wohngebaeude",
            "rechtsschutz", "hausbesitzerhaftpflicht", "tierhalterhaftpflicht",
        ],
    },
    "kfz": {
        "label": "KFZ-Versicherungen",
        "icon": "car",
        "types": ["kfz_auto", "kfz_motorrad", "kfz_anhaenger"],
    },
    "altersvorsorge": {
        "label": "Altersvorsorge",
        "icon": "piggy-bank",
        "types": [
            "riester", "basisrente", "fondsgebundene_rv", "index_rv",
            "kapitallebensversicherung", "bav", "bausparvertrag", "sparkonto",
            "depotanlagen", "wohn_riester_bsv", "wohn_riester_depot",
        ],
    },
    "absicherung": {
        "label": "Absicherung",
        "icon": "shield-check",
        "types": [
            "bu", "grundfaehigkeiten", "dread_disease", "schulunfaehigkeit",
            "existenzschutz", "erwerbsunfaehigkeit", "rlv", "sterbegeld",
            "unfallversicherung",
        ],
    },
    "gesundheit": {
        "label": "Gesundheit & Zusatz",
        "icon": "heart-pulse",
        "types": ["zzv", "ktg", "akz", "skz", "ptg", "arkv"],
    },
    "sonstiges": {
        "label": "Sonstiges",
        "icon": "folder",
        "types": [
            "gewerbeversicherung", "reisehaftpflicht", "reisegepaeck",
            "tierkrankenversicherung",
        ],
    },
}

# ---------------------------------------------------------------------------
# Common field definitions (reusable)
# ---------------------------------------------------------------------------
_F_GESELLSCHAFT = {"name": "gesellschaft", "label": "Gesellschaft", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_TEXT}
_F_BEITRAG = {"name": "beitrag", "label": "Beitrag", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_CURRENCY}
_F_BEITRAG_NETTO = {"name": "beitrag_netto", "label": "Beitrag (Netto)", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_CURRENCY}
_F_BEITRAG_BRUTTO = {"name": "beitrag_brutto", "label": "Beitrag (Brutto)", "priority": PRIORITY_SOLL, "type": FIELD_TYPE_CURRENCY}
_F_TARIFNAME = {"name": "tarifname", "label": "Tarifname / Tarif", "priority": PRIORITY_SOLL, "type": FIELD_TYPE_TEXT}
_F_VERSICHERUNGSSUMME = {"name": "versicherungssumme", "label": "Versicherungssumme", "priority": PRIORITY_KANN, "type": FIELD_TYPE_CURRENCY}
_F_VERTRAGSBEGINN = {"name": "vertragsbeginn", "label": "Vertragsbeginn", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_DATE}
_F_VERTRAGSENDE = {"name": "vertragsende", "label": "Vertragsende", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_DATE}
_F_VERTRAGSBAUSTEIN = {"name": "vertragsbaustein", "label": "Vertragsbaustein", "priority": PRIORITY_SOLL, "type": FIELD_TYPE_TEXT}
_F_DYNAMIK = {"name": "dynamik", "label": "Dynamik", "priority": PRIORITY_KANN, "type": FIELD_TYPE_TEXT}
_F_VERSICHERTE_PERSON = {"name": "versicherte_person", "label": "Versicherte Person", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_TEXT}
_F_SELBSTBETEILIGUNG = {"name": "selbstbeteiligung", "label": "Selbstbeteiligung", "priority": PRIORITY_SOLL, "type": FIELD_TYPE_CURRENCY}
_F_LEISTUNGSART = {"name": "leistungsart", "label": "Leistungsart", "priority": PRIORITY_SOLL, "type": FIELD_TYPE_TEXT}
_F_RENTENHOEHE = {"name": "rentenhoehe", "label": "Rentenhoehe", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_CURRENCY}
_F_VERTRAGSNUMMER = {"name": "vertragsnummer", "label": "Vertragsnummer", "priority": PRIORITY_KANN, "type": FIELD_TYPE_TEXT}

# ---------------------------------------------------------------------------
# Contract Types — full definitions
# ---------------------------------------------------------------------------
CONTRACT_TYPES = {
    # ===== SACHVERSICHERUNGEN =====
    "privathaftpflicht": {
        "label": "Privathaftpflichtversicherung",
        "icon": "shield",
        "category": "sachversicherung",
        "fields": [
            {**_F_GESELLSCHAFT},
            {**_F_BEITRAG},
            {"name": "leistungsart", "label": "Leistungsart (Single/Familie)", "priority": PRIORITY_SOLL, "type": FIELD_TYPE_TEXT},
            {**_F_VERSICHERUNGSSUMME},
            {**_F_TARIFNAME},
        ],
    },
    "hausrat": {
        "label": "Hausratversicherung",
        "icon": "home",
        "category": "sachversicherung",
        "fields": [
            {**_F_GESELLSCHAFT},
            {**_F_BEITRAG},
            {**_F_VERSICHERUNGSSUMME},
            {"name": "wohnflaeche", "label": "Wohnflaeche (qm)", "priority": PRIORITY_SOLL, "type": FIELD_TYPE_NUMBER},
            {**_F_TARIFNAME},
            {**_F_SELBSTBETEILIGUNG},
        ],
    },
    "glasbruch": {
        "label": "Glasbruchversicherung",
        "icon": "square",
        "category": "sachversicherung",
        "fields": [
            {**_F_GESELLSCHAFT},
            {**_F_BEITRAG},
            {**_F_VERSICHERUNGSSUMME},
            {**_F_TARIFNAME},
        ],
    },
    "wohngebaeude": {
        "label": "Wohngebaeudeversicherung",
        "icon": "building",
        "category": "sachversicherung",
        "fields": [
            {**_F_GESELLSCHAFT},
            {**_F_BEITRAG},
            {**_F_VERSICHERUNGSSUMME},
            {"name": "gefahren", "label": "Versicherte Gefahren", "priority": PRIORITY_SOLL, "type": FIELD_TYPE_TEXT},
            {"name": "wert_1914", "label": "Wert 1914", "priority": PRIORITY_KANN, "type": FIELD_TYPE_CURRENCY},
            {**_F_TARIFNAME},
            {**_F_SELBSTBETEILIGUNG},
        ],
    },
    "rechtsschutz": {
        "label": "Rechtsschutzversicherung",
        "icon": "scale",
        "category": "sachversicherung",
        "fields": [
            {**_F_GESELLSCHAFT},
            {**_F_BEITRAG},
            {"name": "rechtsgebiete", "label": "Rechtsgebiete", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_TEXT},
            {**_F_VERSICHERUNGSSUMME},
            {**_F_SELBSTBETEILIGUNG},
            {**_F_TARIFNAME},
        ],
    },
    "hausbesitzerhaftpflicht": {
        "label": "Haus- und Grundbesitzerhaftpflicht",
        "icon": "building-2",
        "category": "sachversicherung",
        "fields": [
            {**_F_GESELLSCHAFT},
            {**_F_BEITRAG},
            {**_F_VERSICHERUNGSSUMME},
            {**_F_TARIFNAME},
        ],
    },
    "tierhalterhaftpflicht": {
        "label": "Tierhalterhaftpflichtversicherung",
        "icon": "paw-print",
        "category": "sachversicherung",
        "fields": [
            {**_F_GESELLSCHAFT},
            {**_F_BEITRAG},
            {"name": "tierart", "label": "Tierart", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_TEXT},
            {**_F_VERSICHERUNGSSUMME},
            {**_F_TARIFNAME},
        ],
    },

    # ===== KFZ =====
    "kfz_auto": {
        "label": "KFZ - Auto",
        "icon": "car",
        "category": "kfz",
        "fields": [
            {**_F_GESELLSCHAFT},
            {**_F_BEITRAG},
            {"name": "sf_klasse", "label": "SF-Klasse", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_TEXT},
            {"name": "jahreskilometer", "label": "Jahreskilometer", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_NUMBER},
            {"name": "hsn", "label": "HSN", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_TEXT},
            {"name": "tsn", "label": "TSN", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_TEXT},
            {"name": "leistungsart", "label": "Leistungsart (HP/TK/VK)", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_TEXT},
            {**_F_SELBSTBETEILIGUNG},
            {**_F_VERTRAGSBAUSTEIN},
            {"name": "fahrerkreis", "label": "Fahrerkreis", "priority": PRIORITY_KANN, "type": FIELD_TYPE_TEXT},
            {**_F_TARIFNAME},
        ],
    },
    "kfz_motorrad": {
        "label": "KFZ - Motorrad",
        "icon": "bike",
        "category": "kfz",
        "fields": [
            {**_F_GESELLSCHAFT},
            {**_F_BEITRAG},
            {"name": "sf_klasse", "label": "SF-Klasse", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_TEXT},
            {"name": "hsn", "label": "HSN", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_TEXT},
            {"name": "tsn", "label": "TSN", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_TEXT},
            {"name": "leistungsart", "label": "Leistungsart (HP/TK/VK)", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_TEXT},
            {**_F_SELBSTBETEILIGUNG},
            {**_F_TARIFNAME},
        ],
    },
    "kfz_anhaenger": {
        "label": "KFZ - Anhaenger",
        "icon": "truck",
        "category": "kfz",
        "fields": [
            {**_F_GESELLSCHAFT},
            {**_F_BEITRAG},
            {"name": "leistungsart", "label": "Leistungsart (HP/TK/VK)", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_TEXT},
            {**_F_TARIFNAME},
        ],
    },

    # ===== ALTERSVORSORGE =====
    "riester": {
        "label": "Riester-Rente",
        "icon": "piggy-bank",
        "category": "altersvorsorge",
        "fields": [
            {**_F_GESELLSCHAFT},
            {**_F_BEITRAG},
            {"name": "eigenbeitrag", "label": "Eigenbeitrag", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_CURRENCY},
            {"name": "zulage", "label": "Staatliche Zulage", "priority": PRIORITY_SOLL, "type": FIELD_TYPE_CURRENCY},
            {"name": "garantierente", "label": "Garantierte Rente", "priority": PRIORITY_SOLL, "type": FIELD_TYPE_CURRENCY},
            {**_F_VERTRAGSBEGINN},
            {**_F_TARIFNAME},
            {**_F_DYNAMIK},
        ],
    },
    "basisrente": {
        "label": "Basisrente (Ruerup)",
        "icon": "landmark",
        "category": "altersvorsorge",
        "fields": [
            {**_F_GESELLSCHAFT},
            {**_F_BEITRAG},
            {"name": "garantierente", "label": "Garantierte Rente", "priority": PRIORITY_SOLL, "type": FIELD_TYPE_CURRENCY},
            {**_F_VERTRAGSBEGINN},
            {**_F_TARIFNAME},
            {**_F_DYNAMIK},
        ],
    },
    "fondsgebundene_rv": {
        "label": "Fondsgebundene Rentenversicherung",
        "icon": "trending-up",
        "category": "altersvorsorge",
        "fields": [
            {**_F_GESELLSCHAFT},
            {**_F_BEITRAG},
            {"name": "fondsauswahl", "label": "Fondsauswahl", "priority": PRIORITY_SOLL, "type": FIELD_TYPE_TEXT},
            {"name": "garantieniveau", "label": "Garantieniveau", "priority": PRIORITY_SOLL, "type": FIELD_TYPE_PERCENT},
            {**_F_VERTRAGSBEGINN},
            {**_F_TARIFNAME},
            {**_F_DYNAMIK},
        ],
    },
    "index_rv": {
        "label": "Index-Rentenversicherung",
        "icon": "bar-chart-3",
        "category": "altersvorsorge",
        "fields": [
            {**_F_GESELLSCHAFT},
            {**_F_BEITRAG},
            {"name": "index_referenz", "label": "Index-Referenz", "priority": PRIORITY_SOLL, "type": FIELD_TYPE_TEXT},
            {"name": "cap", "label": "Cap / Partizipation", "priority": PRIORITY_SOLL, "type": FIELD_TYPE_TEXT},
            {**_F_VERTRAGSBEGINN},
            {**_F_TARIFNAME},
        ],
    },
    "kapitallebensversicherung": {
        "label": "Kapitallebensversicherung",
        "icon": "banknote",
        "category": "altersvorsorge",
        "fields": [
            {**_F_GESELLSCHAFT},
            {**_F_BEITRAG},
            {**_F_VERSICHERTE_PERSON},
            {"name": "versicherungssumme", "label": "Versicherungssumme", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_CURRENCY},
            {"name": "ablaufleistung", "label": "Prognost. Ablaufleistung", "priority": PRIORITY_SOLL, "type": FIELD_TYPE_CURRENCY},
            {**_F_VERTRAGSBEGINN},
            {**_F_VERTRAGSENDE},
            {**_F_TARIFNAME},
        ],
    },
    "bav": {
        "label": "Betriebliche Altersvorsorge (bAV)",
        "icon": "building",
        "category": "altersvorsorge",
        "fields": [
            {**_F_GESELLSCHAFT},
            {"name": "arbeitgeberbeitrag", "label": "Arbeitgeberbeitrag", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_CURRENCY},
            {"name": "arbeitnehmerbeitrag", "label": "Arbeitnehmerbeitrag", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_CURRENCY},
            {"name": "durchfuehrungsweg", "label": "Durchfuehrungsweg", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_TEXT},
            {"name": "garantierente", "label": "Garantierte Rente", "priority": PRIORITY_SOLL, "type": FIELD_TYPE_CURRENCY},
            {**_F_VERTRAGSBEGINN},
            {**_F_TARIFNAME},
        ],
    },
    "bausparvertrag": {
        "label": "Bausparvertrag",
        "icon": "home",
        "category": "altersvorsorge",
        "fields": [
            {**_F_GESELLSCHAFT},
            {"name": "bausparsumme", "label": "Bausparsumme", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_CURRENCY},
            {"name": "sparbeitrag", "label": "Sparbeitrag", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_CURRENCY},
            {"name": "guthabenzins", "label": "Guthabenzins", "priority": PRIORITY_SOLL, "type": FIELD_TYPE_PERCENT},
            {"name": "darlehenszins", "label": "Darlehenszins", "priority": PRIORITY_SOLL, "type": FIELD_TYPE_PERCENT},
            {**_F_TARIFNAME},
        ],
    },
    "sparkonto": {
        "label": "Sparkonto / Festgeld / Tagesgeld",
        "icon": "wallet",
        "category": "altersvorsorge",
        "fields": [
            {**_F_GESELLSCHAFT},
            {"name": "kontostand", "label": "Aktueller Kontostand", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_CURRENCY},
            {"name": "zinssatz", "label": "Zinssatz", "priority": PRIORITY_SOLL, "type": FIELD_TYPE_PERCENT},
            {"name": "sparbeitrag", "label": "Monatlicher Sparbeitrag", "priority": PRIORITY_SOLL, "type": FIELD_TYPE_CURRENCY},
        ],
    },
    "depotanlagen": {
        "label": "Depotanlagen / Fonds / ETFs",
        "icon": "line-chart",
        "category": "altersvorsorge",
        "fields": [
            {**_F_GESELLSCHAFT},
            {"name": "depotwert", "label": "Aktueller Depotwert", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_CURRENCY},
            {"name": "sparrate", "label": "Monatliche Sparrate", "priority": PRIORITY_SOLL, "type": FIELD_TYPE_CURRENCY},
            {"name": "fondsauswahl", "label": "Fondsauswahl / ETFs", "priority": PRIORITY_SOLL, "type": FIELD_TYPE_TEXT},
            {"name": "depotbank", "label": "Depotbank", "priority": PRIORITY_KANN, "type": FIELD_TYPE_TEXT},
        ],
    },
    "wohn_riester_bsv": {
        "label": "Wohn-Riester (Bausparvertrag)",
        "icon": "home",
        "category": "altersvorsorge",
        "fields": [
            {**_F_GESELLSCHAFT},
            {"name": "bausparsumme", "label": "Bausparsumme", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_CURRENCY},
            {"name": "eigenbeitrag", "label": "Eigenbeitrag", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_CURRENCY},
            {"name": "zulage", "label": "Staatliche Zulage", "priority": PRIORITY_SOLL, "type": FIELD_TYPE_CURRENCY},
            {**_F_TARIFNAME},
        ],
    },
    "wohn_riester_depot": {
        "label": "Wohn-Riester (Depot)",
        "icon": "home",
        "category": "altersvorsorge",
        "fields": [
            {**_F_GESELLSCHAFT},
            {"name": "depotwert", "label": "Aktueller Depotwert", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_CURRENCY},
            {"name": "eigenbeitrag", "label": "Eigenbeitrag", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_CURRENCY},
            {"name": "zulage", "label": "Staatliche Zulage", "priority": PRIORITY_SOLL, "type": FIELD_TYPE_CURRENCY},
            {**_F_TARIFNAME},
        ],
    },

    # ===== ABSICHERUNG =====
    "bu": {
        "label": "Berufsunfaehigkeitsversicherung (BU)",
        "icon": "shield-check",
        "category": "absicherung",
        "fields": [
            {**_F_GESELLSCHAFT},
            {**_F_VERSICHERTE_PERSON},
            {**_F_BEITRAG_NETTO},
            {**_F_BEITRAG_BRUTTO},
            {**_F_RENTENHOEHE},
            {**_F_VERTRAGSBEGINN},
            {**_F_VERTRAGSENDE},
            {**_F_TARIFNAME},
            {"name": "vertragsbaustein", "label": "Vertragsbaustein (AU, Pflege)", "priority": PRIORITY_SOLL, "type": FIELD_TYPE_TEXT},
            {**_F_DYNAMIK},
        ],
    },
    "grundfaehigkeiten": {
        "label": "Grundfaehigkeitsversicherung",
        "icon": "accessibility",
        "category": "absicherung",
        "fields": [
            {**_F_GESELLSCHAFT},
            {**_F_VERSICHERTE_PERSON},
            {**_F_BEITRAG_NETTO},
            {**_F_RENTENHOEHE},
            {**_F_VERTRAGSBEGINN},
            {**_F_VERTRAGSENDE},
            {**_F_TARIFNAME},
        ],
    },
    "dread_disease": {
        "label": "Dread-Disease-Versicherung",
        "icon": "heart",
        "category": "absicherung",
        "fields": [
            {**_F_GESELLSCHAFT},
            {**_F_VERSICHERTE_PERSON},
            {**_F_BEITRAG},
            {"name": "versicherungssumme", "label": "Versicherungssumme", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_CURRENCY},
            {**_F_VERTRAGSBEGINN},
            {**_F_VERTRAGSENDE},
            {**_F_TARIFNAME},
        ],
    },
    "schulunfaehigkeit": {
        "label": "Schulunfaehigkeitsversicherung",
        "icon": "graduation-cap",
        "category": "absicherung",
        "fields": [
            {**_F_GESELLSCHAFT},
            {**_F_VERSICHERTE_PERSON},
            {**_F_BEITRAG},
            {**_F_RENTENHOEHE},
            {**_F_VERTRAGSBEGINN},
            {**_F_VERTRAGSENDE},
            {**_F_TARIFNAME},
        ],
    },
    "existenzschutz": {
        "label": "Existenzschutzversicherung",
        "icon": "shield",
        "category": "absicherung",
        "fields": [
            {**_F_GESELLSCHAFT},
            {**_F_VERSICHERTE_PERSON},
            {**_F_BEITRAG},
            {**_F_RENTENHOEHE},
            {**_F_VERTRAGSBEGINN},
            {**_F_VERTRAGSENDE},
            {**_F_TARIFNAME},
        ],
    },
    "erwerbsunfaehigkeit": {
        "label": "Erwerbsunfaehigkeitsversicherung",
        "icon": "shield-alert",
        "category": "absicherung",
        "fields": [
            {**_F_GESELLSCHAFT},
            {**_F_VERSICHERTE_PERSON},
            {**_F_BEITRAG},
            {**_F_RENTENHOEHE},
            {**_F_VERTRAGSBEGINN},
            {**_F_VERTRAGSENDE},
            {**_F_TARIFNAME},
        ],
    },
    "rlv": {
        "label": "Risikolebensversicherung (RLV)",
        "icon": "heart-pulse",
        "category": "absicherung",
        "fields": [
            {**_F_GESELLSCHAFT},
            {**_F_VERSICHERTE_PERSON},
            {**_F_BEITRAG},
            {"name": "versicherungssumme", "label": "Versicherungssumme (Todesfallleistung)", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_CURRENCY},
            {**_F_VERTRAGSBEGINN},
            {**_F_VERTRAGSENDE},
            {"name": "beguenstigter", "label": "Beguenstigte Person", "priority": PRIORITY_SOLL, "type": FIELD_TYPE_TEXT},
            {**_F_TARIFNAME},
        ],
    },
    "sterbegeld": {
        "label": "Sterbegeldversicherung",
        "icon": "flower-2",
        "category": "absicherung",
        "fields": [
            {**_F_GESELLSCHAFT},
            {**_F_VERSICHERTE_PERSON},
            {**_F_BEITRAG},
            {"name": "versicherungssumme", "label": "Sterbegeld-Summe", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_CURRENCY},
            {**_F_TARIFNAME},
        ],
    },
    "unfallversicherung": {
        "label": "Unfallversicherung",
        "icon": "alert-triangle",
        "category": "absicherung",
        "fields": [
            {**_F_GESELLSCHAFT},
            {**_F_VERSICHERTE_PERSON},
            {**_F_BEITRAG},
            {"name": "grundsumme", "label": "Grundsumme", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_CURRENCY},
            {"name": "progression", "label": "Progression (%)", "priority": PRIORITY_SOLL, "type": FIELD_TYPE_PERCENT},
            {"name": "invaliditaet", "label": "Invaliditaetssumme", "priority": PRIORITY_SOLL, "type": FIELD_TYPE_CURRENCY},
            {"name": "unfallrente", "label": "Unfallrente", "priority": PRIORITY_KANN, "type": FIELD_TYPE_CURRENCY},
            {**_F_TARIFNAME},
        ],
    },

    # ===== GESUNDHEIT & ZUSATZ =====
    "zzv": {
        "label": "Zahnzusatzversicherung (ZZV)",
        "icon": "smile",
        "category": "gesundheit",
        "fields": [
            {**_F_GESELLSCHAFT},
            {**_F_BEITRAG},
            {"name": "erstattung_zahnersatz", "label": "Erstattung Zahnersatz (%)", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_PERCENT},
            {"name": "erstattung_prophylaxe", "label": "Erstattung Prophylaxe", "priority": PRIORITY_SOLL, "type": FIELD_TYPE_TEXT},
            {**_F_TARIFNAME},
        ],
    },
    "ktg": {
        "label": "Krankentagegeld (KTG)",
        "icon": "bed",
        "category": "gesundheit",
        "fields": [
            {**_F_GESELLSCHAFT},
            {**_F_BEITRAG},
            {"name": "tagessatz", "label": "Tagessatz", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_CURRENCY},
            {"name": "karenzzeit", "label": "Karenzzeit (Tage)", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_NUMBER},
            {**_F_TARIFNAME},
        ],
    },
    "akz": {
        "label": "Ambulante Krankenzusatzversicherung (AKZ)",
        "icon": "stethoscope",
        "category": "gesundheit",
        "fields": [
            {**_F_GESELLSCHAFT},
            {**_F_BEITRAG},
            {"name": "leistungsumfang", "label": "Leistungsumfang", "priority": PRIORITY_SOLL, "type": FIELD_TYPE_TEXT},
            {**_F_TARIFNAME},
        ],
    },
    "skz": {
        "label": "Stationaere Krankenzusatzversicherung (SKZ)",
        "icon": "hospital",
        "category": "gesundheit",
        "fields": [
            {**_F_GESELLSCHAFT},
            {**_F_BEITRAG},
            {"name": "zimmer", "label": "Zimmerkategorie (1-/2-Bett)", "priority": PRIORITY_SOLL, "type": FIELD_TYPE_TEXT},
            {"name": "chefarzt", "label": "Chefarztbehandlung", "priority": PRIORITY_SOLL, "type": FIELD_TYPE_BOOLEAN},
            {**_F_TARIFNAME},
        ],
    },
    "ptg": {
        "label": "Pflegetagegeld (PTG)",
        "icon": "hand-helping",
        "category": "gesundheit",
        "fields": [
            {**_F_GESELLSCHAFT},
            {**_F_BEITRAG},
            {"name": "tagessatz_pflegegrad5", "label": "Tagessatz (Pflegegrad 5)", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_CURRENCY},
            {"name": "abstufung", "label": "Abstufung Pflegegrade", "priority": PRIORITY_SOLL, "type": FIELD_TYPE_TEXT},
            {**_F_TARIFNAME},
        ],
    },
    "arkv": {
        "label": "Auslandsreisekrankenversicherung (ARKV)",
        "icon": "plane",
        "category": "gesundheit",
        "fields": [
            {**_F_GESELLSCHAFT},
            {**_F_BEITRAG},
            {"name": "geltungsbereich", "label": "Geltungsbereich", "priority": PRIORITY_SOLL, "type": FIELD_TYPE_TEXT},
            {**_F_TARIFNAME},
        ],
    },

    # ===== SONSTIGES =====
    "gewerbeversicherung": {
        "label": "Gewerbeversicherung",
        "icon": "briefcase",
        "category": "sonstiges",
        "fields": [
            {**_F_GESELLSCHAFT},
            {**_F_BEITRAG},
            {"name": "sparte", "label": "Sparte / Art", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_TEXT},
            {**_F_VERSICHERUNGSSUMME},
            {**_F_TARIFNAME},
        ],
    },
    "reisehaftpflicht": {
        "label": "Reisehaftpflichtversicherung",
        "icon": "luggage",
        "category": "sonstiges",
        "fields": [
            {**_F_GESELLSCHAFT},
            {**_F_BEITRAG},
            {**_F_VERSICHERUNGSSUMME},
            {**_F_TARIFNAME},
        ],
    },
    "reisegepaeck": {
        "label": "Reisegepaeckversicherung",
        "icon": "luggage",
        "category": "sonstiges",
        "fields": [
            {**_F_GESELLSCHAFT},
            {**_F_BEITRAG},
            {**_F_VERSICHERUNGSSUMME},
            {**_F_TARIFNAME},
        ],
    },
    "tierkrankenversicherung": {
        "label": "Tierkrankenversicherung",
        "icon": "paw-print",
        "category": "sonstiges",
        "fields": [
            {**_F_GESELLSCHAFT},
            {**_F_BEITRAG},
            {"name": "tierart", "label": "Tierart", "priority": PRIORITY_MUSS, "type": FIELD_TYPE_TEXT},
            {"name": "erstattung", "label": "Erstattungssatz (%)", "priority": PRIORITY_SOLL, "type": FIELD_TYPE_PERCENT},
            {**_F_TARIFNAME},
        ],
    },
}


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def get_contract_type(type_key: str) -> dict | None:
    """Get a contract type definition by key."""
    return CONTRACT_TYPES.get(type_key)


def get_fields_for_type(type_key: str) -> list[dict]:
    """Get the field definitions for a contract type."""
    ct = CONTRACT_TYPES.get(type_key)
    return ct["fields"] if ct else []


def get_muss_fields(type_key: str) -> list[dict]:
    """Get only MUSS (required) fields for a contract type."""
    return [f for f in get_fields_for_type(type_key) if f["priority"] == PRIORITY_MUSS]


def get_category_for_type(type_key: str) -> str | None:
    """Get the category key for a contract type."""
    ct = CONTRACT_TYPES.get(type_key)
    return ct["category"] if ct else None


def get_all_type_keys() -> list[str]:
    """Get all contract type keys."""
    return list(CONTRACT_TYPES.keys())


def get_types_by_category(category_key: str) -> list[str]:
    """Get all contract type keys belonging to a category."""
    cat = CHECKLIST_CATEGORIES.get(category_key)
    return cat["types"] if cat else []


def compute_completeness(type_key: str, extracted_fields: dict) -> dict:
    """
    Compute completeness statistics for a contract type given extracted data.

    Args:
        type_key: Contract type key
        extracted_fields: dict mapping field_name → {value, confidence, ...}

    Returns:
        Dict with muss_total, muss_filled, soll_total, soll_filled,
        kann_total, kann_filled, percent_muss, percent_total
    """
    fields = get_fields_for_type(type_key)
    stats = {
        "muss_total": 0, "muss_filled": 0,
        "soll_total": 0, "soll_filled": 0,
        "kann_total": 0, "kann_filled": 0,
    }

    for field in fields:
        prio = field["priority"]
        stats[f"{prio}_total"] += 1
        if field["name"] in extracted_fields and extracted_fields[field["name"]].get("value"):
            stats[f"{prio}_filled"] += 1

    total = stats["muss_total"] + stats["soll_total"] + stats["kann_total"]
    filled = stats["muss_filled"] + stats["soll_filled"] + stats["kann_filled"]

    stats["percent_muss"] = (
        round(stats["muss_filled"] / stats["muss_total"] * 100)
        if stats["muss_total"] > 0 else 100
    )
    stats["percent_total"] = (
        round(filled / total * 100) if total > 0 else 100
    )

    return stats


def get_field_status(field_def: dict, extracted_data: dict | None) -> str:
    """
    Determine the Ampel-Status for a single field.

    Returns: 'green', 'yellow', 'red', or 'gray'
    """
    if extracted_data is None or not extracted_data.get("value"):
        if field_def["priority"] == PRIORITY_MUSS:
            return "red"
        elif field_def["priority"] == PRIORITY_SOLL:
            return "yellow"
        else:
            return "gray"

    confidence = extracted_data.get("confidence", 0)
    if confidence >= 0.8:
        return "green"
    else:
        return "yellow"


# Classification keywords for mock mode
CLASSIFICATION_KEYWORDS = {
    "privathaftpflicht": ["haftpflicht", "privathaftpflicht", "phv"],
    "hausrat": ["hausrat", "hausratversicherung"],
    "glasbruch": ["glasbruch", "glasversicherung"],
    "wohngebaeude": ["wohngebaeude", "gebaeudeversicherung", "gebaeude"],
    "rechtsschutz": ["rechtsschutz", "rechtsschutzversicherung"],
    "hausbesitzerhaftpflicht": ["haus- und grundbesitzer", "hausbesitzerhaftpflicht"],
    "tierhalterhaftpflicht": ["tierhalterhaftpflicht", "hundehaftpflicht", "pferdehaftpflicht"],
    "kfz_auto": ["kfz", "kraftfahrzeug", "kfz-versicherung", "sf-klasse", "hsn", "tsn", "fahrzeugschein"],
    "kfz_motorrad": ["motorrad", "motorradversicherung", "zweirad"],
    "kfz_anhaenger": ["anhaenger", "anhaengerversicherung"],
    "riester": ["riester", "riester-rente", "zulagenrente"],
    "basisrente": ["basisrente", "ruerup", "ruerup-rente"],
    "fondsgebundene_rv": ["fondsgebunden", "fondsrente", "fondsgebundene rentenversicherung", "fonds-police"],
    "index_rv": ["indexrente", "index-police", "indexgebunden"],
    "kapitallebensversicherung": ["kapitallebensversicherung", "kapital-lebensversicherung", "lebensversicherung"],
    "bav": ["betriebliche altersvorsorge", "bav", "direktversicherung", "pensionskasse", "pensionsfonds"],
    "bausparvertrag": ["bauspar", "bausparvertrag", "bausparkasse"],
    "sparkonto": ["sparkonto", "tagesgeld", "festgeld", "sparbuch"],
    "depotanlagen": ["depot", "fonds", "etf", "wertpapier", "aktien"],
    "wohn_riester_bsv": ["wohn-riester", "wohnriester"],
    "wohn_riester_depot": ["wohn-riester-depot", "riester-depot", "wohn-riester depot"],
    "bu": ["berufsunfaehigkeit", "bu-versicherung", "bu-rente", "berufsunfaehigkeitsversicherung"],
    "grundfaehigkeiten": ["grundfaehigkeit", "grundfaehigkeitsversicherung"],
    "dread_disease": ["dread disease", "schwere krankheiten", "critical illness"],
    "schulunfaehigkeit": ["schulunfaehigkeit", "schulunfaehigkeitsversicherung"],
    "existenzschutz": ["existenzschutz", "existenzschutzversicherung"],
    "erwerbsunfaehigkeit": ["erwerbsunfaehigkeit", "erwerbsminderung", "eu-rente"],
    "rlv": ["risikoleben", "risikolebensversicherung", "rlv", "todesfallschutz"],
    "sterbegeld": ["sterbegeld", "sterbegeldversicherung", "bestattungsvorsorge"],
    "unfallversicherung": ["unfall", "unfallversicherung", "invaliditaet", "progression"],
    "zzv": ["zahnzusatz", "zahnversicherung", "zzv", "zahnersatz"],
    "ktg": ["krankentagegeld", "ktg", "tagegeld"],
    "akz": ["ambulant", "ambulante zusatz", "akz"],
    "skz": ["stationaer", "stationaere zusatz", "skz", "krankenhauszusatz"],
    "ptg": ["pflege", "pflegetagegeld", "pflegeversicherung", "pflegezusatz"],
    "arkv": ["auslandsreisekranken", "reisekranken", "arkv", "auslandskranken"],
    "gewerbeversicherung": ["gewerbe", "gewerbeversicherung", "betriebshaftpflicht"],
    "reisehaftpflicht": ["reisehaftpflicht"],
    "reisegepaeck": ["reisegepaeck", "gepaeckversicherung"],
    "tierkrankenversicherung": ["tierkranken", "tier-op", "tierkrankenversicherung"],
}
