from sqlalchemy.orm import Session

from app.db.models.album import DbAlbum
from app.db.models.artist import DbArtist, DbArtistAlias
from app.db.models.song import DbSong
from app.db.models.song_artist import DbSongArtist
from app.services.artist_parsing import clean_artist_name, normalize_artist_name


class ArtistRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, artist_id: int) -> DbArtist | None:
        return self.db.get(DbArtist, artist_id)

    def get_by_name(self, name: str) -> DbArtist | None:
        return (
            self.db.query(DbArtist)
            .filter(DbArtist.name == clean_artist_name(name).lower())
            .first()
        )

    def find(self, name: str) -> DbArtist | None:
        """The artist a name means: an alias of theirs, or their stored name."""
        key = normalize_artist_name(clean_artist_name(name))
        if key:
            alias = (
                self.db.query(DbArtistAlias).filter(DbArtistAlias.alias == key).first()
            )
            if alias:
                return alias.artist
        return self.get_by_name(name)

    def resolve(
        self,
        name: str,
        mbid: str | None = None,
        ytm_id: str | None = None,
        *,
        credited_as: str | None = None,
    ) -> DbArtist:
        """The artist row for one credited name, created if there's none.

        Looks up by MusicBrainz artist id, then YouTube Music channel id, then
        alias, then name; `credited_as` is tried by alias and name too. A match
        by name picks up whichever ids the credit carries. Flushes, never
        commits: the caller writing the credits commits once.
        """
        name = clean_artist_name(name)
        artist = None
        if mbid:
            artist = (
                self.db.query(DbArtist)
                .filter(DbArtist.musicbrainz_artist_id == mbid)
                .first()
            )
        if artist is None and ytm_id:
            artist = (
                self.db.query(DbArtist)
                .filter(DbArtist.youtube_music_artist_id == ytm_id)
                .first()
            )
        if artist is None:
            artist = self.find(name)
        if artist is None and credited_as:
            artist = self.find(credited_as)

        if artist is None:
            artist = DbArtist(
                name=name.lower(),
                display_name=name,
                musicbrainz_artist_id=mbid,
                youtube_music_artist_id=ytm_id,
            )
            self.db.add(artist)
            self.db.flush()
            self.add_alias(artist, name, "credited")
            return artist

        # A match by name picks up the credit's ids, when no other row has them
        # (the lookups above found none, so neither does).
        if mbid and not artist.musicbrainz_artist_id:
            artist.musicbrainz_artist_id = mbid
        if ytm_id and not artist.youtube_music_artist_id:
            artist.youtube_music_artist_id = ytm_id
        # A properly cased name replaces a missing or lowercase one, never one
        # a person set.
        if name != artist.name and (
            not artist.display_name or artist.display_name == artist.name
        ):
            artist.display_name = name
        self.db.flush()
        return artist

    def add_alias(self, artist: DbArtist, name: str, source: str) -> None:
        """Record another name for an artist. A name already taken is left alone."""
        name = clean_artist_name(name)
        key = normalize_artist_name(name)
        if not key:
            return
        if self.db.query(DbArtistAlias.id).filter(DbArtistAlias.alias == key).first():
            return
        self.db.add(
            DbArtistAlias(artist_id=artist.id, alias=key, name=name, source=source)
        )
        self.db.flush()

    def merge_into(self, source: DbArtist, target: DbArtist) -> int:
        """Fold `source` into `target` and delete it. Returns the songs moved.

        Moves every credit (a song crediting both keeps one), repoints
        songs.artist_id and albums.artist_id, keeps the source's names as
        aliases, takes its ids and image when the target has none. Flushes,
        never commits.
        """
        if source.id == target.id:
            return 0

        source_names = [source.display_name or source.name, source.name]
        source_names += [alias.name for alias in source.aliases]
        mbid, ytm_id = source.musicbrainz_artist_id, source.youtube_music_artist_id
        if target.image_status != "found" and source.image_status == "found":
            target.image_path = source.image_path
            target.image_status = "found"

        target_song_ids = {
            song_id
            for (song_id,) in self.db.query(DbSongArtist.song_id).filter(
                DbSongArtist.artist_id == target.id
            )
        }
        moved = 0
        for link in list(source.song_artist_links):
            if link.song_id in target_song_ids:
                # The target's credit stays; primary wins over featured.
                kept = (
                    self.db.query(DbSongArtist)
                    .filter(
                        DbSongArtist.song_id == link.song_id,
                        DbSongArtist.artist_id == target.id,
                    )
                    .one()
                )
                if link.role == "primary":
                    kept.role = "primary"
                kept.credited_as = kept.credited_as or link.credited_as
                self.db.delete(link)
            else:
                link.artist_id = target.id
            moved += 1
        self.db.flush()

        self.db.query(DbSong).filter(DbSong.artist_id == source.id).update(
            {DbSong.artist_id: target.id}, synchronize_session="fetch"
        )
        self.db.query(DbAlbum).filter(DbAlbum.artist_id == source.id).update(
            {DbAlbum.artist_id: target.id}, synchronize_session="fetch"
        )

        # Its collections still hold the rows just moved; reloaded, they're
        # empty, so the delete doesn't null them out.
        self.db.expire(source)
        self.db.delete(source)
        self.db.flush()

        if mbid and not target.musicbrainz_artist_id:
            target.musicbrainz_artist_id = mbid
        if ytm_id and not target.youtube_music_artist_id:
            target.youtube_music_artist_id = ytm_id
        for name in source_names:
            self.add_alias(target, name, "merge")
        self.db.flush()
        return moved

    def is_unused(self, artist: DbArtist) -> bool:
        """No credits, no albums, and no song pointing at it."""
        return not (
            self.db.query(DbSongArtist.id)
            .filter(DbSongArtist.artist_id == artist.id)
            .first()
            or self.db.query(DbAlbum.id).filter(DbAlbum.artist_id == artist.id).first()
            or self.db.query(DbSong.id).filter(DbSong.artist_id == artist.id).first()
        )

    def delete_if_unused(self, artist: DbArtist) -> bool:
        """Delete an artist nothing refers to any more. Flushes, never commits."""
        if not self.is_unused(artist):
            return False
        self.db.delete(artist)
        self.db.flush()
        return True

    def get_all_with_image_status(self, status: str) -> list[DbArtist]:
        return self.db.query(DbArtist).filter(DbArtist.image_status == status).all()

    def update_image(
        self, artist: DbArtist, *, image_path: str | None, status: str
    ) -> DbArtist:
        artist.image_path = image_path
        artist.image_status = status
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

        # Sessions don't autoflush: without this, the query below finds the songs
        # just deleted and counts them twice.
        self.db.flush()

        # Also handle songs that have artist_id FK directly but no song_artists entries
        orphan_songs = self.db.query(DbSong).filter(DbSong.artist_id == artist.id).all()
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
