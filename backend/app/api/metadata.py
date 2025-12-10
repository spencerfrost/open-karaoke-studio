"""
FastAPI router for metadata search endpoints.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel


from app.exceptions import NetworkError, ServiceError, ValidationError
from app.services.metadata_service import MetadataService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/metadata", tags=["metadata"])


class MetadataSearchParams(BaseModel):
    """Search parameters used in the request."""
    artist: str
    title: str
    album: str
    limit: int
    sort_by: str


class MetadataResult(BaseModel):
    """Individual metadata result."""
    artist: Optional[str] = None
    title: Optional[str] = None
    album: Optional[str] = None
    artwork_url: Optional[str] = None
    genre: Optional[str] = None
    release_date: Optional[str] = None
    track_number: Optional[int] = None
    
    class Config:
        extra = "allow"


class MetadataSearchResponse(BaseModel):
    """Response model for metadata search."""
    results: List[dict]
    search_params: MetadataSearchParams
    count: int


@router.get("/search", response_model=MetadataSearchResponse)
async def search_metadata(
    title: str = Query("", description="Song title to search for"),
    artist: str = Query("", description="Artist name to search for"),
    album: str = Query("", description="Album name to search for"),
    limit: int = Query(5, ge=1, le=50, description="Maximum number of results"),
    sort_by: str = Query("relevance", description="Sort order for results")
):
    """
    Search for song metadata using iTunes Search API.
    
    At least one of 'title' or 'artist' must be provided.
    Returns metadata including artwork URLs, genre, release date, etc.
    """
    logger.info("Received metadata search request")

    try:
        # Clean input
        title = title.strip()
        artist = artist.strip()
        album = album.strip()

        # Validate that at least title or artist is provided
        if not title and not artist:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "At least one of 'title' or 'artist' parameters is required",
                    "code": "MISSING_SEARCH_PARAMETERS"
                }
            )

        logger.info(
            "Metadata search - Artist: '%s', Title: '%s', Album: '%s', Limit: %s",
            artist, title, album, limit
        )

        # Initialize service
        metadata_service = MetadataService()

        # Search using the service layer
        results = metadata_service.search_metadata(artist, title, album, limit)

        # Format response using service
        search_params = MetadataSearchParams(
            artist=artist,
            title=title,
            album=album,
            limit=limit,
            sort_by=sort_by
        )

        logger.info("Metadata search returned %s results", len(results))
        
        return MetadataSearchResponse(
            results=results,
            search_params=search_params,
            count=len(results)
        )

    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError as e:
        logger.error("Metadata connection error: %s", e)
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to metadata service: {str(e)}"
        )
    except TimeoutError as e:
        logger.error("Metadata timeout error: %s", e)
        raise HTTPException(
            status_code=504,
            detail=f"Metadata service request timed out: {str(e)}"
        )
    except Exception as e:
        logger.error("Unexpected metadata search error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during metadata search: {str(e)}"
        )
