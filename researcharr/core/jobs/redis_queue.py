"""Redis-based distributed job queue implementation."""

from __future__ import annotations

import logging
import random
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

try:
    import redis
except ImportError:
    redis = None  # type: ignore

if TYPE_CHECKING:
    from redis import Redis as RedisClient  # type: ignore
else:
    RedisClient = Any  # type: ignore

from .queue import JobQueue
from .types import JobDefinition, JobPriority, JobResult, JobStatus

logger = logging.getLogger(__name__)


class RedisJobQueue(JobQueue):
    """Redis-based distributed job queue.

    Uses Redis data structures:
    - Sorted sets for priority queues (one per priority level)
    - Hashes for job data storage
    - Hashes for job status tracking
    - Lists for dead letter queue
    - Strings for metrics counters

    Benefits:
    - Multiple workers across processes/hosts
    - Persistent job storage
    - Atomic operations
    - Fast priority-based retrieval
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        key_prefix: str = "researcharr:jobs:",
        max_dead_letters: int = 1000,
    ):
        """Initialize Redis queue.

        Args:
            redis_url: Redis connection URL
            key_prefix: Prefix for all Redis keys
            max_dead_letters: Maximum dead letter queue size
        """
        if redis is None:
            raise ImportError(
                "redis package is required for RedisJobQueue. Install with: pip install redis"
            )

        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.max_dead_letters = max_dead_letters
        self._redis: RedisClient | None = None
        self._initialized = False

    def _key(self, suffix: str) -> str:
        """Generate Redis key with prefix.

        Args:
            suffix: Key suffix

        Returns:
            Full Redis key
        """
        return f"{self.key_prefix}{suffix}"

    def initialize(self) -> None:
        """Initialize Redis connection."""
        if self._initialized:
            return

        try:
            self._redis = redis.from_url(
                self.redis_url,
                decode_responses=False,  # We'll handle JSON encoding/decoding
                max_connections=20,
                socket_connect_timeout=5,
                socket_keepalive=True,
            )

            # Test connection
            self._redis.ping()

            self._initialized = True
            logger.info(f"Redis job queue initialized: {self.redis_url}")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise ConnectionError(f"Cannot connect to Redis at {self.redis_url}") from e

    def shutdown(self, graceful: bool = True) -> None:
        """Shutdown Redis connection.

        Args:
            graceful: If True, wait for pending operations
        """
        if self._redis:
            self._redis.close()
            self._redis = None
            self._initialized = False
            logger.info("Redis job queue shutdown complete")

    def submit(self, job: JobDefinition) -> UUID:
        """Submit a job to the queue.

        Args:
            job: Job definition

        Returns:
            job_id: UUID of the submitted job

        Raises:
            ValueError: If job validation fails
            ConnectionError: If Redis is not available
        """
        if not self._redis:
            raise ConnectionError("Redis connection not initialized")

        # Serialize job
        job_data = job.to_json()
        job_id_str = str(job.id)

        # Use Redis pipeline for atomic operations
        with self._redis.pipeline(transaction=True) as pipe:
            # Store job data
            pipe.hset(self._key("data"), job_id_str, job_data)

            # Store job status
            pipe.hset(self._key("status"), job_id_str, JobStatus.PENDING.value)

            # If scheduled_at in future, enqueue into scheduled set; else ready queue
            if job.scheduled_at and job.scheduled_at.timestamp() > datetime.now(UTC).timestamp():
                # Score = scheduled timestamp; separate ZSET for scheduled jobs
                pipe.zadd(self._key("scheduled"), {job_id_str: job.scheduled_at.timestamp()})
            else:
                # Priority scoring: lower score gets popped first via ZPOPMIN.
                # Make higher priority => more negative score.
                score = (-job.priority.value * 1e9) + job.created_at.timestamp()
                priority_queue_key = self._key(f"queue:p{job.priority.value}")
                pipe.zadd(priority_queue_key, {job_id_str: score})

            # Increment submitted counter
            pipe.incr(self._key("metrics:submitted"))

            pipe.execute()

        logger.debug(f"Job {job_id_str} submitted with priority {job.priority.name}")
        return job.id

    def get_next(self, worker_id: str) -> JobDefinition | None:
        """Get the next job from queue for a worker.

        Args:
            worker_id: Unique identifier of the requesting worker

        Returns:
            JobDefinition if available, None if queue empty
        """
        if not self._redis:
            raise ConnectionError("Redis connection not initialized")

        # Promote due scheduled jobs before checking ready queues
        self._promote_scheduled()

        # Check priority queues from highest to lowest
        for priority in reversed(list(JobPriority)):
            priority_queue_key = self._key(f"queue:p{priority.value}")

            # Atomically get and remove highest priority job (lowest score)
            # Use ZPOPMIN for atomic pop
            result = self._redis.zpopmin(priority_queue_key, count=1)
            result_seq = cast(Sequence[tuple[bytes | str, float]], result)

            if result_seq:
                job_id_str, _score = result_seq[0]
                if isinstance(job_id_str, bytes):
                    job_id_str = job_id_str.decode("utf-8")

                # Get job data
                job_data = self._redis.hget(self._key("data"), job_id_str)
                if not job_data:
                    logger.warning(f"Job {job_id_str} not found in data store")
                    continue

                if isinstance(job_data, bytes):
                    job_data = job_data.decode("utf-8")

                job = JobDefinition.from_json(job_data)

                # Update status to RUNNING
                with self._redis.pipeline(transaction=True) as pipe:
                    pipe.hset(self._key("status"), job_id_str, JobStatus.RUNNING.value)
                    pipe.hset(self._key("worker"), job_id_str, worker_id)
                    pipe.hset(self._key("started"), job_id_str, datetime.now(UTC).isoformat())
                    pipe.execute()

                logger.debug(f"Job {job_id_str} assigned to worker {worker_id}")
                return job

        return None

    def _promote_scheduled(self, batch: int = 100) -> None:
        """Move due scheduled jobs into ready priority queues.

        Args:
            batch: Maximum number of due jobs to promote per invocation.
        """
        if not self._redis:
            return None
        now_ts = datetime.now(UTC).timestamp()
        # Fetch due job IDs
        due = self._redis.zrangebyscore(self._key("scheduled"), 0, now_ts, start=0, num=batch)
        due_ids = cast(Sequence[bytes | str], due)
        if not due_ids:
            return None
        with self._redis.pipeline(transaction=True) as pipe:
            for raw_id in due_ids:
                job_id_str = raw_id.decode("utf-8") if isinstance(raw_id, bytes) else raw_id
                # Remove from scheduled set
                pipe.zrem(self._key("scheduled"), job_id_str)
                # Load job priority
                job_data = self._redis.hget(self._key("data"), job_id_str)
                if not job_data:
                    continue
                if isinstance(job_data, bytes):
                    job_data = job_data.decode("utf-8")
                try:
                    job = JobDefinition.from_json(job_data)
                except Exception:
                    continue
                score = (-job.priority.value * 1e9) + datetime.now(UTC).timestamp()
                pipe.zadd(self._key(f"queue:p{job.priority.value}"), {job_id_str: score})
            pipe.execute()

    def complete(self, job_id: UUID, result: JobResult) -> None:
        """Mark job as completed with result.

        Args:
            job_id: Job identifier
            result: Execution result
        """
        if not self._redis:
            raise ConnectionError("Redis connection not initialized")

        job_id_str = str(job_id)
        result_data = result.to_json()

        with self._redis.pipeline(transaction=True) as pipe:
            # Update status
            pipe.hset(self._key("status"), job_id_str, JobStatus.COMPLETED.value)

            # Store result (with TTL of 7 days)
            result_key = self._key(f"result:{job_id_str}")
            pipe.setex(result_key, 7 * 24 * 3600, result_data)

            # Remove worker assignment
            pipe.hdel(self._key("worker"), job_id_str)

            # Increment completed counter
            pipe.incr(self._key("metrics:completed"))

            pipe.execute()

        logger.debug(f"Job {job_id_str} completed successfully")

    def fail(self, job_id: UUID, error: str, retry: bool = True) -> None:
        """Mark job as failed.

        Args:
            job_id: Job identifier
            error: Error message/traceback
            retry: Whether to retry (if retries remaining)
        """
        if not self._redis:
            raise ConnectionError("Redis connection not initialized")

        job_id_str = str(job_id)

        # Get job data to check retry count
        job_data = self._redis.hget(self._key("data"), job_id_str)
        if not job_data:
            logger.warning(f"Job {job_id_str} not found")
            return

        if isinstance(job_data, bytes):
            job_data = job_data.decode("utf-8")

        job = JobDefinition.from_json(job_data)

        # Get current attempt count
        attempts_key = self._key(f"attempts:{job_id_str}")
        attempts = cast(int, self._redis.incr(attempts_key))

        should_retry = retry and attempts <= job.max_retries

        if should_retry:
            # Calculate retry delay with exponential backoff + jitter
            delay = job.retry_delay * (job.retry_backoff ** (attempts - 1))
            jitter = random.uniform(0, delay * 0.1)  # 10% jitter
            total_delay = min(delay + jitter, 300.0)  # Max 5 minutes

            # Requeue with delay
            retry_time = datetime.now(UTC).timestamp() + total_delay
            score = (-job.priority.value * 1e9) + retry_time

            with self._redis.pipeline(transaction=True) as pipe:
                # Update status to RETRYING
                pipe.hset(self._key("status"), job_id_str, JobStatus.RETRYING.value)

                # Store error
                pipe.hset(self._key("error"), job_id_str, error)

                # Add back to queue with new score
                priority_queue_key = self._key(f"queue:p{job.priority.value}")
                pipe.zadd(priority_queue_key, {job_id_str: score})

                # Remove worker assignment
                pipe.hdel(self._key("worker"), job_id_str)

                # Increment retry counter
                pipe.incr(self._key("metrics:retried"))

                pipe.execute()

            logger.info(
                f"Job {job_id_str} will retry in {total_delay:.1f}s (attempt {attempts}/{job.max_retries})"
            )
        else:
            # Move to dead letter queue
            with self._redis.pipeline(transaction=True) as pipe:
                # Update status to DEAD_LETTER
                pipe.hset(self._key("status"), job_id_str, JobStatus.DEAD_LETTER.value)

                # Store final error
                pipe.hset(self._key("error"), job_id_str, error)

                # Add to dead letter list (keep last N)
                pipe.lpush(self._key("dead_letter"), job_id_str)
                pipe.ltrim(self._key("dead_letter"), 0, self.max_dead_letters - 1)

                # Remove worker assignment
                pipe.hdel(self._key("worker"), job_id_str)

                # Increment dead letter counter
                pipe.incr(self._key("metrics:dead_letter"))

                pipe.execute()

            logger.error(f"Job {job_id_str} moved to dead letter queue after {attempts} attempts")

    def cancel(self, job_id: UUID) -> bool:
        """Cancel a pending job.

        Args:
            job_id: Job identifier

        Returns:
            True if cancelled, False if already running/completed
        """
        if not self._redis:
            raise ConnectionError("Redis connection not initialized")

        job_id_str = str(job_id)

        # Get current status
        status_bytes = self._redis.hget(self._key("status"), job_id_str)
        if not status_bytes:
            return False

        status = status_bytes.decode("utf-8") if isinstance(status_bytes, bytes) else status_bytes
        status_enum = JobStatus(status)

        # Can only cancel pending or retrying jobs
        if status_enum not in (JobStatus.PENDING, JobStatus.RETRYING):
            return False

        # Get job to find priority
        job_data = self._redis.hget(self._key("data"), job_id_str)
        if not job_data:
            return False

        if isinstance(job_data, bytes):
            job_data = job_data.decode("utf-8")

        job = JobDefinition.from_json(job_data)

        with self._redis.pipeline(transaction=True) as pipe:
            # Remove from priority queue
            priority_queue_key = self._key(f"queue:p{job.priority.value}")
            pipe.zrem(priority_queue_key, job_id_str)

            # Update status
            pipe.hset(self._key("status"), job_id_str, JobStatus.CANCELLED.value)

            # Increment cancelled counter
            pipe.incr(self._key("metrics:cancelled"))

            pipe.execute()

        logger.debug(f"Job {job_id_str} cancelled")
        return True

    def get_status(self, job_id: UUID) -> JobStatus | None:
        """Get current status of a job.

        Args:
            job_id: Job identifier

        Returns:
            Current JobStatus, or None if job not found
        """
        if not self._redis:
            raise ConnectionError("Redis connection not initialized")

        status_bytes = self._redis.hget(self._key("status"), str(job_id))
        if not status_bytes:
            return None

        status_str = (
            status_bytes.decode("utf-8") if isinstance(status_bytes, bytes) else status_bytes
        )
        return JobStatus(status_str)

    def get_result(self, job_id: UUID) -> JobResult | None:
        """Get result of a completed job.

        Args:
            job_id: Job identifier

        Returns:
            JobResult if job completed, None if not found or not finished
        """
        if not self._redis:
            raise ConnectionError("Redis connection not initialized")

        result_key = self._key(f"result:{str(job_id)}")
        result_data = self._redis.get(result_key)

        if not result_data:
            return None

        if isinstance(result_data, bytes):
            result_data = result_data.decode("utf-8")

        return JobResult.from_json(result_data)

    def list_jobs(
        self,
        status: JobStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[JobDefinition]:
        """List jobs, optionally filtered by status.

        Args:
            status: Filter by specific status (None = all jobs)
            limit: Maximum number of jobs to return
            offset: Number of jobs to skip (for pagination)

        Returns:
            List of job definitions matching criteria
        """
        if not self._redis:
            raise ConnectionError("Redis connection not initialized")

        # Get all job IDs with status
        status_map = self._redis.hgetall(self._key("status"))

        # Filter by status if specified
        if status:
            job_ids = [
                job_id
                for job_id, job_status in status_map.items()
                if (job_status.decode("utf-8") if isinstance(job_status, bytes) else job_status)
                == status.value
            ]
        else:
            job_ids = list(status_map.keys())

        # Get job data
        jobs = []
        if job_ids := job_ids[offset : offset + limit]:
            job_data_list = cast(
                Sequence[bytes | None], self._redis.hmget(self._key("data"), *job_ids)
            )
            for job_data in job_data_list:
                if job_data:
                    decoded_data = (
                        job_data.decode("utf-8") if isinstance(job_data, bytes) else job_data
                    )
                    jobs.append(JobDefinition.from_json(decoded_data))

        return jobs

    def get_dead_letters(self, limit: int = 100) -> list[JobDefinition]:
        """Get jobs that failed permanently (dead letter queue).

        Args:
            limit: Maximum number of jobs to return

        Returns:
            List of permanently failed jobs
        """
        if not self._redis:
            raise ConnectionError("Redis connection not initialized")

        # Get job IDs from dead letter list
        job_ids = cast(
            Sequence[bytes | str], self._redis.lrange(self._key("dead_letter"), 0, limit - 1)
        )

        # Get job data
        jobs = []
        if job_ids:
            job_data_list = cast(
                Sequence[bytes | None], self._redis.hmget(self._key("data"), *job_ids)
            )
            for job_data in job_data_list:
                if job_data:
                    decoded_data = (
                        job_data.decode("utf-8") if isinstance(job_data, bytes) else job_data
                    )
                    jobs.append(JobDefinition.from_json(decoded_data))

        return jobs

    def requeue_dead_letter(self, job_id: UUID) -> bool:
        """Move a dead-letter job back to pending queue.

        Args:
            job_id: Job identifier

        Returns:
            True if requeued, False if job not in dead letter queue
        """
        if not self._redis:
            raise ConnectionError("Redis connection not initialized")

        job_id_str = str(job_id)

        # Check if in dead letter queue
        status = self.get_status(job_id)
        if status != JobStatus.DEAD_LETTER:
            return False

        # Get job data
        job_data = self._redis.hget(self._key("data"), job_id_str)
        if not job_data:
            return False

        if isinstance(job_data, bytes):
            job_data = job_data.decode("utf-8")

        job = JobDefinition.from_json(job_data)

        with self._redis.pipeline(transaction=True) as pipe:
            # Remove from dead letter list
            pipe.lrem(self._key("dead_letter"), 0, job_id_str)

            # Reset attempts
            pipe.delete(self._key(f"attempts:{job_id_str}"))

            # Update status to PENDING
            pipe.hset(self._key("status"), job_id_str, JobStatus.PENDING.value)

            # Add back to priority queue
            score = (-job.priority.value * 1e9) + datetime.now(UTC).timestamp()
            priority_queue_key = self._key(f"queue:p{job.priority.value}")
            pipe.zadd(priority_queue_key, {job_id_str: score})

            pipe.execute()

        logger.info(f"Job {job_id_str} requeued from dead letter")
        return True

    def purge(self, status: JobStatus | None = None) -> int:
        """Remove jobs from queue.

        Args:
            status: Remove only jobs with this status (None = all jobs)

        Returns:
            Number of jobs removed
        """
        if not self._redis:
            raise ConnectionError("Redis connection not initialized")

        # Get all job IDs with status
        status_map = self._redis.hgetall(self._key("status"))

        # Filter by status if specified
        if status:
            job_ids = [
                job_id
                for job_id, job_status in status_map.items()
                if (job_status.decode("utf-8") if isinstance(job_status, bytes) else job_status)
                == status.value
            ]
        else:
            job_ids = list(status_map.keys())

        if not job_ids:
            return 0

        # Get job priorities for queue cleanup
        job_data_list = cast(Sequence[bytes | None], self._redis.hmget(self._key("data"), *job_ids))
        priority_sets = {}
        for job_id, data in zip(job_ids, job_data_list, strict=False):
            if data:
                decoded_data = data.decode("utf-8") if isinstance(data, bytes) else data
                job = JobDefinition.from_json(decoded_data)
                priority_sets.setdefault(job.priority.value, []).append(job_id)

        # Remove in pipeline
        with self._redis.pipeline(transaction=True) as pipe:
            # Remove from data, status, worker, error hashes
            pipe.hdel(self._key("data"), *job_ids)
            pipe.hdel(self._key("status"), *job_ids)
            pipe.hdel(self._key("worker"), *job_ids)
            pipe.hdel(self._key("error"), *job_ids)

            # Remove from priority queues
            for priority, ids in priority_sets.items():
                pipe.zrem(self._key(f"queue:p{priority}"), *ids)

            # Remove from dead letter list
            for job_id in job_ids:
                pipe.lrem(self._key("dead_letter"), 0, job_id)

            # Remove attempts counters
            for job_id in job_ids:
                pipe.delete(self._key(f"attempts:{job_id}"))

            # Remove results
            for job_id in job_ids:
                pipe.delete(self._key(f"result:{job_id}"))

            pipe.execute()

        count = len(job_ids)
        logger.info(f"Purged {count} jobs (status={status})")
        return count

    def get_metrics(self) -> dict[str, Any]:
        """Get queue metrics.

        Returns:
            Dictionary with metrics
        """
        if not self._redis:
            raise ConnectionError("Redis connection not initialized")

        # Get status counts
        status_map = self._redis.hgetall(self._key("status"))
        status_counts = {
            status.value: sum(
                bool((s.decode("utf-8") if isinstance(s, bytes) else s) == status.value)
                for s in status_map.values()
            )
            for status in JobStatus
        }
        # Get lifetime counters
        metrics_keys = [
            "metrics:submitted",
            "metrics:completed",
            "metrics:retried",
            "metrics:dead_letter",
            "metrics:cancelled",
        ]
        metrics_values = cast(
            Sequence[bytes | None], self._redis.mget([self._key(k) for k in metrics_keys])
        )

        submitted = int(metrics_values[0] or 0)
        completed = int(metrics_values[1] or 0)
        retried = int(metrics_values[2] or 0)
        dead_letter = int(metrics_values[3] or 0)
        cancelled = int(metrics_values[4] or 0)

        return {
            "pending": status_counts.get(JobStatus.PENDING.value, 0),
            "running": status_counts.get(JobStatus.RUNNING.value, 0),
            "completed": status_counts.get(JobStatus.COMPLETED.value, 0),
            "failed": status_counts.get(JobStatus.FAILED.value, 0),
            "dead_letter": status_counts.get(JobStatus.DEAD_LETTER.value, 0),
            "retrying": status_counts.get(JobStatus.RETRYING.value, 0),
            "cancelled": status_counts.get(JobStatus.CANCELLED.value, 0),
            "total_submitted": submitted,
            "total_completed": completed,
            "total_retried": retried,
            "total_dead_letter": dead_letter,
            "total_cancelled": cancelled,
        }
