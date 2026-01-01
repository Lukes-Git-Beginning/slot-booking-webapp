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

    # 7. Sentry Error Tracking Check
    try:
        sentry_dsn = os.environ.get('SENTRY_DSN')
        if sentry_dsn:
            checks['sentry'] = {
                'status': 'healthy',
                'message': 'Sentry error tracking enabled',
                'configured': True
            }
        else:
            checks['sentry'] = {
                'status': 'info',
                'message': 'Sentry not configured (optional)',
                'configured': False
            }
    except Exception as e:
        checks['sentry'] = {
            'status': 'unknown',
            'message': f'Sentry check failed: {str(e)}'
        }

    # 8. Google Calendar API Quota Check
    try:
        cal_service = GoogleCalendarService()
        if cal_service.service:
            quota_used = cal_service._daily_quota_used
            quota_limit = cal_service._quota_limit
            quota_pct = (quota_used / quota_limit * 100) if quota_limit > 0 else 0

            checks['calendar_quota'] = {
                'status': 'healthy' if quota_pct < 80 else 'warning',
                'message': f'{quota_used}/{quota_limit} requests used ({quota_pct:.1f}%)',
                'quota_used': quota_used,
                'quota_limit': quota_limit,
                'quota_percent': round(quota_pct, 2)
            }
    except Exception as e:
        checks['calendar_quota'] = {
            'status': 'unknown',
            'message': f'Could not check quota: {str(e)}'
        }

    # Build response
    response = {
        'status': 'healthy' if overall_healthy else 'unhealthy',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'checks': checks,
        'version': '3.3.7',  # Business Tool Hub version
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


@health_bp.route("/health/detailed")
def health_detailed():
    """
    Detailed health check with extended diagnostics
    Returns comprehensive system information for debugging
    """
    try:
        details = {}

        # Google Calendar detailed check
        try:
            cal_service = GoogleCalendarService()
            details['google_calendar'] = {
                'configured': cal_service.service is not None,
                'has_credentials': cal_service.credentials is not None if hasattr(cal_service, 'credentials') else False,
                'status': 'operational' if cal_service.service else 'not_configured'
            }
        except Exception as e:
            details['google_calendar'] = {
                'configured': False,
                'error': str(e),
                'status': 'error'
            }

        # Database files check
        try:
            persist_dir = data_persistence.data_dir
            json_files = list(persist_dir.glob('*.json')) if persist_dir.exists() else []
            details['database'] = {
                'type': 'JSON Files',
                'location': str(persist_dir),
                'files_count': len(json_files),
                'files': [f.name for f in json_files],
                'status': 'operational' if persist_dir.exists() else 'error'
            }
        except Exception as e:
            details['database'] = {
                'error': str(e),
                'status': 'error'
            }

        # Memory usage detailed
        try:
            memory = psutil.virtual_memory()
            details['memory'] = {
                'total_gb': memory.total / (1024 * 1024 * 1024),
                'available_gb': memory.available / (1024 * 1024 * 1024),
                'used_gb': memory.used / (1024 * 1024 * 1024),
                'percent': memory.percent,
                'status': 'healthy' if memory.percent < 90 else 'warning'
            }
        except Exception as e:
            details['memory'] = {'error': str(e), 'status': 'error'}

        # Disk space detailed
        try:
            disk = psutil.disk_usage('/')
            details['disk_space'] = {
                'total_gb': disk.total / (1024 * 1024 * 1024),
                'free_gb': disk.free / (1024 * 1024 * 1024),
                'used_gb': disk.used / (1024 * 1024 * 1024),
                'percent': disk.percent,
                'status': 'healthy' if disk.percent < 80 else 'warning'
            }
        except Exception as e:
            details['disk_space'] = {'error': str(e), 'status': 'error'}

        return jsonify({
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'version': '3.3.7',
            'details': details
        }), 200
    except Exception as e:
        return jsonify({
            'error': f'Health detailed check failed: {str(e)}',
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


@health_bp.route("/health/calendars")
def health_calendars():
    """
    Calendar health check endpoint
    Tests connectivity to all consultant Google Calendars
    Admin-only endpoint for proactive monitoring
    """
    from app.core.google_calendar import get_google_calendar_service
    from googleapiclient.errors import HttpError
    from datetime import timedelta

    results = {}
    calendar_service = get_google_calendar_service()

    if not calendar_service:
        return jsonify({
            'success': False,
            'error': 'Calendar service not initialized'
        }), 500

    # Parse consultants from environment variable
    consultants_env = os.getenv("CONSULTANTS", "")
    consultants = {}

    if consultants_env:
        # Format: "Name1:email1,Name2:email2"
        for pair in consultants_env.split(","):
            if ":" in pair:
                name, email = pair.split(":", 1)
                consultants[name.strip()] = email.strip()

    if not consultants:
        # Fallback to default consultants if env var not set
        consultants = {
            "Daniel": "daniel.herbort.zfa@gmail.com",
            "Simon": "simonmast9@gmail.com",
            "Ann-Kathrin": "a.welge.zfa@gmail.com",
            "Christian": "chmast95@gmail.com",
            "Tim": "tim.kreisel71@gmail.com",
            "Sara": "mastsara2@gmail.com",
            "Dominik": "mikic.dom@gmail.com",
            "Sonja": "sonjamast98@gmail.com"
        }

    # Test each consultant's calendar
    for name, cal_id in consultants.items():
        try:
            # Minimal API call: Get 1 event from last 7 days
            time_min = (datetime.now() - timedelta(days=7)).isoformat() + 'Z'
            time_max = datetime.now().isoformat() + 'Z'

            events = calendar_service.get_events(
                calendar_id=cal_id,
                time_min=time_min,
                time_max=time_max,
                max_results=1
            )

            # Check if we got a valid response
            if events is not None:
                event_count = len(events.get('items', [])) if isinstance(events, dict) else 0
                results[name] = {
                    'status': 'healthy',
                    'calendar_id': cal_id,
                    'events_found': event_count
                }
            else:
                results[name] = {
                    'status': 'error',
                    'calendar_id': cal_id,
                    'error_message': 'Calendar service returned None'
                }

        except HttpError as e:
            results[name] = {
                'status': 'error',
                'calendar_id': cal_id,
                'error_code': e.resp.status,
                'error_message': str(e)
            }
        except Exception as e:
            results[name] = {
                'status': 'error',
                'calendar_id': cal_id,
                'error_message': str(e)
            }

    # Calculate overall health
    healthy_count = sum(1 for r in results.values() if r['status'] == 'healthy')
    total_count = len(results)
    health_percentage = round(healthy_count / total_count * 100, 1) if total_count > 0 else 0

    # Determine overall status
    if health_percentage == 100:
        overall_status = 'healthy'
    elif health_percentage >= 80:
        overall_status = 'degraded'
    else:
        overall_status = 'critical'

    return jsonify({
        'overall_status': overall_status,
        'summary': {
            'healthy': healthy_count,
            'total': total_count,
            'health_percentage': health_percentage
        },
        'calendars': results,
        'timestamp': datetime.now().isoformat()
    }), 200


def get_uptime_seconds():
    """Get uptime in seconds"""
    try:
        boot_time = psutil.boot_time()
        return int(datetime.now().timestamp() - boot_time)
    except:
        return 0