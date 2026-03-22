from sqlalchemy.orm import Session

from app.db.models.artist import DbArtist


class ArtistRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_name(self, name: str) -> DbArtist | None:
        return (
            self.db.query(DbArtist)
            .filter(DbArtist.name == name.lower().strip())
            .first()
        )

    def get_or_create(self, name: str) -> DbArtist:
        normalized = name.lower().strip()
        artist = self.get_by_name(normalized)
        if not artist:
            artist = DbArtist(name=normalized)
            self.db.add(artist)
            self.db.commit()
            self.db.refresh(artist)
        return artist

    def update_image(
        self, artist: DbArtist, *, image_path: str | None, status: str
    ) -> DbArtist:
        artist.image_path = image_path
        artist.image_status = status
        self.db.commit()
        self.db.refresh(artist)
        return artist

    def update_bio(
        self, artist: DbArtist, *, bio: str | None, status: str
    ) -> DbArtist:
        artist.bio = bio
        artist.bio_status = status
        self.db.commit()
        self.db.refresh(artist)
        return artist
