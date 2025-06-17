# backend/app/db/database.py
"""
Database utility functions
"""

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

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

from ..config import get_config
from ..services import file_management
from .models import Base, DbSong, Song, SongMetadata

# Get configuration and create database engine
config = get_config()
DATABASE_URL = config.DATABASE_URL
logging.info(f"Database URL: {DATABASE_URL}")

# Log the actual database file path for SQLite debugging
if DATABASE_URL.startswith("sqlite:"):
    db_file_path = DATABASE_URL.replace("sqlite:///", "")
    logging.info(f"SQLite database file path: {db_file_path}")
    logging.info(f"Database file exists: {Path(db_file_path).exists()}")

    # Log current working directory for debugging path resolution
    import os

    logging.info(f"Current working directory: {os.getcwd()}")
    logging.info(f"Absolute database path: {Path(db_file_path).resolve()}")

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
    engine = create_engine(DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Initialize the database
def init_db():
    """Initialize the database with tables from models"""
    Base.metadata.create_all(bind=engine)

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
                logging.info("SQLite configured with WAL mode for better concurrency")
        except Exception as e:
            logging.warning(f"Failed to configure SQLite pragmas: {e}")


def force_db_sync():
    """Force SQLite WAL checkpoint to ensure data is written to main database file"""
    if config.DATABASE_URL.startswith("sqlite:"):
        try:
            with engine.connect() as connection:
                from sqlalchemy import text

                # Force WAL checkpoint to flush all pending transactions
                result = connection.execute(text("PRAGMA wal_checkpoint(FULL);"))
                logging.info(f"WAL checkpoint result: {result.fetchone()}")
                connection.commit()
        except Exception as e:
            logging.warning(f"Failed to execute WAL checkpoint: {e}")


# SQLAlchemy session middleware for route handlers (placeholder, can be implemented if needed)
class DBSessionMiddleware:
    """Middleware to manage database sessions in web requests"""

    pass


def ensure_db_schema():
    """Ensure the database schema is up to date with the latest model definitions"""
    # Check if we're using SQLite and get the database path
    if config.DATABASE_URL.startswith("sqlite:"):
        # Extract path from sqlite:///path/to/db
        db_path_str = config.DATABASE_URL.replace("sqlite:///", "")
        db_path = Path(db_path_str)

        if not db_path.exists():
            logging.info("Creating database schema from scratch")
            Base.metadata.create_all(bind=engine)
            return
    else:
        # For non-SQLite databases, just ensure schema exists
        Base.metadata.create_all(bind=engine)
        return

    # If DB exists, check for missing columns
    inspector = inspect(engine)
    for table in Base.metadata.tables.values():
        table_name = table.name
        existing_columns = {col["name"] for col in inspector.get_columns(table_name)}
        missing_columns = set()

        for column in table.columns:
            if column.name not in existing_columns:
                missing_columns.add(column.name)

        if missing_columns:
            logging.info(f"Missing columns in {table_name}: {missing_columns}")
            # Add columns using direct SQL
            with engine.connect() as connection:
                for col_name in missing_columns:
                    col = table.columns[col_name]
                    col_type = col.type.compile(dialect=engine.dialect)

                    # Handle nullability
                    nullable = "" if col.nullable else "NOT NULL"

                    # Handle defaults carefully
                    default = ""
                    if col.default is not None:
                        if hasattr(col.default, "arg") and col.default.arg is not None:
                            if isinstance(col.default.arg, str):
                                default = f"DEFAULT '{col.default.arg}'"
                            elif isinstance(col.default.arg, bool):
                                default = f"DEFAULT {1 if col.default.arg else 0}"
                            else:
                                default = f"DEFAULT {col.default.arg}"

                    sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type} {nullable} {default}".strip()
                    try:
                        from sqlalchemy import text

                        connection.execute(text(sql))
                        connection.commit()
                        logging.info(f"Added column: {sql}")
                    except Exception as e:
                        logging.error(f"Error adding column {col_name}: {e}")


@contextmanager
def get_db_session() -> Iterator[Session]:
    """Get a database session with automatic closing"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
