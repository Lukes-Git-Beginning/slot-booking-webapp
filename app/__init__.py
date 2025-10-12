# -*- coding: utf-8 -*-
"""
Central Business Tool Hub - Flask Application Factory
Zentraler Hub für alle Business-Tools mit Microservice-Architektur
"""

from flask import Flask, render_template, redirect, url_for, request, session
from typing import Optional
import os
import logging
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

    # Extensions initialisieren (bestehende)
    from app.core.extensions import init_extensions
    init_extensions(app)

    # Middleware initialisieren (bestehende)
    from app.core.middleware import init_middleware
    init_middleware(app)

    # Logging konfigurieren
    setup_logging(app)

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
            'version': '1.0.0',
            'tools': {
                'slots': 'healthy',
                't2': 'healthy',
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

        log_dir = app.config.get('LOG_DIR', 'logs')
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
        app.logger.warning(f" Could not load legacy slots blueprints: {e}")
        # Fallback to new slots blueprint if legacy fails
        try:
            from app.routes.slots import slots_bp
            app.register_blueprint(slots_bp, url_prefix='/slots')
            app.logger.info(" New slots blueprint registered (fallback)")
        except ImportError as e2:
            app.logger.error(f" No slots blueprint available: {e2}")

    # T2-Closer-System Blueprint (NEU)
    try:
        from app.routes.t2 import t2_bp
        app.register_blueprint(t2_bp, url_prefix='/t2')
        app.logger.info(" T2 blueprint registered")
    except ImportError as e:
        app.logger.info(f" Creating T2 blueprint: {e}")

    # API Gateway Blueprint (erweitert bestehende API)
    try:
        from app.routes.api_gateway import api_gateway_bp
        app.register_blueprint(api_gateway_bp, url_prefix='/api')
        app.logger.info(" API Gateway blueprint registered")
    except ImportError as e:
        app.logger.info(f" Creating API Gateway: {e}")
        # Fallback: Bestehende API verwenden
        try:
            from app.routes.api import api_bp
            app.register_blueprint(api_bp, url_prefix='/api')
            app.logger.info(" Legacy API blueprint registered")
        except ImportError as e2:
            app.logger.warning(f" API blueprint error: {e2}")

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


def register_error_handlers(app: Flask) -> None:
    """Error-Handler für alle HTTP-Status-Codes

    HINWEIS: Error Handlers werden jetzt über den error_handlers_bp Blueprint registriert.
    Diese Funktion bleibt als Fallback, falls der Blueprint nicht geladen werden kann.
    """
    pass

    # Fallback Error Handlers (nur wenn Blueprint fehlt)
    # @app.errorhandler(400)
    # def bad_request(error):
    #     return render_template('errors/400.html', error=error), 400

    # @app.errorhandler(401)
    # def unauthorized(error):
    #     return redirect(url_for('auth.login', next=request.url))

    # @app.errorhandler(403)
    # def forbidden(error):
    #     return render_template('errors/403.html', error=error), 403

    # @app.errorhandler(404)
    # def not_found(error):
    #     return render_template('errors/404.html', error=error), 404

    # @app.errorhandler(500)
    # def internal_error(error):
    #     app.logger.error(f'Server Error: {error}')
    #     return render_template('errors/500.html', error=error), 500

    # @app.errorhandler(503)
    # def service_unavailable(error):
    #     return render_template('errors/503.html', error=error), 503


def register_template_context(app: Flask) -> None:
    """Global Template Context Processors"""

    @app.context_processor
    def inject_global_vars():
        """Globale Template-Variablen"""
        return {
            'current_year': datetime.now().year,
            'app_name': 'Business Tool Hub',
            'app_version': '1.0.0',
            'current_user': session.get('user'),
            'is_admin': session.get('user') in get_admin_users(),
            'available_tools': get_available_tools(),
            'notifications': get_user_notifications(),
        }

    @app.template_filter('datetime')
    def datetime_filter(dt):
        """Datetime-Filter für Templates"""
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt)
            except:
                return dt
        return dt.strftime('%d.%m.%Y %H:%M')

    @app.template_filter('date')
    def date_filter(dt):
        """Date-Filter für Templates"""
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt)
            except:
                return dt
        return dt.strftime('%d.%m.%Y')

    @app.template_filter('avatar_url')
    def avatar_url_filter(avatar_id, category="default", size=128):
        """Avatar URL Generator Filter - DiceBear API Integration"""
        from app.utils.avatar_generator import get_avatar_url
        return get_avatar_url(avatar_id, category, size)


def register_request_hooks(app: Flask) -> None:
    """Request-Hooks für Session-Management und Logging"""

    @app.before_request
    def before_request():
        """Vor jedem Request ausführen"""
        # User-Activity-Tracking
        if 'user' in session:
            session['last_activity'] = datetime.now().isoformat()

        # Request-Logging für wichtige Endpoints
        if request.endpoint and not request.endpoint.startswith('static'):
            app.logger.debug(f'Request: {request.method} {request.path} from {request.remote_addr}')

    @app.after_request
    def after_request(response):
        """Nach jedem Request ausführen"""
        # Security-Headers setzen
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'

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
    except:
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
            'url': '/slots/',
            'status': 'active',
            'users': get_tool_user_count('slots'),
            'color': '#2196F3'
        },
        {
            'id': 't2',
            'name': 'T2-Closer',
            'description': 'T2-Termin-Management',
            'icon': '👥',
            'url': '/t2/',
            'status': 'active',
            'users': get_tool_user_count('t2'),
            'color': '#4CAF50'
        },
        {
            'id': 'analytics',
            'name': 'Analytics',
            'description': 'Business Intelligence',
            'icon': '📊',
            'url': '/analytics/',
            'status': 'active',
            'users': get_tool_user_count('analytics'),
            'color': '#FF9800'
        },
        {
            'id': 'tool4',
            'name': 'Tool #4',
            'description': 'Coming Soon',
            'icon': '🔧',
            'url': '#',
            'status': 'coming_soon',
            'users': 0,
            'color': '#9E9E9E'
        },
        {
            'id': 'tool5',
            'name': 'Tool #5',
            'description': 'Coming Soon',
            'icon': '⚙️',
            'url': '#',
            'status': 'coming_soon',
            'users': 0,
            'color': '#9E9E9E'
        },
        {
            'id': 'tool6',
            'name': 'Tool #6',
            'description': 'Coming Soon',
            'icon': '🚀',
            'url': '#',
            'status': 'coming_soon',
            'users': 0,
            'color': '#9E9E9E'
        }
    ]

    # Tools nach Benutzer-Berechtigungen filtern
    if user:
        return [tool for tool in tools if user_has_tool_access(user, tool['id'])]

    return []


def get_tool_user_count(tool_id: str) -> int:
    """Aktive Benutzer-Anzahl für Tool ermitteln"""
    # Hier würde später echte User-Activity-Tracking implementiert
    if tool_id == 'slots':
        return 25  # Dummy-Wert
    elif tool_id == 't2':
        return 8   # Dummy-Wert
    return 0


def user_has_tool_access(username: str, tool_id: str) -> bool:
    """Prüfen ob Benutzer Zugang zu Tool hat"""
    # Basis-Implementierung - später erweitern mit Role-Based-Access

    admin_users = get_admin_users()

    # Admins haben Zugang zu allen Tools
    if username in admin_users:
        return True

    # Standard-Benutzer haben Zugang zu Slots und T2
    if tool_id in ['slots', 't2']:
        return True

    # Analytics nur für Admins
    if tool_id == 'analytics':
        return username in admin_users

    # Andere Tools nur für Admins (vorerst)
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