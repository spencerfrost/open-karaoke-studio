"""
Base SQLAlchemy declaration and shared constants.
"""

from sqlalchemy.orm import declarative_base

Base = declarative_base()

UNKNOWN_ARTIST = "Unknown Artist"
