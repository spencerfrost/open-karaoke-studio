from sqlalchemy.orm import Session

from app.db.models.artist import DbArtist
from app.db.models.song import DbSong
from app.db.models.song_artist import DbSongArtist


class ArtistRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, artist_id: int) -> DbArtist | None:
        return self.db.get(DbArtist, artist_id)

    def get_by_name(self, name: str) -> DbArtist | None:
        return (
            self.db.query(DbArtist)
            .filter(DbArtist.name == name.lower().strip())
            .first()
        )

    def get_or_create(self, name: str, display_name: str | None = None) -> DbArtist:
        normalized = name.lower().strip()
        artist = self.get_by_name(normalized)
        if not artist:
            artist = DbArtist(
                name=normalized,
                display_name=display_name or name,
            )
            self.db.add(artist)
            self.db.commit()
            self.db.refresh(artist)
        elif display_name and display_name != normalized:
            # Update display_name if the caller provides a properly-cased version
            # and the current value is missing or just the lowercase name
            if not artist.display_name or artist.display_name == normalized:
                artist.display_name = display_name
                self.db.commit()
                self.db.refresh(artist)
        return artist

    def get_all_with_image_status(self, status: str) -> list[DbArtist]:
        return (
            self.db.query(DbArtist)
            .filter(DbArtist.image_status == status)
            .all()
        )

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

    def update_display_name(self, artist: DbArtist, display_name: str) -> DbArtist:
        artist.display_name = display_name
        self.db.commit()
        self.db.refresh(artist)
        return artist

    def delete_with_cascade(self, artist: DbArtist) -> dict:
        """
        Delete an artist. Songs that are exclusively linked to this artist are also
        deleted. Songs shared with other artists have only this artist's credit removed.
        """
        deleted_songs = 0
        unlinked_songs = 0

        # Find all songs linked to this artist via the join table
        links = (
            self.db.query(DbSongArtist)
            .filter(DbSongArtist.artist_id == artist.id)
            .all()
        )

        for link in links:
            song_id = link.song_id
            # Count other artist credits on this song
            other_credits = (
                self.db.query(DbSongArtist)
                .filter(
                    DbSongArtist.song_id == song_id,
                    DbSongArtist.artist_id != artist.id,
                )
                .count()
            )
            if other_credits > 0:
                # Song has other artists — only remove this artist's credit
                self.db.delete(link)
                unlinked_songs += 1
            else:
                # Song is exclusively this artist's — delete the song (cascades the link)
                song = self.db.get(DbSong, song_id)
                if song:
                    self.db.delete(song)
                    deleted_songs += 1

        # Also handle songs that have artist_id FK directly but no song_artists entries
        orphan_songs = (
            self.db.query(DbSong)
            .filter(DbSong.artist_id == artist.id)
            .all()
        )
        for song in orphan_songs:
            # Only delete if it has no other artist credits in join table
            other_credits = (
                self.db.query(DbSongArtist)
                .filter(
                    DbSongArtist.song_id == song.id,
                    DbSongArtist.artist_id != artist.id,
                )
                .count()
            )
            if other_credits == 0:
                self.db.delete(song)
                deleted_songs += 1

        self.db.delete(artist)
        self.db.commit()

        return {"deleted_songs": deleted_songs, "unlinked_songs": unlinked_songs}
