"""
Database utilities for testing.
"""

import tempfile
from pathlib import Path
from typing import List, Dict, Any
from unittest.mock import Mock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def create_test_database():
    """Create an in-memory test database"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    return engine


def create_test_session(engine):
    """Create a test database session"""
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def populate_test_database(session, songs_data: List[Dict[str, Any]] = None):
    """Populate test database with sample data"""
    if not songs_data:
        from tests.fixtures.test_data import SAMPLE_SONGS
        songs_data = SAMPLE_SONGS
    
    try:
        from app.db.models import DbSong
        for song_data in songs_data:
            db_song = DbSong(**song_data)
            session.add(db_song)
        session.commit()
    except ImportError:
        # If models aren't available, just return mocks
        pass


def cleanup_test_database(session):
    """Clean up test database"""
    session.rollback()
    session.close()


class MockDatabase:
    """Mock database for testing without SQLAlchemy"""
    
    def __init__(self):
        self.songs = []
        self.jobs = []
    
    def add_song(self, song_data):
        self.songs.append(song_data)
    
    def get_all_songs(self):
        return self.songs
    
    def get_song(self, song_id):
        return next((s for s in self.songs if s.get('id') == song_id), None)
    
    def add_job(self, job_data):
        self.jobs.append(job_data)
    
    def get_all_jobs(self):
        return self.jobs
    
    def get_job(self, job_id):
        return next((j for j in self.jobs if j.get('id') == job_id), None)
    
    def clear(self):
        self.songs.clear()
        self.jobs.clear()
