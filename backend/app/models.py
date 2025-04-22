"""
Data models for the application
"""
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
import json
import os
from pathlib import Path

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class Job:
    id: str
    filename: str
    status: JobStatus
    progress: int = 0
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        
        # Convert string status to Enum if needed
        if isinstance(self.status, str):
            self.status = JobStatus(self.status)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary with datetime serialization"""
        data = asdict(self)
        
        # Convert datetime objects to ISO format strings
        for key in ['created_at', 'started_at', 'completed_at']:
            if data[key] is not None:
                data[key] = data[key].isoformat()
        
        # Convert Enum to string
        data['status'] = self.status.value
        
        return data

class JobStore:
    """Simple job storage mechanism - in production, use a database instead"""
    def __init__(self, storage_dir: str = None):
        self.storage_dir = Path(storage_dir or os.path.join(os.path.dirname(__file__), 'job_store'))
        os.makedirs(self.storage_dir, exist_ok=True)
    
    def _job_path(self, job_id: str) -> Path:
        return self.storage_dir / f"{job_id}.json"
    
    def save_job(self, job: Job) -> None:
        """Save job to storage"""
        with open(self._job_path(job.id), 'w') as f:
            json.dump(job.to_dict(), f)
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID"""
        path = self._job_path(job_id)
        if not path.exists():
            return None
            
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                
            # Parse datetime strings back to datetime objects
            for key in ['created_at', 'started_at', 'completed_at']:
                if data[key]:
                    data[key] = datetime.fromisoformat(data[key])
                    
            return Job(**data)
        except Exception as e:
            print(f"Error loading job {job_id}: {e}")
            return None
    
    def get_all_jobs(self) -> List[Job]:
        """Get all jobs"""
        jobs = []
        for path in self.storage_dir.glob("*.json"):
            job_id = path.stem
            job = self.get_job(job_id)
            if job:
                jobs.append(job)
        return jobs
    
    def get_jobs_by_status(self, status: JobStatus) -> List[Job]:
        """Get jobs by status"""
        return [job for job in self.get_all_jobs() if job.status == status]
    
    def delete_job(self, job_id: str) -> bool:
        """Delete job from storage"""
        path = self._job_path(job_id)
        if path.exists():
            path.unlink()
            return True
        return False
    
    # Job statistics
    def get_stats(self) -> Dict[str, int]:
        """Get job statistics"""
        all_jobs = self.get_all_jobs()
        return {
            "queue_length": len([j for j in all_jobs if j.status == JobStatus.PENDING]),
            "active_jobs": len([j for j in all_jobs if j.status == JobStatus.PROCESSING]),
            "completed_jobs": len([j for j in all_jobs if j.status == JobStatus.COMPLETED]),
            "failed_jobs": len([j for j in all_jobs if j.status == JobStatus.FAILED]) + 
                          len([j for j in all_jobs if j.status == JobStatus.CANCELLED])
        }
