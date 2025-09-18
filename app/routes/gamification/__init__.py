# -*- coding: utf-8 -*-
"""
Gamification route blueprints
"""

from flask import Blueprint

gamification_bp = Blueprint('gamification', __name__)

# Import all gamification route modules to register them
from . import badges, quests, shop, analytics