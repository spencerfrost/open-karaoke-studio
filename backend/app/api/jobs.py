"""
Job management endpoints for the Open Karaoke Studio API.
These endpoints provide access to job processing and status.
"""

from flask import Blueprint, request, jsonify

from ..db.models import JobStatus
from ..services import JobsService

jobs_bp = Blueprint("jobs", __name__, url_prefix="/api/jobs")
jobs_service = JobsService()


@jobs_bp.route("/status", methods=["GET"])
def get_job_status():
    """Get the overall status of job processing"""
    stats = jobs_service.get_statistics()
    return jsonify(stats)


@jobs_bp.route("/", methods=["GET"])
def get_jobs():
    """List all jobs with their status"""
    status_filter = request.args.get("status", None)

    if status_filter:
        try:
            status = JobStatus(status_filter)
            jobs = jobs_service.get_jobs_by_status(status)
        except ValueError:
            return jsonify({"error": f"Invalid status: {status_filter}"}), 400
    else:
        jobs = jobs_service.get_all_jobs()

    return jsonify({"jobs": [job.to_dict() for job in jobs]})


@jobs_bp.route("/<job_id>", methods=["GET"])
def get_job(job_id):
    """Get detailed information about a specific job"""
    job_details = jobs_service.get_job_with_details(job_id)

    if not job_details:
        return jsonify({"error": "Job not found"}), 404

    return jsonify(job_details)


@jobs_bp.route("/<job_id>/cancel", methods=["POST"])
def cancel_job(job_id):
    """Cancel a pending or in-progress job"""
    job = jobs_service.get_job(job_id)

    if not job:
        return jsonify({"error": "Job not found"}), 404

    if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
        return jsonify({"error": f"Cannot cancel job with status {job.status}"}), 400

    success = jobs_service.cancel_job(job_id)
    
    if success:
        return jsonify({"success": True, "message": "Job cancelled", "job_id": job_id})
    else:
        return jsonify({"error": "Failed to cancel job"}), 500
