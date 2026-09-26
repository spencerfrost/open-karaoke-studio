# backend/app/db/database.py
"""
Database utility functions
"""

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)

from app.config import get_config
from app.services import file_management
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    asc,
    create_engine,
    desc,
    func,
    inspect,
)
from sqlalchemy.orm import Session, sessionmaker

from .models import Base, DbSong

# Get configuration and create database engine
config = get_config()
DATABASE_URL = config.DATABASE_URL
logger.debug("Database URL: %s", DATABASE_URL)

# Log the actual database file path for SQLite debugging
if DATABASE_URL.startswith("sqlite:"):
    db_file_path = DATABASE_URL.replace("sqlite:///", "")
    logger.debug("SQLite database file: %s (exists=%s)", db_file_path, Path(db_file_path).exists())

# Configure SQLite engine for better concurrency and cross-process reliability
if DATABASE_URL.startswith("sqlite:"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "timeout": 30,  # 30 second timeout for database locks
            "check_same_thread": False,  # Allow cross-thread access
        },
        pool_pre_ping=True,  # Verify connections before use
        pool_recycle=3600,  # Recycle connections every hour
        echo=False,  # Set to True for SQL debugging if needed
    )
else:
    # PostgreSQL configuration with connection pooling
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,  # Base pool connections
        max_overflow=20,  # Additional connections when pool is exhausted
        pool_timeout=30,  # Seconds to wait for a connection
        pool_pre_ping=True,  # Verify connections before use
        pool_recycle=1800,  # Recycle connections every 30 minutes
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Initialize the database
def init_db():
    """Initialize the database with tables from models"""
    # Base.metadata.create_all(bind=engine)  # Disabled: Alembic manages schema

    # Configure SQLite for better concurrency if using SQLite
    if config.DATABASE_URL.startswith("sqlite:"):
        try:
            with engine.connect() as connection:
                from sqlalchemy import text

                # Enable WAL mode for better concurrency
                connection.execute(text("PRAGMA journal_mode=WAL;"))
                # Set reasonable timeout
                connection.execute(text("PRAGMA busy_timeout=30000;"))
                # Enable foreign keys
                connection.execute(text("PRAGMA foreign_keys=ON;"))
                # Set synchronous mode for better reliability
                connection.execute(text("PRAGMA synchronous=FULL;"))
                connection.commit()
                logger.info("SQLite configured with WAL mode for better concurrency")
        except Exception as e:
            logger.warning("Failed to configure SQLite pragmas: %s", e)


def force_db_sync():
    """Force SQLite WAL checkpoint to ensure data is written to main database file"""
    if config.DATABASE_URL.startswith("sqlite:"):
        try:
            with engine.connect() as connection:
                from sqlalchemy import text

                # Force WAL checkpoint to flush all pending transactions
                result = connection.execute(text("PRAGMA wal_checkpoint(FULL);"))
                logger.debug("WAL checkpoint result: %s", result.fetchone())
                connection.commit()
        except Exception as e:
            logger.warning("Failed to execute WAL checkpoint: %s", e)


# SQLAlchemy session middleware for route handlers (placeholder, can be implemented if needed)
class DBSessionMiddleware:
    """Middleware to manage database sessions in web requests"""

    pass




@contextmanager
def get_db_session() -> Iterator[Session]:
    """Get a database session with automatic closing"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
