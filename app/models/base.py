# -*- coding: utf-8 -*-
"""
Base Model und Database Setup für SQLAlchemy
Gemeinsame Funktionalität für alle Models
"""

from datetime import datetime
from typing import Any, Dict
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy import DateTime, Integer
import logging
import os

logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    """Base class für alle Models mit automatischen Timestamps"""

    # Automatische Timestamps für alle Models
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert Model zu Dictionary (für JSON-Kompatibilität)"""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            # Datetime zu ISO-String konvertieren
            if isinstance(value, datetime):
                result[column.name] = value.isoformat()
            else:
                result[column.name] = value
        return result

    def __repr__(self) -> str:
        """String-Repräsentation für Debugging"""
        return f"<{self.__class__.__name__}(id={self.id})>"


# Database Engine & Session Management
_engine = None
_session_factory = None


def get_database_url() -> str:
    """
    Gibt Database-URL zurück aus Environment-Variable

    Format: postgresql://user:password@host:port/database
    Default: postgresql://business_hub_user:changeme@localhost/business_hub
    """
    return os.getenv(
        'DATABASE_URL',
        'postgresql://business_hub_user:changeme@localhost/business_hub'
    )


def init_db(app=None) -> None:
    """
    Initialisiert Database Engine und erstellt alle Tables

    Args:
        app: Flask-App-Instanz (optional, für Config-Zugriff)
    """
    global _engine, _session_factory

    try:
        database_url = get_database_url()

        # Engine mit Connection Pooling erstellen
        _engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=10,  # Max 10 simultane Connections
            max_overflow=20,  # Max 20 zusätzliche Connections
            pool_timeout=30,  # 30s Timeout für Connection aus Pool
            pool_recycle=3600,  # Connections nach 1h recyceln
            echo=os.getenv('SQL_ECHO', 'false').lower() == 'true'  # SQL-Logging
        )

        # Session Factory erstellen
        from sqlalchemy.orm import sessionmaker
        _session_factory = sessionmaker(bind=_engine)

        # Alle Tables erstellen (falls nicht vorhanden)
        Base.metadata.create_all(_engine)

        logger.info(f"✅ Database initialisiert: {database_url.split('@')[1]}")

    except Exception as e:
        logger.error(f"❌ Database-Initialisierung fehlgeschlagen: {e}")
        raise


def get_db_session() -> Session:
    """
    Gibt eine neue Database-Session zurück

    Usage:
        with get_db_session() as session:
            user = session.query(User).first()
    """
    if _session_factory is None:
        raise RuntimeError("Database nicht initialisiert! Rufe init_db() zuerst auf.")

    return _session_factory()


def is_postgres_enabled() -> bool:
    """
    Prüft ob PostgreSQL aktiviert ist via Environment Variable

    Returns:
        True wenn USE_POSTGRES=true gesetzt ist
    """
    return os.getenv('USE_POSTGRES', 'false').lower() == 'true'
