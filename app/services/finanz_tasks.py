# -*- coding: utf-8 -*-
"""
Finanzberatung Celery tasks.

All tasks use @shared_task to avoid circular imports with the app factory.
Tasks are automatically discovered when celery_worker.py creates the Flask app.

Future task files (Phase 4):
- app/services/document_tasks.py (extraction, OCR, classification)
- app/services/analysis_tasks.py (embedding, scorecard generation)
"""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(ignore_result=False)
def health_check_task():
    """Simple test task to verify Celery worker connectivity.

    Returns dict with status info. Used by deployment health checks
    and during Phase 1 verification.
    """
    logger.info("Celery health check task executed successfully")
    return {"status": "ok", "message": "Celery worker is running"}
