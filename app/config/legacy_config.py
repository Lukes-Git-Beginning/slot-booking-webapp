# -*- coding: utf-8 -*-
"""
Legacy Logging-Konfiguration
Minimal-Konfiguration für Logging-System
"""

import os

class LoggingConfig:
    """Logging-Konfiguration"""

    # Logging-Level
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

    # Strukturiertes Logging
    ENABLE_STRUCTURED_LOGGING = os.getenv('ENABLE_STRUCTURED_LOGGING', 'false').lower() == 'true'

    # Log-Format
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # Log-Datei (optional)
    LOG_FILE = os.getenv('LOG_FILE', None)

    # Performance-Threshold für langsame Queries (ms)
    SLOW_QUERY_THRESHOLD = int(os.getenv('SLOW_QUERY_THRESHOLD', '1000'))

# Singleton-Instanz
logging_config = LoggingConfig()
