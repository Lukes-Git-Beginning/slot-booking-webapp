# -*- coding: utf-8 -*-
"""
Application entry point for Slot Booking Webapp
Replaces the original slot_booking_webapp.py for startup
"""

from app import create_app
import os

# Determine configuration based on environment
config_name = os.getenv('FLASK_ENV', 'development')

if config_name == 'production':
    config_object = 'app.config.production.ProductionConfig'
elif config_name == 'development':
    config_object = 'app.config.development.DevelopmentConfig'
else:
    config_object = 'app.config.base.Config'

# Create Flask application
app = create_app(config_object)

if __name__ == "__main__":
    # Run the application
    debug_mode = app.config.get('DEBUG', False)
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)