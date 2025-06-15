# backend/app/api/songs_artists.py

from flask import Blueprint, jsonify, request, current_app
from typing import List, Dict, Any, Optional
from ..db import database
from ..services.song_service import SongService
from ..exceptions import ServiceError

artists_bp = Blueprint("songs_artists", __name__, url_prefix="/api/songs")


@artists_bp.route("/artists", methods=["GET"])
def get_artists():
    """Get all unique artists with song counts and optional filtering.
    
    Query Parameters:
        search: Optional search term to filter artists
        limit: Maximum number of artists to return (default: 100)
        offset: Number of artists to skip (default: 0)
    """
    try:
        search_term = request.args.get('search', '').strip()
        limit = min(int(request.args.get('limit', 100)), 200)  # Cap at 200
        offset = int(request.args.get('offset', 0))
        
        # Get artists with song counts from database
        artists = database.get_artists_with_counts(
            search_term=search_term,
            limit=limit,
            offset=offset
        )
        
        total_count = database.get_artists_total_count(search_term=search_term)
        
        response = {
            "artists": artists,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "hasMore": offset + limit < total_count
            }
        }
        
        current_app.logger.info(f"Returning {len(artists)} artists (total: {total_count})")
        return jsonify(response)
        
    except Exception as e:
        current_app.logger.error(f"Error getting artists: {e}", exc_info=True)
        return jsonify({"error": "Failed to fetch artists"}), 500


@artists_bp.route("/by-artist/<string:artist_name>", methods=["GET"])
def get_songs_by_artist(artist_name: str):
    """Get songs for a specific artist with pagination.
    
    Query Parameters:
        limit: Maximum number of songs to return (default: 20)
        offset: Number of songs to skip (default: 0)
        sort: Sort order - 'title', 'album', 'year', 'dateAdded' (default: 'title')
        direction: 'asc' or 'desc' (default: 'asc')
    """
    try:
        limit = min(int(request.args.get('limit', 20)), 100)  # Cap at 100 per page
        offset = int(request.args.get('offset', 0))
        sort_by = request.args.get('sort', 'title')
        direction = request.args.get('direction', 'asc')
        
        # Get songs for artist from database
        songs_data = database.get_songs_by_artist(
            artist_name=artist_name,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            direction=direction
        )
        
        songs = [song.to_pydantic().model_dump() for song in songs_data['songs']]
        total_count = songs_data['total']
        
        response = {
            "songs": songs,
            "artist": artist_name,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "hasMore": offset + limit < total_count
            }
        }
        
        current_app.logger.info(f"Returning {len(songs)} songs for artist '{artist_name}' (total: {total_count})")
        return jsonify(response)
        
    except Exception as e:
        current_app.logger.error(f"Error getting songs for artist '{artist_name}': {e}", exc_info=True)
        return jsonify({"error": "Failed to fetch songs for artist"}), 500


@artists_bp.route("/search", methods=["GET"])
def search_songs_paginated():
    """Enhanced search with pagination and artist grouping options.
    
    Query Parameters:
        q: Search query (required)
        limit: Maximum number of songs to return (default: 20)
        offset: Number of songs to skip (default: 0)
        group_by_artist: If true, group results by artist (default: false)
        sort: Sort order (default: 'relevance')
        direction: 'asc' or 'desc' (default: 'desc')
    """
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({"songs": [], "pagination": {"total": 0, "limit": 0, "offset": 0, "hasMore": False}})
        
        limit = min(int(request.args.get('limit', 20)), 100)
        offset = int(request.args.get('offset', 0))
        group_by_artist = request.args.get('group_by_artist', 'false').lower() == 'true'
        sort_by = request.args.get('sort', 'relevance')
        direction = request.args.get('direction', 'desc')
        
        # Get search results from database
        search_results = database.search_songs_paginated(
            query=query,
            limit=limit,
            offset=offset,
            group_by_artist=group_by_artist,
            sort_by=sort_by,
            direction=direction
        )
        
        if group_by_artist:
            # Group results by artist
            response = {
                "artists": search_results['artists'],  # [{artist: "...", songs: [...], count: N}]
                "totalSongs": search_results['total_songs'],
                "totalArtists": search_results['total_artists'],
                "pagination": search_results['pagination']
            }
        else:
            # Flat list of songs
            songs = [song.to_pydantic().model_dump() for song in search_results['songs']]
            response = {
                "songs": songs,
                "pagination": search_results['pagination']
            }
        
        current_app.logger.info(f"Search '{query}' returned {search_results['pagination']['total']} results")
        return jsonify(response)
        
    except Exception as e:
        current_app.logger.error(f"Error searching songs: {e}", exc_info=True)
        return jsonify({"error": "Failed to search songs"}), 500
