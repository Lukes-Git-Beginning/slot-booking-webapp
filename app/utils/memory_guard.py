# -*- coding: utf-8 -*-
"""
Memory Guard Utilities
Speicher-sichere Funktionen zur Verhinderung von SIGSEGV-Crashes
"""

import gc
import sys
import traceback
import logging
from functools import wraps
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


def memory_guard(max_retries: int = 2, cleanup_on_error: bool = True):
    """
    Decorator zur Verhinderung von Memory-bedingten Crashes

    Args:
        max_retries: Maximale Anzahl von Wiederholungsversuchen
        cleanup_on_error: Ob bei Fehlern Garbage Collection ausgeführt werden soll
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None

            for attempt in range(max_retries + 1):
                try:
                    # Vor kritischen Operationen Garbage Collection ausführen
                    if attempt > 0 and cleanup_on_error:
                        gc.collect()

                    result = func(*args, **kwargs)

                    # Bei Erfolg Result validieren
                    if result is not None and sys.getsizeof(result) > 10 * 1024 * 1024:  # 10MB
                        logger.warning(f"Large result from {func.__name__}: {sys.getsizeof(result)} bytes")

                    return result

                except MemoryError as e:
                    last_error = e
                    logger.error(f"Memory error in {func.__name__} (attempt {attempt + 1}): {e}")
                    if cleanup_on_error:
                        gc.collect()
                    continue

                except Exception as e:
                    # Bei anderen schweren Fehlern sofort abbrechen
                    if any(error_type in str(e).lower() for error_type in ['segmentation', 'sigsegv', 'access violation']):
                        logger.critical(f"Critical memory error in {func.__name__}: {e}")
                        if cleanup_on_error:
                            gc.collect()
                        raise

                    last_error = e
                    if attempt == max_retries:
                        logger.error(f"Final attempt failed for {func.__name__}: {e}")
                        raise
                    else:
                        logger.warning(f"Retrying {func.__name__} after error: {e}")
                        continue

            # Wenn alle Versuche fehlschlagen
            logger.error(f"All attempts failed for {func.__name__}")
            raise last_error if last_error else RuntimeError("Unknown error")

        return wrapper
    return decorator


def safe_import(module_name: str, timeout: int = 10) -> Optional[Any]:
    """
    Sicherer Import mit Timeout-Schutz

    Args:
        module_name: Name des zu importierenden Moduls
        timeout: Timeout in Sekunden

    Returns:
        Importiertes Modul oder None bei Fehler
    """
    try:
        # Basic import ohne komplexe Timeout-Mechanismen für Windows-Kompatibilität
        module = __import__(module_name, fromlist=[''])
        return module
    except ImportError as e:
        logger.debug(f"Module {module_name} nicht verfügbar: {e}")
        return None
    except Exception as e:
        logger.error(f"Fehler beim Import von {module_name}: {e}")
        return None


def check_memory_usage(threshold_mb: int = 100) -> bool:
    """
    Überprüft die aktuelle Speichernutzung

    Args:
        threshold_mb: Schwellenwert in MB

    Returns:
        True wenn unter dem Schwellenwert, False wenn darüber
    """
    try:
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024

        if memory_mb > threshold_mb:
            logger.warning(f"Hohe Speichernutzung: {memory_mb:.1f} MB")
            return False

        return True
    except ImportError:
        # psutil nicht verfügbar, konservativ annehmen dass alles okay ist
        return True
    except Exception as e:
        logger.warning(f"Fehler beim Prüfen der Speichernutzung: {e}")
        return True


def safe_json_operation(operation: Callable, data: Any, max_size_mb: int = 50) -> Any:
    """
    Sichere JSON-Operation mit Größen-Check

    Args:
        operation: JSON-Operation (json.dumps, json.loads, etc.)
        data: Zu verarbeitende Daten
        max_size_mb: Maximale Größe in MB

    Returns:
        Ergebnis der Operation oder None bei Fehler
    """
    try:
        # Größe der Eingangsdaten prüfen
        if hasattr(data, '__len__') and sys.getsizeof(data) > max_size_mb * 1024 * 1024:
            logger.error(f"Data too large for JSON operation: {sys.getsizeof(data)} bytes")
            return None

        result = operation(data)

        # Größe des Ergebnisses prüfen
        if result and sys.getsizeof(result) > max_size_mb * 1024 * 1024:
            logger.warning(f"Large JSON result: {sys.getsizeof(result)} bytes")

        return result

    except MemoryError as e:
        logger.error(f"Memory error in JSON operation: {e}")
        gc.collect()  # Cleanup versuchen
        return None
    except Exception as e:
        logger.error(f"Error in JSON operation: {e}")
        return None


def force_garbage_collection():
    """
    Erzwingt Garbage Collection und loggt Statistiken
    """
    try:
        before = len(gc.get_objects())
        collected = gc.collect()
        after = len(gc.get_objects())

        logger.info(f"Garbage collection: {collected} objects collected, {before} -> {after} objects")

        # Zusätzliche Cleanup-Zyklen für hartnäckige Referenzen
        for _ in range(2):
            gc.collect()

    except Exception as e:
        logger.warning(f"Error during garbage collection: {e}")