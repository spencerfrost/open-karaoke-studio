from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship

from .base import Base


class DbArtist(Base):
    __tablename__ = "artists"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)  # lowercase normalized
    display_name = Column(String, nullable=True)  # user-facing cased name (e.g. "Bonobo")
    image_path = Column(String, nullable=True)
    image_status = Column(String, nullable=False, default="not_checked")
    # image_status values: "not_checked" | "found" | "not_found"
    bio = Column(Text, nullable=True)
    bio_status = Column(String, nullable=False, default="not_checked")
    # bio_status values: "not_checked" | "found" | "not_found"

    songs = relationship("DbSong", back_populates="artist_rel")
    albums = relationship("DbAlbum", back_populates="artist")
    song_artist_links = relationship("DbSongArtist", back_populates="artist_rel")
