# -*- coding: utf-8 -*-
"""
Admin route blueprints
"""

from flask import Blueprint
import logging

admin_bp = Blueprint('admin', __name__)
logger = logging.getLogger(__name__)

# Import all admin route modules to register them
from . import dashboard, reports, users, telefonie, blocked_dates, export, tracking

# Make sure all routes are registered
logger.debug("Admin routes imported successfully")