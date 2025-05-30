"""
API endpoint modules for Open Karaoke Studio.
"""
from flask import Blueprint

# Import all blueprints
from .lyrics import lyrics_bp
from .songs import song_bp
from .queue import queue_bp
from .karaoke_queue import karaoke_queue_bp
from .users import user_bp
from .musicbrainz import mb_bp
from .youtube import youtube_bp

# List of all blueprints to register with the app
all_blueprints = [
    lyrics_bp,
    song_bp,
    queue_bp,
    karaoke_queue_bp,
    user_bp,
    mb_bp,
    youtube_bp,
]

def register_blueprints(app):
    """
    Register all API blueprints with the Flask app
    """
    for blueprint in all_blueprints:
        app.register_blueprint(blueprint)
