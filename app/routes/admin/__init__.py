# -*- coding: utf-8 -*-
"""
Admin route blueprints
"""

from flask import Blueprint

admin_bp = Blueprint('admin', __name__)

# Import all admin route modules to register them
from . import dashboard, reports, users, telefonie

# Make sure all routes are registered
print("SUCCESS: Admin routes imported")