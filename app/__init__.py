# -*- coding: utf-8 -*-
"""
Central Business Tool Hub - Flask Application Factory
Zentraler Hub für alle Business-Tools mit Microservice-Architektur
"""

from flask import Flask, render_template, redirect, url_for, request, session, g
from typing import Optional
import os
import logging
import secrets
from datetime import datetime

def create_app(config_object: Optional[str] = None) -> Flask:
    """
    Application Factory für Central Business Tool Hub

    Args:
        config_object: Konfigurationsobjekt-Pfad

    Returns:
        Konfigurierte Flask-Anwendung
    """
    # Set template and static folders relative to project root
    template_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
    static_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static'))

    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)

    # Konfiguration laden
    if config_object:
        app.config.from_object(config_object)
    else:
        # Standard-Konfiguration für Development
        app.config.from_object('app.config.base.Config')

    # ProxyFix: Flask erkennt HTTPS korrekt hinter Nginx Reverse-Proxy
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # Celery configuration (must be set before init_extensions)
    _redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    # Strip trailing /N to get base URL for DB separation
    _redis_base = _redis_url.rsplit("/", 1)[0] if _redis_url.count("/") > 2 else _redis_url

    app.config["CELERY"] = {
        "broker_url": f"{_redis_base}/1",
        "result_backend": f"{_redis_base}/2",
        "task_ignore_result": True,
        "task_serializer": "json",
        "result_serializer": "json",
        "accept_content": ["json"],
        "task_acks_late": True,
        "task_reject_on_worker_lost": True,
        "task_track_started": True,
        "result_expires": 86400,
        "timezone": "Europe/Berlin",
        "enable_utc": True,
        "task_always_eager": os.getenv("CELERY_TASK_ALWAYS_EAGER", "false").lower()
            in ["true", "1", "yes"],
        "task_eager_propagates": True,
    }

    # Extensions initialisieren (bestehende)
    from app.core.extensions import init_extensions
    init_extensions(app)

    # Database initialisieren (PostgreSQL Migration)
    from app.models import init_db, is_postgres_enabled
    if is_postgres_enabled():
        try:
            init_db(app)
            app.logger.info("PostgreSQL database initialized successfully")
        except Exception as e:
            app.logger.error(f"PostgreSQL initialization failed: {e}", exc_info=True)
            app.logger.warning("Falling back to JSON storage")

    # Middleware initialisieren (bestehende)
    from app.core.middleware import init_middleware
    init_middleware(app)

    # Logging konfigurieren
    setup_logging(app)

    # Sentry Error Tracking initialisieren (Production)
    init_sentry(app)

    # ENV-Validierung
    validate_environment(app)

    # Blueprints registrieren (neue Hub-Architektur)
    register_blueprints(app)

    # Error-Handler registrieren
    register_error_handlers(app)

    # Template-Kontext-Prozessoren
    register_template_context(app)

    # Request-Hooks
    register_request_hooks(app)

    # Legacy-Redirects für Backwards-Compatibility
    register_legacy_redirects(app)

    # Health-Check-Endpoint direkt registrieren (Fallback wenn Blueprint fehlt)
    @app.route('/health')
    def health_check():
        """System-Health-Check für Monitoring"""
        import json
        from datetime import datetime

        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '3.3.19',
            'tools': {
                'slots': 'healthy',
                'analytics': 'not_ready',
            },
            'database': 'healthy',
            'memory': 'ok'
        }

        return json.dumps(health_status, indent=2), 200, {'Content-Type': 'application/json'}

    app.logger.info('Central Business Tool Hub started successfully')

    return app


def setup_logging(app: Flask) -> None:
    """Logging-Konfiguration für Production"""
    if not app.debug:
        import logging.handlers

        log_dir = app.config.get('LOG_DIR', '/var/log/business-hub' if not app.debug else 'logs')
        os.makedirs(log_dir, exist_ok=True)

        # Main application log
        app_handler = logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, 'hub.log'),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        app_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        app_handler.setLevel(logging.INFO)
        app.logger.addHandler(app_handler)
        app.logger.setLevel(logging.INFO)


def init_sentry(app: Flask) -> None:
    """Sentry Error Tracking initialisieren für Production Monitoring"""
    sentry_dsn = app.config.get('SENTRY_DSN') or os.environ.get('SENTRY_DSN')

    if sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.flask import FlaskIntegration

            sentry_sdk.init(
                dsn=sentry_dsn,
                integrations=[FlaskIntegration()],
                traces_sample_rate=0.1,  # 10% Performance Monitoring
                environment='production' if not app.debug else 'development',
                release=f"business-hub@{app.config.get('VERSION', '3.3.19')}",
                # PII disabled — no usernames/IPs sent to external Sentry service
                send_default_pii=False,
                # Logs zu Sentry senden
                enable_tracing=True,
                # Exclude health check endpoints from monitoring
                ignore_errors=[
                    KeyboardInterrupt,
                ],
                before_send=lambda event, hint: _filter_sentry_event(event, hint),
            )
            app.logger.info(f"Sentry initialized for environment: {'production' if not app.debug else 'development'}")
        except ImportError:
            app.logger.warning("Sentry SDK not installed, skipping error tracking")
        except Exception as e:
            app.logger.error(f"Failed to initialize Sentry: {e}")
    else:
        app.logger.warning("SENTRY_DSN not configured - error tracking disabled. Set SENTRY_DSN env var for production monitoring.")


def _filter_sentry_event(event, hint):
    """Filter Sentry events to reduce noise"""
    # Don't send health check requests
    if 'request' in event:
        url = event['request'].get('url', '')
        if '/health' in url or '/ping' in url:
            return None
    return event


def validate_environment(app: Flask) -> None:
    """Pruefe kritische Umgebungsvariablen beim Startup"""
    warnings = []

    if not os.getenv('USERLIST'):
        warnings.append("USERLIST not set - no users can log in")

    if not os.getenv('DATABASE_URL') and app.config.get('USE_POSTGRES'):
        warnings.append("DATABASE_URL not set but USE_POSTGRES enabled")

    google_creds = (
        os.getenv('GOOGLE_CREDS_BASE64')
        or os.getenv('GOOGLE_CREDS_B64')
        or os.getenv('GOOGLE_CREDS_JSON')
    )
    if not google_creds and not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        warnings.append("No Google credentials configured - Calendar features will fail")

    if not os.getenv('SECRET_KEY') and not app.config.get('SECRET_KEY'):
        warnings.append("SECRET_KEY not set - sessions will be insecure")

    for w in warnings:
        app.logger.warning(f"ENV-CHECK: {w}")


def register_blueprints(app: Flask) -> None:
    """Alle Blueprints registrieren - Hub-Architektur + Legacy-Support"""

    # Central Hub Blueprint (NEU)
    try:
        from app.routes.hub import hub_bp
        app.register_blueprint(hub_bp, url_prefix='/')
        app.logger.info("Central Hub blueprint registered")
    except ImportError as e:
        app.logger.info(f"Creating Central Hub blueprint: {e}")

    # Central Authentication Blueprint (NEU - erweitert bestehende auth)
    try:
        from app.routes.auth import auth_bp
        # Auth läuft weiterhin auf Root-Level für Compatibility
        app.register_blueprint(auth_bp)
        app.logger.info("Auth blueprint registered")
    except ImportError as e:
        app.logger.warning(f"Auth blueprint error: {e}")

    # Security Blueprint (Passwort & 2FA)
    try:
        from app.routes.security import security_bp
        app.register_blueprint(security_bp, url_prefix='/security')
        app.logger.info(" Security blueprint registered")
    except ImportError as e:
        app.logger.warning(f" Security blueprint error: {e}")

    # Slot-Booking Tool Blueprint - Use LEGACY blueprints (complete app from Render)
    try:
        from app.routes.main import main_bp
        from app.routes.booking import booking_bp
        from app.routes.calendar import calendar_bp
        from app.routes.scoreboard import scoreboard_bp
        from app.routes.user_profile import user_profile_bp

        app.register_blueprint(main_bp, url_prefix='/slots')
        app.register_blueprint(booking_bp, url_prefix='/slots')
        app.register_blueprint(calendar_bp, url_prefix='/slots')
        app.register_blueprint(scoreboard_bp, url_prefix='/slots')
        app.register_blueprint(user_profile_bp, url_prefix='/slots')
        app.logger.info(" Legacy slots blueprints registered (complete Render app)")
    except ImportError as e:
        app.logger.error(f" Could not load legacy slots blueprints: {e}")
        # CRITICAL: Legacy slots blueprints are required for production
        # If this error occurs, the app cannot function properly

    # T2-Closer-System Blueprint (Feature Flag Toggle)
    try:
        if app.config.get('T2_MODULAR_BLUEPRINTS', False):
            # NEW: Modular blueprint structure (Phase 2+)
            from app.routes.t2 import init_app as init_t2
            init_t2(app)
            app.logger.info("✅ T2 Modular Blueprints ENABLED")
        else:
            # LEGACY: Monolithic t2.py (default, backward compatible)
            from app.routes.t2_legacy import t2_bp
            app.register_blueprint(t2_bp, url_prefix='/t2')
            app.logger.info("✅ T2 Legacy Blueprint ENABLED (default)")
    except ImportError as e:
        app.logger.warning(f"T2-Closer blueprint error: {e}")

    # API Blueprint (Legacy)
    try:
        from app.routes.api import api_bp
        app.register_blueprint(api_bp, url_prefix='/api')
        app.logger.info(" Legacy API blueprint registered")
    except ImportError as e:
        app.logger.warning(f" API blueprint error: {e}")

    # Central Admin Blueprint (erweitert bestehende admin)
    try:
        from app.routes.admin import admin_bp
        app.register_blueprint(admin_bp, url_prefix='/admin')
        app.logger.info(" Admin blueprint registered")
    except ImportError as e:
        app.logger.warning(f" Admin blueprint error: {e}")

    # Gamification Blueprint (bestehend)
    try:
        from app.routes.gamification.legacy_routes import gamification_bp
        app.register_blueprint(gamification_bp, url_prefix='/slots')
        app.logger.info(" Gamification blueprint registered")
    except ImportError as e:
        app.logger.warning(f" Could not import gamification blueprint: {e}")

    # Health Check Blueprint (NEU)
    try:
        from app.routes.health import health_bp
        app.register_blueprint(health_bp)
        app.logger.info(" Health check blueprint registered")
    except ImportError as e:
        app.logger.warning(f" Health check blueprint error: {e}")

    # Error Handlers Blueprint (zentrale Error-Behandlung)
    try:
        from app.routes.error_handlers import error_handlers_bp
        app.register_blueprint(error_handlers_bp)
        app.logger.info("Error handlers blueprint registered")
    except ImportError as e:
        app.logger.warning(f"Error handlers blueprint error: {e}")

    # Analytics Blueprint (NEU - Business Intelligence)
    try:
        from app.routes.analytics import analytics_bp
        app.register_blueprint(analytics_bp, url_prefix='/analytics')
        app.logger.info("Analytics blueprint registered")
    except ImportError as e:
        app.logger.warning(f"Analytics blueprint error: {e}")

    # HubSpot Webhook Blueprint (CRM Integration)
    try:
        from app.routes.hubspot_webhook import hubspot_webhook_bp
        app.register_blueprint(hubspot_webhook_bp)
        # CSRF-Exemption für externe Webhooks
        from app.core.extensions import csrf
        if csrf:
            csrf.exempt(hubspot_webhook_bp)
        app.logger.info("HubSpot webhook blueprint registered")
    except ImportError as e:
        app.logger.warning(f"HubSpot webhook blueprint error: {e}")

    # Finanzberatung Blueprint (Financial Advisory Document Analysis)
    try:
        from app.config.base import FinanzConfig
        if FinanzConfig.FINANZ_ENABLED:
            from app.routes.finanzberatung import init_app as init_finanzberatung
            init_finanzberatung(app)
        else:
            app.logger.info("Finanzberatung blueprint disabled (FINANZ_ENABLED=false)")
    except ImportError as e:
        app.logger.warning(f"Finanzberatung blueprint error: {e}")


def register_error_handlers(app: Flask) -> None:
    """Error-Handler für alle HTTP-Status-Codes

    HINWEIS: Error Handlers werden primär über den error_handlers_bp Blueprint registriert.
    Diese Funktion registriert Fallback-Handler für den Fall, dass der Blueprint nicht geladen wird.
    """
    from flask import render_template, redirect, url_for, request

    # Fallback Error Handlers (aktiv als Redundanz)
    @app.errorhandler(400)
    def bad_request(error):
        app.logger.warning(f'400 Bad Request: {error}')
        return render_template('errors/400.html', error=error), 400

    @app.errorhandler(401)
    def unauthorized(error):
        app.logger.warning(f'401 Unauthorized: {error}')
        return redirect(url_for('auth.login', next=request.url))

    @app.errorhandler(403)
    def forbidden(error):
        app.logger.warning(f'403 Forbidden: {error}')
        return render_template('errors/403.html', error=error), 403

    @app.errorhandler(404)
    def not_found(error):
        # Don't log every 404 (too noisy), only in debug mode
        if app.debug:
            app.logger.debug(f'404 Not Found: {request.url}')
        return render_template('errors/404.html', error=error), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'500 Internal Server Error: {error}')
        return render_template('errors/500.html', error=error), 500

    @app.errorhandler(503)
    def service_unavailable(error):
        app.logger.error(f'503 Service Unavailable: {error}')
        return render_template('errors/503.html', error=error), 503


def register_template_context(app: Flask) -> None:
    """Global Template Context Processors"""

    @app.context_processor
    def inject_global_vars():
        """Globale Template-Variablen"""
        from app.config.base import FinanzConfig

        # Booster and seasonal event data for base template
        active_boosters = []
        seasonal_event = None
        current_user = session.get('user')
        if current_user:
            try:
                from app.services.gameplay_rewards import gameplay_rewards
                active_boosters = gameplay_rewards.get_active_boosters(current_user)
            except Exception:
                pass
            try:
                from app.services.seasonal_events import seasonal_events
                seasonal_event = seasonal_events.get_active_event()
            except Exception:
                pass

        return {
            'current_year': datetime.now().year,
            'app_name': 'Beraterwelt',
            'app_version': '1.0.0',
            'current_user': session.get('user'),
            'is_admin': session.get('user') in get_admin_users(),
            'available_tools': get_available_tools(),
            'notifications': get_user_notifications(),
            'csp_nonce': getattr(g, 'csp_nonce', ''),
            'finanz_enabled': FinanzConfig.FINANZ_ENABLED,
            'finanz_access': user_has_tool_access(session.get('user', ''), 'finanzberatung') if session.get('user') else False,
            'active_boosters': active_boosters,
            'seasonal_event': seasonal_event,
        }

    @app.template_filter('datetime')
    def datetime_filter(dt):
        """Datetime-Filter für Templates"""
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt)
            except (ValueError, TypeError):
                return dt
        return dt.strftime('%d.%m.%Y %H:%M')

    @app.template_filter('date')
    def date_filter(dt):
        """Date-Filter für Templates"""
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt)
            except (ValueError, TypeError):
                return dt
        return dt.strftime('%d.%m.%Y')

    @app.template_filter('avatar_url')
    def avatar_url_filter(avatar_id, category="default", size=128):
        """Avatar URL Generator Filter - DiceBear API Integration"""
        from app.utils.avatar_generator import get_avatar_url
        return get_avatar_url(avatar_id, category, size)

    @app.template_filter('de_number')
    def de_number_filter(value, decimals=1):
        """Format number with German decimal separator (comma)."""
        if value is None:
            return "0"
        try:
            formatted = f"{float(value):.{decimals}f}"
            return formatted.replace(".", ",")
        except (ValueError, TypeError):
            return str(value)


def register_request_hooks(app: Flask) -> None:
    """Request-Hooks für Session-Management und Logging"""

    @app.before_request
    def set_csp_nonce():
        """Generate a unique CSP nonce for each request"""
        g.csp_nonce = secrets.token_urlsafe(16)

    @app.before_request
    def track_session_user():
        """Track whether session had user key at request start (debug)"""
        g._had_user = 'user' in session

    @app.before_request
    def before_request():
        """Vor jedem Request ausführen"""
        # User-Activity-Tracking
        if 'user' in session:
            session['last_activity'] = datetime.now().isoformat()
            session.modified = True  # Force session TTL refresh on every request

        # Request-Logging für wichtige Endpoints
        if request.endpoint and not request.endpoint.startswith('static'):
            app.logger.debug(f'Request: {request.method} {request.path} from {request.remote_addr}')

    @app.after_request
    def watch_session_integrity(response):
        """Temporary debug hook: warn if session loses user key during request"""
        if getattr(g, '_had_user', False) and 'user' not in session:
            sid = getattr(session, 'sid', '?')
            app.logger.error(
                "SESSION CORRUPTION: user key lost during request! "
                "Path: %s, Method: %s, Status: %s, sid: %s",
                request.path, request.method, response.status_code,
                str(sid)[:8]
            )
        return response

    @app.after_request
    def after_request(response):
        """Nach jedem Request ausführen"""
        # Security-Headers setzen
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=(), payment=()'

        # Content Security Policy (CSP) - Nonce-based
        nonce = getattr(g, 'csp_nonce', '')
        csp_directives = [
            "default-src 'self'",
            f"script-src 'self' 'nonce-{nonce}' 'unsafe-eval' https://cdn.jsdelivr.net https://unpkg.com",
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com https://fonts.googleapis.com",
            "img-src 'self' data: https:",
            "font-src 'self' data: https://fonts.gstatic.com https://cdn.jsdelivr.net https://unpkg.com",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]
        response.headers['Content-Security-Policy'] = "; ".join(csp_directives)

        return response


def register_legacy_redirects(app: Flask) -> None:
    """Legacy-Redirects für Backwards-Compatibility"""

    @app.route('/')
    def root_redirect():
        """Root-Path zu Slots-Dashboard umleiten"""
        return redirect('/slots/', code=302)

    @app.route('/day/<date_str>')
    def legacy_day_view(date_str):
        """Legacy /day/ Route zu /slots/day/ umleiten"""
        return redirect(f'/slots/day/{date_str}', code=301)

    @app.route('/booking')
    def legacy_booking():
        return redirect('/slots/booking', code=301)

    @app.route('/calendar')
    def legacy_calendar():
        return redirect('/slots/calendar', code=301)

    @app.route('/my-calendar')
    def legacy_my_calendar():
        """Legacy /my-calendar Route zu /slots/my-calendar umleiten"""
        return redirect('/slots/my-calendar', code=301)

    @app.route('/gamification')
    def legacy_gamification():
        return redirect('/slots/gamification', code=301)

    @app.route('/scoreboard')
    def legacy_scoreboard():
        return redirect('/slots/scoreboard', code=301)

    @app.route('/profile')
    def legacy_profile():
        return redirect('/slots/profile', code=301)

    @app.route('/api/user/<username>/cosmetics')
    def legacy_api_cosmetics(username):
        """Legacy API cosmetics Route zu /slots/api/user/<username>/cosmetics umleiten"""
        return redirect(f'/slots/api/user/{username}/cosmetics', code=301)


def get_admin_users():
    """Admin-Benutzer aus Konfiguration laden"""
    try:
        from app.config.base import Config
        return Config.get_admin_users()
    except (ImportError, AttributeError):
        return ['admin', 'Jose', 'Simon', 'Alex', 'David']  # Fallback


def get_available_tools():
    """Liste aller verfügbaren Tools für Navigation"""
    user = session.get('user')

    tools = [
        {
            'id': 'slots',
            'name': 'Slot-Booking',
            'description': 'Terminbuchungs-System',
            'icon': '🎯',
            'lucide_icon': 'target',
            'url': '/slots/',
            'status': 'active',
            'users': get_tool_user_count('slots'),
            'color': '#d4af6a'  # ZFA Gold
        },
        {
            'id': 't2',
            'name': 'T2-Closer',
            'description': 'T2-Termin-Management',
            'icon': '💼',
            'lucide_icon': 'briefcase',
            'url': '/t2/',
            'status': 'active',
            'users': get_tool_user_count('t2'),
            'color': '#207487'  # ZFA Blau
        },
        {
            'id': 'analytics',
            'name': 'Analytics',
            'description': 'Business Intelligence',
            'icon': '📊',
            'lucide_icon': 'bar-chart-3',
            'url': '/analytics/',
            'status': 'active',
            'users': get_tool_user_count('analytics'),
            'color': '#294c5d'  # ZFA Dunkelblau
        },
        {
            'id': 'tool4',
            'name': 'Tool #4',
            'description': 'Coming Soon',
            'icon': '🔧',
            'lucide_icon': 'wrench',
            'url': '#',
            'status': 'coming_soon',
            'users': 0,
            'color': '#c2ae7f'  # ZFA Gold Dark
        },
        {
            'id': 'tool5',
            'name': 'Tool #5',
            'description': 'Coming Soon',
            'icon': '⚙️',
            'lucide_icon': 'settings',
            'url': '#',
            'status': 'coming_soon',
            'users': 0,
            'color': '#207487'  # ZFA Blau
        },
        {
            'id': 'tool6',
            'name': 'Tool #6',
            'description': 'Coming Soon',
            'icon': '🚀',
            'lucide_icon': 'rocket',
            'url': '#',
            'status': 'coming_soon',
            'users': 0,
            'color': '#294c5d'  # ZFA Dunkelblau
        }
    ]

    # Tools nach Benutzer-Berechtigungen filtern
    if user:
        return [tool for tool in tools if user_has_tool_access(user, tool['id'])]

    return []


def get_tool_user_count(tool_id: str) -> int:
    """Aktive Benutzer-Anzahl für Tool ermitteln (zählt User mit Tool-Zugriff)"""
    try:
        from app.config.base import Config
        all_users = Config.get_all_users()
        # Zähle User die Zugriff auf dieses Tool haben
        count = sum(1 for user in all_users if user_has_tool_access(user, tool_id))
        return count
    except (ImportError, AttributeError):
        # Fallback auf geschätzte Werte wenn Config nicht verfügbar
        return 0


def user_has_tool_access(username: str, tool_id: str) -> bool:
    """Prüfen ob Benutzer Zugang zu Tool hat (rollenbasiert)"""
    admin_users = get_admin_users()
    is_admin = username in admin_users

    # Slots + My Analytics: alle User
    if tool_id in ['slots', 'my-analytics']:
        return True

    # T2: Closer + Opener + Admin
    if tool_id == 't2':
        t2_access = [
            'jose.torspecken', 'alexander.nehm', 'david.nehm',
            'tim.kreisel', 'christian.mast', 'daniel.herbort',
            'sonja.mast', 'simon.mast', 'dominik.mikic',
            'ann-kathrin.welge', 'sara.mast',
        ]
        return is_admin or username in t2_access

    # Onboarding: Service + Closer + Admin
    if tool_id == 'onboarding':
        onboarding_access = [
            'alexandra.börner', 'vanessa.wagner', 'simon.mast',
            'tim.kreisel', 'christian.mast', 'daniel.herbort',
        ]
        return is_admin or username in onboarding_access

    # Analytics: Admin + Marketing/Analytics-Zugang
    if tool_id == 'analytics':
        analytics_access = [
            'moritz.schimanko',
        ]
        return is_admin or username in analytics_access

    # Finanzberatung: Opener + Closer + Admin
    if tool_id == 'finanzberatung':
        finanz_access = [
            'christian.mast', 'tim.kreisel', 'daniel.herbort', 'sonja.mast',
            'simon.mast', 'dominik.mikic', 'ann-kathrin.welge', 'sara.mast',
            'jose.torspecken', 'alexander.nehm', 'david.nehm', 'luke.hoppe',
        ]
        return is_admin or username in finanz_access

    # WIP/coming_soon Tools: nur Username "Admin"
    if tool_id in ['tool4', 'tool5', 'tool6']:
        return username == 'Admin'

    return False


def get_user_notifications():
    """Benutzer-Benachrichtigungen laden"""
    user = session.get('user')
    if not user:
        return []

    # Hier würde später echtes Notification-System implementiert
    return [
        {
            'id': 1,
            'type': 'info',
            'message': 'Willkommen im neuen Business Tool Hub!',
            'timestamp': datetime.now().isoformat(),
            'read': False
        }
    ]