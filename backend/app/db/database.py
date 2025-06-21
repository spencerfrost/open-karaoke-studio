# backend/app/db/database.py
"""
Database utility functions
"""

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)

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
from .models import Base, DbSong

# Get configuration and create database engine
config = get_config()
DATABASE_URL = config.DATABASE_URL
logger.info(f"Database URL: {DATABASE_URL}")

# Log the actual database file path for SQLite debugging
if DATABASE_URL.startswith("sqlite:"):
    db_file_path = DATABASE_URL.replace("sqlite:///", "")
    logger.info(f"SQLite database file path: {db_file_path}")
    logger.info(f"Database file exists: {Path(db_file_path).exists()}")

    # Log current working directory for debugging path resolution
    import os

    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Absolute database path: {Path(db_file_path).resolve()}")

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
                logger.info("SQLite configured with WAL mode for better concurrency")
        except Exception as e:
            logger.warning(f"Failed to configure SQLite pragmas: {e}")


def force_db_sync():
    """Force SQLite WAL checkpoint to ensure data is written to main database file"""
    if config.DATABASE_URL.startswith("sqlite:"):
        try:
            with engine.connect() as connection:
                from sqlalchemy import text

                # Force WAL checkpoint to flush all pending transactions
                result = connection.execute(text("PRAGMA wal_checkpoint(FULL);"))
                # Only log checkpoint results at debug level - this is internal housekeeping
                logging.debug(f"WAL checkpoint result: {result.fetchone()}")
                connection.commit()
        except Exception as e:
            logger.warning(f"Failed to execute WAL checkpoint: {e}")


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

        if not db_path.exists() or db_path.stat().st_size == 0:
            logger.info("Creating database schema from scratch")
            Base.metadata.create_all(bind=engine)
            return
    else:
        # For non-SQLite databases, just ensure schema exists
        Base.metadata.create_all(bind=engine)
        return

    # If DB exists, check for missing tables and columns
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
    except Exception as e:
        logger.warning(f"Could not inspect existing database, recreating schema: {e}")
        Base.metadata.create_all(bind=engine)
        return
    
    # First, create any missing tables
    tables_to_create = []
    for table in Base.metadata.tables.values():
        if table.name not in existing_tables:
            tables_to_create.append(table)
    
    if tables_to_create:
        logger.info(f"Creating missing tables: {[t.name for t in tables_to_create]}")
        Base.metadata.create_all(bind=engine, tables=tables_to_create)
        return  # If we created tables, we're done
    
    # Check for missing columns in existing tables
    for table in Base.metadata.tables.values():
        table_name = table.name
        if table_name not in existing_tables:
            continue  # Skip if table doesn't exist (shouldn't happen after above check)
            
        try:
            existing_columns = {col["name"] for col in inspector.get_columns(table_name)}
        except Exception as e:
            logger.warning(f"Could not inspect table {table_name}, skipping: {e}")
            continue
            
        missing_columns = set()

        for column in table.columns:
            if column.name not in existing_columns:
                missing_columns.add(column.name)

        if missing_columns:
            logger.info(f"Missing columns in {table_name}: {missing_columns}")
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
                        logger.info(f"Added column: {sql}")
                    except Exception as e:
                        logger.error(f"Error adding column {col_name}: {e}")


@contextmanager
def get_db_session() -> Iterator[Session]:
    """Get a database session with automatic closing"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
