"""
Jobs API endpoints for Open Karaoke Studio FastAPI backend.

This module provides REST API endpoints for job management:
- Get job status/statistics
- List all jobs
- Get job details
- Cancel jobs
"""

import logging
from typing import Generator, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session


from app.api.dependencies import require_host
from app.db.database import SessionLocal
from app.db.models import JobStatus, User
from app.services.jobs_service import JobsService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/jobs", tags=["jobs"])


# ============================================================================
# Pydantic Models
# ============================================================================

class JobResponse(BaseModel):
    """Job response model"""

    id: str
    song_id: Optional[str] = None
    task_id: Optional[str] = None
    status: str
    progress: int = 0
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """Response model for job list"""

    jobs: List[dict]


class JobStatisticsResponse(BaseModel):
    """Response model for job statistics"""

    total: int
    pending: int
    processing: int
    completed: int
    failed: int
    cancelled: int


class JobCreateRequest(BaseModel):
    """Request model for creating a job"""

    song_id: str
    job_type: str = "audio_processing"


class JobActionResponse(BaseModel):
    """Response model for job actions"""

    success: bool
    message: str
    job_id: str


# ============================================================================
# Dependencies
# ============================================================================

def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error("Database session error: %s", e)
        db.rollback()
        raise
    finally:
        db.close()


def get_jobs_service() -> JobsService:
    """Dependency to get jobs service"""
    return JobsService()


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/status", response_model=JobStatisticsResponse)
async def get_job_status(
    jobs_service: JobsService = Depends(get_jobs_service),
    current_user: User = Depends(require_host),
):
    """
    Get the overall status of job processing with statistics.
    """
    stats = jobs_service.get_statistics()
    return JobStatisticsResponse(
        total=stats.get("total", 0),
        pending=stats.get("queue_length", 0),
        processing=stats.get("active_jobs", 0),
        completed=stats.get("completed_jobs", 0),
        failed=stats.get("raw_failed", 0),
        cancelled=stats.get("raw_cancelled", 0),
    )


@router.get("", response_model=JobListResponse)
async def get_jobs(
    status: Optional[str] = Query(None, description="Filter by job status"),
    jobs_service: JobsService = Depends(get_jobs_service),
    current_user: User = Depends(require_host),
):
    """
    List all jobs with their status.

    - **status**: Filter by status (pending, processing, completed, failed, cancelled)
    """
    try:
        if status:
            try:
                job_status = JobStatus(status)
                jobs = jobs_service.get_jobs_by_status(job_status)
            except ValueError:
                raise HTTPException(
                    status_code=400, detail=f"Invalid status: {status}"
                )
        else:
            jobs = jobs_service.get_all_jobs()

        return JobListResponse(jobs=[job.to_dict() for job in jobs])

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching jobs: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch jobs: {str(e)}")


@router.get("/{job_id}")
async def get_job(
    job_id: str,
    jobs_service: JobsService = Depends(get_jobs_service),
    current_user: User = Depends(require_host),
):
    """
    Get detailed information about a specific job.
    """
    job_details = jobs_service.get_job_with_details(job_id)

    if not job_details:
        raise HTTPException(status_code=404, detail="Job not found")

    return job_details


@router.post("/{job_id}/cancel", response_model=JobActionResponse)
async def cancel_job(
    job_id: str,
    jobs_service: JobsService = Depends(get_jobs_service),
    current_user: User = Depends(require_host),
):
    """
    Cancel a pending or in-progress job.
    """
    job = jobs_service.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
        raise HTTPException(
            status_code=400, detail=f"Cannot cancel job with status {job.status.value}"
        )

    success = jobs_service.cancel_job(job_id)

    if success:
        return JobActionResponse(
            success=True, message="Job cancelled", job_id=job_id
        )
    else:
        raise HTTPException(status_code=500, detail="Failed to cancel job")
