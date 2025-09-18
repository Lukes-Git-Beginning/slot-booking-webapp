# -*- coding: utf-8 -*-
"""
Slot Booking Webapp - Flask Application Factory
"""

from flask import Flask
from app.core.extensions import init_extensions
from app.core.middleware import init_middleware


def create_app(config_object='app.config.base.Config'):
    """Application factory pattern for Flask app creation"""
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(config_object)

    # Initialize extensions
    init_extensions(app)

    # Initialize middleware
    init_middleware(app)

    # Register blueprints
    try:
        from app.routes.auth import auth_bp
        from app.routes.main import main_bp
        from app.routes.booking import booking_bp
        from app.routes.calendar import calendar_bp
        from app.routes.api import api_bp
        from app.routes.admin import admin_bp
        from app.routes.scoreboard import scoreboard_bp

        app.register_blueprint(auth_bp)
        app.register_blueprint(main_bp)
        app.register_blueprint(booking_bp)
        app.register_blueprint(calendar_bp)
        app.register_blueprint(api_bp, url_prefix='/api')
        app.register_blueprint(admin_bp, url_prefix='/admin')
        app.register_blueprint(scoreboard_bp)

        print("SUCCESS: Blueprints registered successfully")
    except ImportError as e:
        print(f"WARNING: Error importing blueprints: {e}")
        # For now, we'll import and register the old gamification blueprint for compatibility
        try:
            from gamification_routes import gamification_bp
            app.register_blueprint(gamification_bp)
            print("SUCCESS: Legacy gamification blueprint registered")
        except ImportError:
            print("WARNING: Could not import legacy gamification blueprint")

    return app