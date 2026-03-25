"""cleanup_unused_song_metadata_columns

Revision ID: 234d85ef0e00
Revises: 5440cf43e72d
Create Date: 2025-12-27 17:05:59.824632

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '234d85ef0e00'
down_revision: Union[str, None] = '5440cf43e72d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove unused metadata columns from songs table."""
    
    # YouTube metadata - mostly unused uploader/channel info
    op.drop_column('songs', 'uploader')
    op.drop_column('songs', 'uploader_id')
    op.drop_column('songs', 'channel')
    op.drop_column('songs', 'channel_id')
    op.drop_column('songs', 'channel_name')  # Legacy field
    op.drop_column('songs', 'youtube_tags')
    op.drop_column('songs', 'youtube_categories')
    op.drop_column('songs', 'youtube_raw_metadata')
    op.drop_column('songs', 'youtube_channel_id')
    op.drop_column('songs', 'youtube_channel_name')
    op.drop_column('songs', 'description')  # Video description
    op.drop_column('songs', 'upload_date')  # Video upload date
    
    # iTunes metadata - redundant IDs
    op.drop_column('songs', 'itunes_artist_id')
    op.drop_column('songs', 'itunes_collection_id')
    op.drop_column('songs', 'track_time_millis')  # Redundant with duration
    # NOTE: Keeping itunes_preview_url - useful for "what's this song again?" in library
    
    # MusicBrainz metadata - not used
    op.drop_column('songs', 'mbid')
    op.drop_column('songs', 'release_id')
    
    # Other unused fields
    op.drop_column('songs', 'language')
    op.drop_column('songs', 'bpm')


def downgrade() -> None:
    """Restore unused metadata columns to songs table."""
    
    # Restore in reverse order for clean rollback
    op.add_column('songs', sa.Column('bpm', sa.Float(), nullable=True))
    op.add_column('songs', sa.Column('language', sa.String(), nullable=True))
    
    op.add_column('songs', sa.Column('release_id', sa.String(), nullable=True))
    op.add_column('songs', sa.Column('mbid', sa.String(), nullable=True))
    
    op.add_column('songs', sa.Column('track_time_millis', sa.BigInteger(), nullable=True))
    op.add_column('songs', sa.Column('itunes_collection_id', sa.BigInteger(), nullable=True))
    op.add_column('songs', sa.Column('itunes_artist_id', sa.BigInteger(), nullable=True))
    # NOTE: itunes_preview_url is kept, not dropped
    
    op.add_column('songs', sa.Column('upload_date', sa.DateTime(), nullable=True))
    op.add_column('songs', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('songs', sa.Column('youtube_channel_name', sa.String(), nullable=True))
    op.add_column('songs', sa.Column('youtube_channel_id', sa.String(), nullable=True))
    op.add_column('songs', sa.Column('youtube_raw_metadata', sa.Text(), nullable=True))
    op.add_column('songs', sa.Column('youtube_categories', sa.Text(), nullable=True))
    op.add_column('songs', sa.Column('youtube_tags', sa.Text(), nullable=True))
    op.add_column('songs', sa.Column('channel_name', sa.String(), nullable=True))
    op.add_column('songs', sa.Column('channel_id', sa.String(), nullable=True))
    op.add_column('songs', sa.Column('channel', sa.String(), nullable=True))
    op.add_column('songs', sa.Column('uploader_id', sa.String(), nullable=True))
    op.add_column('songs', sa.Column('uploader', sa.String(), nullable=True))
