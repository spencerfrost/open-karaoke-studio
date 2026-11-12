"""lyrics_reports

Someone singing can say a song's lyrics have the wrong words or are out of
sync. Each report is a row; "words" reports also remember the rejected lyrics,
so alignment never picks them again. songs.lyrics_hand_picked_at marks when a
person saved the lyrics; automatic runs only time those, never replace them.

Revision ID: b7d41e9a2c58
Revises: a3e8c1f6d920
Create Date: 2026-09-30 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7d41e9a2c58'
down_revision: Union[str, None] = 'a3e8c1f6d920'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('songs', sa.Column('lyrics_hand_picked_at', sa.DateTime(), nullable=True))
    op.create_table(
        'lyrics_reports',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('song_id', sa.String(), sa.ForeignKey('songs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('kind', sa.String(), nullable=False),
        sa.Column('words_key', sa.String(), nullable=False),
        sa.Column('report_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('reporter_name', sa.String(), nullable=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column(
            'session_id',
            sa.String(length=4),
            sa.ForeignKey('karaoke_sessions.session_id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_reported_at', sa.DateTime(), nullable=False),
        sa.Column('outcome', sa.String(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_by', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.UniqueConstraint('song_id', 'kind', 'words_key', name='uq_lyrics_reports_song_kind_words'),
    )
    op.create_index('ix_lyrics_reports_song_id', 'lyrics_reports', ['song_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_lyrics_reports_song_id', table_name='lyrics_reports')
    op.drop_table('lyrics_reports')
    op.drop_column('songs', 'lyrics_hand_picked_at')
