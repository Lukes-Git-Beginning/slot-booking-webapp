# -*- coding: utf-8 -*-
"""
Test Utilities and Helper Functions
Common functions used across multiple test files.
"""

import json
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional


# ========== ASSERTION HELPERS ==========

def assert_valid_response_json(response, expected_status: int = 200):
    """
    Assert response is valid JSON with expected status code

    Args:
        response: Flask test response
        expected_status: Expected HTTP status code

    Returns:
        Parsed JSON data
    """
    assert response.status_code == expected_status, \
        f"Expected {expected_status}, got {response.status_code}: {response.data}"

    assert response.content_type == 'application/json', \
        f"Expected JSON, got {response.content_type}"

    data = json.loads(response.data)
    return data


def assert_success_response(response, expected_keys: Optional[List[str]] = None):
    """
    Assert response is successful JSON with 'success': True

    Args:
        response: Flask test response
        expected_keys: Optional list of keys that should exist in response

    Returns:
        Parsed JSON data
    """
    data = assert_valid_response_json(response, 200)

    assert 'success' in data, "Response missing 'success' field"
    assert data['success'] is True, f"Expected success=True, got {data.get('success')}"

    if expected_keys:
        for key in expected_keys:
            assert key in data, f"Response missing expected key: {key}"

    return data


def assert_error_response(response, expected_status: int = 400,
                         error_message_contains: Optional[str] = None):
    """
    Assert response is error JSON with 'success': False

    Args:
        response: Flask test response
        expected_status: Expected error status code (default: 400)
        error_message_contains: Optional substring expected in error message

    Returns:
        Parsed JSON data
    """
    data = assert_valid_response_json(response, expected_status)

    assert 'success' in data, "Error response missing 'success' field"
    assert data['success'] is False, f"Expected success=False, got {data.get('success')}"

    assert 'error' in data, "Error response missing 'error' field"

    if error_message_contains:
        error_msg = data['error'].lower()
        assert error_message_contains.lower() in error_msg, \
            f"Expected '{error_message_contains}' in error message, got: {data['error']}"

    return data


def assert_redirect(response, expected_location: str):
    """
    Assert response is redirect to expected location

    Args:
        response: Flask test response
        expected_location: Expected redirect URL (can be partial)
    """
    assert response.status_code == 302, \
        f"Expected redirect (302), got {response.status_code}"

    assert 'Location' in response.headers, "Redirect missing Location header"

    location = response.headers['Location']
    assert expected_location in location, \
        f"Expected redirect to '{expected_location}', got '{location}'"


def assert_requires_auth(response):
    """
    Assert response requires authentication (302 redirect or 401)

    Args:
        response: Flask test response
    """
    assert response.status_code in [302, 401], \
        f"Expected auth required (302 or 401), got {response.status_code}"

    if response.status_code == 302:
        # Should redirect to login
        assert 'login' in response.headers.get('Location', '').lower(), \
            f"Expected redirect to login, got {response.headers.get('Location')}"


# ========== DATE/TIME HELPERS ==========

def get_test_date(days_from_now: int = 0) -> str:
    """
    Get test date string in YYYY-MM-DD format

    Args:
        days_from_now: Number of days from today (positive for future, negative for past)

    Returns:
        Date string in YYYY-MM-DD format
    """
    target_date = date.today() + timedelta(days=days_from_now)
    return target_date.strftime('%Y-%m-%d')


def get_test_datetime(hours_from_now: int = 0) -> str:
    """
    Get test datetime string in ISO format

    Args:
        hours_from_now: Number of hours from now

    Returns:
        Datetime string in ISO format
    """
    target_dt = datetime.now() + timedelta(hours=hours_from_now)
    return target_dt.isoformat()


def is_valid_iso_datetime(dt_string: str) -> bool:
    """
    Check if string is valid ISO datetime

    Args:
        dt_string: Datetime string to validate

    Returns:
        True if valid ISO datetime
    """
    try:
        datetime.fromisoformat(dt_string)
        return True
    except (ValueError, TypeError):
        return False


def is_weekday(date_str: str) -> bool:
    """
    Check if date string is a weekday (Monday-Friday)

    Args:
        date_str: Date string in YYYY-MM-DD format

    Returns:
        True if weekday
    """
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    return dt.weekday() < 5  # 0=Monday, 4=Friday


# ========== DATA GENERATION HELPERS ==========

def generate_booking_data(
    customer_name: str = "Test Customer",
    date_str: Optional[str] = None,
    time_str: str = "14:00",
    **kwargs
) -> Dict[str, Any]:
    """
    Generate booking data dictionary for testing

    Args:
        customer_name: Customer name
        date_str: Booking date (defaults to tomorrow)
        time_str: Booking time
        **kwargs: Additional booking fields

    Returns:
        Booking data dictionary
    """
    if date_str is None:
        date_str = get_test_date(days_from_now=1)

    booking = {
        'customer_name': customer_name,
        'date': date_str,
        'time': time_str,
        'consultant': kwargs.get('consultant', 'Test Consultant'),
        'notes': kwargs.get('notes', ''),
        'phone': kwargs.get('phone', '+49123456789'),
        'email': kwargs.get('email', 'test@example.com')
    }

    # Add any extra fields
    booking.update(kwargs)

    return booking


def generate_t2_booking_data(
    customer_name: str = "Mustermann, Max",
    date_str: Optional[str] = None,
    time_str: str = "14:00",
    coach: str = "Alex",
    berater: str = "Christian",
    **kwargs
) -> Dict[str, Any]:
    """
    Generate T2 booking data dictionary for testing

    Args:
        customer_name: Customer name
        date_str: Booking date (defaults to 2 weeks from now)
        time_str: Booking time
        coach: Coach name
        berater: Berater name
        **kwargs: Additional booking fields

    Returns:
        T2 booking data dictionary
    """
    if date_str is None:
        date_str = get_test_date(days_from_now=14)

    booking = {
        'first_name': customer_name.split(',')[1].strip() if ',' in customer_name else customer_name,
        'last_name': customer_name.split(',')[0].strip() if ',' in customer_name else 'Mustermann',
        'email': kwargs.get('email', 'max@example.com'),
        'phone': kwargs.get('phone', '+49123456789'),
        'topic': kwargs.get('topic', 'Verkaufsgespräch'),
        'date': date_str,
        'time': time_str,
        'coach': coach,
        'berater': berater,
        'notes': kwargs.get('notes', '')
    }

    # Add any extra fields
    booking.update(kwargs)

    return booking


def generate_user_data(
    username: str = "test_user",
    points: int = 100,
    level: int = 5,
    badges: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Generate user data dictionary for testing

    Args:
        username: Username
        points: User points
        level: User level
        badges: List of badge IDs

    Returns:
        User data dictionary
    """
    if badges is None:
        badges = ['first_booking', 'streak_3']

    return {
        'username': username,
        'points': points,
        'level': level,
        'badges': badges,
        'total_bookings': len(badges) * 10,
        'streak_days': 3,
        'last_booking': get_test_datetime(hours_from_now=-24)
    }


# ========== SESSION HELPERS ==========

def create_test_session(client, username: str = "test_user", is_admin: bool = False):
    """
    Create test session for client

    Args:
        client: Flask test client
        username: Username to set in session
        is_admin: Whether user is admin
    """
    with client.session_transaction() as sess:
        sess['user'] = username
        sess['logged_in'] = True
        sess['is_admin'] = is_admin
        sess['last_activity'] = datetime.now().isoformat()
        sess['is_champion'] = False


def clear_test_session(client):
    """
    Clear test session

    Args:
        client: Flask test client
    """
    with client.session_transaction() as sess:
        sess.clear()


def get_session_data(client) -> Dict[str, Any]:
    """
    Get current session data

    Args:
        client: Flask test client

    Returns:
        Session data dictionary
    """
    with client.session_transaction() as sess:
        return dict(sess)


# ========== MOCK HELPERS ==========

def configure_mock_service(mock_obj, **methods):
    """
    Configure mock service with return values

    Args:
        mock_obj: Mock object to configure
        **methods: Method names and their return values

    Example:
        configure_mock_service(mock_service,
                             get_data={"key": "value"},
                             save_data=True)
    """
    for method_name, return_value in methods.items():
        getattr(mock_obj, method_name).return_value = return_value


def assert_mock_called_with(mock_obj, method_name: str, **expected_kwargs):
    """
    Assert mock method was called with expected kwargs

    Args:
        mock_obj: Mock object
        method_name: Method name to check
        **expected_kwargs: Expected keyword arguments
    """
    method = getattr(mock_obj, method_name)
    assert method.called, f"{method_name} was not called"

    call_kwargs = method.call_args[1]
    for key, expected_value in expected_kwargs.items():
        assert key in call_kwargs, f"Expected kwarg '{key}' not found in call"
        assert call_kwargs[key] == expected_value, \
            f"Expected {key}={expected_value}, got {call_kwargs[key]}"


# ========== VALIDATION HELPERS ==========

def is_valid_booking_id(booking_id: str, prefix: str = "T1") -> bool:
    """
    Validate booking ID format

    Args:
        booking_id: Booking ID to validate
        prefix: Expected prefix (T1 or T2)

    Returns:
        True if valid format
    """
    if not booking_id or not isinstance(booking_id, str):
        return False

    # Format: T1-YYYYMMDD-HHMMSS or T2-ABCDEF
    if not booking_id.startswith(f"{prefix}-"):
        return False

    return len(booking_id) > 3


def is_valid_email(email: str) -> bool:
    """
    Basic email validation

    Args:
        email: Email to validate

    Returns:
        True if valid email format
    """
    if not email or '@' not in email:
        return False

    parts = email.split('@')
    return len(parts) == 2 and '.' in parts[1]


def is_valid_time_slot(time_str: str) -> bool:
    """
    Validate time slot format

    Args:
        time_str: Time string to validate (HH:MM format)

    Returns:
        True if valid time format
    """
    try:
        datetime.strptime(time_str, '%H:%M')
        return True
    except ValueError:
        return False


# ========== FILE HELPERS ==========

def load_json_file(file_path: str) -> Dict[str, Any]:
    """
    Load JSON file and return data

    Args:
        file_path: Path to JSON file

    Returns:
        Parsed JSON data
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json_file(file_path: str, data: Dict[str, Any]):
    """
    Save data to JSON file

    Args:
        file_path: Path to JSON file
        data: Data to save
    """
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ========== CALENDAR EVENT HELPERS ==========

def create_calendar_event(
    summary: str = "Test Event",
    start_datetime: Optional[str] = None,
    end_datetime: Optional[str] = None,
    event_id: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create Google Calendar event dictionary for testing

    Args:
        summary: Event summary/title
        start_datetime: Start datetime (ISO format)
        end_datetime: End datetime (ISO format)
        event_id: Event ID
        **kwargs: Additional event fields

    Returns:
        Calendar event dictionary
    """
    if start_datetime is None:
        start_datetime = get_test_datetime(hours_from_now=24)

    if end_datetime is None:
        start_dt = datetime.fromisoformat(start_datetime)
        end_dt = start_dt + timedelta(hours=2)
        end_datetime = end_dt.isoformat()

    event = {
        'id': event_id or f'event-{datetime.now().timestamp()}',
        'summary': summary,
        'start': {'dateTime': start_datetime},
        'end': {'dateTime': end_datetime},
        'colorId': kwargs.get('colorId', '1'),
        'description': kwargs.get('description', ''),
        'status': kwargs.get('status', 'confirmed')
    }

    # Add any extra fields
    event.update(kwargs)

    return event


# ========== STATISTICS HELPERS ==========

def calculate_success_rate(successful: int, total: int) -> float:
    """
    Calculate success rate percentage

    Args:
        successful: Number of successful items
        total: Total number of items

    Returns:
        Success rate as percentage (0-100)
    """
    if total == 0:
        return 0.0
    return round((successful / total) * 100, 2)


def calculate_average(values: List[float]) -> float:
    """
    Calculate average of values

    Args:
        values: List of numeric values

    Returns:
        Average value
    """
    if not values:
        return 0.0
    return round(sum(values) / len(values), 2)


# ========== DEBUGGING HELPERS ==========

def print_response_debug(response, label: str = "Response"):
    """
    Print response details for debugging

    Args:
        response: Flask test response
        label: Label for debug output
    """
    print(f"\n========== {label} ==========")
    print(f"Status: {response.status_code}")
    print(f"Content-Type: {response.content_type}")

    if response.content_type == 'application/json':
        try:
            data = json.loads(response.data)
            print(f"Data: {json.dumps(data, indent=2, ensure_ascii=False)}")
        except json.JSONDecodeError:
            print(f"Data (raw): {response.data}")
    else:
        print(f"Data: {response.data[:200]}...")  # First 200 chars

    print("=" * 40)


def print_session_debug(client, label: str = "Session"):
    """
    Print session data for debugging

    Args:
        client: Flask test client
        label: Label for debug output
    """
    print(f"\n========== {label} ==========")
    with client.session_transaction() as sess:
        for key, value in sess.items():
            print(f"{key}: {value}")
    print("=" * 40)
