"""
SongRepository provides CRUD operations for managing song records in the database.

Methods:
    __init__(db: Session):
        Initializes the repository with a SQLAlchemy database session.

    create(song_data: Dict[str, Any]) -> DbSong:
        Creates and persists a new song record using the provided data.

    fetch(song_id: str) -> Optional[DbSong]:
        Retrieves a single song by its unique identifier.

    fetch_all(
        *, filters=None, sort_by=None, direction="desc", limit=None, offset=None
        Retrieves a list of songs with optional filtering, sorting, and pagination.

    update(song_id: str, **fields) -> Optional[DbSong]:
        Updates an existing song's fields by its ID and returns the updated record.

    delete(song_id: str) -> bool:
        Deletes a song by its ID and returns True if successful, False otherwise.
Song repository for managing song records in the database.

"""

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.models import DbSong


class SongRepository:
    """
    Repository class for managing Song database operations.

    This class provides methods to create, fetch, update, and delete song records
    in the database, as well as to retrieve multiple songs with optional filtering,
    sorting, and pagination.

    Args:
        db (Session): SQLAlchemy database session.

    Methods:
        create(song_data: Dict[str, Any]) -> DbSong:
            Create a new song record in the database.

        fetch(song_id: str) -> Optional[DbSong]:
            Retrieve a single song by its unique identifier.

        fetch_all(
            *, filters=None, sort_by=None, direction="desc", limit=None, offset=None
            Retrieve multiple songs with optional filtering, sorting, and pagination.

        update(song_id: str, **fields) -> Optional[DbSong]:
            Update fields of an existing song record.

        delete(song_id: str) -> bool:
            Delete a song record by its unique identifier.
    """

    def __init__(self, db: Session):
        self.db = db

    def create(self, song_data: Dict[str, Any]) -> DbSong:
        """
        Create a new song record.
        """
        # Always normalize date_added to ISO 8601 (YYYY-MM-DDTHH:MM:SS)
        if "date_added" in song_data and song_data["date_added"]:
            from datetime import datetime

            dt = song_data["date_added"]
            if isinstance(dt, str):
                # Try to parse known formats
                for fmt in (
                    "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%d %H:%M:%S.%f",
                    "%Y-%m-%d %H:%M:%S",
                ):
                    try:
                        dt = datetime.strptime(dt, fmt)
                        break
                    except Exception:
                        continue
            if isinstance(dt, datetime):
                song_data["date_added"] = dt.strftime("%Y-%m-%dT%H:%M:%S")
        song = DbSong(**song_data)
        self.db.add(song)
        self.db.commit()
        self.db.refresh(song)
        return song

    def fetch(self, song_id: str) -> Optional[DbSong]:
        """
        Fetch a single song by its ID.
        """
        return self.db.query(DbSong).filter(DbSong.id == song_id).first()

    def fetch_all(
        self, *, filters=None, sort_by=None, direction="desc", limit=None, offset=None
    ) -> List[DbSong]:
        """
        Fetch all songs with optional filtering, sorting, and pagination.
        :param filters: dict of field-value pairs to filter by
        :param sort_by: field name to sort by (default None)
        :param direction: 'asc' or 'desc' (default 'desc')
        :param limit: max number of results (default None)
        :param offset: number of results to skip (default None)
        """
        query = self.db.query(DbSong)
        if filters:
            for attr, value in filters.items():
                query = query.filter(getattr(DbSong, attr) == value)
        if sort_by:
            sort_col = getattr(DbSong, sort_by, None)
            if sort_col is not None:
                if direction == "desc":
                    query = query.order_by(sort_col.desc())
                else:
                    query = query.order_by(sort_col.asc())
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        return query.all()

    def update(self, song_id: str, **fields) -> Optional[DbSong]:
        """
        Update an existing song record.
        """
        song = self.fetch(song_id)
        if not song:
            return None
        for key, value in fields.items():
            setattr(song, key, value)
        self.db.commit()
        self.db.refresh(song)
        return song

    def delete(self, song_id: str) -> bool:
        """
        Delete a song record by its unique identifier.
        """
        song = self.fetch(song_id)
        if not song:
            return False
        self.db.delete(song)
        self.db.commit()
        return True
