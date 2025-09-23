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


@admin_bp.route("/analytics/export")
@require_admin
def export_analytics():
    """Export analytics data"""
    try:
        if not tracking_system:
            return jsonify({"error": "Tracking system not available"}), 503

        # Get analytics data
        dashboard_data = tracking_system.get_performance_dashboard()

        # Create export
        export_data = {
            'exported_at': datetime.now(TZ).isoformat(),
            'analytics': dashboard_data
        }

        response = make_response(json.dumps(export_data, indent=2))
        response.headers['Content-Type'] = 'application/json'
        response.headers['Content-Disposition'] = 'attachment; filename=analytics_export.json'

        return response

    except Exception as e:
        return jsonify({"error": f"Export failed: {str(e)}"}), 500


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

        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#2563eb'),
            fontName='Helvetica-Bold'
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.HexColor('#1e40af'),
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

        # Header
        elements.append(Paragraph("TELEFONIE POINTS SYSTEM", title_style))
        elements.append(Paragraph("Administrative Summary Report", heading_style))
        elements.append(Paragraph(f"Generated: {datetime.now(TZ).strftime('%d.%m.%Y at %H:%M')}", body_style))
        elements.append(Spacer(1, 30))

        # System Overview
        elements.append(Paragraph("📊 SYSTEM OVERVIEW", heading_style))

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
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')])
            ]))

            elements.append(overview_table)
            elements.append(Spacer(1, 20))

            # Participant List
            elements.append(Paragraph("👥 ACTIVE PARTICIPANTS", heading_style))

            participant_text = ", ".join(participants) if participants else "No participants found"
            elements.append(Paragraph(participant_text, body_style))
            elements.append(Spacer(1, 20))

        except Exception as e:
            elements.append(Paragraph(f"Error loading system data: {str(e)}", body_style))
            elements.append(Spacer(1, 20))

        # System Information
        elements.append(Paragraph("⚙️ SYSTEM INFORMATION", heading_style))

        system_info = [
            "• Telefonie Points Management System",
            "• Weekly goal tracking and performance monitoring",
            "• Automated reporting and analytics",
            "• Executive dashboard and insights",
            "• Professional PDF export capabilities"
        ]

        for info in system_info:
            elements.append(Paragraph(info, body_style))

        elements.append(Spacer(1, 30))

        # Usage Instructions
        elements.append(Paragraph("📋 QUICK ACCESS GUIDE", heading_style))

        instructions = [
            "• Use 'Weekly Executive Report' for detailed weekly analysis",
            "• Use 'Monthly Executive Report' for comprehensive monthly overview",
            "• Export professional PDFs using the dedicated export buttons",
            "• Manage goals and participants in the main admin interface",
            "• Monitor real-time progress through the dashboard"
        ]

        for instruction in instructions:
            elements.append(Paragraph(instruction, body_style))

        # Footer
        elements.append(Spacer(1, 30))
        elements.append(Paragraph("―" * 50, ParagraphStyle('line', alignment=TA_CENTER)))
        elements.append(Paragraph(
            f"Report generated on {datetime.now(TZ).strftime('%d.%m.%Y at %H:%M')} | Telefonie Points Management System",
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
        from legacy.executive_reports import ExecutiveReports
        reports = ExecutiveReports()
        report = reports.generate_weekly_executive_report(week_key)
        return render_template("executive_weekly_report.html", report=report)
    except Exception as e:
        flash(f"❌ Fehler beim Generieren des Wochenberichts: {e}", "danger")
        return redirect(url_for("admin.admin_telefonie"))


@admin_bp.route("/reports/monthly")
@admin_bp.route("/reports/monthly/<int:year>/<int:month>")
@require_admin
def admin_reports_monthly(year=None, month=None):
    """Executive Monthly Report"""
    try:
        from legacy.executive_reports import ExecutiveReports
        reports = ExecutiveReports()
        report = reports.generate_monthly_executive_report(year, month)
        return render_template("executive_monthly_report.html", report=report)
    except Exception as e:
        flash(f"❌ Fehler beim Generieren des Monatsberichts: {e}", "danger")
        return redirect(url_for("admin.admin_telefonie"))


@admin_bp.route("/reports/export/<report_type>")
@require_admin
def admin_telefonie_export_report(report_type):
    """Export Executive Report as Professional PDF"""
    try:
        from legacy.executive_reports import ExecutiveReports
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
            title = f"Weekly Executive Report - Week {report['meta']['week']}"
            filename_prefix = "weekly_executive"
        elif report_type == "monthly":
            year = request.args.get("year", type=int)
            month = request.args.get("month", type=int)
            report = reports.generate_monthly_executive_report(year, month)
            title = f"Monthly Executive Report - {report['meta']['month_name']}"
            filename_prefix = "monthly_executive"
        else:
            flash("❌ Ungültiger Report-Typ", "danger")
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

        # Custom styles for professional appearance
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#2563eb'),
            fontName='Helvetica-Bold'
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.HexColor('#1e40af'),
            fontName='Helvetica-Bold'
        )

        subheading_style = ParagraphStyle(
            'CustomSubheading',
            parent=styles['Heading3'],
            fontSize=14,
            spaceAfter=10,
            spaceBefore=15,
            textColor=colors.HexColor('#374151'),
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
        elements.append(Paragraph(f"Generated: {report['meta']['generated_at']}", body_style))
        elements.append(Spacer(1, 20))

        # Executive Summary Section
        elements.append(Paragraph("📊 EXECUTIVE SUMMARY", heading_style))

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
        status_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#374151')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')])
        ]))

        elements.append(status_table)
        elements.append(Spacer(1, 15))

        # Key Highlights
        elements.append(Paragraph("Key Highlights:", subheading_style))
        for highlight in summary['highlights']:
            elements.append(Paragraph(f"• {highlight}", body_style))
        elements.append(Spacer(1, 20))

        # Performance Overview Section
        if 'performance_overview' in report:
            elements.append(Paragraph("👥 TEAM PERFORMANCE", heading_style))

            perf = report['performance_overview']
            dist = perf['team_distribution']

            # Performance distribution table
            perf_data = [
                ['Performance Level', 'Team Members', 'Percentage'],
                ['🏆 High Performers (90%+)', str(dist['high_performers']), f"{(dist['high_performers']/report['meta']['total_participants']*100):.0f}%"],
                ['👍 Medium Performers (70-89%)', str(dist['medium_performers']), f"{(dist['medium_performers']/report['meta']['total_participants']*100):.0f}%"],
                ['📈 Developing (< 70%)', str(dist['low_performers']), f"{(dist['low_performers']/report['meta']['total_participants']*100):.0f}%"]
            ]

            perf_table = Table(perf_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
            perf_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')])
            ]))

            elements.append(perf_table)
            elements.append(Spacer(1, 15))

            elements.append(Paragraph(f"Team Health Assessment: <b>{perf['team_health']}</b>", highlight_style))
            elements.append(Spacer(1, 20))

        # Individual Performance Details
        if 'performers' in report.get('performance_overview', {}):
            elements.append(Paragraph("Individual Performance Breakdown:", subheading_style))

            performers = report['performance_overview']['performers']

            # High Performers
            if performers['high']:
                elements.append(Paragraph("🏆 High Performers:", subheading_style))
                high_data = [['Name', 'Goal', 'Achieved', 'Rate']]
                for p in performers['high']:
                    high_data.append([p['name'], str(p['goal']), str(p['achieved']), f"{p['rate']}%"])

                high_table = Table(high_data, colWidths=[1.5*inch, 1*inch, 1*inch, 1*inch])
                high_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#059669')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0fdf4')])
                ]))
                elements.append(high_table)
                elements.append(Spacer(1, 10))

            # Low Performers (if any)
            if performers['low']:
                elements.append(Paragraph("📈 Development Opportunities:", subheading_style))
                low_data = [['Name', 'Goal', 'Achieved', 'Rate', 'Gap']]
                for p in performers['low']:
                    gap = p['goal'] - p['achieved'] if p['goal'] > 0 else 0
                    low_data.append([p['name'], str(p['goal']), str(p['achieved']), f"{p['rate']}%", str(gap)])

                low_table = Table(low_data, colWidths=[1.2*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch])
                low_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dc2626')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fef2f2')])
                ]))
                elements.append(low_table)
                elements.append(Spacer(1, 15))

        # Action Items Section
        if 'action_items' in report:
            elements.append(Paragraph("🎯 ACTION ITEMS", heading_style))
            for i, action in enumerate(report['action_items'], 1):
                elements.append(Paragraph(f"{i}. {action}", body_style))
            elements.append(Spacer(1, 20))

        # Trends Analysis (if available)
        if 'trends_analysis' in report:
            trends = report['trends_analysis']
            elements.append(Paragraph("📈 TRENDS ANALYSIS", heading_style))

            if trends['trend_direction'] != 'insufficient_data':
                trend_text = f"Performance is <b>{trends['trend_direction']}</b>"
                if trends['trend_change'] != 0:
                    trend_text += f" by {abs(trends['trend_change'])}% compared to previous period"
                elements.append(Paragraph(trend_text, body_style))

                if trends['weekly_data']:
                    elements.append(Paragraph("Recent Performance History:", subheading_style))
                    trend_data = [['Week', 'Achievement Rate', 'Points Achieved']]
                    for week_data in trends['weekly_data'][-4:]:  # Last 4 weeks
                        trend_data.append([
                            week_data['week'],
                            f"{week_data['achievement_rate']}%",
                            str(week_data['total_points'])
                        ])

                    trend_table = Table(trend_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch])
                    trend_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6366f1')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 0), (-1, -1), 10),
                        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')])
                    ]))
                    elements.append(trend_table)
            else:
                elements.append(Paragraph("Insufficient historical data for trend analysis", body_style))

        # Footer
        elements.append(Spacer(1, 30))
        elements.append(Paragraph("―" * 50, ParagraphStyle('line', alignment=TA_CENTER)))
        elements.append(Paragraph(
            f"Report generated on {datetime.now(TZ).strftime('%d.%m.%Y at %H:%M')} | Telefonie Points Management System",
            ParagraphStyle('footer', fontSize=9, alignment=TA_CENTER, textColor=colors.HexColor('#6b7280'))
        ))

        # Build PDF
        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()

        return Response(pdf, mimetype='application/pdf', headers={
            'Content-Disposition': f"attachment; filename={filename_prefix}_report_{datetime.now(TZ).strftime('%Y%m%d_%H%M')}.pdf"
        })
    except Exception as e:
        flash(f"❌ PDF Export Fehler: {e}", "danger")
        return redirect(url_for("admin.admin_telefonie"))


@admin_bp.route("/storage/optimize", methods=["GET", "POST"])
@require_admin
def admin_storage_optimize():
    """Storage optimization and cleanup"""
    if request.method == "POST":
        try:
            # Perform storage optimization
            from app.core.extensions import data_persistence

            # This would trigger actual optimization
            optimized_files = []

            # Example: cleanup old backups
            data_persistence.auto_cleanup_backups()
            optimized_files.append("backup_cleanup")

            if optimized_files:
                flash(f"Speicher optimiert: {', '.join(optimized_files)}", "success")
            else:
                flash("Keine Optimierung erforderlich", "info")

        except Exception as e:
            flash(f"Optimierungsfehler: {str(e)}", "danger")

        return redirect(url_for("admin.admin_storage_optimize"))

    # GET - show optimization interface
    try:
        # Get storage statistics
        storage_stats = {
            'total_size': '0 MB',  # Would be calculated
            'backup_count': 0,
            'optimization_suggestions': []
        }

        return render_template("admin_storage.html",
                             storage_stats=storage_stats)

    except Exception as e:
        flash(f"Fehler beim Laden der Speicher-Informationen: {str(e)}", "danger")
        return redirect(url_for("admin.admin_dashboard"))