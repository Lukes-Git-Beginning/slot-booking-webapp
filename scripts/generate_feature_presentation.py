# -*- coding: utf-8 -*-
"""
PDF-Präsentation: Feature-Analyse für Business Tool Hub
Generiert professionelle PDF für Management-Präsentation
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from datetime import datetime
import os


class NumberedCanvas(canvas.Canvas):
    """Canvas mit Seitenzahlen und Footer"""

    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        """Seitenzahl und Footer zeichnen"""
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.grey)

        # Seitenzahl
        page_num = f"Seite {self._pageNumber} von {page_count}"
        self.drawRightString(A4[0] - 2*cm, 1.5*cm, page_num)

        # Footer-Linie
        self.setStrokeColor(colors.HexColor("#5ab1ff"))
        self.setLineWidth(0.5)
        self.line(2*cm, 2*cm, A4[0] - 2*cm, 2*cm)

        # Footer-Text
        self.setFont("Helvetica", 8)
        footer_text = "Business Tool Hub - Vertraulich"
        self.drawString(2*cm, 1.5*cm, footer_text)


def create_presentation():
    """Hauptfunktion zum Erstellen der PDF-Präsentation"""

    # Output-Pfad
    output_path = "feature_analyse_presentation.pdf"

    # PDF-Dokument erstellen
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2.5*cm,
        bottomMargin=2.5*cm
    )

    # Container für alle Elemente
    story = []

    # Styles definieren
    styles = getSampleStyleSheet()

    # Custom Styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=colors.HexColor("#0b0f14"),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor("#5ab1ff"),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica'
    )

    heading1_style = ParagraphStyle(
        'CustomHeading1',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor("#0b0f14"),
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold',
        borderPadding=5,
        leftIndent=0
    )

    heading2_style = ParagraphStyle(
        'CustomHeading2',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor("#5ab1ff"),
        spaceAfter=8,
        spaceBefore=10,
        fontName='Helvetica-Bold'
    )

    heading3_style = ParagraphStyle(
        'CustomHeading3',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=colors.HexColor("#0b0f14"),
        spaceAfter=6,
        spaceBefore=8,
        fontName='Helvetica-Bold'
    )

    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=10,
        textColor=colors.HexColor("#0b0f14"),
        spaceAfter=8,
        alignment=TA_JUSTIFY,
        fontName='Helvetica',
        leading=14
    )

    bullet_style = ParagraphStyle(
        'CustomBullet',
        parent=styles['BodyText'],
        fontSize=10,
        textColor=colors.HexColor("#0b0f14"),
        spaceAfter=4,
        leftIndent=20,
        fontName='Helvetica',
        leading=14
    )

    # ===========================================
    # SEITE 1: DECKBLATT
    # ===========================================

    story.append(Spacer(1, 4*cm))

    story.append(Paragraph("Feature-Analyse & Machbarkeitsstudie", title_style))
    story.append(Spacer(1, 1*cm))

    story.append(Paragraph(
        "KI-Dokumentenanalyse, DSGVO-Kalender &<br/>Self-Booking-Portal mit Hubspot-Integration",
        subtitle_style
    ))

    story.append(Spacer(1, 3*cm))

    # Info-Box
    cover_data = [
        ['Projekt:', 'Business Tool Hub - Feature-Erweiterungen'],
        ['Erstellt am:', datetime.now().strftime('%d.%m.%Y')],
        ['Version:', '1.0'],
        ['Status:', 'Vertraulich - Nur für interne Verwendung']
    ]

    cover_table = Table(cover_data, colWidths=[4*cm, 10*cm])
    cover_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#f0f4f8")),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor("#0b0f14")),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#5ab1ff")),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))

    story.append(cover_table)
    story.append(PageBreak())

    # ===========================================
    # SEITE 2: EXECUTIVE SUMMARY
    # ===========================================

    story.append(Paragraph("Executive Summary", heading1_style))
    story.append(Spacer(1, 0.5*cm))

    story.append(Paragraph(
        "Diese Analyse bewertet drei strategische Feature-Erweiterungen für den Business Tool Hub. "
        "Die Bewertung erfolgt nach Machbarkeit, Zeitaufwand, Kosten und Business-Impact.",
        body_style
    ))

    story.append(Spacer(1, 0.5*cm))

    # Übersichtstabelle
    summary_data = [
        ['Feature', 'Komplexität', 'Zeitaufwand', 'Priorität', 'ROI'],
        ['Self-Booking-Portal\n+ Hubspot', 'Mittel', '3-4 Wochen', 'Hoch ⭐⭐⭐', 'Sehr hoch'],
        ['KI-Dokumentenanalyse', 'Mittel-Hoch', '4-6 Wochen', 'Mittel ⭐⭐', 'Mittel'],
        ['DSGVO-Kalender\n(Eigenbau)', 'Hoch', '8-10 Wochen', 'Niedrig ⭐', 'Niedrig'],
        ['DSGVO-Kalender\n(Nextcloud)', 'Mittel', '2-3 Wochen', 'Mittel ⭐⭐', 'Mittel'],
    ]

    summary_table = Table(summary_data, colWidths=[5*cm, 3*cm, 3*cm, 3*cm, 3*cm])
    summary_table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#5ab1ff")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),

        # Body
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor("#0b0f14")),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),

        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),

        # Alternating rows
        ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor("#f0f4f8")),
        ('BACKGROUND', (0, 4), (-1, 4), colors.HexColor("#f0f4f8")),
    ]))

    story.append(summary_table)
    story.append(Spacer(1, 0.7*cm))

    # Empfehlungen
    story.append(Paragraph("📌 Strategische Empfehlungen", heading2_style))
    story.append(Spacer(1, 0.3*cm))

    recommendations = [
        "<b>1. Sofortiger Start:</b> Self-Booking-Portal + Hubspot-Integration (höchster Business-Impact, kurze Time-to-Market)",
        "<b>2. Nach 4-6 Wochen:</b> KI-Dokumentenanalyse mit OpenAI API (MVP-Ansatz, später optional Self-Hosted)",
        "<b>3. DSGVO-Kalender:</b> Nextcloud Calendar statt Eigenentwicklung (90% weniger Aufwand, gleicher Nutzen)",
        "<b>4. Quick-Win:</b> Kundennamen aus Google Calendar entfernen (Pseudonymisierung, 1 Tag Aufwand)"
    ]

    for rec in recommendations:
        story.append(Paragraph(f"• {rec}", bullet_style))
        story.append(Spacer(1, 0.2*cm))

    story.append(PageBreak())

    # ===========================================
    # SEITE 3-4: FEATURE #1 - KI-DOKUMENTENANALYSE
    # ===========================================

    story.append(Paragraph("Feature #1: KI-gestützte Dokumentenanalyse", heading1_style))
    story.append(Spacer(1, 0.5*cm))

    story.append(Paragraph("Anforderungen & Zielsetzung", heading2_style))
    story.append(Paragraph(
        "Automatisierte Analyse von Dokumenten (PDF, Word, Text) für das Ausarbeitungsteam "
        "zur Effizienzsteigerung und Qualitätssicherung. KI-gestützte Extraktion von "
        "Kernaussagen, Zusammenfassungen und relevanten Informationen.",
        body_style
    ))
    story.append(Spacer(1, 0.3*cm))

    # Use Cases
    story.append(Paragraph("Typische Anwendungsfälle:", heading3_style))
    use_cases_ki = [
        "Automatische Zusammenfassung von Verträgen und Vereinbarungen",
        "Extraktion von Schlüsselinformationen aus Kundendokumenten",
        "Semantische Suche über Dokumenten-Archiv",
        "Konsistenz-Checks und Qualitätssicherung",
        "Automatische Kategorisierung und Tagging"
    ]

    for uc in use_cases_ki:
        story.append(Paragraph(f"• {uc}", bullet_style))

    story.append(Spacer(1, 0.5*cm))

    # Technische Architektur
    story.append(Paragraph("Technische Umsetzung", heading2_style))

    tech_data_ki = [
        ['Komponente', 'Technologie', 'Aufwand'],
        ['Document Upload', 'Flask Blueprint + Storage', '2-3 Tage'],
        ['PDF/Word-Extraktion', 'PyPDF2, python-docx', '2-3 Tage'],
        ['KI-Integration', 'OpenAI GPT-4 API', '3-4 Tage'],
        ['Vector Database', 'ChromaDB (lokal)', '2-3 Tage'],
        ['Analysis UI', 'Frontend + Chat-Interface', '4-5 Tage'],
        ['Testing & DSGVO', 'Compliance-Prüfung', '3-4 Tage'],
    ]

    tech_table_ki = Table(tech_data_ki, colWidths=[5*cm, 6*cm, 3.5*cm])
    tech_table_ki.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#5ab1ff")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (2, 1), (2, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
    ]))

    story.append(tech_table_ki)
    story.append(Spacer(1, 0.5*cm))

    # DSGVO-Compliance
    story.append(Paragraph("⚠️ DSGVO-Compliance (KRITISCH!)", heading2_style))
    story.append(Paragraph(
        "<b>Problem:</b> Dokumente können personenbezogene Daten enthalten. OpenAI API "
        "überträgt Daten in die USA → DSGVO-Risiko!",
        body_style
    ))
    story.append(Spacer(1, 0.2*cm))

    dsgvo_options = [
        "<b>Option 1:</b> Nur anonymisierte/pseudonymisierte Dokumente verarbeiten",
        "<b>Option 2:</b> Self-Hosted KI-Modell (Llama 3, Mistral) → GPU-Server erforderlich (~€150-300/Monat)",
        "<b>Option 3:</b> EU-basierte KI-Provider (z.B. Aleph Alpha) → höhere Kosten",
        "<b>Empfehlung:</b> Start mit Option 1 (MVP), später auf Option 2 upgraden"
    ]

    for opt in dsgvo_options:
        story.append(Paragraph(f"• {opt}", bullet_style))

    story.append(Spacer(1, 0.5*cm))

    # Kosten
    story.append(Paragraph("Kosten-Übersicht", heading2_style))

    costs_data_ki = [
        ['Position', 'Kosten', 'Notizen'],
        ['Entwicklung (MVP)', '€0', 'Inhouse (2-3 Wochen)'],
        ['OpenAI API (monatlich)', '€50-200', 'Abhängig von Nutzung'],
        ['GPU-Server (optional)', '€150-300/Monat', 'Für Self-Hosted-Modell'],
        ['Storage (Dokumente)', '€10-20/Monat', 'Cloud-Storage'],
    ]

    costs_table_ki = Table(costs_data_ki, colWidths=[5*cm, 3.5*cm, 6*cm])
    costs_table_ki.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#5ab1ff")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    story.append(costs_table_ki)
    story.append(Spacer(1, 0.5*cm))

    # Zeitplan
    story.append(Paragraph("Zeitplan & Meilensteine", heading2_style))

    timeline_data_ki = [
        ['Phase', 'Dauer', 'Deliverables'],
        ['MVP - Basic Upload & Analysis', '2-3 Wochen', 'Upload, PDF-Extraktion, OpenAI-Integration, Basic UI'],
        ['Production - Advanced Features', '+2-3 Wochen', 'Vector Database, Semantic Search, Queue-System'],
        ['DSGVO-Compliance', '+1 Woche', 'Anonymisierung, Privacy-Checks, Dokumentation'],
    ]

    timeline_table_ki = Table(timeline_data_ki, colWidths=[5.5*cm, 3*cm, 6*cm])
    timeline_table_ki.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#5ab1ff")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    story.append(timeline_table_ki)
    story.append(Spacer(1, 0.5*cm))

    # Risiken
    story.append(Paragraph("Risiken & Gegenmaßnahmen", heading2_style))

    risks_ki = [
        "<b>API-Kosten explodieren:</b> Rate-Limiting, Kosten-Monitoring, Budget-Alerts",
        "<b>DSGVO-Verstoß:</b> Nur anonymisierte Daten, Self-Hosted-Option prüfen",
        "<b>Qualität der KI-Outputs:</b> Prompt-Engineering, Human-in-the-Loop-Workflow",
        "<b>Performance bei großen Dokumenten:</b> Queue-System (Celery), Chunk-Processing"
    ]

    for risk in risks_ki:
        story.append(Paragraph(f"• {risk}", bullet_style))

    story.append(Spacer(1, 0.5*cm))

    # Bewertung
    story.append(Paragraph("✅ Gesamtbewertung", heading2_style))

    rating_data_ki = [
        ['Kriterium', 'Bewertung', 'Begründung'],
        ['Machbarkeit', '⭐⭐⭐⭐ (Gut)', 'Technisch unkompliziert mit OpenAI'],
        ['Business-Impact', '⭐⭐⭐ (Mittel)', 'Effizienzgewinn für Ausarbeitungsteam'],
        ['Zeitaufwand', '⭐⭐⭐ (Mittel)', '4-6 Wochen bis Production-Ready'],
        ['DSGVO-Risiko', '⭐⭐ (Hoch)', 'Erfordert sorgfältige Datenhandhabung'],
        ['ROI', '⭐⭐⭐ (Mittel)', 'Abhängig von Nutzungsintensität'],
    ]

    rating_table_ki = Table(rating_data_ki, colWidths=[4*cm, 4*cm, 6.5*cm])
    rating_table_ki.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#5ab1ff")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    story.append(rating_table_ki)

    story.append(PageBreak())

    # ===========================================
    # SEITE 5-6: FEATURE #2 - DSGVO-KALENDER
    # ===========================================

    story.append(Paragraph("Feature #2: DSGVO-konformer Kalender", heading1_style))
    story.append(Spacer(1, 0.5*cm))

    story.append(Paragraph("Problem-Statement", heading2_style))
    story.append(Paragraph(
        "Google Calendar speichert Kundendaten (Namen in Event-Titeln) auf US-Servern. "
        "Dies ist potenziell DSGVO-kritisch und könnte zu rechtlichen Risiken führen. "
        "Ziel ist eine DSGVO-konforme Alternative mit voller Datenkontrolle.",
        body_style
    ))
    story.append(Spacer(1, 0.5*cm))

    # Lösungsoptionen-Vergleich
    story.append(Paragraph("Lösungsoptionen im Vergleich", heading2_style))

    calendar_options = [
        ['Option', 'Zeitaufwand', 'Komplexität', 'Features', 'Empfehlung'],
        [
            'Eigenentwicklung',
            '8-10 Wochen',
            'Sehr hoch',
            '60% von Google',
            '❌ Nicht empfohlen'
        ],
        [
            'Nextcloud Calendar',
            '2-3 Wochen',
            'Mittel',
            '90% von Google',
            '✅ Empfohlen'
        ],
        [
            'CalDAV-Server\n(Radicale)',
            '1-2 Wochen',
            'Niedrig',
            '70% von Google',
            '⚠️ Für Basis-Anforderungen'
        ],
        [
            'Quick-Fix:\nPseudonymisierung',
            '1 Tag',
            'Sehr niedrig',
            '100% (bestehendes System)',
            '✅ Sofort-Maßnahme'
        ],
    ]

    calendar_table = Table(calendar_options, colWidths=[3.5*cm, 2.5*cm, 2.5*cm, 3.5*cm, 3*cm])
    calendar_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#5ab1ff")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (1, 1), (2, -1), 'CENTER'),
        ('ALIGN', (4, 1), (4, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        # Highlight empfohlene Optionen
        ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor("#e8f5e9")),
        ('BACKGROUND', (0, 4), (-1, 4), colors.HexColor("#fff3e0")),
    ]))

    story.append(calendar_table)
    story.append(Spacer(1, 0.5*cm))

    # Detaillierte Bewertung: Eigenentwicklung
    story.append(Paragraph("❌ Option 1: Eigenentwicklung (Nicht empfohlen)", heading3_style))

    eigen_points = [
        "<b>Vorteile:</b> Volle Kontrolle, maßgeschneiderte Features",
        "<b>Nachteile:</b> Sehr hoher Entwicklungsaufwand (8-10 Wochen), fehleranfällig",
        "<b>Risiken:</b> Recurring Events schwer zu implementieren, hoher Wartungsaufwand",
        "<b>Fazit:</b> Kosten-Nutzen-Verhältnis schlecht, 90% der Arbeit ist bereits in Nextcloud gelöst"
    ]

    for point in eigen_points:
        story.append(Paragraph(f"• {point}", bullet_style))

    story.append(Spacer(1, 0.4*cm))

    # Detaillierte Bewertung: Nextcloud
    story.append(Paragraph("✅ Option 2: Nextcloud Calendar (EMPFOHLEN)", heading3_style))

    nextcloud_points = [
        "<b>Vorteile:</b> Open-Source, DSGVO-konform, Feature-Reich, aktive Community",
        "<b>Features:</b> Recurring Events, CalDAV/CardDAV, Mobile Apps, Sharing, Notifications",
        "<b>Integration:</b> REST API für Business Tool Hub, bestehende Python-Clients",
        "<b>Zeitaufwand:</b> 2-3 Wochen (Setup, Integration, Migration)",
        "<b>Kosten:</b> €0 (Self-Hosted auf Hetzner-Server)",
        "<b>Fazit:</b> Beste Lösung - 90% weniger Aufwand als Eigenentwicklung bei gleichem Nutzen"
    ]

    for point in nextcloud_points:
        story.append(Paragraph(f"• {point}", bullet_style))

    story.append(Spacer(1, 0.4*cm))

    # Quick-Fix
    story.append(Paragraph("⚡ Option 3: Quick-Fix - Pseudonymisierung (Sofort-Maßnahme)", heading3_style))

    quickfix_points = [
        "<b>Umsetzung:</b> Kundennamen aus Calendar-Titeln entfernen, stattdessen IDs verwenden",
        "<b>Beispiel:</b> Statt 'Max Mustermann - T1' → 'Kunde #12345 - T1'",
        "<b>Vorteile:</b> Sofort umsetzbar (1 Tag), kein System-Wechsel",
        "<b>Nachteile:</b> Weniger benutzerfreundlich, Google bleibt Third-Party",
        "<b>Fazit:</b> Als Übergangs-Lösung bis Nextcloud implementiert ist"
    ]

    for point in quickfix_points:
        story.append(Paragraph(f"• {point}", bullet_style))

    story.append(Spacer(1, 0.5*cm))

    # Migrations-Strategie
    story.append(Paragraph("Migrations-Strategie (Nextcloud-Option)", heading2_style))

    migration_phases = [
        ['Phase', 'Aktivität', 'Dauer'],
        ['1. Setup', 'Nextcloud auf Hetzner installieren & konfigurieren', '2-3 Tage'],
        ['2. Migration', '9 Berater-Kalender + Zentralkalender migrieren (CalDAV)', '3-4 Tage'],
        ['3. Integration', 'Business Tool Hub an Nextcloud anbinden (API)', '4-5 Tage'],
        ['4. Testing', 'Funktions-Tests, Berater-Schulung (9 Berater)', '2-3 Tage'],
        ['5. Go-Live', 'Cutover, Monitoring', '1 Tag'],
    ]

    migration_table = Table(migration_phases, colWidths=[2*cm, 9*cm, 3.5*cm])
    migration_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#5ab1ff")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (2, 1), (2, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    story.append(migration_table)
    story.append(Spacer(1, 0.5*cm))

    # Bewertung
    story.append(Paragraph("✅ Gesamtbewertung", heading2_style))

    rating_data_cal = [
        ['Kriterium', 'Eigenentwicklung', 'Nextcloud', 'Quick-Fix'],
        ['Zeitaufwand', '8-10 Wochen', '2-3 Wochen', '1 Tag'],
        ['Komplexität', '⭐⭐⭐⭐⭐ (Sehr hoch)', '⭐⭐⭐ (Mittel)', '⭐ (Sehr niedrig)'],
        ['DSGVO-Compliance', '✅ 100%', '✅ 100%', '⚠️ 80%'],
        ['Feature-Umfang', '60%', '90%', '100% (bestehendes)'],
        ['Empfehlung', '❌', '✅✅✅', '✅ (Übergang)'],
    ]

    rating_table_cal = Table(rating_data_cal, colWidths=[4*cm, 3.5*cm, 3.5*cm, 3.5*cm])
    rating_table_cal.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#5ab1ff")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        # Highlight Nextcloud
        ('BACKGROUND', (2, 1), (2, -1), colors.HexColor("#e8f5e9")),
    ]))

    story.append(rating_table_cal)

    story.append(PageBreak())

    # ===========================================
    # SEITE 7-8: FEATURE #3 - SELF-BOOKING-PORTAL
    # ===========================================

    story.append(Paragraph("Feature #3: Self-Booking-Portal + Hubspot", heading1_style))
    story.append(Spacer(1, 0.5*cm))

    story.append(Paragraph("Business Case", heading2_style))
    story.append(Paragraph(
        "Kunden können selbstständig Termine buchen ohne manuellen Koordinationsaufwand. "
        "Automatische Synchronisation mit Hubspot CRM für nahtlose Lead-Verwaltung. "
        "Reduziert administrativen Aufwand und verbessert Customer Experience.",
        body_style
    ))
    story.append(Spacer(1, 0.5*cm))

    # Kundennutzen
    story.append(Paragraph("💡 Kundennutzen", heading3_style))

    customer_benefits = [
        "<b>24/7 Verfügbarkeit:</b> Termine jederzeit buchen aus ~573 verfügbaren Slots, keine Wartezeit",
        "<b>Transparenz:</b> Echtzeit-Verfügbarkeit aller 9 Berater sichtbar",
        "<b>Sofort-Bestätigung:</b> Automatische Email mit Termin-Details + Calendar-Invite",
        "<b>Self-Service:</b> Unabhängig von Geschäftszeiten, mobil-optimiert"
    ]

    for benefit in customer_benefits:
        story.append(Paragraph(f"• {benefit}", bullet_style))

    story.append(Spacer(1, 0.3*cm))

    # Unternehmensnutzen
    story.append(Paragraph("📈 Unternehmensnutzen", heading3_style))

    business_benefits = [
        "<b>Effizienz:</b> 80% Reduktion von manuellen Terminabsprachen",
        "<b>Lead-Tracking:</b> Alle Buchungen automatisch in Hubspot Pipeline",
        "<b>Analytics:</b> Conversion-Tracking, Berater-Auslastung, Peak-Times",
        "<b>Skalierbarkeit:</b> Unbegrenzte Buchungen ohne zusätzlichen Aufwand"
    ]

    for benefit in business_benefits:
        story.append(Paragraph(f"• {benefit}", bullet_style))

    story.append(Spacer(1, 0.5*cm))

    # User Journey
    story.append(Paragraph("🔄 User Journey (Kunde bucht Termin)", heading2_style))

    journey_data = [
        ['#', 'Schritt', 'System-Aktion'],
        ['1', 'Kunde öffnet Booking-Page\n(öffentlich, kein Login)', 'Verfügbarkeiten laden aus Availability-JSON'],
        ['2', 'Kunde wählt Berater & Zeitslot', 'Echtzeit-Check: Slot noch verfügbar?'],
        ['3', 'Kunde füllt Kontakt-Formular aus\n(Name, Email, Telefon)', 'Validierung + reCAPTCHA'],
        ['4', 'Bestätigung & Submit', 'Google Calendar Event erstellen'],
        ['5', 'Hubspot-Integration', 'Contact anlegen/updaten + Deal erstellen'],
        ['6', 'Email-Benachrichtigung', 'Kunde + Berater erhalten Bestätigung'],
    ]

    journey_table = Table(journey_data, colWidths=[1*cm, 6*cm, 7.5*cm])
    journey_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#5ab1ff")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    story.append(journey_table)
    story.append(Spacer(1, 0.5*cm))

    # Technische Integration
    story.append(Paragraph("⚙️ Technische Integration", heading2_style))

    story.append(Paragraph(
        "<b>Vorteil:</b> 80% der erforderlichen Infrastruktur existiert bereits!",
        body_style
    ))
    story.append(Spacer(1, 0.2*cm))

    tech_integration = [
        "<b>✅ Bereits vorhanden:</b> Slot-Booking-System, Availability-Management, Google Calendar-Integration",
        "<b>✅ Bereits vorhanden:</b> Blueprint-Architektur für einfache Erweiterung",
        "<b>🔧 Neu zu entwickeln:</b> Public Booking-Page (kein Login), Hubspot API-Integration",
        "<b>🔧 Neu zu entwickeln:</b> Email-Notification-System (SendGrid/Mailgun)",
        "<b>🔧 Neu zu entwickeln:</b> Spam-Protection (reCAPTCHA v3, Rate-Limiting)"
    ]

    for item in tech_integration:
        story.append(Paragraph(f"• {item}", bullet_style))

    story.append(Spacer(1, 0.5*cm))

    # Hubspot-Integration Details
    story.append(Paragraph("🔗 Hubspot-Integration Details", heading2_style))

    hubspot_data = [
        ['Funktion', 'Hubspot API-Endpoint', 'Daten'],
        [
            'Contact anlegen/updaten',
            'POST /contacts/v1/contact',
            'Name, Email, Telefon, Source: "Self-Booking"'
        ],
        [
            'Deal erstellen',
            'POST /deals/v1/deal',
            'Pipeline: "Slot-Booking", Stage: "Booked", Amount'
        ],
        [
            'Activity loggen',
            'POST /engagements/v1/engagements',
            'Type: "Meeting", Termin-Details'
        ],
        [
            'Custom Properties',
            'Various',
            'Berater, Termin-Datum, Slot-Type'
        ],
    ]

    hubspot_table = Table(hubspot_data, colWidths=[4*cm, 5*cm, 5.5*cm])
    hubspot_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#5ab1ff")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    story.append(hubspot_table)
    story.append(Spacer(1, 0.5*cm))

    # Zeitplan & Meilensteine
    story.append(Paragraph("📅 Zeitplan & Meilensteine", heading2_style))

    timeline_selfbooking = [
        ['Woche', 'Meilenstein', 'Deliverables'],
        [
            '1',
            'Public Booking-Page',
            'Frontend (Berater-Auswahl, Slot-Kalender), Backend-Route, Validierung'
        ],
        [
            '2',
            'Hubspot-Integration',
            'API-Integration, Contact-Sync, Deal-Creation, Testing'
        ],
        [
            '3',
            'Notifications & Security',
            'Email-System (SendGrid), reCAPTCHA, Rate-Limiting, DSGVO-Compliance'
        ],
        [
            '4',
            'Testing & Launch',
            'User-Testing, Mobile-Optimierung, Monitoring, Go-Live'
        ],
    ]

    timeline_table_sb = Table(timeline_selfbooking, colWidths=[1.5*cm, 4*cm, 9*cm])
    timeline_table_sb.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#5ab1ff")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    story.append(timeline_table_sb)
    story.append(Spacer(1, 0.5*cm))

    # ROI-Projektion
    story.append(Paragraph("💰 ROI-Projektion", heading2_style))

    roi_data = [
        ['Metrik', 'Aktuell (manuell)', 'Mit Self-Booking', 'Einsparung'],
        ['Ø Zeit pro Buchung', '15 Min', '0 Min (automatisch)', '15 Min'],
        ['Buchungen/Monat', '~257', '~385 (+50%)', '+128 Buchungen'],
        ['Show-Rate (aktuell)', '36,3%', 'Unverändert (Reminders bereits aktiv)', '-'],
        ['Admin-Aufwand/Monat', '64 Stunden', '13 Stunden', '51 Stunden'],
        ['Kosten Admin-Zeit (@€40/h)', '€2.560', '€520', '€2.040/Monat'],
        ['ROI nach 3 Monaten', '-', '-', '€6.120'],
    ]

    roi_table = Table(roi_data, colWidths=[4*cm, 3.5*cm, 3.5*cm, 3.5*cm])
    roi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#5ab1ff")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        # Highlight ROI-Zeile
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#fff3e0")),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))

    story.append(roi_table)
    story.append(Spacer(1, 0.5*cm))

    # Bewertung
    story.append(Paragraph("✅ Gesamtbewertung", heading2_style))

    rating_data_sb = [
        ['Kriterium', 'Bewertung', 'Begründung'],
        ['Machbarkeit', '⭐⭐⭐⭐⭐ (Sehr gut)', 'Nutzt bestehende Infrastruktur optimal'],
        ['Business-Impact', '⭐⭐⭐⭐⭐ (Sehr hoch)', 'Klarer ROI, Kundennutzen, Effizienzgewinn'],
        ['Zeitaufwand', '⭐⭐⭐⭐ (Gut)', 'Nur 3-4 Wochen bis Production-Ready'],
        ['Komplexität', '⭐⭐⭐ (Mittel)', 'Standard-Technologien, gut dokumentiert'],
        ['ROI', '⭐⭐⭐⭐⭐ (Sehr hoch)', 'Amortisation in 1-2 Monaten'],
    ]

    rating_table_sb = Table(rating_data_sb, colWidths=[4*cm, 4*cm, 6.5*cm])
    rating_table_sb.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#5ab1ff")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    story.append(rating_table_sb)

    story.append(PageBreak())

    # ===========================================
    # SEITE 9: GESAMTBEWERTUNG & ROADMAP
    # ===========================================

    story.append(Paragraph("Gesamtbewertung & Empfohlene Roadmap", heading1_style))
    story.append(Spacer(1, 0.5*cm))

    # Vergleichstabelle
    story.append(Paragraph("Feature-Vergleich", heading2_style))

    comparison_data = [
        ['Feature', 'Komplexität', 'Zeitaufwand', 'Kosten/Monat', 'Business-Impact', 'Priorität'],
        [
            'Self-Booking + Hubspot',
            'Mittel',
            '3-4 Wochen',
            '~€50',
            '⭐⭐⭐⭐⭐',
            '1 (Hoch)'
        ],
        [
            'KI-Dokumentenanalyse',
            'Mittel-Hoch',
            '4-6 Wochen',
            '€100-300',
            '⭐⭐⭐',
            '2 (Mittel)'
        ],
        [
            'DSGVO-Kalender\n(Nextcloud)',
            'Mittel',
            '2-3 Wochen',
            '€0',
            '⭐⭐⭐',
            '3 (Mittel)'
        ],
        [
            'DSGVO-Quick-Fix',
            'Niedrig',
            '1 Tag',
            '€0',
            '⭐⭐',
            'Sofort'
        ],
    ]

    comparison_table = Table(comparison_data, colWidths=[4*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2*cm])
    comparison_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#5ab1ff")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        # Highlight Priorität 1
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor("#e8f5e9")),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
    ]))

    story.append(comparison_table)
    story.append(Spacer(1, 0.7*cm))

    # Empfohlene Roadmap
    story.append(Paragraph("📅 Empfohlene Umsetzungs-Roadmap", heading2_style))

    roadmap_data = [
        ['Phase', 'Zeitraum', 'Features', 'Ziel'],
        [
            'Sofort',
            'Tag 1',
            'DSGVO-Quick-Fix (Pseudonymisierung)',
            'Compliance-Risiko minimieren'
        ],
        [
            'Phase 1',
            'Wochen 1-4',
            'Self-Booking-Portal + Hubspot',
            'Schneller ROI, Kundennutzen'
        ],
        [
            'Phase 2',
            'Wochen 5-8',
            'KI-Dokumentenanalyse (MVP)',
            'Effizienzgewinn Ausarbeitungsteam'
        ],
        [
            'Phase 3',
            'Wochen 9-11',
            'Nextcloud Calendar Migration',
            'Vollständige DSGVO-Compliance'
        ],
        [
            'Phase 4',
            'Wochen 12-17',
            'KI-Docs Production + Self-Hosted',
            'Optimierung, Kostenreduktion'
        ],
    ]

    roadmap_table = Table(roadmap_data, colWidths=[2*cm, 2.5*cm, 5.5*cm, 4.5*cm])
    roadmap_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#5ab1ff")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    story.append(roadmap_table)
    story.append(Spacer(1, 0.7*cm))

    # Ressourcen-Planung
    story.append(Paragraph("👥 Ressourcen-Planung", heading2_style))

    resources_data = [
        ['Rolle', 'Phase 1', 'Phase 2', 'Phase 3', 'Phase 4'],
        ['Backend-Entwickler', '80%', '60%', '40%', '60%'],
        ['Frontend-Entwickler', '60%', '40%', '20%', '40%'],
        ['DevOps/Infrastruktur', '20%', '10%', '60%', '20%'],
        ['QA/Testing', '20%', '30%', '20%', '30%'],
    ]

    resources_table = Table(resources_data, colWidths=[4*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm])
    resources_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#5ab1ff")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    story.append(resources_table)
    story.append(Spacer(1, 0.7*cm))

    # Gesamtkosten
    story.append(Paragraph("💰 Gesamtkosten-Übersicht", heading2_style))

    total_costs = [
        ['Position', 'Einmalig', 'Monatlich (laufend)'],
        ['Entwicklung (alle Features)', '€0 (Inhouse)', '-'],
        ['OpenAI API (KI-Docs)', '-', '€100-200'],
        ['SendGrid/Mailgun (Emails)', '-', '€0-35'],
        ['GPU-Server (optional, später)', '-', '€150-300'],
        ['Nextcloud Hosting', '€0 (Hetzner)', '€0'],
        ['Hubspot API', '€0', '€0 (bereits vorhanden)'],
        ['GESAMT (initial)', '€0', '€100-235'],
        ['GESAMT (mit Self-Hosted KI)', '€0', '€150-335'],
    ]

    costs_table_final = Table(total_costs, colWidths=[7*cm, 3.5*cm, 4*cm])
    costs_table_final.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#5ab1ff")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        # Highlight Gesamt
        ('BACKGROUND', (0, -2), (-1, -1), colors.HexColor("#fff3e0")),
        ('FONTNAME', (0, -2), (-1, -1), 'Helvetica-Bold'),
    ]))

    story.append(costs_table_final)
    story.append(Spacer(1, 0.7*cm))

    # Finale Empfehlung
    story.append(Paragraph("✅ Finale Empfehlung", heading2_style))

    final_recommendations = [
        "<b>Sofort starten:</b> Self-Booking-Portal + Hubspot (Woche 1-4) → Höchster ROI, schnellste Amortisation",
        "<b>Parallel-Entwicklung möglich:</b> DSGVO-Quick-Fix (Tag 1) während Self-Booking läuft",
        "<b>Nach 1 Monat:</b> KI-Dokumentenanalyse mit OpenAI-MVP (Woche 5-8) → Business-Value für Ausarbeitungsteam",
        "<b>Mittelfristig:</b> Nextcloud Calendar (Woche 9-11) → Vollständige DSGVO-Compliance",
        "<b>Optimierung:</b> Self-Hosted KI-Modell (Woche 12+) → Kostenreduktion langfristig",
        "<b>Gesamtdauer:</b> Alle Features in 17 Wochen (~4 Monate) Production-Ready"
    ]

    for rec in final_recommendations:
        story.append(Paragraph(f"• {rec}", bullet_style))

    story.append(Spacer(1, 0.5*cm))

    # Success Metrics
    story.append(Paragraph("📊 Erfolgs-Metriken (KPIs)", heading2_style))

    kpis = [
        "<b>Self-Booking:</b> Buchungen/Monat (+50% Ziel), Admin-Zeit-Reduktion (-80% Ziel)",
        "<b>KI-Docs:</b> Dokumente/Monat verarbeitet, Zeit pro Analyse (-60% Ziel)",
        "<b>DSGVO-Kalender:</b> Migration erfolgreich, 0 Compliance-Verstöße",
        "<b>Hubspot:</b> Conversion-Rate, Pipeline-Velocity, Lead-Quality"
    ]

    for kpi in kpis:
        story.append(Paragraph(f"• {kpi}", bullet_style))

    story.append(PageBreak())

    # ===========================================
    # SEITE 10: APPENDIX
    # ===========================================

    story.append(Paragraph("Appendix: Technische Details", heading1_style))
    story.append(Spacer(1, 0.5*cm))

    # API-Kosten Details
    story.append(Paragraph("API-Kosten-Übersicht", heading2_style))

    api_costs = [
        ['Service', 'Pricing-Modell', 'Geschätzte Kosten'],
        ['OpenAI GPT-4', '€0.01-0.03 / 1K Tokens', '€100-200/Monat (bei 100 Docs)'],
        ['Claude API', 'Ähnlich OpenAI', '€100-200/Monat'],
        ['SendGrid', 'Bis 100 Emails/Tag kostenlos', '€0 (unter Limit)'],
        ['Mailgun', '€0.80 / 1K Emails', '€35/Monat (bei 50K Emails)'],
        ['Hubspot API', 'Inkludiert in Professional+', '€0 (bereits vorhanden)'],
        ['reCAPTCHA', 'Kostenlos (Google)', '€0'],
    ]

    api_table = Table(api_costs, colWidths=[4*cm, 5*cm, 5.5*cm])
    api_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#5ab1ff")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    story.append(api_table)
    story.append(Spacer(1, 0.7*cm))

    # Technologie-Stack
    story.append(Paragraph("Technologie-Stack", heading2_style))

    tech_stack = [
        ['Komponente', 'Technologie', 'Status'],
        ['Backend Framework', 'Flask (Python)', '✅ Bereits vorhanden'],
        ['Frontend', 'Tailwind CSS + DaisyUI', '✅ Bereits vorhanden'],
        ['Datenbank', 'JSON-Files (später SQLite)', '✅ Bereits vorhanden'],
        ['Calendar API', 'Google Calendar API', '✅ Bereits vorhanden'],
        ['KI-Integration', 'OpenAI GPT-4 API', '🔧 Neu'],
        ['CRM-Integration', 'Hubspot REST API', '🔧 Neu'],
        ['Email-Service', 'SendGrid/Mailgun', '🔧 Neu'],
        ['Vector Database', 'ChromaDB', '🔧 Neu'],
        ['Spam-Protection', 'reCAPTCHA v3', '🔧 Neu'],
    ]

    stack_table = Table(tech_stack, colWidths=[4*cm, 5.5*cm, 5*cm])
    stack_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#5ab1ff")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    story.append(stack_table)
    story.append(Spacer(1, 0.7*cm))

    # Glossar
    story.append(Paragraph("Glossar", heading2_style))

    glossary_items = [
        "<b>MVP (Minimum Viable Product):</b> Minimal funktionsfähige Version mit Kern-Features",
        "<b>ROI (Return on Investment):</b> Rentabilität einer Investition",
        "<b>DSGVO:</b> Datenschutz-Grundverordnung (EU-weit)",
        "<b>CalDAV:</b> Standard-Protokoll für Kalender-Synchronisation",
        "<b>API:</b> Application Programming Interface (Schnittstelle)",
        "<b>Self-Hosted:</b> Auf eigenen Servern betrieben (keine Cloud)",
        "<b>Vector Database:</b> Datenbank für semantische Ähnlichkeits-Suche",
        "<b>reCAPTCHA:</b> Google-Service zur Spam-Prävention",
        "<b>Queue-System:</b> Asynchrone Verarbeitung von Tasks"
    ]

    for item in glossary_items:
        story.append(Paragraph(f"• {item}", bullet_style))

    story.append(Spacer(1, 1*cm))

    # Kontakt / Nächste Schritte
    story.append(Paragraph("Nächste Schritte", heading2_style))

    next_steps = [
        "1. <b>Entscheidung:</b> Freigabe für Self-Booking-Portal (Phase 1)",
        "2. <b>Kick-Off:</b> Projekt-Planning, Ressourcen-Zuweisung",
        "3. <b>Development Start:</b> Sprint 1 - Public Booking-Page",
        "4. <b>Hubspot-Setup:</b> API-Keys, Pipeline-Konfiguration",
        "5. <b>Testing:</b> User-Acceptance-Tests nach 3 Wochen",
        "6. <b>Go-Live:</b> Production-Deployment nach 4 Wochen"
    ]

    for step in next_steps:
        story.append(Paragraph(step, bullet_style))
        story.append(Spacer(1, 0.2*cm))

    # PDF generieren
    doc.build(story, canvasmaker=NumberedCanvas)

    print(f"\nPDF erfolgreich erstellt: {output_path}")
    print(f"Seiten: ~10")
    print(f"Features analysiert: 3 (KI-Docs, DSGVO-Kalender, Self-Booking)")
    print(f"Bereit fuer Management-Praesentation!")

    return output_path


if __name__ == "__main__":
    create_presentation()
