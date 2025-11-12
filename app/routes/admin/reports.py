# -*- coding: utf-8 -*-
"""
Admin reports routes
Analytics, exports, and reporting functionality
"""

from flask import render_template, request, redirect, url_for, flash, jsonify, make_response
from datetime import datetime, timedelta
import pytz
import json
import io
import csv

from app.config.base import slot_config
from app.core.extensions import tracking_system
from app.utils.decorators import require_admin
from app.routes.admin import admin_bp
from app.services.weekly_points import get_week_key, list_recent_weeks, compute_week_stats

TZ = pytz.timezone(slot_config.TIMEZONE)


@admin_bp.route("/tracking/report/weekly")
@require_admin
def weekly_tracking_report():
    """Show weekly report"""
    try:
        if not tracking_system:
            return jsonify({"error": "Tracking system not available"}), 503

        report = tracking_system.get_weekly_report()
        return jsonify(report)

    except Exception as e:
        return jsonify({"error": f"Report generation failed: {str(e)}"}), 500


# export_analytics endpoint removed - use /admin/export-all-data instead


@admin_bp.route("/export/csv")
@require_admin
def export_csv():
    """Export booking data as CSV"""
    try:
        if not tracking_system:
            flash("Tracking-System nicht verfügbar", "warning")
            return redirect(url_for("admin.admin_dashboard"))

        # Get all bookings
        all_bookings = tracking_system.load_all_bookings()

        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(['Date', 'Time', 'Customer', 'User', 'Color', 'Description'])

        # Write data
        for booking in all_bookings:
            writer.writerow([
                booking.get('date', ''),
                booking.get('time_slot', ''),
                booking.get('customer_name', ''),
                booking.get('user', ''),
                booking.get('color_id', ''),
                booking.get('description', '')
            ])

        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = 'attachment; filename=bookings_export.csv'

        return response

    except Exception as e:
        flash(f"CSV-Export fehlgeschlagen: {str(e)}", "danger")
        return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/export/pdf")
@require_admin
def admin_export_pdf():
    """Export admin summary as professional PDF"""
    try:
        import io
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from flask import Response

        # Generate professional admin summary PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=1*inch,
            bottomMargin=1*inch
        )

        elements = []
        styles = getSampleStyleSheet()

        # Custom styles mit ZFA-Branding
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=28,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#d4af6a'),  # ZFA Gold
            fontName='Helvetica-Bold',
            leading=34
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=18,
            spaceAfter=15,
            spaceBefore=25,
            textColor=colors.HexColor('#207487'),  # ZFA Blau
            fontName='Helvetica-Bold',
            borderPadding=(10, 5, 10, 5),
            backColor=colors.HexColor('#f0f9ff')  # Subtiler Hintergrund
        )

        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=8,
            textColor=colors.HexColor('#374151'),
            fontName='Helvetica'
        )

        # Header
        elements.append(Paragraph("TELEFONIE POINTS SYSTEM", title_style))
        elements.append(Paragraph("Administrativer Übersichtsbericht", heading_style))
        elements.append(Paragraph(f"Erstellt: {datetime.now(TZ).strftime('%d.%m.%Y um %H:%M Uhr')}", body_style))
        elements.append(Spacer(1, 30))

        # System Overview
        elements.append(Paragraph("📊 SYSTEMÜBERSICHT", heading_style))

        # Get some basic stats
        try:
            from app.services.weekly_points import get_participants, get_week_key, compute_week_stats
            current_week = get_week_key(datetime.now(TZ))
            participants = get_participants()
            week_stats = compute_week_stats(current_week)

            overview_data = [
                ['Metric', 'Value'],
                ['Total Participants', str(len(participants))],
                ['Current Week', current_week],
                ['Week Goal Total', str(week_stats["summary"]["total_goal"])],
                ['Week Achieved Total', str(week_stats["summary"]["total_achieved"])],
                ['Achievement Rate', f"{(week_stats['summary']['total_achieved']/week_stats['summary']['total_goal']*100) if week_stats['summary']['total_goal'] > 0 else 0:.1f}%"]
            ]

            overview_table = Table(overview_data, colWidths=[3*inch, 2*inch])
            overview_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d4af6a')),  # ZFA Gold Header
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('FONTSIZE', (0, 1), (-1, -1), 11),
                ('GRID', (0, 0), (-1, -1), 1.5, colors.HexColor('#207487')),  # ZFA Blau Grid
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fafaf9')]),
                ('TOPPADDING', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12)
            ]))

            elements.append(overview_table)
            elements.append(Spacer(1, 20))

            # Participant List
            elements.append(Paragraph("👥 AKTIVE TEILNEHMER", heading_style))

            participant_text = ", ".join(participants) if participants else "Keine Teilnehmer gefunden"
            elements.append(Paragraph(participant_text, body_style))
            elements.append(Spacer(1, 20))

        except Exception as e:
            elements.append(Paragraph(f"Fehler beim Laden der Systemdaten: {str(e)}", body_style))
            elements.append(Spacer(1, 20))

        # System Information
        elements.append(Paragraph("⚙️ SYSTEMINFORMATIONEN", heading_style))

        system_info = [
            "• Telefonie-Punktesystem",
            "• Wöchentliches Ziel-Tracking und Leistungsüberwachung",
            "• Automatisierte Berichte und Analytics",
            "• Executive Dashboard und Insights",
            "• Professionelle PDF-Export-Funktionen"
        ]

        for info in system_info:
            elements.append(Paragraph(info, body_style))

        elements.append(Spacer(1, 30))

        # Usage Instructions
        elements.append(Paragraph("📋 SCHNELLZUGRIFF", heading_style))

        instructions = [
            "• 'Wöchentlicher Executive Report' für detaillierte Wochenanalysen",
            "• 'Monatlicher Executive Report' für umfassende Monatsübersichten",
            "• Professionelle PDFs über die Export-Buttons exportieren",
            "• Ziele und Teilnehmer im Admin-Interface verwalten",
            "• Echtzeit-Fortschritt über das Dashboard überwachen"
        ]

        for instruction in instructions:
            elements.append(Paragraph(instruction, body_style))

        # Footer
        elements.append(Spacer(1, 30))
        elements.append(Paragraph("―" * 50, ParagraphStyle('line', alignment=TA_CENTER)))
        elements.append(Paragraph(
            f"Bericht erstellt am {datetime.now(TZ).strftime('%d.%m.%Y um %H:%M Uhr')} | Telefonie-Punktesystem",
            ParagraphStyle('footer', fontSize=9, alignment=TA_CENTER, textColor=colors.HexColor('#6b7280'))
        ))

        # Build PDF
        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()

        return Response(pdf, mimetype='application/pdf', headers={
            'Content-Disposition': f"attachment; filename=admin_summary_{datetime.now(TZ).strftime('%Y%m%d_%H%M')}.pdf"
        })

    except Exception as e:
        flash(f"PDF-Export fehlgeschlagen: {str(e)}", "danger")
        return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/reports/weekly")
@admin_bp.route("/reports/weekly/<week_key>")
@require_admin
def admin_reports_weekly(week_key=None):
    """Executive Weekly Report"""
    try:
        from app.services.executive_reports import ExecutiveReports
        reports = ExecutiveReports()
        report = reports.generate_weekly_executive_report(week_key)
        return render_template("executive_weekly_report.html", report=report)
    except Exception as e:
        flash(f"Fehler beim Generieren des Wochenberichts: {e}", "danger")
        return redirect(url_for("admin.admin_telefonie"))


@admin_bp.route("/reports/monthly")
@admin_bp.route("/reports/monthly/<int:year>/<int:month>")
@require_admin
def admin_reports_monthly(year=None, month=None):
    """Executive Monthly Report"""
    try:
        from app.services.executive_reports import ExecutiveReports
        reports = ExecutiveReports()
        report = reports.generate_monthly_executive_report(year, month)
        return render_template("executive_monthly_report.html", report=report)
    except Exception as e:
        flash(f"Fehler beim Generieren des Monatsberichts: {e}", "danger")
        return redirect(url_for("admin.admin_telefonie"))


@admin_bp.route("/reports/export/<report_type>")
@require_admin
def admin_telefonie_export_report(report_type):
    """Export Executive Report as Professional PDF"""
    try:
        from app.services.executive_reports import ExecutiveReports
        import io
        from reportlab.lib.pagesizes import A4, letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        from flask import Response

        reports = ExecutiveReports()

        if report_type == "weekly":
            week = request.args.get("week")
            report = reports.generate_weekly_executive_report(week)
            title = f"Wöchentlicher Executive Report - Woche {report['meta']['week']}"
            filename_prefix = "weekly_executive"
        elif report_type == "monthly":
            year = request.args.get("year", type=int)
            month = request.args.get("month", type=int)
            report = reports.generate_monthly_executive_report(year, month)
            title = f"Monatlicher Executive Report - {report['meta']['month_name']}"
            filename_prefix = "monthly_executive"
        else:
            flash("Ungültiger Report-Typ", "danger")
            return redirect(url_for("admin.admin_telefonie"))

        # Generate Professional PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=1*inch,
            bottomMargin=1*inch
        )

        elements = []
        styles = getSampleStyleSheet()

        # Custom styles for professional appearance mit ZFA-Branding
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=28,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#d4af6a'),  # ZFA Gold
            fontName='Helvetica-Bold',
            leading=34
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=18,
            spaceAfter=15,
            spaceBefore=25,
            textColor=colors.HexColor('#207487'),  # ZFA Blau
            fontName='Helvetica-Bold',
            borderPadding=(10, 5, 10, 5),
            backColor=colors.HexColor('#f0f9ff')
        )

        subheading_style = ParagraphStyle(
            'CustomSubheading',
            parent=styles['Heading3'],
            fontSize=14,
            spaceAfter=12,
            spaceBefore=18,
            textColor=colors.HexColor('#294c5d'),  # ZFA Dunkelblau
            fontName='Helvetica-Bold'
        )

        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=8,
            textColor=colors.HexColor('#374151'),
            fontName='Helvetica'
        )

        highlight_style = ParagraphStyle(
            'Highlight',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=8,
            textColor=colors.HexColor('#059669'),
            fontName='Helvetica-Bold'
        )

        # Header with company branding
        elements.append(Paragraph("TELEFONIE POINTS SYSTEM", title_style))
        elements.append(Paragraph(title, heading_style))
        elements.append(Paragraph(f"Erstellt: {report['meta']['generated_at']}", body_style))
        elements.append(Spacer(1, 20))

        # Executive Summary Section
        elements.append(Paragraph("📊 ZUSAMMENFASSUNG", heading_style))

        summary = report['executive_summary']
        status = summary['overall_status']

        # Status indicator table
        status_data = [
            ['Overall Status', f"{status['icon']} {status['status']}"],
            ['Achievement Rate', f"{summary['key_metrics'].get('achievement_rate', summary['key_metrics'].get('monthly_achievement_rate', 0))}%"],
            ['Points Achieved', f"{summary['key_metrics'].get('total_points_achieved', summary['key_metrics'].get('total_monthly_achieved', 0))}"],
            ['Points Target', f"{summary['key_metrics'].get('total_points_goal', summary['key_metrics'].get('total_monthly_goal', 0))}"]
        ]

        status_table = Table(status_data, colWidths=[2.5*inch, 2.5*inch])

        # Dynamische Farbe basierend auf Status
        if status['color'] == 'green':
            status_bg = colors.HexColor('#10b981')
            status_text = colors.white
        elif status['color'] == 'yellow':
            status_bg = colors.HexColor('#f59e0b')
            status_text = colors.white
        else:
            status_bg = colors.HexColor('#ef4444')
            status_text = colors.white

        status_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d4af6a')),  # ZFA Gold
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            # Status-Zeile mit dynamischer Farbe
            ('BACKGROUND', (0, 1), (-1, 1), status_bg),
            ('TEXTCOLOR', (0, 1), (-1, 1), status_text),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            # Rest
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 2), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('GRID', (0, 0), (-1, -1), 1.5, colors.HexColor('#207487')),  # ZFA Blau Grid
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 2), (-1, -1), [colors.white, colors.HexColor('#fafaf9')]),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12)
        ]))

        elements.append(status_table)
        elements.append(Spacer(1, 15))

        # Key Highlights
        elements.append(Paragraph("Wichtigste Kennzahlen:", subheading_style))
        for highlight in summary['highlights']:
            elements.append(Paragraph(f"• {highlight}", body_style))
        elements.append(Spacer(1, 20))

        # Performance Overview Section
        if 'performance_overview' in report:
            elements.append(Paragraph("👥 TEAMLEISTUNG", heading_style))

            perf = report['performance_overview']
            dist = perf['team_distribution']

            # Performance distribution table
            perf_data = [
                ['Leistungsstufe', 'Teammitglieder', 'Prozent'],
                ['🏆 Top-Leister (90%+)', str(dist['high_performers']), f"{(dist['high_performers']/report['meta']['total_participants']*100):.0f}%"],
                ['👍 Solide Leister (70-89%)', str(dist['medium_performers']), f"{(dist['medium_performers']/report['meta']['total_participants']*100):.0f}%"],
                ['📈 Entwicklungspotenzial (< 70%)', str(dist['low_performers']), f"{(dist['low_performers']/report['meta']['total_participants']*100):.0f}%"]
            ]

            perf_table = Table(perf_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
            perf_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d4af6a')),  # ZFA Gold Header
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('GRID', (0, 0), (-1, -1), 1.5, colors.HexColor('#207487')),  # ZFA Blau Grid
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fafaf9')]),
                ('TOPPADDING', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12)
            ]))

            elements.append(perf_table)
            elements.append(Spacer(1, 15))

            elements.append(Paragraph(f"Team-Gesundheit: <b>{perf['team_health']}</b>", highlight_style))
            elements.append(Spacer(1, 20))

        # Individual Performance Details - VOLLSTÄNDIGE TEAM-ÜBERSICHT (alle Telefonisten)
        if 'performers' in report.get('performance_overview', {}):
            elements.append(Paragraph("Individuelle Leistungsübersicht:", subheading_style))

            performers = report['performance_overview']['performers']

            # NEUE SEKTION: Vollständige Team-Tabelle mit ALLEN Telefonisten
            # Kombiniere High, Medium & Low Performer in EINER Tabelle
            all_team_members = []

            # High Performers (90%+)
            for p in performers['high']:
                all_team_members.append((p, '🏆 Top', 'high'))

            # Medium Performers (70-89%) - JETZT AUCH ANGEZEIGT!
            for p in performers['medium']:
                all_team_members.append((p, '👍 Gut', 'medium'))

            # Low Performers (<70%)
            for p in performers['low']:
                all_team_members.append((p, '📈 Entwicklung', 'low'))

            # Sortiere nach Achievement Rate (absteigend)
            all_team_members.sort(key=lambda x: x[0]['rate'], reverse=True)

            if all_team_members:
                elements.append(Paragraph("👥 VOLLSTÄNDIGE TEAM-ÜBERSICHT", subheading_style))

                # Erstelle Tabelle mit allen Telefonisten
                team_data = [['Name', 'Ziel', 'Erreicht', 'Rate', 'Status']]
                for member, status, category in all_team_members:
                    team_data.append([
                        member['name'],
                        str(member['goal']),
                        str(member['achieved']),
                        f"{member['rate']}%",
                        status
                    ])

                team_table = Table(team_data, colWidths=[1.5*inch, 0.9*inch, 0.9*inch, 0.9*inch, 1.3*inch])

                # Basis-Style
                base_style = [
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d4af6a')),  # ZFA Gold Header
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (0, -1), 'LEFT'),  # Namen linksbündig
                    ('ALIGN', (1, 0), (-1, -1), 'CENTER'),  # Rest zentriert
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 11),
                    ('GRID', (0, 0), (-1, -1), 1.2, colors.HexColor('#207487')),  # ZFA Blau Grid
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fafaf9')]),
                    ('TOPPADDING', (0, 0), (-1, -1), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 12)
                ]

                team_table.setStyle(TableStyle(base_style))

                # Farbliche Hervorhebung der Status-Spalte nach Performance
                for i, (member, status, category) in enumerate(all_team_members, start=1):
                    if category == 'high':
                        # Grün für Top-Leister
                        team_table.setStyle(TableStyle([
                            ('BACKGROUND', (4, i), (4, i), colors.HexColor('#dcfce7')),
                            ('TEXTCOLOR', (4, i), (4, i), colors.HexColor('#166534')),
                            ('FONTNAME', (4, i), (4, i), 'Helvetica-Bold')
                        ]))
                    elif category == 'medium':
                        # Blau für solide Leister
                        team_table.setStyle(TableStyle([
                            ('BACKGROUND', (4, i), (4, i), colors.HexColor('#dbeafe')),
                            ('TEXTCOLOR', (4, i), (4, i), colors.HexColor('#1e40af')),
                            ('FONTNAME', (4, i), (4, i), 'Helvetica-Bold')
                        ]))
                    elif category == 'low':
                        # Rot für Entwicklungspotenzial
                        team_table.setStyle(TableStyle([
                            ('BACKGROUND', (4, i), (4, i), colors.HexColor('#fee2e2')),
                            ('TEXTCOLOR', (4, i), (4, i), colors.HexColor('#991b1b')),
                            ('FONTNAME', (4, i), (4, i), 'Helvetica-Bold')
                        ]))

                elements.append(team_table)
                elements.append(Spacer(1, 20))

        # Trends Analysis (if available)
        if 'trends_analysis' in report:
            trends = report['trends_analysis']
            elements.append(Paragraph("📈 TRENDANALYSE", heading_style))

            if trends['trend_direction'] != 'insufficient_data':
                # Übersetze Trend-Richtung
                trend_direction_de = {
                    'improving': 'steigend',
                    'declining': 'fallend',
                    'stable': 'stabil'
                }.get(trends['trend_direction'], trends['trend_direction'])

                trend_text = f"Leistung ist <b>{trend_direction_de}</b>"
                if trends['trend_change'] != 0:
                    trend_text += f" um {abs(trends['trend_change'])}% gegenüber der Vorperiode"
                elements.append(Paragraph(trend_text, body_style))

                if trends['weekly_data']:
                    elements.append(Paragraph("Aktuelle Leistungshistorie:", subheading_style))
                    trend_data = [['Woche', 'Erreichungsrate', 'Erreichte Punkte']]
                    for week_data in trends['weekly_data'][-4:]:  # Last 4 weeks
                        trend_data.append([
                            week_data['week'],
                            f"{week_data['achievement_rate']}%",
                            str(week_data['total_points'])
                        ])

                    trend_table = Table(trend_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch])
                    trend_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#294c5d')),  # ZFA Dunkelblau
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 0), (-1, -1), 11),
                        ('GRID', (0, 0), (-1, -1), 1.2, colors.HexColor('#207487')),  # ZFA Blau Grid
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
                        ('TOPPADDING', (0, 0), (-1, -1), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 10)
                    ]))
                    elements.append(trend_table)
            else:
                elements.append(Paragraph("Unzureichende historische Daten für Trendanalyse", body_style))

        # Footer mit ZFA-Branding
        elements.append(Spacer(1, 40))

        # Goldene Trennlinie
        from reportlab.platypus import HRFlowable
        hr = HRFlowable(
            width="100%",
            thickness=2,
            color=colors.HexColor('#d4af6a'),  # ZFA Gold
            spaceBefore=10,
            spaceAfter=15
        )
        elements.append(hr)

        footer_text = f"Bericht erstellt am {datetime.now(TZ).strftime('%d.%m.%Y um %H:%M Uhr')} | Zentrum für Finanzielle Aufklärung - Telefonie-Punktesystem"
        elements.append(Paragraph(
            footer_text,
            ParagraphStyle(
                'footer',
                fontSize=9,
                alignment=TA_CENTER,
                textColor=colors.HexColor('#6b7280'),
                fontName='Helvetica-Oblique'
            )
        ))

        # Build PDF
        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()

        return Response(pdf, mimetype='application/pdf', headers={
            'Content-Disposition': f"attachment; filename={filename_prefix}_report_{datetime.now(TZ).strftime('%Y%m%d_%H%M')}.pdf"
        })
    except Exception as e:
        flash(f"PDF Export Fehler: {e}", "danger")
        return redirect(url_for("admin.admin_telefonie"))


# admin_storage_optimize endpoint removed - not needed