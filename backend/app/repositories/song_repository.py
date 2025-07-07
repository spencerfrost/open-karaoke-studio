from typing import Any, Dict, List, Optional

from app.db.models import DbSong
from sqlalchemy.orm import Session


class SongRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, song_data: Dict[str, Any]) -> DbSong:
        song = DbSong(**song_data)
        self.db.add(song)
        self.db.commit()
        self.db.refresh(song)
        return song

    def fetch(self, song_id: str) -> Optional[DbSong]:
        return self.db.query(DbSong).filter(DbSong.id == song_id).first()

    def fetch_all(self, **filters) -> List[DbSong]:
        query = self.db.query(DbSong)
        for attr, value in filters.items():
            query = query.filter(getattr(DbSong, attr) == value)
        return query.all()

    def update(self, song_id: str, **fields) -> Optional[DbSong]:
        song = self.fetch(song_id)
        if not song:
            return None
        for key, value in fields.items():
            setattr(song, key, value)
        self.db.commit()
        self.db.refresh(song)
        return song

    def delete(self, song_id: str) -> bool:
        song = self.fetch(song_id)
        if not song:
            return False
        self.db.delete(song)
        self.db.commit()
        return True

    def search(self, query: str, **params) -> List[DbSong]:
        # Placeholder for advanced/fuzzy search implementation
        # Example: return self.db.query(DbSong).filter(DbSong.title.ilike(f"%{query}%")).all()
        pass
