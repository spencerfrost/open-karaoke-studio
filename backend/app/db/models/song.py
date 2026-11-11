"""
Song database model - Single source of truth.
"""

from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import deferred, relationship

from .base import UNKNOWN_ARTIST, Base

SongStatus = Literal["processing", "queued", "processed", "error"]


class DbSong(Base):
    __tablename__ = "songs"
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    artist = Column(String, nullable=False, default=UNKNOWN_ARTIST)
    duration = Column(Float, nullable=True)  # Duration in seconds
    date_added = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    thumbnail_path = Column(String, nullable=True)
    source = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    video_id = Column(String, nullable=True)
    # The video is YouTube's upload of an album track ("Provided to YouTube
    # by ..."): its picture is the album cover, so the video has no still of
    # its own. None until the download (or the backfill) has looked.
    video_is_album_art = Column(Boolean, nullable=True)

    # Core metadata
    album = Column(String, nullable=True)
    release_date = Column(String, nullable=True)
    year = Column(Integer, nullable=True)
    show_name = Column(String, nullable=True)  # Musical/soundtrack, e.g. "Wicked"
    # When a person last set or cleared the show name. While set, the show
    # isn't taken from the recording any more; cleared, the song has no show.
    show_name_hand_set_at = Column(DateTime, nullable=True)
    # Sung language as a Whisper code ("en", "fr"); None until detected or set
    language = Column(String, nullable=True)

    # Lyrics
    plain_lyrics = Column(Text, nullable=True)
    synced_lyrics = Column(Text, nullable=True)
    word_synced_lyrics = Column(
        Text, nullable=True
    )  # JSON: {words, language, mean_score, ...}
    # When a person last saved these lyrics (edited, pasted or picked from
    # search). While set, automatic runs only time them and never replace them
    # with another source. A run that sees it change stops and starts again.
    lyrics_hand_picked_at = Column(DateTime, nullable=True)

    # Explicit lyrics, from the album lookup; None when it couldn't tell
    explicit = Column(Boolean, nullable=True)

    # Relational links (nullable; backfilled by migration)
    artist_id = Column(Integer, ForeignKey("artists.id"), nullable=True)
    # Written with `album` by app.services.album_service, so the name and the
    # cover come from the same release.
    album_id = Column(Integer, ForeignKey("albums.id"), nullable=True)
    # When a person last set the album name. While set, automatic album
    # lookups skip the song; the cover it had stays linked.
    album_hand_set_at = Column(DateTime, nullable=True)
    # When the album lookup last ended without a cover. Missing-mode runs skip
    # the song until an "all" run looks again.
    album_checked_at = Column(DateTime, nullable=True)

    # Processing metadata
    engine_type = Column(
        String, nullable=True
    )  # Separation engine used (demucs, roformer, hybrid, clean_backing)
    vocal_range_low = Column(String, nullable=True)  # Lowest sung note, e.g. "G2"
    vocal_range_high = Column(String, nullable=True)  # Highest sung note, e.g. "E5"
    # Measured on the stems as played by default (no lead vocal); see services/audio.py
    loudness_lufs = Column(Float, nullable=True)  # EBU R128 integrated loudness
    true_peak_dbtp = Column(Float, nullable=True)  # Loudest instant, in dB true peak
    gain_db = Column(Float, nullable=True)  # Correction the player applies
    # When the lead and backing vocals are singing, from the stems; JSON, see
    # services/singing_map.py. Null until measured.
    singing_map = Column(Text, nullable=True)
    # Which version of each step last reached an answer for this song (see
    # services/processing_versions.py). Empty or behind: the step runs again
    # when the song is next queued to sing.
    loudness_version = Column(Integer, nullable=True)
    singing_map_version = Column(Integer, nullable=True)
    vocal_range_version = Column(Integer, nullable=True)
    word_timing_version = Column(Integer, nullable=True)
    # The LRC offset sweep layer, JSON (see services/lrc_offset_layer.py): the
    # score at every whole-song shift tried, and the aligned words at the best
    # shift when it passes the gate. Deferred: it can run to tens of kB.
    lrc_offset_sweep = deferred(Column(Text, nullable=True))
    lrc_offset_version = Column(Integer, nullable=True)
    # md5 of the synced_lyrics the sweep measured; another means it's stale.
    lrc_offset_lrc_md5 = Column(String(32), nullable=True)
    # The shift that passed the gate, waiting for "Apply shifts"; null when
    # there's none or it's been applied.
    lrc_offset_pending_shift = Column(Float, nullable=True)

    # Processing state: "processing" | "queued" | "processed" | "error"
    status = Column(String, nullable=False, default="processing")
    # Failure reason when status="error" (yt-dlp/demucs error text, truncated)
    error_message = Column(Text, nullable=True)
    # When it last failed (UTC); set while status="error". SongRepository.update
    # keeps it in step with status.
    failed_at = Column(DateTime, nullable=True)

    # AcoustID fingerprinting
    musicbrainz_recording_id = Column(String, nullable=True)
    acoustid_score = Column(Float, nullable=True)
    acoustid_fingerprint_status = Column(String, nullable=False, default="not_checked")
    # acoustid_fingerprint_status: "not_checked" | "matched" | "suggested" |
    # "ambiguous" | "no_match" | "failed" | "skipped". "matched" means AcoustID
    # agreed with the title and artist (or a person picked the recording);
    # "suggested" means it named the song differently, kept below for review.
    acoustid_suggested_recording_id = Column(String, nullable=True)
    acoustid_suggested_title = Column(String, nullable=True)
    acoustid_suggested_artist = Column(String, nullable=True)
    # When a person last set this song's title or artist (edited it, applied a
    # match, accepted or turned down a suggestion). While set, automatic runs
    # never change its title, artist, recording or artist credits.
    metadata_confirmed_at = Column(DateTime, nullable=True)

    queue_items = relationship(
        "KaraokeQueueItem", back_populates="song", cascade="all, delete-orphan"
    )
    artist_rel = relationship("DbArtist", back_populates="songs")
    album_rel = relationship("DbAlbum", back_populates="songs")
    song_artists = relationship(
        "DbSongArtist",
        back_populates="song_rel",
        cascade="all, delete-orphan",
        lazy="joined",
    )

    def to_dict(self) -> dict:
        """Convert to API response format - replaces to_pydantic()"""
        # Extract year from release_date if available
        year_value = None
        if self.year is not None:
            year_value = self.year
        elif self.release_date is not None:
            try:
                year_value = (
                    int(str(self.release_date).split("-")[0])
                    if "-" in str(self.release_date)
                    else int(str(self.release_date))
                )
            except (ValueError, AttributeError):
                year_value = None

        return {
            "id": self.id,
            "title": self.title,
            "artist": self.artist,
            "duration": self.duration,  # Duration in seconds
            "status": self.status,
            "errorMessage": self.error_message,
            "failedAt": (
                self.failed_at.isoformat() if self.failed_at is not None else None
            ),
            "dateAdded": (
                self.date_added.isoformat() if self.date_added is not None else None
            ),
            "backingVocalPath": (
                f"/api/songs/{self.id}/download/backing-vocals"
                if self.engine_type and self.engine_type.startswith("three_track")
                else None
            ),
            "thumbnail": self.thumbnail_path,
            # Source info
            "videoId": self.video_id,
            "videoIsAlbumArt": self.video_is_album_art,
            "sourceUrl": self.source_url,
            "source": self.source,
            # Metadata
            "album": self.album,
            "releaseDate": self.release_date,
            "year": year_value,
            "showName": self.show_name,
            "language": self.language,
            # Lyrics
            "lyricsHandPicked": self.lyrics_hand_picked_at is not None,
            "plainLyrics": self.plain_lyrics,
            "syncedLyrics": self.synced_lyrics,
            "wordSyncedLyrics": self.word_synced_lyrics,
            "explicit": self.explicit,
            "albumHandSet": self.album_hand_set_at is not None,
            # Relational IDs and computed cover URL
            "artistId": self.artist_id,
            "albumId": self.album_id,
            "albumCoverUrl": (
                f"/api/albums/{self.album_id}/cover"
                if self.album_id and self.album_rel and self.album_rel.cover_path
                else None
            ),
            # Processing metadata
            "engineType": self.engine_type,
            "vocalRangeLow": self.vocal_range_low,
            "vocalRangeHigh": self.vocal_range_high,
            "loudnessLufs": self.loudness_lufs,
            "truePeakDbtp": self.true_peak_dbtp,
            "gainDb": self.gain_db,
            # AcoustID fingerprinting
            "musicbrainzRecordingId": self.musicbrainz_recording_id,
            "acoustidScore": self.acoustid_score,
            "acoustidFingerprintStatus": self.acoustid_fingerprint_status,
            "acoustidSuggestion": (
                {
                    "recordingId": self.acoustid_suggested_recording_id,
                    "title": self.acoustid_suggested_title,
                    "artist": self.acoustid_suggested_artist,
                }
                if self.acoustid_suggested_recording_id
                else None
            ),
            "metadataConfirmed": self.metadata_confirmed_at is not None,
            # Structured artist credits
            "artists": (
                [
                    {
                        "id": sa.artist_rel.id,
                        "name": sa.artist_rel.display_name or sa.artist_rel.name,
                        "role": sa.role,
                        "creditedAs": sa.credited_as,
                    }
                    for sa in sorted(self.song_artists, key=lambda x: x.display_order)
                ]
                if self.song_artists
                else []
            ),
        }


def in_songbook():
    """SQL filter for the songs the songbook lists: all but failed ones.

    A failed song can't be sung. Adding it again restarts the failed row
    (POST /api/songs/{id}/retry), and admins find it under Failed songs.
    """
    return DbSong.status != "error"
