# -*- coding: utf-8 -*-
"""Shared utility functions for tracking system."""

import os
import json
import tempfile


def _atomic_json_write(filepath, data):
    """Atomic write: schreibt in Temp-Datei, dann rename. Verhindert Datenverlust bei Crash."""
    dir_name = os.path.dirname(filepath) or "."
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, filepath)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def _get_german_weekday(weekday_index):
    """Helper: Englischer Wochentag-Index zu deutschem Namen"""
    weekdays_de = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    return weekdays_de[weekday_index]
