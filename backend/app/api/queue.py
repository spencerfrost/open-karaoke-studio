"""
Queue management endpoints for the Open Karaoke Studio API.
These endpoints provide access to the processing queue and job status.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..db.models import JobStatus, JobStore
from ..services import file_management

queue_bp = Blueprint('queue', __name__, url_prefix='/queue')
job_store = JobStore()

@queue_bp.route('/status', methods=['GET'])
def get_queue_status():
    """Get the overall status of the processing queue"""
    stats = job_store.get_stats()
    return jsonify(stats)

@queue_bp.route('/jobs', methods=['GET'])
def get_queue_jobs():
    """List all jobs in the queue with their status"""
    status_filter = request.args.get("status", None)

    if status_filter:
        try:
            status = JobStatus(status_filter)
            jobs = job_store.get_jobs_by_status(status)
        except ValueError:
            return jsonify({"error": f"Invalid status: {status_filter}"}), 400
    else:
        jobs = job_store.get_all_jobs()

    def get_created_time(job):
        if job.created_at is None:
            # Return a minimum datetime if created_at is None
            return datetime.min.replace(tzinfo=timezone.utc)

        if job.created_at.tzinfo is None:
                return job.created_at.replace(tzinfo=timezone.utc)
        return job.created_at

    jobs = sorted(jobs, key=get_created_time, reverse=True)

    return jsonify({
        "jobs": [job.to_dict() for job in jobs]
    })
@queue_bp.route('/job/<job_id>', methods=['GET'])
def get_queue_job(job_id):
    """Get detailed information about a specific job"""
    job = job_store.get_job(job_id)

    if not job:
        return jsonify({"error": "Job not found"}), 404

    response = job.to_dict()

    # Add additional info for completed jobs
    if job.status == JobStatus.COMPLETED:
        song_dir = file_management.get_song_dir(Path(job.filename))
        vocals_path = file_management.get_vocals_path_stem(song_dir).with_suffix(".mp3")  # Assuming mp3
        instrumental_path = file_management.get_instrumental_path_stem(song_dir).with_suffix(".mp3")

        response.update({
            "vocals_path": str(vocals_path),
            "instrumental_path": str(instrumental_path)
        })

    # Estimate completion time if processing
    if job.status == JobStatus.PROCESSING and job.started_at:
        if job.progress > 0:
            elapsed_time = (datetime.now() - job.started_at).total_seconds()
            if elapsed_time > 0:
                # Estimate based on current progress
                time_per_percent = elapsed_time / job.progress
                remaining_percent = 100 - job.progress
                estimated_remaining = remaining_percent * time_per_percent

                estimated_completion = datetime.now() + timedelta(seconds=estimated_remaining)
                response["expected_completion"] = estimated_completion.isoformat()

    return jsonify(response)

@queue_bp.route('/job/<job_id>/cancel', methods=['POST'])
def cancel_queue_job(job_id):
    """Cancel a pending or in-progress job"""
    job = job_store.get_job(job_id)

    if not job:
        return jsonify({"error": "Job not found"}), 404

    if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
        return jsonify({"error": f"Cannot cancel job with status {job.status}"}), 400

    # Update job status
    job.status = JobStatus.CANCELLED
    job.completed_at = datetime.now()
    job.error = "Cancelled by user"
    job_store.save_job(job)

    # TODO: Implement actual task cancellation in Celery
    # This would involve celery.control.revoke(task_id, terminate=True)

    return jsonify({
        "success": True,
        "message": "Job cancelled",
        "job_id": job_id
    })
