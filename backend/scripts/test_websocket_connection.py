#!/usr/bin/env python3
"""
Simple test script to verify WebSocket connection and job broadcasting
"""
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.models import Job, JobStatus
from app.repositories import JobRepository
from app.utils.events import publish_job_event


def test_job_creation_and_broadcast():
    """Test creating a job and broadcasting it via the event system"""
    print("🧪 Testing job creation and WebSocket broadcasting...")

    # Create a test job
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        filename="test.mp3",
        status=JobStatus.PENDING,
        status_message="Test job for WebSocket verification",
        progress=0,
        title="Test Song",
        artist="Test Artist",
        created_at=datetime.now(timezone.utc),
    )

    print(f"📝 Creating test job: {job_id}")

    # Save the job using the repository (this should trigger the event)
    job_repository = JobRepository()
    job_repository.create(job)

    print(f"✅ Job {job_id} created successfully")

    # Simulate a job update
    job.status = JobStatus.PROCESSING
    job.progress = 50
    job.status_message = "Processing audio..."

    print(f"📊 Updating job {job_id} to processing...")
    job_repository.update(job)

    print(f"✅ Job {job_id} updated successfully")

    # Clean up the test job
    print(f"🧹 Cleaning up test job {job_id}")
    job_repository.delete_job(job_id)

    print(
        "🎉 Test completed! Check the console output above for WebSocket broadcasting messages."
    )
    print(
        "If you see messages like '📢 Publishing job event' and '🎯 WebSocket handler received job event', the system is working."
    )


if __name__ == "__main__":
    test_job_creation_and_broadcast()
