from sqlalchemy.orm import Session

from app.db.models.album import DbAlbum


class AlbumRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_itunes_id(self, collection_id: int) -> DbAlbum | None:
        return (
            self.db.query(DbAlbum)
            .filter(DbAlbum.itunes_collection_id == collection_id)
            .first()
        )

    def get_or_create(
        self,
        *,
        title: str,
        itunes_collection_id: int,
        artist_id: int | None = None,
        release_date: str | None = None,
    ) -> DbAlbum:
        album = self.get_by_itunes_id(itunes_collection_id)
        if not album:
            album = DbAlbum(
                title=title,
                itunes_collection_id=itunes_collection_id,
                artist_id=artist_id,
                release_date=release_date,
            )
            self.db.add(album)
            self.db.commit()
            self.db.refresh(album)
        return album

    def update_cover(self, album: DbAlbum, cover_path: str) -> DbAlbum:
        album.cover_path = cover_path
        album.image_status = "found"
        self.db.commit()
        self.db.refresh(album)
        return album
