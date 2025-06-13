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
    include_dismissed = request.args.get("include_dismissed", "false").lower() == "true"

    if status_filter:
        try:
            status = JobStatus(status_filter)
            jobs = jobs_service.get_jobs_by_status(status)
            # Filter dismissed jobs unless explicitly requested
            if not include_dismissed:
                jobs = [job for job in jobs if not job.dismissed]
        except ValueError:
            return jsonify({"error": f"Invalid status: {status_filter}"}), 400
    else:
        # Default to active jobs (non-dismissed) unless explicitly requested
        if include_dismissed:
            jobs = jobs_service.get_all_jobs(include_dismissed=True)
        else:
            jobs = jobs_service.get_active_jobs()

    return jsonify({"jobs": [job.to_dict() for job in jobs]})


@jobs_bp.route("/dismissed", methods=["GET"])
def get_dismissed_jobs():
    """List all dismissed jobs"""
    jobs = jobs_service.get_dismissed_jobs()
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


@jobs_bp.route("/<job_id>/dismiss", methods=["POST"])
def dismiss_job(job_id):
    """Dismiss a failed, completed, or cancelled job from the UI"""
    job = jobs_service.get_job(job_id)

    if not job:
        return jsonify({"error": "Job not found"}), 404

    if job.status not in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
        return (
            jsonify(
                {
                    "error": f"Cannot dismiss job with status {job.status}. Only completed, failed, or cancelled jobs can be dismissed."
                }
            ),
            400,
        )

    success = jobs_service.dismiss_job(job_id)

    if success:
        return jsonify({"success": True, "message": "Job dismissed", "job_id": job_id})
    else:
        return jsonify({"error": "Failed to dismiss job"}), 500
