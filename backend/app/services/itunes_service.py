# backend/app/services/itunes_service.py
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
from .file_management import download_image, get_cover_art_path
from flask import current_app

def search_itunes(artist: str, title: str, album: str = '', limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search iTunes for song metadata with sorting by release date.
    
    Args:
        artist (str): Artist name
        title (str): Song title
        album (str): Album name (optional, used to improve search)
        limit (int): Maximum number of results to return
        
    Returns:
        List[Dict[str, Any]]: List of song metadata sorted by release date (newest first)
    """
    try:
        # Build search term - iTunes works best with simple search terms
        search_terms = []
        if artist:
            search_terms.append(artist)
        if title:
            search_terms.append(title)
        if album:
            search_terms.append(album)
            
        search_query = " ".join(search_terms)
        
        # iTunes Search API parameters
        params = {
            'term': search_query,
            'entity': 'song',  # Search for songs specifically
            'media': 'music',
            'limit': min(50, limit * 5),  # Get more results to filter through
            'sort': 'recent',  # Sort by release date (newest first)
            'country': 'US',  # Can be made configurable
        }
        
        logging.info(f"Searching iTunes with query: '{search_query}' (limit: {params['limit']})")
        
        # Make API request
        response = requests.get(
            'https://itunes.apple.com/search',
            params=params,
            timeout=10,
            headers={'User-Agent': 'OpenKaraokeStudio/1.0'}
        )
        response.raise_for_status()
        
        data = response.json()
        results = data.get('results', [])
        
        logging.info(f"iTunes returned {len(results)} raw results")
        
        matches = []
        for i, track in enumerate(results):
            try:
                # Extract metadata from iTunes response
                track_data = {
                    "id": track.get('trackId'),
                    "title": track.get('trackName'),
                    "artist": track.get('artistName'),
                    "artistId": track.get('artistId'),
                    "album": track.get('collectionName'),
                    "albumId": track.get('collectionId'),
                    "releaseDate": track.get('releaseDate'),
                    "genre": track.get('primaryGenreName'),
                    "duration": track.get('trackTimeMillis'),  # Duration in milliseconds
                    "trackNumber": track.get('trackNumber'),
                    "discNumber": track.get('discNumber'),
                    "country": track.get('country'),
                    "currency": track.get('currency'),
                    "price": track.get('trackPrice'),
                    "previewUrl": track.get('previewUrl'),
                    "artworkUrl30": track.get('artworkUrl30'),
                    "artworkUrl60": track.get('artworkUrl60'),
                    "artworkUrl100": track.get('artworkUrl100'),
                    "collectionPrice": track.get('collectionPrice'),
                    "trackExplicitness": track.get('trackExplicitness'),
                    "collectionExplicitness": track.get('collectionExplicitness'),
                    "isStreamable": track.get('isStreamable', False),
                }
                
                # Convert release date to a more readable format
                if track_data["releaseDate"]:
                    try:
                        release_dt = datetime.fromisoformat(track_data["releaseDate"].replace('Z', '+00:00'))
                        track_data["releaseYear"] = release_dt.year
                        track_data["releaseDateFormatted"] = release_dt.strftime('%Y-%m-%d')
                    except (ValueError, AttributeError):
                        track_data["releaseYear"] = None
                        track_data["releaseDateFormatted"] = None
                
                # Convert duration from milliseconds to seconds
                if track_data["duration"]:
                    track_data["durationSeconds"] = track_data["duration"] // 1000
                
                logging.debug(f"iTunes result {i+1}: '{track_data['title']}' by {track_data['artist']} ({track_data.get('releaseDateFormatted', 'Unknown date')})")
                
                matches.append(track_data)
                
            except Exception as e:
                logging.warning(f"Error processing iTunes track result: {e}")
                continue
        
        # Apply additional filtering to prioritize canonical releases
        filtered_matches = _filter_canonical_releases(matches, artist, title)
        
        # Return only the requested number of results
        return filtered_matches[:limit]
        
    except requests.RequestException as e:
        logging.error(f"iTunes API request error: {e}")
    except Exception as e:
        logging.error(f"iTunes search error: {e}")
    
    return []

def _filter_canonical_releases(tracks: List[Dict[str, Any]], artist_query: str, title_query: str) -> List[Dict[str, Any]]:
    """
    Filter and rank tracks to prioritize canonical releases.
    iTunes already sorts by release date, but we can do additional filtering.
    
    Args:
        tracks: List of iTunes track data
        artist_query: Original artist search query
        title_query: Original title search query
        
    Returns:
        List[Dict[str, Any]]: Filtered and ranked tracks
    """
    if not tracks:
        return tracks
    
    # Score each track for canonical likelihood
    scored_tracks = []
    
    for track in tracks:
        score = 0.0
        
        title = track.get('title', '').lower()
        artist = track.get('artist', '').lower()
        album = track.get('album', '').lower()
        
        # Exact matches get high scores
        if title == title_query.lower():
            score += 50
        elif title_query.lower() in title:
            score += 25
            
        if artist == artist_query.lower():
            score += 30
        elif artist_query.lower() in artist:
            score += 15
        
        # Avoid obvious compilation indicators
        compilation_keywords = [
            'greatest hits', 'best of', 'compilation', 'collection',
            'anthology', 'live', 'karaoke', 'tribute', 'cover'
        ]
        
        if not any(keyword in album for keyword in compilation_keywords):
            score += 20
        
        # Prefer tracks that are streamable
        if track.get('isStreamable'):
            score += 10
            
        # Prefer non-explicit versions for karaoke (optional)
        if track.get('trackExplicitness') == 'notExplicit':
            score += 5
            
        scored_tracks.append({
            'track': track,
            'score': score
        })
    
    # Sort by score (highest first), keeping iTunes' date sorting as secondary
    scored_tracks.sort(key=lambda x: x['score'], reverse=True)
    
    # Log the ranking
    logging.info("iTunes canonical ranking:")
    for i, item in enumerate(scored_tracks[:5]):  # Show top 5
        track = item['track']
        logging.info(f"  {i+1}. '{track.get('title', 'Unknown')}' by {track.get('artist', 'Unknown')} [{track.get('album', 'Unknown')}] - Score: {item['score']:.1f}")
    
    return [item['track'] for item in scored_tracks]

def get_itunes_cover_art(track_data: Dict[str, Any], song_dir: Path) -> Optional[str]:
    """
    Download cover art from iTunes artwork URLs.
    
    Args:
        track_data: iTunes track metadata
        song_dir: Directory to save cover art
        
    Returns:
        str: Relative path to downloaded cover art or None
    """
    try:
        # Try to get the highest quality artwork available
        artwork_url = (
            track_data.get('artworkUrl100') or 
            track_data.get('artworkUrl60') or 
            track_data.get('artworkUrl30')
        )
        
        if not artwork_url:
            return None
            
        # iTunes artwork URLs can be modified to get higher resolution
        # Replace the size in the URL with a larger size
        high_res_url = artwork_url.replace('100x100', '600x600').replace('60x60', '600x600').replace('30x30', '600x600')
        
        cover_path = get_cover_art_path(song_dir)
        
        if download_image(high_res_url, cover_path):
            from ..config import get_config
            config = get_config()
            return str(cover_path.relative_to(config.LIBRARY_DIR))
            
    except Exception as e:
        logging.error(f"iTunes cover art download error: {e}")
    
    return None

def enhance_metadata_with_itunes(metadata: Dict[str, Any], song_dir: Path) -> Dict[str, Any]:
    """
    Enhance song metadata with iTunes data.
    
    Args:
        metadata: Existing song metadata
        song_dir: Song directory for cover art
        
    Returns:
        Dict[str, Any]: Enhanced metadata
    """
    try:
        artist = metadata.get('artist', '')
        title = metadata.get('title', '')
        
        if not artist or artist == "Unknown Artist" or not title:
            return metadata
            
        itunes_results = search_itunes(artist, title, limit=1)
        
        if not itunes_results:
            return metadata
        
        itunes_data = itunes_results[0]
        
        # Download cover art
        cover_art_path = get_itunes_cover_art(itunes_data, song_dir)
        
        # Enhance metadata with iTunes data
        enhanced = metadata.copy()
        enhanced.update({
            "id": itunes_data.get("id"),
            "title": itunes_data.get("title") or metadata.get("title"),
            "artist": itunes_data.get("artist") or metadata.get("artist"),
            "artistId": itunes_data.get("artistId"),
            "album": itunes_data.get("album") or metadata.get("album"),
            "albumId": itunes_data.get("albumId"),
            "releaseDate": itunes_data.get("releaseDateFormatted"),
            "releaseYear": itunes_data.get("releaseYear"),
            "genre": itunes_data.get("genre") or metadata.get("genre"),
            "duration": itunes_data.get("durationSeconds"),
            "trackNumber": itunes_data.get("trackNumber"),
            "previewUrl": itunes_data.get("previewUrl"),
            "isStreamable": itunes_data.get("isStreamable"),
        })
        
        if cover_art_path:
            enhanced["coverArt"] = cover_art_path
            
        return enhanced
        
    except Exception as e:
        logging.error(f"Error enhancing metadata with iTunes: {e}")
        return metadata

# Test function for quick verification
def test_itunes_search():
    """Quick test function to verify iTunes API is working."""
    test_queries = [
        ("Coldplay", "Yellow"),
        ("The Beatles", "Hey Jude"),
        ("Queen", "Bohemian Rhapsody"),
    ]
    
    for artist, title in test_queries:
        print(f"\n--- Testing: {artist} - {title} ---")
        results = search_itunes(artist, title, limit=3)
        
        if results:
            for i, result in enumerate(results, 1):
                print(f"{i}. {result.get('title')} by {result.get('artist')}")
                print(f"   Album: {result.get('album')}")
                print(f"   Release: {result.get('releaseDateFormatted')}")
                print(f"   Genre: {result.get('genre')}")
        else:
            print("No results found")

if __name__ == "__main__":
    # Quick test when running the file directly
    test_itunes_search()
