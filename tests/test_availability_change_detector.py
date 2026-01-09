# -*- coding: utf-8 -*-
"""
Test Availability Change Detector
Unit tests for change detection logic with past/future slot filtering
"""

import pytest
from datetime import datetime
import pytz
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.availability_change_detector import detect_availability_changes


def test_past_slots_ignored():
    """Past slots should not trigger deletions"""
    berlin_tz = pytz.timezone('Europe/Berlin')
    now = berlin_tz.localize(datetime(2026, 1, 9, 12, 0))  # Noon

    old = {
        "2026-01-09 09:00": ["Daniel", "Christian"],  # Past
        "2026-01-09 14:00": ["Tim"]                   # Future
    }
    new = {
        "2026-01-09 14:00": ["Tim"]                   # Future
    }

    changes = detect_availability_changes(old, new, now=now)

    assert changes['total_deletions'] == 0, "Past slots should not trigger deletions"
    assert len(changes['deletions']) == 0, "No deletions should be reported"


def test_future_deletion_detected():
    """Real deletions in future slots should be detected"""
    berlin_tz = pytz.timezone('Europe/Berlin')
    now = berlin_tz.localize(datetime(2026, 1, 9, 12, 0))

    old = {
        "2026-01-09 14:00": ["Daniel", "Christian"]
    }
    new = {
        "2026-01-09 14:00": ["Christian"]  # Daniel removed
    }

    changes = detect_availability_changes(old, new, now=now)

    assert changes['total_deletions'] == 1, "Should detect 1 deletion"
    assert len(changes['deletions']) == 1, "Should have 1 deletion record"
    assert changes['deletions'][0]['consultant'] == 'Daniel', "Daniel should be marked as removed"
    assert changes['deletions'][0]['slot'] == '2026-01-09 14:00', "Correct slot should be identified"


def test_backward_compatible_no_now_param():
    """Function should work without now parameter"""
    old = {
        "2026-01-09 14:00": ["Daniel"]
    }
    new = {
        "2026-01-09 14:00": []
    }

    # Should not crash when called without 'now' parameter
    changes = detect_availability_changes(old, new)

    assert 'total_deletions' in changes, "Should return valid result structure"
    assert 'deletions' in changes, "Should include deletions list"
    assert changes['total_deletions'] == 1, "Should detect deletion using current time"


def test_invalid_timestamp_included():
    """Invalid timestamps should be included (not crash)"""
    berlin_tz = pytz.timezone('Europe/Berlin')
    now = berlin_tz.localize(datetime(2026, 1, 9, 12, 0))

    old = {
        "invalid-timestamp": ["Daniel"],
        "2026-01-09 14:00": ["Tim"]
    }
    new = {
        "2026-01-09 14:00": ["Tim"]
    }

    # Should not crash, should include invalid timestamp in comparison
    changes = detect_availability_changes(old, new, now=now)

    # Invalid timestamp is included (safer), so Daniel removal is detected
    assert changes['total_deletions'] == 1, "Should detect deletion from invalid timestamp slot"
    assert changes['deletions'][0]['slot'] == 'invalid-timestamp', "Invalid slot should be included"
    assert changes['deletions'][0]['consultant'] == 'Daniel', "Daniel should be marked as removed"


def test_exact_current_time_treated_as_past():
    """Slot at exact current time should be treated as past"""
    berlin_tz = pytz.timezone('Europe/Berlin')
    now = berlin_tz.localize(datetime(2026, 1, 9, 9, 0))  # Exactly 09:00

    old = {
        "2026-01-09 09:00": ["Daniel"]  # Exactly now
    }
    new = {}

    changes = detect_availability_changes(old, new, now=now)

    # Slot at exactly current time should be filtered as past (not future)
    assert changes['total_deletions'] == 0, "Slot at exact current time should be treated as past"


def test_complex_scenario():
    """Mixed past/future with multiple consultants"""
    berlin_tz = pytz.timezone('Europe/Berlin')
    now = berlin_tz.localize(datetime(2026, 1, 9, 12, 0))

    old = {
        "2026-01-09 09:00": ["Daniel", "Christian"],  # Past - ignore
        "2026-01-09 14:00": ["Daniel", "Christian"],  # Future
        "2026-01-09 16:00": ["Tim", "Simon"]          # Future
    }
    new = {
        "2026-01-09 14:00": ["Christian"],            # Daniel removed
        "2026-01-09 16:00": ["Tim", "Simon"]          # Unchanged
    }

    changes = detect_availability_changes(old, new, now=now)

    # Only Daniel's removal from 14:00 should be detected (09:00 is past)
    assert changes['total_deletions'] == 1, "Should detect exactly 1 deletion"
    assert changes['deletions'][0]['slot'] == "2026-01-09 14:00", "Deletion should be from 14:00 slot"
    assert changes['deletions'][0]['consultant'] == 'Daniel', "Daniel should be marked as removed"


def test_timezone_naive_datetime_handled():
    """Timezone-naive datetime should be localized"""
    now_naive = datetime(2026, 1, 9, 12, 0)  # No timezone

    old = {
        "2026-01-09 09:00": ["Daniel"]
    }
    new = {}

    # Should not crash, should localize to Berlin time
    changes = detect_availability_changes(old, new, now=now_naive)

    # Past slot (09:00) should be ignored
    assert changes['total_deletions'] == 0, "Past slot should be ignored after localization"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
