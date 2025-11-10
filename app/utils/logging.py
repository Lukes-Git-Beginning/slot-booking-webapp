# -*- coding: utf-8 -*-
"""
Structured Logging für Slot Booking Webapp
Konsistente, strukturierte Logs mit verschiedenen Levels und Kontextinformationen
"""

import logging
import json
import time
import sys
from datetime import datetime
from typing import Dict, Any, Optional, Union, List
from contextlib import contextmanager
from functools import wraps
import traceback
from app.config.legacy_config import logging_config

class StructuredFormatter(logging.Formatter):
    """Custom Formatter für strukturierte Logs"""
    
    def format(self, record):
        # Basis-Log-Objekt
        log_obj = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Extra-Felder hinzufügen (falls vorhanden)
        if hasattr(record, 'extra_fields'):
            log_obj.update(record.extra_fields)
        
        # Exception-Informationen
        if record.exc_info:
            log_obj["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Performance-Metriken
        if hasattr(record, 'duration_ms'):
            log_obj["performance"] = {
                "duration_ms": record.duration_ms,
                "slow_query": record.duration_ms > logging_config.SLOW_QUERY_THRESHOLD
            }
        
        # Request-Kontext (falls verfügbar)
        if hasattr(record, 'request_context'):
            log_obj["request"] = record.request_context
        
        # User-Kontext
        if hasattr(record, 'user_context'):
            log_obj["user"] = record.user_context
        
        return json.dumps(log_obj, ensure_ascii=False)

class StructuredLogger:
    """Strukturierter Logger mit erweiterten Features"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.name = name
        self._setup_logger()
    
    def _setup_logger(self):
        """Logger-Setup mit strukturiertem Format"""
        if not self.logger.handlers:  # Nur einmal konfigurieren
            self.logger.setLevel(getattr(logging, logging_config.LOG_LEVEL))
            
            # Console Handler
            console_handler = logging.StreamHandler(sys.stdout)
            if logging_config.ENABLE_STRUCTURED_LOGGING:
                console_handler.setFormatter(StructuredFormatter())
            else:
                console_handler.setFormatter(
                    logging.Formatter(logging_config.LOG_FORMAT)
                )
            self.logger.addHandler(console_handler)
            
            # File Handler (optional)
            if logging_config.LOG_FILE:
                try:
                    file_handler = logging.FileHandler(logging_config.LOG_FILE)
                    file_handler.setFormatter(StructuredFormatter())
                    self.logger.addHandler(file_handler)
                except Exception as e:
                    self.logger.warning(f"Could not set up file logging: {e}")
    
    def _log_with_context(
        self, 
        level: int, 
        message: str, 
        extra_fields: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        operation: Optional[str] = None,
        duration_ms: Optional[float] = None,
        exc_info: bool = False
    ):
        """Internes Logging mit Kontext"""
        extra = {"extra_fields": extra_fields or {}}
        
        # User-Kontext hinzufügen
        if user_id:
            extra["user_context"] = {"user_id": user_id}
        
        # Request-Kontext
        try:
            from flask import g, request
            if request:
                extra["request_context"] = {
                    "method": request.method,
                    "url": request.url,
                    "user_agent": request.headers.get("User-Agent"),
                    "ip": request.remote_addr,
                    "request_id": request_id or getattr(g, "request_id", None)
                }
        except (RuntimeError, AttributeError):
            # Flask-Kontext nicht verfügbar (außerhalb Request-Lifecycle)
            pass
        
        # Performance-Metriken
        if duration_ms is not None:
            extra["duration_ms"] = duration_ms
        
        # Operation-Typ
        if operation:
            extra["extra_fields"]["operation"] = operation
        
        self.logger.log(level, message, extra=extra, exc_info=exc_info)
    
    def debug(self, message: str, **kwargs):
        """Debug-Level Logging"""
        self._log_with_context(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Info-Level Logging"""
        self._log_with_context(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Warning-Level Logging"""
        self._log_with_context(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Error-Level Logging"""
        kwargs.setdefault("exc_info", True)
        self._log_with_context(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Critical-Level Logging"""
        kwargs.setdefault("exc_info", True)
        self._log_with_context(logging.CRITICAL, message, **kwargs)
    
    # Spezialisierte Log-Methoden
    def log_calendar_api_call(
        self, 
        operation: str, 
        duration_ms: float,
        success: bool = True,
        status_code: Optional[int] = None,
        error_message: Optional[str] = None,
        **kwargs
    ):
        """Logging für Google Calendar API Calls"""
        extra_fields = {
            "api": "google_calendar",
            "success": success,
            "status_code": status_code
        }
        
        if success:
            self.info(
                f"Calendar API call successful: {operation}",
                extra_fields=extra_fields,
                operation=operation,
                duration_ms=duration_ms,
                **kwargs
            )
        else:
            extra_fields["error_message"] = error_message
            self.error(
                f"Calendar API call failed: {operation}",
                extra_fields=extra_fields,
                operation=operation,
                duration_ms=duration_ms,
                **kwargs
            )
    
    def log_booking_event(
        self,
        event_type: str,  # created, updated, cancelled
        booking_id: Optional[str] = None,
        user_id: Optional[str] = None,
        slot_date: Optional[str] = None,
        slot_time: Optional[str] = None,
        **kwargs
    ):
        """Logging für Booking-Events"""
        extra_fields = {
            "event_type": event_type,
            "booking_id": booking_id,
            "slot_date": slot_date,
            "slot_time": slot_time
        }
        
        self.info(
            f"Booking {event_type}: {booking_id or 'unknown'}",
            extra_fields=extra_fields,
            user_id=user_id,
            operation="booking",
            **kwargs
        )
    
    def log_user_action(
        self,
        action: str,
        user_id: Optional[str] = None,
        resource: Optional[str] = None,
        success: bool = True,
        **kwargs
    ):
        """Logging für User-Aktionen"""
        extra_fields = {
            "action": action,
            "resource": resource,
            "success": success
        }
        
        level = logging.INFO if success else logging.WARNING
        message = f"User action: {action}"
        if not success:
            message += " (failed)"
        
        self._log_with_context(
            level,
            message,
            extra_fields=extra_fields,
            user_id=user_id,
            operation="user_action",
            **kwargs
        )
    
    def log_performance(
        self,
        operation: str,
        duration_ms: float,
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Logging für Performance-Metriken"""
        extra_fields = {
            "operation_type": "performance",
            **(details or {})
        }
        
        is_slow = duration_ms > logging_config.SLOW_QUERY_THRESHOLD
        level = logging.WARNING if is_slow else logging.INFO
        
        message = f"Performance: {operation} took {duration_ms:.2f}ms"
        if is_slow:
            message += " (SLOW)"
        
        self._log_with_context(
            level,
            message,
            extra_fields=extra_fields,
            operation=operation,
            duration_ms=duration_ms,
            **kwargs
        )
    
    def log_security_event(
        self,
        event_type: str,  # auth_success, auth_failure, access_denied, etc.
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Logging für Sicherheitsereignisse"""
        extra_fields = {
            "event_type": event_type,
            "ip_address": ip_address,
            "security_event": True,
            **(details or {})
        }
        
        # Security-Events sind immer wichtig
        level = logging.WARNING if "failure" in event_type or "denied" in event_type else logging.INFO
        
        self._log_with_context(
            level,
            f"Security event: {event_type}",
            extra_fields=extra_fields,
            user_id=user_id,
            operation="security",
            **kwargs
        )

# Performance-Timing Decorator
def log_performance(operation_name: Optional[str] = None, logger: Optional[StructuredLogger] = None):
    """Decorator für Performance-Logging"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            log = logger or get_logger(func.__module__)
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                log.log_performance(op_name, duration_ms)
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                log.log_performance(
                    op_name, 
                    duration_ms, 
                    details={"error": str(e), "success": False}
                )
                raise
        return wrapper
    return decorator

# Context Manager für Request-Logging
@contextmanager
def log_request(logger: StructuredLogger, operation: str, user_id: Optional[str] = None):
    """Context Manager für Request-Logging"""
    start_time = time.time()
    request_id = f"{int(start_time * 1000)}"  # Simple request ID
    
    logger.info(
        f"Starting {operation}",
        extra_fields={"request_id": request_id, "operation": operation},
        user_id=user_id
    )
    
    try:
        yield request_id
        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            f"Completed {operation}",
            extra_fields={"request_id": request_id, "success": True},
            duration_ms=duration_ms,
            user_id=user_id
        )
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            f"Failed {operation}: {str(e)}",
            extra_fields={"request_id": request_id, "success": False},
            duration_ms=duration_ms,
            user_id=user_id
        )
        raise

# Logger-Factory
_loggers: Dict[str, StructuredLogger] = {}

def get_logger(name: str) -> StructuredLogger:
    """Holt oder erstellt einen Logger"""
    if name not in _loggers:
        _loggers[name] = StructuredLogger(name)
    return _loggers[name]

# Standard-Logger für die Hauptanwendung
app_logger = get_logger("slot_booking_webapp")
calendar_logger = get_logger("calendar_api")
booking_logger = get_logger("booking_system")
auth_logger = get_logger("authentication")
performance_logger = get_logger("performance")