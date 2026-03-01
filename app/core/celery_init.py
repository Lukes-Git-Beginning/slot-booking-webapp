# -*- coding: utf-8 -*-
"""
Celery initialization with Flask app context integration.

Source: https://flask.palletsprojects.com/en/stable/patterns/celery/
All tasks automatically run within Flask app context.
"""
import logging
from celery import Celery, Task
from flask import Flask

logger = logging.getLogger(__name__)


def celery_init_app(app: Flask) -> Celery:
    """Initialize Celery with Flask app context.

    All tasks automatically run within Flask app context,
    enabling access to database, config, and other extensions.

    Args:
        app: Flask application instance with CELERY config dict set.

    Returns:
        Configured Celery application instance.
    """
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.config_from_object(app.config["CELERY"])
    celery_app.set_default()
    app.extensions["celery"] = celery_app
    logger.info("Celery initialized successfully")
    return celery_app
