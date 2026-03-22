"""add_artist_bio_and_acoustid_fields

Revision ID: c6683db9eb12
Revises: a3b4c5d6e7f8
Create Date: 2026-03-22 18:01:50.183509

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c6683db9eb12'
down_revision: Union[str, None] = 'a3b4c5d6e7f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Artist bio fields
    op.add_column('artists', sa.Column('bio', sa.Text(), nullable=True))
    op.add_column('artists', sa.Column('bio_status', sa.String(), nullable=False, server_default='not_checked'))

    # AcoustID fingerprinting fields on songs
    op.add_column('songs', sa.Column('musicbrainz_recording_id', sa.String(), nullable=True))
    op.add_column('songs', sa.Column('acoustid_score', sa.Float(), nullable=True))
    op.add_column('songs', sa.Column('acoustid_fingerprint_status', sa.String(), nullable=False, server_default='not_checked'))

    # Intentionally no other changes — autogenerate noise omitted.
    return

    # (unreachable — kept for reference only)
    op.alter_column('jobs', 'id',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=False)
    op.alter_column('jobs', 'filename',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               nullable=False)
    op.alter_column('jobs', 'status',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               nullable=False)
    op.alter_column('jobs', 'progress',
               existing_type=sa.BIGINT(),
               type_=sa.Integer(),
               existing_nullable=True)
    op.alter_column('jobs', 'task_id',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    op.alter_column('jobs', 'song_id',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    op.alter_column('jobs', 'title',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    op.alter_column('jobs', 'artist',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    op.alter_column('jobs', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               type_=sa.DateTime(),
               existing_nullable=True)
    op.alter_column('jobs', 'started_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               type_=sa.DateTime(),
               existing_nullable=True)
    op.alter_column('jobs', 'completed_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               type_=sa.DateTime(),
               existing_nullable=True)
    op.alter_column('jobs', 'phase',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               nullable=False)
    op.alter_column('jobs', 'retry_count',
               existing_type=sa.BIGINT(),
               type_=sa.Integer(),
               existing_nullable=True)
    op.alter_column('karaoke_queue', 'id',
               existing_type=sa.BIGINT(),
               type_=sa.Integer(),
               existing_nullable=False,
               autoincrement=True)
    op.alter_column('karaoke_queue', 'singer_name',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               nullable=False)
    op.alter_column('karaoke_queue', 'song_id',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               nullable=False)
    op.alter_column('karaoke_queue', 'position',
               existing_type=sa.BIGINT(),
               type_=sa.Integer(),
               nullable=False)
    op.alter_column('karaoke_sessions', 'session_id',
               existing_type=sa.VARCHAR(length=32),
               type_=sa.String(length=4),
               existing_nullable=False)
    op.drop_index(op.f('ix_performance_history_performed_at'), table_name='performance_history')
    op.alter_column('session_devices', 'session_id',
               existing_type=sa.VARCHAR(length=32),
               type_=sa.String(length=4),
               existing_nullable=False)
    op.drop_index(op.f('ix_session_playback_states_session_id'), table_name='session_playback_states')
    op.alter_column('songs', 'id',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=False)
    op.alter_column('songs', 'title',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               nullable=False)
    op.alter_column('songs', 'artist',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               nullable=False)
    op.alter_column('songs', 'date_added',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               type_=sa.DateTime(),
               existing_nullable=True)
    op.alter_column('songs', 'thumbnail_path',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    op.alter_column('songs', 'source',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    op.alter_column('songs', 'source_url',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    op.alter_column('songs', 'video_id',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    op.alter_column('songs', 'album',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    op.alter_column('songs', 'release_date',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    op.alter_column('songs', 'year',
               existing_type=sa.BIGINT(),
               type_=sa.Integer(),
               existing_nullable=True)
    op.alter_column('songs', 'genre',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    op.alter_column('songs', 'itunes_track_id',
               existing_type=sa.BIGINT(),
               type_=sa.Integer(),
               existing_nullable=True)
    op.alter_column('songs', 'itunes_preview_url',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    op.drop_column('songs', 'cover_art_path')
    op.drop_column('songs', 'lyrics')
    op.drop_column('songs', 'favorite')
    op.alter_column('users', 'id',
               existing_type=sa.BIGINT(),
               type_=sa.Integer(),
               existing_nullable=False,
               autoincrement=True)
    op.alter_column('users', 'username',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               nullable=False)
    op.alter_column('users', 'password_hash',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    op.alter_column('users', 'display_name',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    op.alter_column('users', 'theme',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    op.alter_column('users', 'color',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    op.alter_column('users', 'is_host',
               existing_type=sa.BOOLEAN(),
               nullable=True,
               existing_server_default=sa.text('false'))
    op.drop_index(op.f('idx_16471_sqlite_autoindex_users_1'), table_name='users')
    op.create_unique_constraint(None, 'users', ['username'])
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('songs', 'acoustid_fingerprint_status')
    op.drop_column('songs', 'acoustid_score')
    op.drop_column('songs', 'musicbrainz_recording_id')
    op.drop_column('artists', 'bio_status')
    op.drop_column('artists', 'bio')

    return

    # (unreachable — autogenerate noise omitted)
    op.drop_constraint(None, 'users', type_='unique')
    op.create_index(op.f('idx_16471_sqlite_autoindex_users_1'), 'users', ['username'], unique=True)
    op.alter_column('users', 'is_host',
               existing_type=sa.BOOLEAN(),
               nullable=False,
               existing_server_default=sa.text('false'))
    op.alter_column('users', 'color',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.alter_column('users', 'theme',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.alter_column('users', 'display_name',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.alter_column('users', 'password_hash',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.alter_column('users', 'username',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               nullable=True)
    op.alter_column('users', 'id',
               existing_type=sa.Integer(),
               type_=sa.BIGINT(),
               existing_nullable=False,
               autoincrement=True)
    op.add_column('songs', sa.Column('favorite', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.add_column('songs', sa.Column('lyrics', sa.TEXT(), autoincrement=False, nullable=True))
    op.add_column('songs', sa.Column('cover_art_path', sa.TEXT(), autoincrement=False, nullable=True))
    op.alter_column('songs', 'itunes_preview_url',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.alter_column('songs', 'itunes_track_id',
               existing_type=sa.Integer(),
               type_=sa.BIGINT(),
               existing_nullable=True)
    op.alter_column('songs', 'genre',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.alter_column('songs', 'year',
               existing_type=sa.Integer(),
               type_=sa.BIGINT(),
               existing_nullable=True)
    op.alter_column('songs', 'release_date',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.alter_column('songs', 'album',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.alter_column('songs', 'video_id',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.alter_column('songs', 'source_url',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.alter_column('songs', 'source',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.alter_column('songs', 'thumbnail_path',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.alter_column('songs', 'date_added',
               existing_type=sa.DateTime(),
               type_=postgresql.TIMESTAMP(timezone=True),
               existing_nullable=True)
    op.alter_column('songs', 'artist',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               nullable=True)
    op.alter_column('songs', 'title',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               nullable=True)
    op.alter_column('songs', 'id',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=False)
    op.create_index(op.f('ix_session_playback_states_session_id'), 'session_playback_states', ['session_id'], unique=True)
    op.alter_column('session_devices', 'session_id',
               existing_type=sa.String(length=4),
               type_=sa.VARCHAR(length=32),
               existing_nullable=False)
    op.create_index(op.f('ix_performance_history_performed_at'), 'performance_history', ['performed_at'], unique=False)
    op.alter_column('karaoke_sessions', 'session_id',
               existing_type=sa.String(length=4),
               type_=sa.VARCHAR(length=32),
               existing_nullable=False)
    op.alter_column('karaoke_queue', 'position',
               existing_type=sa.Integer(),
               type_=sa.BIGINT(),
               nullable=True)
    op.alter_column('karaoke_queue', 'song_id',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               nullable=True)
    op.alter_column('karaoke_queue', 'singer_name',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               nullable=True)
    op.alter_column('karaoke_queue', 'id',
               existing_type=sa.Integer(),
               type_=sa.BIGINT(),
               existing_nullable=False,
               autoincrement=True)
    op.alter_column('jobs', 'retry_count',
               existing_type=sa.Integer(),
               type_=sa.BIGINT(),
               existing_nullable=True)
    op.alter_column('jobs', 'phase',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               nullable=True)
    op.alter_column('jobs', 'completed_at',
               existing_type=sa.DateTime(),
               type_=postgresql.TIMESTAMP(timezone=True),
               existing_nullable=True)
    op.alter_column('jobs', 'started_at',
               existing_type=sa.DateTime(),
               type_=postgresql.TIMESTAMP(timezone=True),
               existing_nullable=True)
    op.alter_column('jobs', 'created_at',
               existing_type=sa.DateTime(),
               type_=postgresql.TIMESTAMP(timezone=True),
               existing_nullable=True)
    op.alter_column('jobs', 'artist',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.alter_column('jobs', 'title',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.alter_column('jobs', 'song_id',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.alter_column('jobs', 'task_id',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.alter_column('jobs', 'progress',
               existing_type=sa.Integer(),
               type_=sa.BIGINT(),
               existing_nullable=True)
    op.alter_column('jobs', 'status',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               nullable=True)
    op.alter_column('jobs', 'filename',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               nullable=True)
    op.alter_column('jobs', 'id',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=False)
    # ### end Alembic commands ###
