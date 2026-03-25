from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .base import Base


class DbAlbum(Base):
    __tablename__ = "albums"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    artist_id = Column(Integer, ForeignKey("artists.id"), nullable=True)
    itunes_collection_id = Column(Integer, nullable=True, unique=True)
    release_date = Column(String, nullable=True)
    cover_path = Column(String, nullable=True)  # relative: "covers/{collection_id}.jpg"
    image_status = Column(String, nullable=False, default="not_checked")
    # image_status values: "not_checked" | "found" | "not_found"

    artist = relationship("DbArtist", back_populates="albums")
    songs = relationship("DbSong", back_populates="album_rel")
