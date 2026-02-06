"""
FastAPI router for YouTube search and download endpoints.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator


from app.exceptions import NetworkError, ServiceError, ValidationError
from app.services.youtube_service import YouTubeService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/youtube", tags=["youtube"])


class YouTubeDownloadRequest(BaseModel):
    """Request model for YouTube download."""
    video_id: str = Field(..., min_length=1, max_length=100, description="YouTube video ID")
    song_id: str = Field(..., min_length=1, max_length=100, description="Song ID to associate with")
    title: Optional[str] = Field(None, max_length=200, description="Custom title override")
    artist: Optional[str] = Field(None, max_length=200, description="Custom artist override")
    album: Optional[str] = Field(None, max_length=200, description="Album name")
    searchThumbnailUrl: Optional[str] = Field(None, max_length=500, description="Original search result thumbnail URL")
    engine_type: str = Field("three_track", description="Separation engine to use (demucs, roformer, hybrid, clean_backing, three_track)")

    @field_validator("video_id", "song_id")
    @classmethod
    def validate_required_ids(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("Field cannot be empty")
        return v.strip()

    @field_validator("title", "artist", "album")
    @classmethod
    def validate_optional_strings(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and isinstance(v, str):
            stripped = v.strip()
            if stripped == "":
                return None
            return stripped
        return v

    @field_validator("engine_type")
    @classmethod
    def validate_engine_type(cls, v: str) -> str:
        valid_engines = {"demucs", "roformer", "hybrid", "clean_backing", "three_track"}
        if v not in valid_engines:
            raise ValueError(f"Invalid engine_type. Must be one of: {', '.join(valid_engines)}")
        return v


class YouTubeSearchResponse(BaseModel):
    """Response model for YouTube search results."""
    success: bool
    message: str
    data: list


class YouTubeDownloadResponse(BaseModel):
    """Response model for YouTube download initiation."""
    success: bool
    message: str
    data: dict


@router.get("/search", response_model=YouTubeSearchResponse)
async def search_youtube(
    query: str = Query(..., min_length=1, description="Search query"),
    maxResults: int = Query(10, ge=1, le=50, description="Maximum number of results")
):
    """
    Search YouTube for videos.
    
    Returns a list of video results matching the query.
    """
    try:
        youtube_service = YouTubeService()
        results = youtube_service.search_videos(query, maxResults)

        return YouTubeSearchResponse(
            success=True,
            message=f"Found {len(results)} videos matching '{query}'",
            data=results
        )

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NetworkError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ConnectionError as e:
        logger.error("YouTube connection error: %s", e)
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to YouTube API: {str(e)}"
        )
    except TimeoutError as e:
        logger.error("YouTube timeout error: %s", e)
        raise HTTPException(
            status_code=504,
            detail=f"YouTube API request timed out: {str(e)}"
        )
    except Exception as e:
        logger.error("Unexpected YouTube search error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during YouTube search: {str(e)}"
        )


@router.post("/download", response_model=YouTubeDownloadResponse, status_code=202)
async def download_youtube(request: YouTubeDownloadRequest):
    """
    Download and process a YouTube video.
    
    Creates a background job to download the video and process the audio.
    Returns immediately with a job ID for tracking progress.
    """
    try:
        youtube_service = YouTubeService()
        job_id = youtube_service.download_and_process_async(
            song_id=request.song_id,
            video_id_or_url=request.video_id,
            artist=request.artist or "",
            title=request.title or "",
            engine_type=request.engine_type,
        )

        logger.info(
            "YouTube processing started for song %s, video %s, job %s",
            request.song_id,
            request.video_id,
            job_id,
        )

        return YouTubeDownloadResponse(
            success=True,
            message="YouTube processing started",
            data={
                "jobId": job_id,
                "status": "pending",
                "message": "YouTube processing job created",
            }
        )

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Unexpected YouTube download error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error starting YouTube download: {str(e)}"
        )
