# -*- coding: utf-8 -*-
"""
Standardized Error Handling für Slot Booking Webapp
Konsistente Error-Responses und zentrale Exception-Behandlung
"""

import traceback
from datetime import datetime
from typing import Dict, Any, Optional, Union
from flask import jsonify, flash, redirect, url_for, Response
from enum import Enum

class ErrorType(Enum):
    """Standardisierte Error-Kategorien"""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication" 
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    EXTERNAL_SERVICE = "external_service"
    DATABASE = "database"
    CALENDAR_API = "calendar_api"
    INTERNAL = "internal"
    RATE_LIMIT = "rate_limit"
    CONFIGURATION = "configuration"

class ErrorSeverity(Enum):
    """Error-Schweregrade"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AppError(Exception):
    """Basis-Exception für alle Anwendungsfehler"""
    
    def __init__(
        self, 
        message: str,
        error_type: ErrorType = ErrorType.INTERNAL,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.severity = severity
        self.details = details or {}
        self.user_message = user_message or message
        self.timestamp = datetime.now()
        self.stack_trace = traceback.format_exc()

class ValidationError(AppError):
    """Validierungsfehler"""
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        super().__init__(
            message, 
            error_type=ErrorType.VALIDATION,
            severity=ErrorSeverity.LOW,
            **kwargs
        )
        if field:
            self.details["field"] = field

class CalendarAPIError(AppError):
    """Google Calendar API Fehler"""
    def __init__(self, message: str, status_code: Optional[int] = None, **kwargs):
        super().__init__(
            message,
            error_type=ErrorType.CALENDAR_API,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )
        if status_code:
            self.details["status_code"] = status_code

class ExternalServiceError(AppError):
    """Externer Service Fehler"""
    def __init__(self, service: str, message: str, **kwargs):
        super().__init__(
            f"{service}: {message}",
            error_type=ErrorType.EXTERNAL_SERVICE,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )
        self.details["service"] = service

class ErrorHandler:
    """Zentrale Error-Behandlung"""
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialisiere Error-Handler für Flask-App"""
        @app.errorhandler(AppError)
        def handle_app_error(error: AppError):
            return self.handle_error(error)
        
        @app.errorhandler(404)
        def handle_not_found(error):
            return self.handle_http_error(404, "Seite nicht gefunden")
        
        @app.errorhandler(500)
        def handle_internal_error(error):
            return self.handle_http_error(500, "Interner Serverfehler")
    
    def handle_error(self, error: AppError) -> Union[Response, str]:
        """Behandle AppError"""
        # Log error (hier würde normalerweise ein Logger verwendet)
        print(f"[{error.severity.value.upper()}] {error.error_type.value}: {error.message}")
        
        if error.details:
            print(f"Details: {error.details}")
        
        # Return appropriate response based on request type
        from flask import request
        if request.is_json or 'application/json' in request.headers.get('Accept', ''):
            return self.json_error_response(error)
        else:
            return self.flash_error_response(error)
    
    def json_error_response(self, error: AppError) -> Response:
        """JSON Error Response"""
        response_data = {
            "error": True,
            "type": error.error_type.value,
            "severity": error.severity.value,
            "message": error.user_message,
            "timestamp": error.timestamp.isoformat(),
            "details": error.details
        }
        
        # Status Code basierend auf Error-Typ
        status_codes = {
            ErrorType.VALIDATION: 400,
            ErrorType.AUTHENTICATION: 401,
            ErrorType.AUTHORIZATION: 403,
            ErrorType.NOT_FOUND: 404,
            ErrorType.RATE_LIMIT: 429,
            ErrorType.EXTERNAL_SERVICE: 502,
            ErrorType.CALENDAR_API: 502,
            ErrorType.DATABASE: 500,
            ErrorType.CONFIGURATION: 500,
            ErrorType.INTERNAL: 500
        }
        
        status_code = status_codes.get(error.error_type, 500)
        return jsonify(response_data), status_code
    
    def flash_error_response(self, error: AppError) -> str:
        """Flash-Message Error Response mit Redirect"""
        # Flash-Kategorien basierend auf Schweregrad
        flash_categories = {
            ErrorSeverity.LOW: "info",
            ErrorSeverity.MEDIUM: "warning", 
            ErrorSeverity.HIGH: "danger",
            ErrorSeverity.CRITICAL: "danger"
        }
        
        category = flash_categories.get(error.severity, "danger")
        flash(error.user_message, category)
        
        # Redirect basierend auf Error-Typ
        if error.error_type == ErrorType.AUTHENTICATION:
            return redirect(url_for("login"))
        elif error.error_type == ErrorType.AUTHORIZATION:
            return redirect(url_for("index"))
        else:
            # Default redirect oder zurück zur vorherigen Seite
            from flask import request
            return redirect(request.referrer or url_for("index"))
    
    def handle_http_error(self, status_code: int, message: str) -> Response:
        """Handle HTTP-Errors"""
        from flask import request
        
        # Für API-Requests (die mit /api/ beginnen) oder AJAX-Requests nur JSON zurückgeben
        is_api_request = request.path.startswith('/api/') or request.is_json or 'XMLHttpRequest' in request.headers.get('X-Requested-With', '')
        
        if status_code == 404:
            error_type = ErrorType.NOT_FOUND
        else:
            error_type = ErrorType.INTERNAL
            
        error = AppError(
            message=f"HTTP {status_code}: {message}",
            error_type=error_type,
            severity=ErrorSeverity.MEDIUM,
            user_message=message
        )
        
        # Für API/AJAX-Requests immer JSON Response, keine Flash Messages
        if is_api_request:
            return self.json_error_response(error)
        else:
            return self.handle_error(error)

# Convenience functions für häufige Error-Patterns
def raise_validation_error(message: str, field: Optional[str] = None, user_message: Optional[str] = None):
    """Raise standardized validation error"""
    raise ValidationError(
        message=message,
        field=field,
        user_message=user_message or f"Validierungsfehler: {message}"
    )

def raise_calendar_error(message: str, status_code: Optional[int] = None):
    """Raise standardized calendar API error"""
    user_msg = "Fehler beim Zugriff auf den Kalender. Bitte versuchen Sie es später erneut."
    raise CalendarAPIError(
        message=message,
        status_code=status_code,
        user_message=user_msg
    )

def raise_auth_error(message: str = "Zugriff verweigert"):
    """Raise standardized authorization error"""
    raise AppError(
        message=message,
        error_type=ErrorType.AUTHORIZATION,
        severity=ErrorSeverity.MEDIUM,
        user_message="Sie haben keine Berechtigung für diese Aktion."
    )

def safe_execute(func, *args, **kwargs):
    """Sichere Ausführung mit standardisiertem Error-Handling"""
    try:
        return func(*args, **kwargs)
    except AppError:
        # Re-raise unsere eigenen Errors
        raise
    except Exception as e:
        # Wrap unbekannte Exceptions
        raise AppError(
            message=f"Unerwarteter Fehler in {func.__name__}: {str(e)}",
            error_type=ErrorType.INTERNAL,
            severity=ErrorSeverity.HIGH,
            details={"function": func.__name__, "args": str(args)},
            user_message="Ein unerwarteter Fehler ist aufgetreten. Das Entwicklungsteam wurde benachrichtigt."
        )

# Globaler Error-Handler
error_handler = ErrorHandler()