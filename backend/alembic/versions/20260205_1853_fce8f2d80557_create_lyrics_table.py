"""create_lyrics_table

Revision ID: fce8f2d80557
Revises: 618143a6fa78
Create Date: 2026-02-05 18:53:55.503411

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'fce8f2d80557'
down_revision: Union[str, None] = '618143a6fa78'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create lyrics table and migrate existing lyrics data from songs."""
    op.create_table('lyrics',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('song_id', sa.String(), nullable=False),
        sa.Column('type', sa.String(length=10), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['song_id'], ['songs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_lyrics_song_id', 'lyrics', ['song_id'], unique=False)
    op.create_index('idx_lyrics_song_type_active', 'lyrics', ['song_id', 'type', 'is_active'], unique=False)

    # Migrate existing lyrics data from songs table
    connection = op.get_bind()

    connection.execute(sa.text("""
        INSERT INTO lyrics (song_id, type, content, source, is_active, created_at, updated_at)
        SELECT id, 'plain', plain_lyrics, 'legacy_migration', true, NOW(), NOW()
        FROM songs WHERE plain_lyrics IS NOT NULL AND plain_lyrics != ''
    """))

    connection.execute(sa.text("""
        INSERT INTO lyrics (song_id, type, content, source, is_active, created_at, updated_at)
        SELECT id, 'synced', synced_lyrics, 'legacy_migration', true, NOW(), NOW()
        FROM songs WHERE synced_lyrics IS NOT NULL AND synced_lyrics != ''
    """))


def downgrade() -> None:
    """Drop lyrics table. Old columns on songs table are still intact."""
    op.drop_index('idx_lyrics_song_type_active', table_name='lyrics')
    op.drop_index('idx_lyrics_song_id', table_name='lyrics')
    op.drop_table('lyrics')
