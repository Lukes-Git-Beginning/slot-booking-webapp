# -*- coding: utf-8 -*-
"""
WSGI entry point for production deployment
"""

from app import create_app

# Create application instance for WSGI server
application = create_app('app.config.production.ProductionConfig')

if __name__ == "__main__":
    application.run()