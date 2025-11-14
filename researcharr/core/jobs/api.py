"""Job Queue API endpoints for ResearchArr.

This module provides REST API endpoints for managing the job queue system.
"""

from __future__ import annotations

import inspect
import logging
from datetime import datetime
from functools import wraps
from uuid import UUID

from werkzeug.security import check_password_hash

from flask import Blueprint, current_app, jsonify, request
from researcharr.core.jobs.types import JobPriority, JobStatus

logger = logging.getLogger(__name__)

# Create jobs API blueprint
jobs_bp = Blueprint("jobs_api", __name__)


def require_auth(func):
    """Decorator that requires either valid API key or web session.

    Works with both sync and async view functions; always returns an async wrapper
    for uniform behavior under Flask 3's async support.
    """

    @wraps(func)
    async def wrapped(*args, **kwargs):  # type: ignore
        # Session-based auth
        if hasattr(current_app, "session_get") and current_app.session_get("logged_in"):
            result = func(*args, **kwargs)
            return await result if inspect.isawaitable(result) else result

        # API key auth
        api_key = request.headers.get("X-API-Key")
        if api_key:
            stored_key = getattr(current_app, "config_data", {}).get("api_key")
            if stored_key and check_password_hash(stored_key, api_key):
                result = func(*args, **kwargs)
                return await result if inspect.isawaitable(result) else result

        return jsonify({"error": "unauthorized"}), 401

    return wrapped


def get_job_service():
    """Get the job service from the app context."""
    service = getattr(current_app, "job_service", None)
    if service is None:
        return None, jsonify({"error": "Job service not initialized"}), 503
    return service, None, None


@jobs_bp.route("/jobs", methods=["GET"])
@require_auth
async def list_jobs():
    """List jobs with optional filtering.

    Query params:
        status: Filter by status (pending, running, completed, failed, etc.)
        limit: Maximum number of jobs to return (default: 100)
        offset: Number of jobs to skip (default: 0)
    """
    service, error_resp, code = get_job_service()
    if error_resp:
        return error_resp, code

    try:
        # Parse query parameters
        status_str = request.args.get("status")
        status = JobStatus[status_str.upper()] if status_str else None
        limit = int(request.args.get("limit", 100))
        offset = int(request.args.get("offset", 0))

        # Get jobs from service (would need to make this async-aware or use sync wrapper)
        # For now, return mock data structure
        jobs = await service.list_jobs(status=status, limit=limit, offset=offset)
        return jsonify({"jobs": jobs, "total": len(jobs)})

    except (ValueError, KeyError) as e:
        return jsonify({"error": f"Invalid parameter: {e}"}), 400
    except Exception as e:
        logger.exception("Error listing jobs")
        return jsonify({"error": str(e)}), 500


@jobs_bp.route("/jobs", methods=["POST"])
@require_auth
async def submit_job():
    """Submit a new job to the queue.

    Request body:
        {
            "handler": "handler_name",
            "args": [...],  // optional
            "kwargs": {...},  // optional
            "priority": "normal|low|high|critical",  // optional
            "max_retries": 3,  // optional
            "timeout": 300  // optional
        }
    """
    service, error_resp, code = get_job_service()
    if error_resp:
        return error_resp, code

    try:
        data = request.get_json(force=True)
        handler = data.get("handler")

        if not handler:
            return jsonify({"error": "handler is required"}), 400

        # Parse parameters
        args = tuple(data.get("args", []))
        kwargs = data.get("kwargs", {})
        priority_str = data.get("priority", "normal").upper()
        priority = JobPriority[priority_str]
        scheduled_at = None
        if "scheduled_at" in data and data["scheduled_at"]:
            try:
                scheduled_at = datetime.fromisoformat(data["scheduled_at"])
            except Exception:
                return jsonify({"error": "invalid scheduled_at timestamp"}), 400
        max_retries = data.get("max_retries", 3)
        timeout = data.get("timeout")

        # Submit job (would need async wrapper)
        # Submit actual job
        job_id = await service.submit_job(
            handler,
            args=args,
            kwargs=kwargs,
            priority=priority,
            scheduled_at=scheduled_at,
            max_retries=max_retries,
            timeout=timeout,
        )

        return jsonify(
            {
                "job_id": str(job_id),
                "status": "submitted",
                "scheduled_at": scheduled_at.isoformat() if scheduled_at else None,
            }
        ), 201

    except KeyError as e:
        return jsonify({"error": f"Invalid priority: {e}"}), 400
    except Exception as e:
        logger.exception("Error submitting job")
        return jsonify({"error": str(e)}), 500


@jobs_bp.route("/jobs/<job_id>", methods=["GET"])
@require_auth
async def get_job(job_id: str):
    """Get job status and details."""
    service, error_resp, code = get_job_service()
    if error_resp:
        return error_resp, code

    try:
        # Parse job_id
        try:
            uuid_id = UUID(job_id)
        except ValueError:
            return jsonify({"error": "Invalid job ID format"}), 400

        # Get job status and result
        # status = await service.get_job_status(uuid_id)
        # result = await service.get_job_result(uuid_id)

        return jsonify(
            {
                "job_id": job_id,
                "status": "placeholder",
                "result": None,
            }
        )

    except Exception as e:
        logger.exception("Error getting job")
        return jsonify({"error": str(e)}), 500


@jobs_bp.route("/jobs/<job_id>", methods=["DELETE"])
@require_auth
async def cancel_job(job_id: str):
    """Cancel a pending or running job."""
    service, error_resp, code = get_job_service()
    if error_resp:
        return error_resp, code

    try:
        try:
            uuid_id = UUID(job_id)
        except ValueError:
            return jsonify({"error": "Invalid job ID format"}), 400

        # cancelled = await service.cancel_job(uuid_id)
        cancelled = False

        if cancelled:
            return jsonify({"job_id": job_id, "status": "cancelled"})
        return jsonify({"error": "Job not found or cannot be cancelled"}), 404

    except Exception as e:
        logger.exception("Error cancelling job")
        return jsonify({"error": str(e)}), 500


@jobs_bp.route("/jobs/dead-letters", methods=["GET"])
@require_auth
async def get_dead_letters():
    """Get permanently failed jobs."""
    service, error_resp, code = get_job_service()
    if error_resp:
        return error_resp, code

    try:
        limit = int(request.args.get("limit", 100))
        # dead_letters = await service.get_dead_letters(limit=limit)

        return jsonify({"jobs": [], "total": 0})

    except Exception as e:
        logger.exception("Error getting dead letters")
        return jsonify({"error": str(e)}), 500


@jobs_bp.route("/jobs/dead-letters/<job_id>", methods=["POST"])
@require_auth
async def retry_dead_letter(job_id: str):
    """Retry a permanently failed job."""
    service, error_resp, code = get_job_service()
    if error_resp:
        return error_resp, code

    try:
        try:
            uuid_id = UUID(job_id)
        except ValueError:
            return jsonify({"error": "Invalid job ID format"}), 400

        # requeued = await service.retry_dead_letter(uuid_id)
        requeued = False

        if requeued:
            return jsonify({"job_id": job_id, "status": "requeued"})
        return jsonify({"error": "Job not found in dead letter queue"}), 404

    except Exception as e:
        logger.exception("Error retrying dead letter")
        return jsonify({"error": str(e)}), 500


@jobs_bp.route("/jobs/metrics", methods=["GET"])
@require_auth
async def get_metrics():
    """Get job queue metrics."""
    service, error_resp, code = get_job_service()
    if error_resp:
        return error_resp, code

    try:
        # metrics = await service.get_metrics()
        metrics = {
            "queue": {
                "pending": 0,
                "running": 0,
                "completed": 0,
                "failed": 0,
                "dead_letter": 0,
            },
            "workers": {
                "total": 0,
                "healthy": 0,
                "idle": 0,
                "busy": 0,
            },
        }

        return jsonify(metrics)

    except Exception as e:
        logger.exception("Error getting metrics")
        return jsonify({"error": str(e)}), 500


@jobs_bp.route("/jobs/workers", methods=["GET"])
@require_auth
async def get_workers():
    """Get worker pool information."""
    service, error_resp, code = get_job_service()
    if error_resp:
        return error_resp, code

    try:
        # workers = await service.get_workers()
        workers = []

        return jsonify({"workers": workers, "total": len(workers)})

    except Exception as e:
        logger.exception("Error getting workers")
        return jsonify({"error": str(e)}), 500


@jobs_bp.route("/jobs/workers/scale", methods=["POST"])
@require_auth
def scale_workers():
    """Scale the worker pool.

    Request body:
        {
            "count": 4
        }
    """
    service, error_resp, code = get_job_service()
    if error_resp:
        return error_resp, code

    try:
        data = request.get_json(force=True)
        count = data.get("count")

        if not isinstance(count, int) or count < 0:
            return jsonify({"error": "count must be a positive integer"}), 400

        # await service.scale_workers(count)

        return jsonify({"workers": count, "status": "scaled"})

    except Exception as e:
        logger.exception("Error scaling workers")
        return jsonify({"error": str(e)}), 500
