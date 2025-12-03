# -*- coding: utf-8 -*-
"""
Error Tracking Utilities
Generate contextual error IDs for tracking and debugging
"""

from datetime import datetime
import uuid


def generate_error_id(category: str = "ERR") -> str:
    """
    Generate contextual error ID

    Format: <CATEGORY>-<YYYYMMDD>-<HHMMSS>-<4-CHAR-UUID>

    Examples:
        - BOOK-20251203-143022-A8F2 (booking error)
        - CAL-20251203-143045-B3D9 (calendar error)
        - TRK-20251203-143101-C7E1 (tracking error)

    Args:
        category: Error category prefix (default: "ERR")

    Returns:
        str: Contextual error ID
    """
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    unique_id = str(uuid.uuid4())[:4].upper()
    return f"{category}-{timestamp}-{unique_id}"
