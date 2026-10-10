from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from .base import Base


class DbAlbum(Base):
    __tablename__ = "albums"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    artist_id = Column(Integer, ForeignKey("artists.id"), nullable=True)
    # Where the album was found: "ytmusic" (browseId) or "deezer" (album id).
    # "itunes" rows predate them; rows with no source were made from songs.album.
    source = Column(String, nullable=True)
    source_id = Column(String, nullable=True)
    release_date = Column(String, nullable=True)  # year, e.g. "1975"
    cover_path = Column(String, nullable=True)  # relative: "covers/album-{id}.jpg"
    image_status = Column(String, nullable=False, default="not_checked")
    # image_status values: "not_checked" | "found" | "not_found"

    __table_args__ = (
        UniqueConstraint("source", "source_id", name="uq_albums_source_source_id"),
    )

    artist = relationship("DbArtist", back_populates="albums")
    songs = relationship("DbSong", back_populates="album_rel")
