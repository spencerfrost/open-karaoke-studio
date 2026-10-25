from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .base import Base


class DbArtist(Base):
    __tablename__ = "artists"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)  # lowercase normalized
    display_name = Column(
        String, nullable=True
    )  # user-facing cased name (e.g. "Bonobo")
    # The artist's identity whenever it's known: two rows with one MusicBrainz
    # id are the same artist (Dixie Chicks and The Chicks).
    musicbrainz_artist_id = Column(String, nullable=True, unique=True)
    # The YouTube Music channel, from songs added through search.
    youtube_music_artist_id = Column(String, nullable=True, unique=True)
    image_path = Column(String, nullable=True)
    image_status = Column(String, nullable=False, default="not_checked")
    # image_status values: "not_checked" | "found" | "not_found"

    songs = relationship("DbSong", back_populates="artist_rel")
    albums = relationship("DbAlbum", back_populates="artist")
    song_artist_links = relationship("DbSongArtist", back_populates="artist_rel")
    aliases = relationship(
        "DbArtistAlias", back_populates="artist", cascade="all, delete-orphan"
    )


class DbArtistAlias(Base):
    """Another name an artist goes by, so it resolves to (and finds) them.

    From MusicBrainz's alias list, names a recording credited them as, and
    artists merged into this one.
    """

    __tablename__ = "artist_aliases"
    id = Column(Integer, primary_key=True, autoincrement=True)
    artist_id = Column(
        Integer,
        ForeignKey("artists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # normalize_artist_name(name): one alias can only point at one artist.
    alias = Column(String, nullable=False, unique=True)
    # The spelling as seen, for search.
    name = Column(String, nullable=False)
    # "musicbrainz" | "credited" | "merge"
    source = Column(String(20), nullable=False)

    artist = relationship("DbArtist", back_populates="aliases")
