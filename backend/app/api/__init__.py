"""
API endpoint modules for Open Karaoke Studio.
"""

from .jobs import jobs_bp
from .karaoke_queue import karaoke_queue_bp

# Import all blueprints
from .lyrics import lyrics_bp
from .metadata import metadata_bp
from .songs import song_bp

# from .songs_artists import artists_bp
from .users import user_bp
from .youtube import youtube_bp
from .youtube_music import youtube_music_bp

# List of all blueprints to register with the app
all_blueprints = [
    lyrics_bp,
    song_bp,
    jobs_bp,
    karaoke_queue_bp,
    user_bp,
    metadata_bp,
    youtube_bp,
    youtube_music_bp,
]


def register_blueprints(app):
    """
    Register all API blueprints with the Flask app
    """
    for blueprint in all_blueprints:
        app.register_blueprint(blueprint)
