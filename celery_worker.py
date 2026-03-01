# -*- coding: utf-8 -*-
"""
Celery worker entry point.

Usage:
    celery -A celery_worker:celery_app worker --loglevel=info

For development with CELERY_TASK_ALWAYS_EAGER=true,
tasks run synchronously inside the Flask process (no worker needed).
"""
from dotenv import load_dotenv
load_dotenv()

from app import create_app

flask_app = create_app()
celery_app = flask_app.extensions["celery"]
