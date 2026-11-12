from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models.album import DbAlbum
from app.db.models.song import DbSong


class AlbumRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_source(self, source: str, source_id: str) -> DbAlbum | None:
        return (
            self.db.query(DbAlbum)
            .filter(DbAlbum.source == source, DbAlbum.source_id == source_id)
            .first()
        )

    def get_or_create(
        self,
        *,
        source: str,
        source_id: str,
        title: str,
        artist_id: int | None = None,
        release_date: str | None = None,
    ) -> DbAlbum:
        album = self.get_by_source(source, source_id)
        if album:
            return album
        album = DbAlbum(
            source=source,
            source_id=source_id,
            title=title,
            artist_id=artist_id,
            release_date=release_date,
        )
        self.db.add(album)
        try:
            self.db.commit()
        except IntegrityError:
            # Another song on the same album created it first.
            self.db.rollback()
            album = self.get_by_source(source, source_id)
            if album is None:
                raise
            return album
        self.db.refresh(album)
        return album

    def update_cover(self, album: DbAlbum, cover_path: str) -> DbAlbum:
        album.cover_path = cover_path
        album.image_status = "found"
        self.db.commit()
        self.db.refresh(album)
        return album

    def mark_cover_not_found(self, album: DbAlbum) -> DbAlbum:
        """The source has no artwork for it: stop asking."""
        album.image_status = "not_found"
        self.db.commit()
        self.db.refresh(album)
        return album

    def unlinked(self) -> list[DbAlbum]:
        """Albums no song links to."""
        return (
            self.db.query(DbAlbum)
            .outerjoin(DbSong, DbSong.album_id == DbAlbum.id)
            .filter(DbSong.id.is_(None))
            .all()
        )
