# backend/app/services/musicbrainz_service.py
import musicbrainzngs
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
from .file_management import download_image, get_cover_art_path
from flask import current_app

# Configure MusicBrainz API client
musicbrainzngs.set_useragent(
    "OpenKaraokeStudio", 
    "1.0", 
    "s.s.frost@gmail.com"  # Replace with actual contact
)

def search_musicbrainz(artist: str, title: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search MusicBrainz for recording metadata.
    
    Args:
        artist (str): Artist name
        title (str): Song title
        limit (int): Maximum number of results to return
        
    Returns:
        List[Dict[str, Any]]: List of recording metadata or empty list if none found
    """
    try:
        logging.info(f"Searching MusicBrainz for: {artist} - {title}")
        
        search_params = {}
        if artist:
            search_params['artist'] = artist
        if title:
            search_params['recording'] = title
        
        result = musicbrainzngs.search_recordings(
            limit=limit,
            **search_params
        )
        
        matches = []
        if result and 'recording-list' in result and result['recording-list']:
            for recording in result['recording-list']:
                try:
                    genre = _extract_genre(recording)
                    language = _extract_language(recording)
                    release_info = _extract_release_info(recording)
                    cover_art_url = None
                    if release_info and release_info.get('id'):
                        try:
                            cover_art_url = _get_cover_art_url(release_info['id'])
                        except Exception as e:
                            logging.warning(f"Error getting cover art URL: {e}")
                    
                    recording_data = {
                        "mbid": recording.get('id'),
                        "title": recording.get('title'),
                        "length": recording.get('length'),
                        "artist": recording.get('artist-credit', [{}])[0].get('artist', {}).get('name'),
                        "artist_id": recording.get('artist-credit', [{}])[0].get('artist', {}).get('id'),
                        "release": release_info,
                        "genre": genre,
                        "language": language,
                        "coverArtUrl": cover_art_url,
                        "duration": recording.get('length'),
                        
                    }
                    
                    
                    matches.append(recording_data)
                except Exception as e:
                    logging.warning(f"Error processing recording: {e}")
            
            return matches
            
    except Exception as e:
        logging.error(f"MusicBrainz search error: {e}")
    
    return []

def _extract_genre(recording: Dict[str, Any]) -> Optional[str]:
    """Extract genre from recording tags."""
    common_genres = [
        'rock', 'pop', 'hip hop', 'rap', 'r&b', 'jazz', 'blues', 
        'country', 'folk', 'electronic', 'dance', 'metal', 'classical', 
        'reggae', 'punk', 'soul', 'indie', 'alternative', 'disco', 
        'house', 'techno', 'trance'
    ]
    
    if 'tag-list' in recording:
        for tag in recording.get('tag-list', []):
            if tag.get('name') and tag.get('count'):
                try:
                    count = int(tag.get('count', 0))
                    if count > 0:
                        tag_name = tag.get('name').lower()
                        if tag_name in common_genres:
                            return tag_name.capitalize()
                except (ValueError, TypeError):
                    continue
        
        highest_count = 0
        best_tag = None
        
        for tag in recording.get('tag-list', []):
            try:
                if tag.get('name'):
                    count = int(tag.get('count', 0))
                    if count > highest_count:
                        highest_count = count
                        best_tag = tag.get('name')
            except (ValueError, TypeError):
                continue
                
        if best_tag:
            return best_tag.capitalize()
    
    return None

def _extract_language(recording: Dict[str, Any]) -> Optional[str]:
    """Extract language from recording tags."""
    common_languages = [
        'english', 'spanish', 'french', 'german', 'italian', 
        'japanese', 'korean', 'chinese', 'portuguese', 'russian'
    ]
    
    if 'tag-list' in recording:
        for tag in recording.get('tag-list', []):
            try:
                if tag.get('name') and int(tag.get('count', 0)) > 0:
                    tag_name = tag.get('name').lower()
                    if tag_name in common_languages:
                        return tag_name.capitalize()
            except (ValueError, TypeError):
                continue
    
    return None

def _get_cover_art_url(release_id: str) -> Optional[str]:
    """Get cover art URL for a release from MusicBrainz Cover Art Archive."""
    if not release_id:
        return None
    
    try:
        cover_art_list = musicbrainzngs.get_image_list(release_id)
        
        if cover_art_list and 'images' in cover_art_list and cover_art_list['images']:
            front_images = [img for img in cover_art_list['images'] if img.get('front', False)]
            
            if front_images:
                return front_images[0]['thumbnails'].get('large', front_images[0]['image'])
            else:
                return cover_art_list['images'][0]['thumbnails'].get('large', cover_art_list['images'][0]['image'])
                
    except Exception as e:
        logging.info(f"No cover art available for release {release_id}: {e}")
    
    return None

def _extract_release_info(recording: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract release information from a recording."""
    if 'release-list' not in recording or not recording['release-list']:
        return None
    
    # Prefer a release with country 'US', then 'GB' (UK), then 'CA' (Canada), otherwise use the first release
    preferred_countries = ['US', 'GB', 'CA']
    releases = recording['release-list']
    release = next(
        (r for country in preferred_countries for r in releases if r.get('country') == country),
        releases[0]
    )
    
    return {
        "id": release.get('id'),
        "title": release.get('title'),
        "date": release.get('date')
    }

def get_cover_art(release_id: str, song_dir: Path) -> Optional[str]:
    """Download cover art for a release from MusicBrainz Cover Art Archive."""
    if not release_id:
        return None
    
    try:
        cover_art_list = musicbrainzngs.get_image_list(release_id)
        
        if cover_art_list and 'images' in cover_art_list and cover_art_list['images']:
            front_images = [img for img in cover_art_list['images'] if img.get('front', False)]
            
            if front_images:
                image_url = front_images[0]['image']
            else:
                image_url = cover_art_list['images'][0]['image']
            
            cover_path = get_cover_art_path(song_dir)
            if download_image(image_url, cover_path):
                from . import config
                return str(cover_path.relative_to(config.BASE_LIBRARY_DIR))
                
    except Exception as e:
        logging.error(f"Cover art lookup error: {e}")
    
    return None

def enhance_metadata_with_musicbrainz(metadata: Dict[str, Any], song_dir: Path) -> Dict[str, Any]:
    """Enhance song metadata with MusicBrainz data."""
    try:
        artist = metadata.get('artist', '')
        title = metadata.get('title', '')
        
        if not artist or artist == "Unknown Artist" or not title:
            return metadata
            
        mb_results = search_musicbrainz(artist, title, limit=1)
        
        if not mb_results or len(mb_results) == 0:
            return metadata
        
        mb_data = mb_results[0]
            
        cover_art_path = None
        if mb_data.get('release', {}) and mb_data['release'].get('id'):
            cover_art_path = get_cover_art(mb_data['release']['id'], song_dir)
            
        enhanced = metadata.copy()
        enhanced.update({
            "mbid": mb_data.get("mbid"),
            "title": mb_data.get("title") if mb_data.get("title") else metadata.get("title"),
            "artist": mb_data.get("artist") if mb_data.get("artist") else metadata.get("artist"),
            "artistId": mb_data.get("artist_id"),
            "releaseTitle": mb_data.get("release", {}).get("title"),
            "releaseId": mb_data.get("release", {}).get("id"),
            "releaseDate": mb_data.get("release", {}).get("date"),
            "genre": mb_data.get("genre") if mb_data.get("genre") else metadata.get("genre"),
            "language": mb_data.get("language") if mb_data.get("language") else metadata.get("language"),
        })
        
        if cover_art_path:
            enhanced["coverArt"] = cover_art_path
            
        return enhanced
        
    except Exception as e:
        logging.error(f"Error enhancing metadata with MusicBrainz: {e}")
        return metadata
