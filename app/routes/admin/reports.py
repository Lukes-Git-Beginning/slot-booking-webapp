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
from weekly_points import get_week_key, list_recent_weeks, compute_week_stats

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
            flash("Tracking system not available", "warning")
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
        flash(f"CSV export failed: {str(e)}", "danger")
        return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/export/pdf")
@require_admin
def admin_export_pdf():
    """Export report as PDF"""
    try:
        # For now, return JSON - PDF generation would require reportlab
        export_data = {
            'report_type': 'admin_summary',
            'generated_at': datetime.now(TZ).isoformat(),
            'data': 'PDF generation not yet implemented'
        }

        response = make_response(json.dumps(export_data, indent=2))
        response.headers['Content-Type'] = 'application/json'
        response.headers['Content-Disposition'] = 'attachment; filename=admin_report.json'

        return response

    except Exception as e:
        flash(f"PDF export failed: {str(e)}", "danger")
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
    """Export Executive Report as PDF"""
    try:
        from legacy.executive_reports import ExecutiveReports
        import io
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from flask import Response

        reports = ExecutiveReports()

        if report_type == "weekly":
            week = request.args.get("week")
            report = reports.generate_weekly_executive_report(week)
            title = f"Weekly Executive Report - Week {report['meta']['week']}"
        elif report_type == "monthly":
            year = request.args.get("year", type=int)
            month = request.args.get("month", type=int)
            report = reports.generate_monthly_executive_report(year, month)
            title = f"Monthly Executive Report - {report['meta']['month_name']}"
        else:
            flash("❌ Ungültiger Report-Typ", "danger")
            return redirect(url_for("admin.admin_telefonie"))

        # Generate PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        # Title
        title_para = Paragraph(title, styles['Heading1'])
        elements.append(title_para)
        elements.append(Spacer(1, 20))

        # Executive Summary
        summary_title = Paragraph("Executive Summary", styles['Heading2'])
        elements.append(summary_title)

        summary_text = f"Achievement Rate: {report['executive_summary']['key_metrics'].get('achievement_rate', report['executive_summary']['key_metrics'].get('monthly_achievement_rate', 0))}%"
        summary_para = Paragraph(summary_text, styles['Normal'])
        elements.append(summary_para)
        elements.append(Spacer(1, 10))

        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()

        return Response(pdf, mimetype='application/pdf', headers={
            'Content-Disposition': f"attachment; filename={report_type}_executive_report_{datetime.now(TZ).strftime('%Y%m%d_%H%M')}.pdf"
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
                flash(f"Storage optimized: {', '.join(optimized_files)}", "success")
            else:
                flash("No optimization needed", "info")

        except Exception as e:
            flash(f"Optimization error: {str(e)}", "danger")

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
        flash(f"Error loading storage info: {str(e)}", "danger")
        return redirect(url_for("admin.admin_dashboard"))