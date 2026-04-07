"""
Jobs API endpoints for Open Karaoke Studio FastAPI backend.

This module provides REST API endpoints for job management:
- Get job status/statistics
- List all jobs
- Get job details
- Cancel jobs
- Dismiss jobs
"""

import logging
from typing import Generator, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session


from app.db.database import SessionLocal
from app.db.models import JobStatus
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
    dismissed: bool = False

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
async def get_job_status(jobs_service: JobsService = Depends(get_jobs_service)):
    """
    Get the overall status of job processing with statistics.
    """
    stats = jobs_service.get_statistics()
    # Map service stats to response model
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
    include_dismissed: bool = Query(False, description="Include dismissed jobs"),
    jobs_service: JobsService = Depends(get_jobs_service),
):
    """
    List all jobs with their status.
    
    - **status**: Filter by status (pending, processing, completed, failed, cancelled)
    - **include_dismissed**: Include dismissed jobs in results
    """
    try:
        if status:
            try:
                job_status = JobStatus(status)
                jobs = jobs_service.get_jobs_by_status(job_status)
                # Filter dismissed jobs unless explicitly requested
                if not include_dismissed:
                    jobs = [job for job in jobs if not job.dismissed]
            except ValueError:
                raise HTTPException(
                    status_code=400, detail=f"Invalid status: {status}"
                )
        else:
            # Default to active jobs (non-dismissed) unless explicitly requested
            if include_dismissed:
                jobs = jobs_service.get_all_jobs(include_dismissed=True)
            else:
                jobs = jobs_service.get_active_jobs()

        return JobListResponse(jobs=[job.to_dict() for job in jobs])

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching jobs: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch jobs: {str(e)}")


@router.get("/dismissed", response_model=JobListResponse)
async def get_dismissed_jobs(jobs_service: JobsService = Depends(get_jobs_service)):
    """
    List all dismissed jobs.
    """
    try:
        jobs = jobs_service.get_dismissed_jobs()
        return JobListResponse(jobs=[job.to_dict() for job in jobs])

    except Exception as e:
        logger.error("Error fetching dismissed jobs: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch dismissed jobs: {str(e)}")


@router.get("/{job_id}")
async def get_job(job_id: str, jobs_service: JobsService = Depends(get_jobs_service)):
    """
    Get detailed information about a specific job.
    """
    job_details = jobs_service.get_job_with_details(job_id)

    if not job_details:
        raise HTTPException(status_code=404, detail="Job not found")

    return job_details


@router.post("/{job_id}/cancel", response_model=JobActionResponse)
async def cancel_job(job_id: str, jobs_service: JobsService = Depends(get_jobs_service)):
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


@router.post("/{job_id}/dismiss", response_model=JobActionResponse)
async def dismiss_job(job_id: str, jobs_service: JobsService = Depends(get_jobs_service)):
    """
    Dismiss a failed, completed, or cancelled job from the UI.
    """
    job = jobs_service.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot dismiss job with status {job.status.value}. Only completed, failed, or cancelled jobs can be dismissed.",
        )

    success = jobs_service.dismiss_job(job_id)

    if success:
        return JobActionResponse(
            success=True, message="Job dismissed", job_id=job_id
        )
    else:
        raise HTTPException(status_code=500, detail="Failed to dismiss job")


@router.post("/process-audio", response_model=JobResponse)
async def start_audio_processing(job_data: JobCreateRequest):
    """
    Start audio processing job using existing Celery infrastructure.
    This demonstrates how FastAPI integrates with the current Celery setup.
    """
    try:
        # Import and dispatch to existing Celery worker
        # from app.jobs.jobs import process_audio_job
        # task = process_audio_job.delay(job_data.song_id)
        # return JobResponse(
        #     id=job_data.song_id,
        #     task_id=task.id,
        #     status="queued"
        # )

        # Mock response for demo - replace with actual Celery integration
        return JobResponse(
            id=job_data.song_id,
            task_id="demo-task-123",
            status="queued",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start job: {str(e)}")
