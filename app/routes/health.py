# -*- coding: utf-8 -*-
"""
Health Check and Monitoring Endpoints
"""

from flask import Blueprint, jsonify, request
from datetime import datetime
import os
import psutil

from app.services.data_persistence import data_persistence
from app.core.google_calendar import GoogleCalendarService
from app.services.holiday_service import holiday_service

health_bp = Blueprint('health', __name__)


@health_bp.route("/health")
def health_check():
    """
    Comprehensive health check endpoint
    Returns system status and service availability
    """
    checks = {}
    overall_healthy = True

    # 1. Data Persistence Check
    try:
        # Test if we can access persistent data
        test_data = data_persistence.load_data('user_stats', default={})
        checks['data_persistence'] = {
            'status': 'healthy',
            'message': 'Data persistence layer accessible'
        }
    except Exception as e:
        checks['data_persistence'] = {
            'status': 'unhealthy',
            'message': f'Data persistence error: {str(e)}'
        }
        overall_healthy = False

    # 2. Google Calendar API Check
    try:
        cal_service = GoogleCalendarService()
        if cal_service.service is not None:
            checks['google_calendar'] = {
                'status': 'healthy',
                'message': 'Google Calendar API configured'
            }
        else:
            checks['google_calendar'] = {
                'status': 'degraded',
                'message': 'Google Calendar API not configured'
            }
    except Exception as e:
        checks['google_calendar'] = {
            'status': 'degraded',
            'message': f'Calendar API warning: {str(e)}'
        }
        # Calendar not critical, don't mark overall as unhealthy

    # 3. Holiday Service Check
    try:
        from datetime import date
        # Test with a known holiday (Christmas)
        test_result = holiday_service.is_holiday(date(2024, 12, 25))
        checks['holiday_service'] = {
            'status': 'healthy',
            'message': 'Holiday service operational'
        }
    except Exception as e:
        checks['holiday_service'] = {
            'status': 'degraded',
            'message': f'Holiday service warning: {str(e)}'
        }
        # Holiday service is not critical, so don't mark as unhealthy

    # 4. Cache Manager Check
    try:
        from app.core.extensions import cache_manager
        cache_stats = cache_manager.get_stats()
        checks['cache_manager'] = {
            'status': 'healthy',
            'message': 'Cache manager operational',
            'stats': cache_stats
        }
    except Exception as e:
        checks['cache_manager'] = {
            'status': 'degraded',
            'message': f'Cache manager warning: {str(e)}'
        }

    # 5. File System & Disk Space Check
    try:
        persist_dir = str(data_persistence.data_dir)
        if os.path.exists(persist_dir) and os.access(persist_dir, os.W_OK):
            # Check disk space
            disk = psutil.disk_usage(persist_dir)
            disk_free_pct = 100 - disk.percent

            if disk_free_pct < 10:
                checks['filesystem'] = {
                    'status': 'critical',
                    'message': f'Critical: Only {disk_free_pct:.1f}% disk space remaining',
                    'disk_free_gb': disk.free / (1024 * 1024 * 1024),
                    'disk_used_pct': disk.percent
                }
                overall_healthy = False
            elif disk_free_pct < 20:
                checks['filesystem'] = {
                    'status': 'warning',
                    'message': f'Warning: Only {disk_free_pct:.1f}% disk space remaining',
                    'disk_free_gb': disk.free / (1024 * 1024 * 1024),
                    'disk_used_pct': disk.percent
                }
            else:
                checks['filesystem'] = {
                    'status': 'healthy',
                    'message': f'Filesystem healthy ({disk_free_pct:.1f}% free)',
                    'disk_free_gb': disk.free / (1024 * 1024 * 1024),
                    'disk_used_pct': disk.percent
                }
        else:
            checks['filesystem'] = {
                'status': 'unhealthy',
                'message': f'Persistent directory not writable: {persist_dir}'
            }
            overall_healthy = False
    except Exception as e:
        checks['filesystem'] = {
            'status': 'unhealthy',
            'message': f'Filesystem error: {str(e)}'
        }
        overall_healthy = False

    # 6. System Resources Check
    try:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        memory_healthy = memory.percent < 90
        disk_healthy = disk.percent < 90

        checks['system_resources'] = {
            'status': 'healthy' if (memory_healthy and disk_healthy) else 'degraded',
            'memory_usage': f'{memory.percent:.1f}%',
            'memory_available_mb': memory.available / (1024 * 1024),
            'disk_usage': f'{disk.percent:.1f}%',
            'disk_free_gb': disk.free / (1024 * 1024 * 1024)
        }

        if not (memory_healthy and disk_healthy):
            overall_healthy = False
    except Exception as e:
        checks['system_resources'] = {
            'status': 'unknown',
            'message': f'Could not check resources: {str(e)}'
        }

    # Build response
    response = {
        'status': 'healthy' if overall_healthy else 'unhealthy',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'checks': checks,
        'version': '3.2.0',  # Business Tool Hub version
        'uptime': get_uptime()
    }

    status_code = 200 if overall_healthy else 503
    return jsonify(response), status_code


@health_bp.route("/health/ready")
def readiness_check():
    """
    Kubernetes-style readiness probe
    Returns 200 if app is ready to serve traffic
    """
    try:
        # Quick check: Can we access critical services?
        data_persistence.load_data('user_stats', default={})
        return jsonify({
            'status': 'ready',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'not_ready',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }), 503


@health_bp.route("/health/live")
def liveness_check():
    """
    Kubernetes-style liveness probe
    Returns 200 if app is alive (even if degraded)
    """
    return jsonify({
        'status': 'alive',
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }), 200


@health_bp.route("/health/metrics")
def metrics():
    """
    Prometheus-style metrics endpoint
    Returns key application metrics
    """
    try:
        # System metrics
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        disk = psutil.disk_usage('/')

        # Application metrics
        try:
            user_stats = data_persistence.load_data('user_stats', default={})
            total_users = len(user_stats)
        except:
            total_users = 0

        try:
            scores = data_persistence.load_data('scores', default={})
            total_bookings = sum(len(v.get('termine', [])) for v in scores.values())
        except:
            total_bookings = 0

        metrics_data = {
            'system': {
                'memory_usage_percent': memory.percent,
                'memory_available_mb': memory.available / (1024 * 1024),
                'cpu_percent': cpu_percent,
                'disk_usage_percent': disk.percent,
                'disk_free_gb': disk.free / (1024 * 1024 * 1024)
            },
            'application': {
                'total_users': total_users,
                'total_bookings': total_bookings,
                'uptime_seconds': get_uptime_seconds()
            },
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }

        return jsonify(metrics_data), 200
    except Exception as e:
        return jsonify({
            'error': f'Could not generate metrics: {str(e)}',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }), 500


@health_bp.route("/health/ping")
def ping():
    """
    Simple ping endpoint for basic connectivity tests
    """
    return jsonify({'pong': True}), 200


# Helper Functions

def get_uptime():
    """Get human-readable uptime"""
    try:
        boot_time = psutil.boot_time()
        uptime_seconds = datetime.now().timestamp() - boot_time

        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)

        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    except:
        return "unknown"


def get_uptime_seconds():
    """Get uptime in seconds"""
    try:
        boot_time = psutil.boot_time()
        return int(datetime.now().timestamp() - boot_time)
    except:
        return 0