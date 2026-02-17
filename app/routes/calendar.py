# -*- coding: utf-8 -*-
"""
Calendar routes
Calendar view and personal calendar functionality
"""

from flask import Blueprint, render_template, session, jsonify, request
from datetime import datetime, timedelta
import pytz
import json
import os

from app.config.base import slot_config
from app.core.extensions import data_persistence, csrf
from app.core.google_calendar import get_google_calendar_service
from app.utils.decorators import require_login

calendar_bp = Blueprint('calendar', __name__)
TZ = pytz.timezone(slot_config.TIMEZONE)


def is_user_booking(event, username, username_variants, consultants_dict):
    """
    Multi-stage fallback filtering to determine if an event belongs to a user.

    This function implements a 5-stage matching strategy:
    1. Exact Tag Match: [Booked by: username] in description
    2. Consultant Calendar Match: Event organizer/creator is user's email
    3. Attendee Match: User's email is in event attendees
    4. Fuzzy Match: Username appears anywhere in description/summary
    5. Unclaimed: No match found (returns False)

    Args:
        event: Google Calendar event dict
        username: Current user's username (e.g., "christian.mast")
        username_variants: List of username variants (e.g., ["christian.mast", "christian"])
        consultants_dict: Dictionary mapping consultant names to emails

    Returns:
        tuple: (is_match: bool, match_reason: str or None, matched_variant: str or None)
               match_reason can be: 'tag', 'calendar', 'attendee', 'fuzzy', or None
    """
    description = event.get('description', '')
    summary = event.get('summary', '')

    # Stage 1: Exact Tag Match [Booked by: username]
    # This is the most reliable method - tags are added by the booking system
    for variant in username_variants:
        booked_by_tag = f"[Booked by: {variant}]"
        if booked_by_tag in description:
            return (True, 'tag', variant)

    # Stage 2: Consultant Email Match (organizer/creator)
    # Check if the event was created by/organized by the user's calendar
    # Find user's email from consultants config
    user_email = None
    for consultant_name, consultant_email in consultants_dict.items():
        # Match consultant name with any username variant (case-insensitive)
        consultant_name_lower = consultant_name.lower()
        for variant in username_variants:
            # Handle both "christian.mast" and "christian" formats
            variant_parts = variant.lower().split('.')
            first_name = variant_parts[0]

            if consultant_name_lower == first_name or consultant_name_lower in variant.lower():
                user_email = consultant_email
                break
        if user_email:
            break

    if user_email:
        # Check organizer
        organizer_email = event.get('organizer', {}).get('email', '')
        if user_email.lower() == organizer_email.lower():
            return (True, 'calendar', username)

        # Check creator
        creator_email = event.get('creator', {}).get('email', '')
        if user_email.lower() == creator_email.lower():
            return (True, 'calendar', username)

        # Stage 3: Attendee Match
        # Check if user's email is in the attendees list
        for attendee in event.get('attendees', []):
            if attendee.get('email', '').lower() == user_email.lower():
                return (True, 'attendee', username)

    # Stage 4: Fuzzy Match (username appears in description or location)
    # IMPORTANT: Do NOT search in summary (customer name) - that would match customers named "Christian"
    # Only search in description and location where the telefonist name should appear
    # IMPORTANT: Only search for FULL usernames (with dot) to avoid false positives
    # e.g., "christian.mast" YES, "christian" NO (would match customer names)
    description_lower = description.lower()
    location = event.get('location', '')
    location_lower = location.lower()

    for variant in username_variants:
        # Skip single-name variants (firstname only) to prevent false positives
        # "Wolf, Christian" description shouldn't match user "christian.mast"
        if '.' not in variant:
            continue

        variant_lower = variant.lower()
        # Only match whole words to reduce false positives
        # Check if variant appears as a word (with word boundaries)
        import re
        pattern = r'\b' + re.escape(variant_lower) + r'\b'
        if re.search(pattern, description_lower) or re.search(pattern, location_lower):
            return (True, 'fuzzy', variant)

    # No match found
    return (False, None, None)


def get_user_bookings_from_db(username, days_back=30, days_forward=90):
    """
    Read user's bookings from PostgreSQL database

    Args:
        username: The user to get bookings for
        days_back: How many days back to read (default: 30)
        days_forward: How many days forward to read (default: 90)

    Returns:
        List of booking dicts with customer, date, time, etc.
    """
    from datetime import date, timedelta
    import logging

    logger = logging.getLogger(__name__)

    try:
        from app.models import init_db, Booking
        from app.utils.db_utils import db_session_scope_no_commit

        # Ensure database is initialized before querying
        init_db()

        start_date = date.today() - timedelta(days=days_back)
        end_date = date.today() + timedelta(days=days_forward)

        with db_session_scope_no_commit() as session:
            # Query bookings for this user within date range (past + future)
            bookings = session.query(Booking).filter(
                Booking.username == username,
                Booking.date >= start_date,
                Booking.date <= end_date
            ).order_by(Booking.date.desc()).all()

            # Convert to dict format (same as JSONL)
            user_bookings = []
            for booking in bookings:
                user_bookings.append({
                    'id': booking.booking_id,
                    'user': booking.username,
                    'customer': booking.customer,
                    'date': booking.date.strftime('%Y-%m-%d'),
                    'time': booking.time,
                    'weekday': booking.weekday,
                    'week_number': booking.week_number,
                    'color_id': booking.color_id,
                    'potential_type': booking.potential_type,
                    'description_length': booking.description_length,
                    'has_description': booking.has_description,
                    'timestamp': booking.booking_timestamp.isoformat()
                })

        logger.debug(f"Loaded {len(user_bookings)} bookings from PostgreSQL for {username}")
        return user_bookings

    except Exception as e:
        logger.error(f"Error reading bookings from PostgreSQL: {e}")
        return []


def get_user_bookings_from_jsonl(username, days_back=30):
    """
    Read user's bookings directly from bookings.jsonl
    This is more reliable than parsing Google Calendar tags.

    Args:
        username: The user to get bookings for
        days_back: How many days back to read (default: 30)

    Returns:
        List of booking dicts with customer, date, time, etc.
    """
    import json
    import os
    from datetime import date, timedelta

    bookings_file = "data/tracking/bookings.jsonl"
    if not os.path.exists(bookings_file):
        return []

    cutoff_date = date.today() - timedelta(days=days_back)
    user_bookings = []

    try:
        with open(bookings_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    booking = json.loads(line.strip())

                    # Check if this booking belongs to the user
                    if booking.get('user') != username:
                        continue

                    # Check if booking is within date range
                    booking_date_str = booking.get('date')
                    if booking_date_str:
                        booking_date = date.fromisoformat(booking_date_str)
                        if booking_date < cutoff_date:
                            continue

                    user_bookings.append(booking)

                except (json.JSONDecodeError, ValueError) as e:
                    continue
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error reading bookings.jsonl: {e}")

    return user_bookings


def get_user_bookings(username, days_back=30, days_forward=90):
    """
    Smart wrapper: Uses PostgreSQL if enabled, falls back to JSONL

    Args:
        username: The user to get bookings for
        days_back: How many days back to read (default: 30)
        days_forward: How many days forward to read (default: 90)

    Returns:
        List of booking dicts
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        from app.models import is_postgres_enabled

        if is_postgres_enabled():
            logger.info(f"Using PostgreSQL for booking data (user: {username}, range: -{days_back} to +{days_forward} days)")
            bookings = get_user_bookings_from_db(username, days_back, days_forward)
            if bookings:  # Nur wenn Daten gefunden wurden
                return bookings
            else:
                logger.warning("PostgreSQL returned no bookings, trying JSONL fallback")
    except Exception as e:
        logger.warning(f"PostgreSQL not available, using JSONL fallback: {e}")

    # Fallback zu JSONL
    logger.info(f"Using JSONL for booking data (user: {username})")
    return get_user_bookings_from_jsonl(username, days_back)


def extract_status_from_title(title: str):
    """
    Extract status marker from event title (case-insensitive).

    Event titles have format: "Customer Name ( Status )"

    Args:
        title: Event title like "Müller, Hans ( Verschoben )"

    Returns:
        tuple: (status_marker, clean_customer_name, should_display)
        - status_marker: "erschienen", "verschoben", "ghost", etc. (lowercase)
        - clean_customer_name: "Müller, Hans" (without marker)
        - should_display: False for "Exit" events (filter out)
    """
    import re

    # Pattern: ( Status ) at end of title (case-insensitive)
    pattern = r'\s*\(\s*(Exit|Verschoben|Nicht\s+Erschienen|Ghost|Erschienen|Abgesagt|Vorbehalt)\s*\)\s*$'
    match = re.search(pattern, title, re.IGNORECASE)

    if match:
        status = match.group(1).lower().strip()
        clean_title = re.sub(pattern, '', title, flags=re.IGNORECASE).strip()

        # Filter out "Exit" events
        if status == 'exit':
            return (status, clean_title, False)

        return (status, clean_title, True)

    # No marker found → Pending
    return ('pending', title.strip(), True)


def map_status_to_column(status_marker: str) -> str:
    """
    Map status marker to kanban column name.

    Args:
        status_marker: Status from title (lowercase)

    Returns:
        Column name for kanban board
    """
    STATUS_TO_COLUMN = {
        'pending': 'pending',
        'vorbehalt': 'pending',
        'erschienen': 'erschienen',
        'abgesagt': 'abgesagt',
        'verschoben': 'verschoben',
        'nicht erschienen': 'nicht_erschienen',
        'ghost': 'ghost',
        'exit': None  # Don't display
    }

    return STATUS_TO_COLUMN.get(status_marker, 'pending')


def determine_status_from_color_and_date(color_id: str, event_date, summary: str):
    """
    Determine booking status based on Title Marker (Priority 1), Color ID, and Date.

    Priority Order:
    1. Title Marker: "( erschienen )", "( Verschoben )", "( Ghost )", etc.
    2. Color ID: Google Calendar colors (manually set)
    3. Date: Past events → Erschienen, Future → Pending

    Google Calendar Color Mapping (Fallback):
    - Tomate (11/Rot): Exit, Nicht Erschienen, Ghost
    - Mandarine (6/Orange): Abgesagt, Verschoben
    - Salbei (2/Grün Hell): Normal Potential Unbestätigt
    - Basilikum (10/Grün): Normal Potential Bestätigt
    - Pfau (9/Türkis): Top Potential Unbestätigt
    - Heidelbeere (7/Blau): Top Potential Bestätigt
    - Weintraube (3/Lila): Rückholung (als Pending)
    - Grafit (8/Grau): Verschoben (Berater-Mangel, als Pending)

    Args:
        color_id: Google Calendar Color ID (may be incorrect due to API issue)
        event_date: Date of the event
        summary: Event title with status markers

    Returns:
        Column name or None (to filter out)
    """
    from datetime import date

    today = date.today()
    is_past = event_date < today

    # 🔥 PRIORITY 1: Check title marker (most reliable - manually set in Calendar!)
    status_from_title, _, should_display = extract_status_from_title(summary)

    # Filter Exit events
    if status_from_title == 'exit' or not should_display or 'exit' in summary.lower():
        return None  # Don't display

    # If title has explicit status marker, use it! (Priority 1)
    if status_from_title in ['erschienen', 'verschoben', 'abgesagt', 'ghost', 'vorbehalt']:
        if status_from_title == 'vorbehalt':
            return 'pending'
        return status_from_title

    # Special case: "nicht erschienen" needs underscore
    if status_from_title == 'nicht erschienen':
        return 'nicht_erschienen'

    # 🔥 PRIORITY 2: Use Color ID if no title marker (fallback)
    if color_id == '11':  # Tomate (Rot) - Exit/Nicht Erschienen/Ghost
        if 'ghost' in summary.lower():
            return 'ghost'
        return 'nicht_erschienen'

    elif color_id == '6':  # Mandarine (Orange) - Abgesagt/Verschoben
        if 'verschoben' in summary.lower():
            return 'verschoben'
        return 'abgesagt'

    # 🔥 PRIORITY 3: Use Date for Potential colors (no explicit status)
    elif color_id in ['2', '10', '9', '7', '3', '8', '1']:  # All potential colors + default
        if is_past:
            return 'erschienen'  # Past event → Customer showed up
        else:
            return 'pending'  # Future event → Pending

    else:
        # Default: Use date logic
        return 'pending' if not is_past else 'erschienen'


@calendar_bp.route("/my-calendar")
@require_login
def my_calendar():
    """Display user's personal calendar view with Table and Kanban modes"""
    from datetime import datetime as dt_module, date
    from app.utils.color_mapping import get_booking_status, get_column_stats
    from app.utils.helpers import get_username_variants
    from collections import defaultdict
    import logging
    import re

    logger = logging.getLogger(__name__)
    user = session.get("user")

    # Get view mode parameter (table or kanban)
    view_mode = request.args.get('view', 'table')

    # Get user's bookings from the past 60 days and next 90 days (PostgreSQL can handle larger ranges)
    start_date = (dt_module.now(TZ) - timedelta(days=30)).strftime("%Y-%m-%d")
    end_date = (dt_module.now(TZ) + timedelta(days=30)).strftime("%Y-%m-%d")

    # 🆕 SMART APPROACH: Read bookings from PostgreSQL or JSONL (auto-detection)
    logger.info(f"MY-CALENDAR: Loading bookings for user '{user}'")
    user_bookings = get_user_bookings(user, days_back=60, days_forward=90)
    logger.info(f"MY-CALENDAR: Found {len(user_bookings)} bookings")

    # Get events from Google Calendar
    google_calendar_service = get_google_calendar_service()
    if not google_calendar_service:
        logger.warning("Google Calendar service not available")
        return render_template("my_calendar.html",
                             my_events=[],
                             kanban_columns={},
                             stats={},
                             view_mode=view_mode,
                             user=user)

    # Fetch ALL events from Google Calendar using pagination (no limit!)
    from app.config.base import config
    events_result = google_calendar_service.get_all_events_paginated(
        calendar_id=config.CENTRAL_CALENDAR_ID,
        time_min=f"{start_date}T00:00:00+01:00",
        time_max=f"{end_date}T23:59:59+01:00",
        cache_duration=300  # 5 minute cache for performance
    )

    all_calendar_events = events_result.get('items', []) if events_result else []
    total_pages = events_result.get('total_pages', 0) if events_result else 0
    logger.info(f"MY-CALENDAR: Fetched {len(all_calendar_events)} events from {total_pages} pages ({start_date} to {end_date})")

    # Create a lookup map for events by date+customer name
    event_lookup = {}
    for evt in all_calendar_events:
        summary = evt.get('summary', '')
        start_dt = evt.get('start', {}).get('dateTime', '')

        # Skip invalid events
        if not start_dt or summary.isdigit():
            continue

        try:
            dt = dt_module.fromisoformat(start_dt.replace('Z', '+00:00'))
            evt_date = dt.strftime('%Y-%m-%d')
            evt_time = dt.strftime('%H:%M')

            # Normalize summary (remove status markers for matching)
            summary_normalized = re.sub(r'\s*\([^)]*\)\s*$', '', summary).strip()

            # Create lookup keys: Name + Date ONLY (ignore time for flexibility!)
            # This allows matching even if event time changed (e.g., 20:00 → 20:15)
            keys = [
                f"{summary}_{evt_date}",  # Original + Date
                f"{summary_normalized}_{evt_date}",  # Normalized + Date (IMPORTANT!)
                f"{summary.replace(',', '')}_{evt_date}",  # No comma + Date
                f"{summary_normalized.replace(',', '')}_{evt_date}",  # Normalized + no comma + Date
            ]

            for key in keys:
                event_lookup[key.lower()] = evt

        except Exception as e:
            continue

    logger.info(f"MY-CALENDAR (NEW): Created lookup with {len(event_lookup)} keys")

    # Initialize data structures
    my_events = []
    kanban_columns = defaultdict(list)
    today = date.today()

    # Week boundaries for weekly stats
    from app.utils.helpers import get_week_start
    current_week_start = get_week_start(today)
    last_week_start = current_week_start - timedelta(weeks=1)

    # Process bookings from jsonl and enrich with Calendar event data
    for booking in user_bookings:
        customer = booking.get('customer', '')
        booking_date_str = booking.get('date', '')
        booking_time = booking.get('time', '')

        if not all([customer, booking_date_str, booking_time]):
            continue

        # Try to find matching event: Name + Date ONLY (time ignored!)
        # This matches events even if time changed (e.g., verschoben from 20:00 to 20:15)
        lookup_keys = [
            f"{customer}_{booking_date_str}".lower(),  # Name + Date
            f"{customer.replace(',', '')}_{booking_date_str}".lower(),  # No comma + Date
        ]

        calendar_event = None
        for key in lookup_keys:
            if key in event_lookup:
                calendar_event = event_lookup[key]
                break

        # If no match, use default values
        if calendar_event:
            color_id = calendar_event.get('colorId', '1')
            event_id = calendar_event.get('id', '')
            summary = calendar_event.get('summary', customer)
            description = calendar_event.get('description', '')
        else:
            # Booking exists in jsonl but not in Calendar (deleted?)
            color_id = '1'  # Default grey
            event_id = ''
            summary = customer
            description = ''
            logger.warning(f"MY-CALENDAR (NEW): Booking not found in Calendar: {customer} on {booking_date_str} {booking_time}")

        # Parse event data
        start_dt = f"{booking_date_str}T{booking_time}:00+01:00"

        if not start_dt:
            continue

        try:
            dt = dt_module.fromisoformat(start_dt.replace('Z', '+00:00'))
            event_date = dt.date()
            date_str = dt.strftime('%d.%m.%Y')
            hour_str = dt.strftime('%H:%M')
        except Exception as e:
            logger.error(f"Error parsing datetime for event '{summary}': {e}")
            continue

        # Determine status from Color ID + Date (primary) with title fallback
        column = determine_status_from_color_and_date(color_id, event_date, summary)

        # Filter out "Exit" events or unmapped status
        if column is None:
            logger.info(f"MY-CALENDAR: Filtering out event: {summary} (Exit or unmapped)")
            continue

        # Extract customer name (remove status markers if present)
        _, customer_name, _ = extract_status_from_title(summary)
        if not customer_name:
            customer_name = summary  # Fallback to full summary

        # Get status information for display (color_mapping for UI labels)
        # NOTE: Title status has priority, colorId is just for verification
        status_info = get_booking_status(color_id, summary, event_date)

        # Calculate customer_showed for compatibility
        if status_info['is_positive'] is True:
            customer_showed = True
        elif status_info['is_positive'] is False:
            customer_showed = False
        else:
            customer_showed = None  # Pending

        # Calculate week flags
        is_current_week = current_week_start <= event_date < (current_week_start + timedelta(weeks=1))
        is_last_week = last_week_start <= event_date < current_week_start

        # Calculate days ago/until
        days_diff = (today - event_date).days
        if days_diff > 0:
            days_ago = days_diff
            days_until = 0
        elif days_diff < 0:
            days_ago = 0
            days_until = abs(days_diff)
        else:
            days_ago = 0
            days_until = 0

        # Extract booked_by initials (from booking data, not from matching)
        booking_user = booking.get('user', user)
        parts = booking_user.split('.')
        if len(parts) >= 2:
            booked_by_initials = f"{parts[0][0].upper()}{parts[1][0].upper()}"
        else:
            booked_by_initials = booking_user[:2].upper()

        # Determine potential type label
        potential_map = {
            '2': 'Normal',
            '7': 'Top',
            '5': 'Sonderkunde',
            '3': 'Rückholung',
            '11': 'No-Show',
            '6': 'Verschoben',
            '9': 'Standard',
            '10': 'Standard'
        }
        potential = potential_map.get(color_id, 'Sonstiges')

        # Calculate points (for gamification)
        points = 3
        if color_id == '7':  # Top Potential
            points = 5
        elif color_id == '5':  # Sonderkunde
            points = 4
        elif color_id == '3':  # Rückholung
            points = 3
        elif color_id in ['11', '6']:  # No-Show, Verschoben
            points = 0

        # Clean description (remove booked by tag if present)
        clean_desc = description
        import re
        clean_desc = re.sub(r'\[Booked by: [^\]]+\]', '', clean_desc)
        clean_desc = clean_desc.strip() or '-'

        # Build event dict
        event_dict = {
            'id': event_id,
            'summary': summary,
            'customer_name': customer_name,
            'date': date_str,
            'hour': hour_str,
            'date_obj': event_date,
            'color_id': color_id,
            'potential': potential,
            'points': points,
            'desc': clean_desc,
            'booked_by': booking_user,
            'booked_by_initials': booked_by_initials,
            'match_reason': 'jsonl',  # Matched via bookings.jsonl (new approach)

            # Status information from color_mapping
            'status': status_info['status'],
            'status_label': status_info['label'],
            'badge_class': status_info['badge_class'],
            'row_bg_class': status_info['bg_class'],
            'status_icon': status_info['status_icon'],
            'is_positive': status_info['is_positive'],
            'column': status_info['column'],

            # Additional flags
            'customer_showed': customer_showed,
            'is_future': event_date >= today,
            'is_current_week': is_current_week,
            'is_last_week': is_last_week,
            'days_ago': days_ago,
            'days_until': days_until,
        }

        my_events.append(event_dict)

        # Add to kanban column
        kanban_columns[status_info['column']].append(event_dict)

    # Sort events by date (newest first for table view)
    my_events.sort(key=lambda x: x['date_obj'], reverse=True)

    # Sort kanban columns by date
    for column in kanban_columns.values():
        column.sort(key=lambda x: x['date_obj'], reverse=False)

    # Calculate statistics
    stats = get_column_stats(kanban_columns)

    logger.info(f"MY-CALENDAR: Found {len(my_events)} bookings for user '{user}'")
    logger.info(f"MY-CALENDAR: Stats - Total: {stats['total']}, Erschienen: {stats['erschienen']}, "
               f"No-Show: {stats['nicht_erschienen']}, Ghost: {stats['ghost']}")

    return render_template("my_calendar.html",
                         my_events=my_events,
                         kanban_columns=dict(kanban_columns),
                         stats=stats,
                         view_mode=view_mode,
                         user=user)


@calendar_bp.route("/my-customers")
@require_login
def my_customers():
    """Dashboard for telemarketers to see attendance rate of their customers"""
    from datetime import datetime as dt_module
    user = session.get("user")

    # Get user's bookings since September 1st (or 90 days back, whichever is earlier)
    september_first = datetime(2024, 9, 1).date()
    ninety_days_ago = (dt_module.now(TZ) - timedelta(days=90)).date()

    # Use the earlier date
    start_date_obj = september_first if september_first < ninety_days_ago else ninety_days_ago
    start_date = start_date_obj.strftime("%Y-%m-%d")
    end_date = (dt_module.now(TZ) + timedelta(days=30)).strftime("%Y-%m-%d")

    # Get events from Google Calendar
    google_calendar_service = get_google_calendar_service()
    if not google_calendar_service:
        return render_template("my_customers.html", customers=[], stats={}, user=user)

    from app.config.base import config
    events_result = google_calendar_service.get_all_events_paginated(
        calendar_id=config.CENTRAL_CALENDAR_ID,
        time_min=f"{start_date}T00:00:00+01:00",
        time_max=f"{end_date}T23:59:59+01:00",
        cache_duration=300  # 5 minute cache for customer analytics
    )

    all_events = events_result.get('items', []) if events_result else []

    # Filter events booked by this user and analyze outcomes
    from collections import defaultdict
    customer_data = defaultdict(lambda: {
        'name': '',
        'total': 0,
        'erschienen': 0,
        'no_show': 0,
        'cancelled': 0,
        'pending': 0,
        'events': []
    })

    outcome_map = {
        '2': 'erschienen',      # Sage/Green - Normal
        '7': 'erschienen',      # Peacock/Türkis - Top
        '11': 'no_show',        # Tomate/Red - No Show
        '6': 'cancelled',       # Mandarine/Orange - Cancelled
        '5': 'pending',         # Banana/Yellow - Closer needed (pending)
    }

    # Get all possible username variants for backward compatibility
    from app.utils.helpers import get_username_variants
    username_variants = get_username_variants(user)

    for event in all_events:
        description = event.get('description', '')

        # Only events booked by this user - check all username variants
        is_booked_by_user = False
        for variant in username_variants:
            booked_by_tag = f"[Booked by: {variant}]"
            if booked_by_tag in description:
                is_booked_by_user = True
                break

        if not is_booked_by_user:
            continue

        summary = event.get('summary', '').strip()
        if not summary:
            continue

        # Parse customer name (format: "Nachname, Vorname")
        customer_name = summary

        color_id = event.get('colorId', '1')
        outcome = outcome_map.get(color_id, 'pending')

        # Get event time
        start_dt = event.get('start', {}).get('dateTime', '')
        event_date = ''
        if start_dt:
            try:
                dt = dt_module.fromisoformat(start_dt.replace('Z', '+00:00'))
                event_date = dt.strftime('%d.%m.%Y')
            except:
                pass

        # Track customer stats
        customer_data[customer_name]['name'] = customer_name
        customer_data[customer_name]['total'] += 1
        customer_data[customer_name][outcome] += 1
        customer_data[customer_name]['events'].append({
            'date': event_date,
            'outcome': outcome,
            'color_id': color_id
        })

    # Calculate attendance rates
    customers = []
    for customer_name, data in customer_data.items():
        total = data['total']
        erschienen = data['erschienen']
        no_show = data['no_show']
        cancelled = data['cancelled']
        pending = data['pending']

        # Calculate rate (only from completed outcomes)
        completed = erschienen + no_show + cancelled
        attendance_rate = (erschienen / completed * 100) if completed > 0 else 0
        no_show_rate = (no_show / completed * 100) if completed > 0 else 0

        customers.append({
            'name': customer_name,
            'total': total,
            'erschienen': erschienen,
            'no_show': no_show,
            'cancelled': cancelled,
            'pending': pending,
            'attendance_rate': round(attendance_rate, 1),
            'no_show_rate': round(no_show_rate, 1),
            'events': data['events']
        })

    # Sort by total appointments descending
    customers.sort(key=lambda x: x['total'], reverse=True)

    # Calculate overall stats
    total_customers = len(customers)
    total_appointments = sum(c['total'] for c in customers)
    total_erschienen = sum(c['erschienen'] for c in customers)
    total_no_show = sum(c['no_show'] for c in customers)
    total_cancelled = sum(c['cancelled'] for c in customers)
    total_pending = sum(c['pending'] for c in customers)

    completed_total = total_erschienen + total_no_show + total_cancelled
    overall_attendance_rate = (total_erschienen / completed_total * 100) if completed_total > 0 else 0
    overall_no_show_rate = (total_no_show / completed_total * 100) if completed_total > 0 else 0

    stats = {
        'total_customers': total_customers,
        'total_appointments': total_appointments,
        'total_erschienen': total_erschienen,
        'total_no_show': total_no_show,
        'total_cancelled': total_cancelled,
        'total_pending': total_pending,
        'overall_attendance_rate': round(overall_attendance_rate, 1),
        'overall_no_show_rate': round(overall_no_show_rate, 1)
    }

    return render_template("my_customers.html", customers=customers, stats=stats, user=user)


@calendar_bp.route("/calendar-view")
@require_login
def calendar_view():
    """Display full calendar view with actual availability data"""
    # Get data for calendar view
    today = datetime.now(TZ).date()

    # Get week parameter from request (for navigation)
    week_param = request.args.get('week')
    if week_param:
        try:
            # Parse week parameter (format: YYYY-MM-DD)
            current_week = datetime.strptime(week_param, '%Y-%m-%d').date()
            # Ensure it's a Monday
            current_week = current_week - timedelta(days=current_week.weekday())
        except ValueError:
            # Fall back to current week if invalid date
            from app.utils.helpers import get_week_start
            current_week = get_week_start(today)
    else:
        # Calculate week navigation
        from app.utils.helpers import get_week_start
        current_week = get_week_start(today)

    prev_week = current_week - timedelta(weeks=1)
    next_week = current_week + timedelta(weeks=1)

    # Generate week dates for template
    week_start = current_week
    week_end = current_week + timedelta(days=6)

    # Load availability data from persistent storage
    availability_data = {}
    # Try persistent storage first
    availability_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'persistent', 'availability.json')

    # Fallback to old location
    if not os.path.exists(availability_path):
        availability_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'static', 'availability.json')

    try:
        with open(availability_path, 'r', encoding='utf-8') as f:
            availability_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        availability_data = {}

    # Generate weekdays data for calendar display
    from app.services.holiday_service import holiday_service

    weekdays_data = []
    for i in range(7):
        day = current_week + timedelta(days=i)

        # Skip blocked dates - show as empty
        if holiday_service.is_blocked_date(day):
            weekdays_data.append({
                'date': day,
                'name': day.strftime('%A'),
                'is_today': day == today,
                'availability': []
            })
            continue

        day_availability = []

        # Process availability for this day
        for time_slot, consultants in availability_data.items():
            if time_slot.startswith(day.strftime('%Y-%m-%d')):
                # Extract time from slot key (format: "2025-09-22 20:00")
                time_part = time_slot.split(' ')[1]
                start_time = datetime.strptime(f"{day.strftime('%Y-%m-%d')} {time_part}", '%Y-%m-%d %H:%M')
                end_time = start_time + timedelta(hours=2)  # 2-hour blocks

                # Determine availability level based on consultant count
                slot_count = len(consultants)
                if slot_count >= 4:
                    availability_level = 'high'
                elif slot_count >= 1:
                    availability_level = 'medium'
                else:
                    availability_level = 'none'

                day_availability.append({
                    'time': time_part,
                    'start_time': start_time,
                    'end_time': end_time,
                    'slot_count': slot_count,
                    'available_consultants': consultants,
                    'availability_level': availability_level
                })

        weekdays_data.append({
            'date': day,
            'name': day.strftime('%A'),
            'is_today': day == today,
            'availability': day_availability
        })

    return render_template("slots/calendar_view.html",
                         today=today,
                         availability=availability_data,
                         prev_week=prev_week,
                         next_week=next_week,
                         current_week=current_week,
                         week_start=week_start,
                         week_end=week_end,
                         weekdays_data=weekdays_data,
                         calendar_week=current_week.isocalendar()[1])


# ============================================================================
# MY CALENDAR - PHASE 2 API ENDPOINTS (Drag & Drop, Reschedule)
# ============================================================================

@calendar_bp.route('/api/update-event-status', methods=['POST'])
@require_login
def api_update_event_status():
    """
    Update event status via drag & drop (changes color in Google Calendar)

    Request JSON:
        {
            "event_id": "abc123",
            "new_status": "erschienen" | "ghost" | "verschoben" | etc.
        }

    Returns:
        {"success": True, "message": "Status updated"}
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        data = request.get_json()
        event_id = data.get('event_id')
        new_status = data.get('new_status')
        user = session.get('user')

        if not event_id or not new_status:
            return jsonify({'success': False, 'error': 'Missing event_id or new_status'}), 400

        # Map status to Google Calendar colorId
        status_to_color = {
            'pending': '1',         # Lavendel (future events)
            'erschienen': '2',      # Grün (appeared)
            'rückholung': '3',      # Weintraube (recall)
            'sonderkunde': '5',     # Gelb (special customer)
            'verschoben': '6',      # Orange (rescheduled/cancelled)
            'nicht_erschienen': '11', # Rot (no-show)
            'ghost': '11'           # Rot (ghost - will add marker to title)
        }

        color_id = status_to_color.get(new_status)
        if not color_id:
            return jsonify({'success': False, 'error': f'Invalid status: {new_status}'}), 400

        # Get Google Calendar service
        calendar_service = get_google_calendar_service()
        if not calendar_service:
            return jsonify({'success': False, 'error': 'Calendar service not available'}), 503

        from app.config.base import config

        # Get event to check permissions and preserve [Booked by:] tag
        try:
            event = calendar_service.service.events().get(
                calendarId=config.CENTRAL_CALENDAR_ID,
                eventId=event_id
            ).execute()
        except Exception as e:
            logger.error(f"Error fetching event {event_id}: {e}")
            return jsonify({'success': False, 'error': 'Event not found'}), 404

        # Preserve [Booked by:] tag from description
        current_description = event.get('description', '')
        booked_by_tag = None

        if '[Booked by:' in current_description:
            # Extract the tag to preserve it
            tag_start = current_description.find('[Booked by:')
            tag_end = current_description.find(']', tag_start)
            if tag_end != -1:
                booked_by_tag = current_description[tag_start:tag_end+1]
                logger.info(f"MY-CALENDAR: Preserving tag: {booked_by_tag}")

        # Update event color
        update_body = {'colorId': color_id}

        # Special handling for "ghost" status - add marker to summary
        if new_status == 'ghost':
            current_summary = event.get('summary', '')
            if '( Ghost )' not in current_summary and '(Ghost)' not in current_summary:
                # Remove other status markers first
                clean_summary = current_summary
                for marker in [' ( Verschoben )', ' (Verschoben)', ' ( Abgesagt )', ' (Abgesagt)',
                              ' ( nicht erschienen )', ' (nicht erschienen)', ' ( erschienen )', ' (erschienen)']:
                    clean_summary = clean_summary.replace(marker, '')
                update_body['summary'] = f"{clean_summary.strip()} ( Ghost )"

        # If we have a booked_by_tag and we're not setting a new description, preserve it
        if booked_by_tag and 'description' not in update_body:
            # Keep the original description with the tag intact
            update_body['description'] = current_description

        # Execute update
        try:
            calendar_service.service.events().patch(
                calendarId=config.CENTRAL_CALENDAR_ID,
                eventId=event_id,
                body=update_body
            ).execute()

            logger.info(f"MY-CALENDAR: Status updated for event {event_id} to {new_status} by {user}")

            # Invalidate cache
            from app.core.extensions import cache_manager
            cache_manager.clear_pattern('calendar_events_*')

            return jsonify({
                'success': True,
                'message': f'Status updated to {new_status}',
                'new_color_id': color_id
            })

        except Exception as e:
            logger.error(f"Error updating event {event_id}: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    except Exception as e:
        logger.error(f"API error in update-event-status: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@calendar_bp.route('/api/get-available-slots', methods=['GET'])
@require_login
def api_get_available_slots():
    """
    Get available time slots for a specific date (for reschedule modal)

    Query params:
        date: YYYY-MM-DD (optional, defaults to tomorrow)

    Returns:
        {
            "success": True,
            "date": "2025-10-26",
            "slots": [
                {"time": "14:00", "consultants": ["christian.mast", "luke.hoppe"], "count": 2},
                ...
            ]
        }
    """
    import logging
    from datetime import datetime as dt_module, date as date_class
    from app.services.booking_service import get_effective_availability

    logger = logging.getLogger(__name__)

    try:
        # Get date parameter or use tomorrow
        date_param = request.args.get('date')
        if date_param:
            try:
                check_date = dt_module.strptime(date_param, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'success': False, 'error': 'Invalid date format (use YYYY-MM-DD)'}), 400
        else:
            check_date = dt_module.now(TZ).date() + timedelta(days=1)

        # Get availability for common time slots
        time_slots = ['09:00', '11:00', '14:00', '16:00', '18:00', '20:00']
        available_slots = []

        date_str = check_date.strftime('%Y-%m-%d')

        for time_slot in time_slots:
            consultants = get_effective_availability(date_str, time_slot)

            if consultants:  # Only include slots with availability
                available_slots.append({
                    'time': time_slot,
                    'consultants': consultants,
                    'count': len(consultants)
                })

        return jsonify({
            'success': True,
            'date': date_str,
            'slots': available_slots
        })

    except Exception as e:
        logger.error(f"API error in get-available-slots: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@calendar_bp.route('/api/reschedule-booking', methods=['POST'])
@require_login
def api_reschedule_booking():
    """
    Reschedule a booking (mark old as verschoben, create new)

    Request JSON:
        {
            "old_event_id": "abc123",
            "customer_name": "Müller, Hans",
            "new_date": "2025-10-26",
            "new_time": "14:00",
            "consultant": "christian.mast",  # optional, auto-select if empty
            "note": "Kunde hat angerufen",   # optional
            "reason": "customer"             # optional: "customer" (Verschoben) or "overhang" (Überhang)
        }

    Returns:
        {"success": True, "new_event_id": "xyz789", "message": "..."}
    """
    import logging
    from datetime import datetime as dt_module
    from app.services.booking_service import book_slot_for_user, get_effective_availability

    logger = logging.getLogger(__name__)

    try:
        data = request.get_json()
        old_event_id = data.get('old_event_id')
        customer_name = data.get('customer_name')
        new_date = data.get('new_date')
        new_time = data.get('new_time')
        consultant = data.get('consultant', '')
        note = data.get('note', '')
        reason = data.get('reason', 'customer')  # "customer" or "overhang"
        user = session.get('user')

        # Validation
        if not all([old_event_id, customer_name, new_date, new_time]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400

        # Parse customer name (format: "Nachname, Vorname" or "Vorname Nachname")
        if ',' in customer_name:
            parts = customer_name.split(',', 1)
            last_name = parts[0].strip()
            first_name = parts[1].strip() if len(parts) > 1 else ''
        else:
            parts = customer_name.split(' ', 1)
            first_name = parts[0].strip()
            last_name = parts[1].strip() if len(parts) > 1 else ''

        # Auto-select consultant if not provided
        if not consultant:
            available_consultants = get_effective_availability(new_date, new_time)
            if not available_consultants:
                return jsonify({'success': False, 'error': f'No availability at {new_date} {new_time}'}), 400
            consultant = available_consultants[0]  # Pick first available

        # Step 1: Mark old event as "Verschoben"
        calendar_service = get_google_calendar_service()
        if calendar_service:
            try:
                from app.config.base import config

                # Get old event
                old_event = calendar_service.service.events().get(
                    calendarId=config.CENTRAL_CALENDAR_ID,
                    eventId=old_event_id
                ).execute()

                # Update to verschoben or überhang based on reason
                old_summary = old_event.get('summary', '')
                if reason == 'overhang':
                    status_marker = '( Überhang )'
                    log_label = 'überhang'
                else:
                    status_marker = '( Verschoben )'
                    log_label = 'verschoben'

                if status_marker not in old_summary and '( Verschoben )' not in old_summary and '( Überhang )' not in old_summary:
                    new_summary = f"{old_summary.strip()} {status_marker}"
                else:
                    new_summary = old_summary

                calendar_service.service.events().patch(
                    calendarId=config.CENTRAL_CALENDAR_ID,
                    eventId=old_event_id,
                    body={
                        'colorId': '6',  # Orange
                        'summary': new_summary
                    }
                ).execute()

                logger.info(f"MY-CALENDAR: Marked old event {old_event_id} as {log_label} by {user}")

            except Exception as e:
                logger.warning(f"Could not update old event {old_event_id}: {e}")
                # Continue anyway

        # Step 2: Book new slot
        reschedule_note = f"Umbuchung von altem Termin.\n{note}" if note else "Umbuchung von altem Termin."

        booking_result = book_slot_for_user(
            user=user,
            date_str=new_date,
            time_str=new_time,
            berater=consultant,
            first_name=first_name,
            last_name=last_name,
            description=reschedule_note,
            color_id='2'  # Normal (Grün) for new booking
        )

        if booking_result.get('success'):
            logger.info(f"MY-CALENDAR: Rescheduled booking for {customer_name} to {new_date} {new_time} by {user}")

            # Invalidate cache
            from app.core.extensions import cache_manager
            cache_manager.clear_pattern('calendar_events_*')

            return jsonify({
                'success': True,
                'message': f'Termin erfolgreich umgebucht auf {new_date} {new_time}',
                'new_event_id': booking_result.get('event_id'),
                'consultant': consultant
            })
        else:
            return jsonify({
                'success': False,
                'error': booking_result.get('error', 'Booking failed')
            }), 400

    except Exception as e:
        logger.error(f"API error in reschedule-booking: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500