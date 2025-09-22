# -*- coding: utf-8 -*-
"""
Slot Booking Webapp - Flask Application Factory
"""

from flask import Flask
from app.core.extensions import init_extensions
from app.core.middleware import init_middleware


def create_app(config_object='app.config.base.Config'):
    """Application factory pattern for Flask app creation"""
    import os

    # Set template and static folders relative to project root
    template_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
    static_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static'))

    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)

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

    # Always register the gamification blueprint
    try:
        from gamification_routes import gamification_bp
        app.register_blueprint(gamification_bp)
        print("SUCCESS: Gamification blueprint registered")
    except ImportError as e:
        print(f"WARNING: Could not import gamification blueprint: {e}")

    return app