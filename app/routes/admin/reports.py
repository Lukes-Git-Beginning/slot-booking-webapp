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
    """Weekly reports overview"""
    if not week_key:
        week_key = get_week_key(datetime.now(TZ))

    try:
        # Get week data
        recent_weeks = list_recent_weeks(12)  # Last 12 weeks
        week_stats = compute_week_stats(week_key)

        return render_template("admin_reports_weekly.html",
                             current_week=week_key,
                             recent_weeks=recent_weeks,
                             week_stats=week_stats)

    except Exception as e:
        flash(f"Error loading weekly report: {str(e)}", "danger")
        return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/reports/monthly")
@admin_bp.route("/reports/monthly/<int:year>/<int:month>")
@require_admin
def admin_reports_monthly(year=None, month=None):
    """Monthly reports overview"""
    if not year or not month:
        now = datetime.now(TZ)
        year = now.year
        month = now.month

    try:
        # Generate monthly report data
        month_key = f"{year}-{month:02d}"

        # This would be enhanced with actual monthly statistics
        monthly_data = {
            'month': month_key,
            'total_bookings': 0,
            'unique_customers': 0,
            'top_performers': []
        }

        return render_template("admin_reports_monthly.html",
                             year=year,
                             month=month,
                             monthly_data=monthly_data)

    except Exception as e:
        flash(f"Error loading monthly report: {str(e)}", "danger")
        return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/reports/export/<report_type>")
@require_admin
def admin_telefonie_export_report(report_type):
    """Export specific report type"""
    try:
        if report_type == "weekly":
            week_key = request.args.get("week", get_week_key(datetime.now(TZ)))
            stats = compute_week_stats(week_key)

            export_data = {
                'report_type': 'weekly',
                'week': week_key,
                'data': stats,
                'exported_at': datetime.now(TZ).isoformat()
            }

        elif report_type == "monthly":
            year = int(request.args.get("year", datetime.now(TZ).year))
            month = int(request.args.get("month", datetime.now(TZ).month))

            export_data = {
                'report_type': 'monthly',
                'year': year,
                'month': month,
                'data': {},  # Would be filled with actual data
                'exported_at': datetime.now(TZ).isoformat()
            }

        else:
            return jsonify({"error": "Invalid report type"}), 400

        response = make_response(json.dumps(export_data, indent=2))
        response.headers['Content-Type'] = 'application/json'
        response.headers['Content-Disposition'] = f'attachment; filename={report_type}_report.json'

        return response

    except Exception as e:
        return jsonify({"error": f"Export failed: {str(e)}"}), 500


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