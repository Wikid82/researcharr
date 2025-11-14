"""Thread-based worker pool implementation."""

from __future__ import annotations

import importlib
import logging
import os
import threading
import time
import traceback
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from .queue import JobQueue
from .types import JobDefinition, JobProgress, JobResult, JobStatus
from .worker import WorkerInfo, WorkerPool, WorkerStatus

logger = logging.getLogger(__name__)


class ThreadedWorker:
    """Single threaded worker that processes jobs from queue."""

    def __init__(
        self,
        worker_id: str,
        queue: JobQueue,
        handlers: dict[str, Callable],
        event_callback: Callable[[str, dict[str, Any]], Any] | None = None,
    ):
        """Initialize worker.

        Args:
            worker_id: Unique worker identifier
            queue: Job queue to pull from
            handlers: Dict mapping handler names to callables
            event_callback: Optional callback for events (sync function)
        """
        self.worker_id = worker_id
        self.queue = queue
        self.handlers = handlers
        self.event_callback = event_callback

        self.info = WorkerInfo(
            id=worker_id,
            status=WorkerStatus.IDLE,
            hostname=os.uname().nodename,
            pid=os.getpid(),
        )

        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._heartbeat_thread: threading.Thread | None = None

    def _emit(self, name: str, payload: dict[str, Any]) -> None:
        """Emit an event through the callback."""
        if not self.event_callback:
            return
        try:
            self.event_callback(name, payload)
        except Exception:
            logger.exception("Event callback error for %s", name)

    def start(self) -> None:
        """Start the worker."""
        if self._thread and self._thread.is_alive():
            logger.warning(f"Worker {self.worker_id} already running")
            return

        self.info.status = WorkerStatus.IDLE
        self.info.started_at = datetime.now(UTC)
        self._stop_event.clear()

        # Start worker thread
        self._thread = threading.Thread(target=self._run_loop, name=f"worker-{self.worker_id}", daemon=True)
        self._thread.start()

        # Start heartbeat thread
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            name=f"heartbeat-{self.worker_id}",
            daemon=True
        )
        self._heartbeat_thread.start()

        logger.info(f"Worker {self.worker_id} started (PID: {self.info.pid})")

    def stop(self, graceful: bool = True, timeout: float = 30.0) -> None:
        """Stop the worker.

        Args:
            graceful: Wait for current job to complete
            timeout: Max time to wait
        """
        if not self._thread or not self._thread.is_alive():
            return

        self.info.status = WorkerStatus.STOPPING
        self._stop_event.set()

        if graceful and self._thread:
            self._thread.join(timeout=timeout)
            if self._thread.is_alive():
                logger.warning(f"Worker {self.worker_id} did not stop gracefully within timeout")

        # Stop heartbeat
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=1.0)

        self.info.status = WorkerStatus.STOPPED
        logger.info(f"Worker {self.worker_id} stopped")

    def _run_loop(self) -> None:
        """Main worker loop."""
        while not self._stop_event.is_set():
            try:
                # Get next job
                job = self.queue.get_next(self.worker_id)

                if job is None:
                    # No jobs available, wait a bit
                    time.sleep(0.5)
                    continue

                # Execute job
                self._execute_job(job)

            except Exception as e:
                logger.error(f"Worker {self.worker_id} error in main loop: {e}")
                self.info.status = WorkerStatus.ERROR
                time.sleep(1)  # Brief pause before retrying

    def _execute_job(self, job: JobDefinition) -> None:
        """Execute a single job.

        Args:
            job: Job to execute
        """
        self.info.status = WorkerStatus.BUSY
        self.info.current_job = job.id

        started_at = datetime.now(UTC)
        result = JobResult(
            job_id=job.id,
            status=JobStatus.RUNNING,
            worker_id=self.worker_id,
            started_at=started_at,
        )

        logger.info(f"Worker {self.worker_id} executing job {job.id} ({job.handler})")

        # Publish job started event
        self._emit(
            "job.started",
            {
                "job_id": str(job.id),
                "worker_id": self.worker_id,
                "handler": job.handler,
                "attempt": result.attempts + 1,
            },
        )

        try:
            # Get handler
            handler = self._get_handler(job.handler)

            # Create progress callback
            def progress_callback(current: int, total: int | None = None, message: str = ""):
                progress = JobProgress(
                    job_id=job.id,
                    current=current,
                    total=total,
                    message=message,
                )
                self._emit("job.progress", progress.to_dict())

            # Execute with timeout (using threading.Timer for timeout)
            if job.timeout:
                timer = threading.Timer(job.timeout, lambda: None)
                timer.start()
                try:
                    output = handler(job, progress_callback)
                finally:
                    timer.cancel()
            else:
                output = handler(job, progress_callback)

            # Job succeeded
            result.status = JobStatus.COMPLETED
            result.result = output
            result.completed_at = datetime.now(UTC)

            self.queue.complete(job.id, result)

            self.info.jobs_completed += 1

            logger.info(f"Worker {self.worker_id} completed job {job.id} in {result.duration:.2f}s")

            # Publish job completed event
            self._emit(
                "job.completed",
                {
                    "job_id": str(job.id),
                    "duration": result.duration,
                    "worker_id": self.worker_id,
                },
            )

        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
            logger.error(f"Worker {self.worker_id} job {job.id} failed: {e}")

            self.queue.fail(job.id, error_msg, retry=True)
            self.info.jobs_failed += 1

            self._emit(
                "job.failed",
                {
                    "job_id": str(job.id),
                    "error": str(e),
                    "will_retry": True,
                },
            )

        finally:
            self.info.status = WorkerStatus.IDLE
            self.info.current_job = None

    def _get_handler(self, handler_name: str) -> Callable:
        """Get handler function by name.

        Args:
            handler_name: Handler name or fully qualified path

        Returns:
            Handler callable

        Raises:
            ValueError: If handler not found
        """
        # Check registered handlers first
        if handler_name in self.handlers:
            return self.handlers[handler_name]

        # Try to import from fully qualified path
        try:
            module_path, func_name = handler_name.rsplit(".", 1)
            module = importlib.import_module(module_path)
            return getattr(module, func_name)
        except (ValueError, ImportError, AttributeError) as e:
            raise ValueError(f"Handler not found: {handler_name}") from e

    def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats."""
        while not self._stop_event.is_set():
            try:
                self.info.last_heartbeat = datetime.now(UTC)
                time.sleep(10)  # Heartbeat every 10 seconds
            except Exception:
                break


class ThreadedWorkerPool(WorkerPool):
    """Thread-based worker pool."""

    def __init__(
        self,
        queue: JobQueue,
        handlers: dict[str, Callable] | None = None,
        event_callback: Callable[[str, dict[str, Any]], Any] | None = None,
    ):
        """Initialize worker pool.

        Args:
            queue: Job queue
            handlers: Dict mapping handler names to callables
            event_callback: Optional callback for events
        """
        self.queue = queue
        self.handlers = handlers or {}
        self.event_callback = event_callback

        self._workers: dict[str, ThreadedWorker] = {}
        self._worker_counter = 0
        self._lock = threading.Lock()

    def register_handler(self, name: str, handler: Callable) -> None:
        """Register a job handler.

        Args:
            name: Handler name
            handler: Callable(job, progress_callback)
        """
        self.handlers[name] = handler
        logger.debug(f"Registered handler: {name}")

    def start(self, count: int = 1) -> None:
        """Start worker threads.

        Args:
            count: Number of workers to start

        Raises:
            ValueError: If count < 1
        """
        if count < 1:
            raise ValueError("Worker count must be at least 1")

        logger.info(f"Starting {count} workers")

        with self._lock:
            for _ in range(count):
                worker_id = f"worker-{self._worker_counter}"
                self._worker_counter += 1

                worker = ThreadedWorker(
                    worker_id=worker_id,
                    queue=self.queue,
                    handlers=self.handlers,
                    event_callback=self.event_callback,
                )

                worker.start()
                self._workers[worker_id] = worker

        logger.info(f"Worker pool started with {len(self._workers)} workers")

    def stop(self, graceful: bool = True, timeout: float = 30.0) -> None:
        """Stop all workers.

        Args:
            graceful: Wait for current jobs to complete
            timeout: Max time to wait for graceful shutdown
        """
        if not self._workers:
            return

        logger.info(f"Stopping {len(self._workers)} workers (graceful={graceful})")

        # Stop all workers
        threads = []
        for worker in self._workers.values():
            thread = threading.Thread(target=worker.stop, args=(graceful, timeout))
            thread.start()
            threads.append(thread)

        # Wait for all to stop
        for thread in threads:
            thread.join(timeout=timeout)

        with self._lock:
            self._workers.clear()

        logger.info("Worker pool stopped")

    def scale(self, target_count: int) -> None:
        """Scale workers to target count.

        Args:
            target_count: Desired number of workers
        """
        with self._lock:
            current_count = len(self._workers)

            if target_count == current_count:
                return

            if target_count > current_count:
                # Scale up
                self.start(target_count - current_count)
            else:
                # Scale down
                stop_count = current_count - target_count
                workers_to_stop = list(self._workers.values())[:stop_count]

                for worker in workers_to_stop:
                    worker.stop(graceful=True)
                    self._workers.pop(worker.worker_id, None)

        logger.info(f"Scaled worker pool from {current_count} to {target_count}")

    def get_workers(self) -> list[WorkerInfo]:
        """Get information about all workers.

        Returns:
            List of worker information objects
        """
        with self._lock:
            return [worker.info for worker in self._workers.values()]

    def get_worker(self, worker_id: str) -> WorkerInfo | None:
        """Get information about a specific worker.

        Args:
            worker_id: Worker identifier

        Returns:
            WorkerInfo if found, None otherwise
        """
        with self._lock:
            worker = self._workers.get(worker_id)
            return worker.info if worker else None

    def restart_worker(self, worker_id: str) -> bool:
        """Restart a specific worker.

        Args:
            worker_id: Worker identifier

        Returns:
            True if restarted, False if worker not found
        """
        with self._lock:
            worker = self._workers.get(worker_id)
            if not worker:
                return False

            # Stop and restart
            worker.stop(graceful=True)
            worker.start()

        logger.info(f"Restarted worker {worker_id}")
        return True

    def heartbeat(self, worker_id: str) -> None:
        """Update worker heartbeat timestamp.

        Args:
            worker_id: Worker identifier
        """
        with self._lock:
            if worker := self._workers.get(worker_id):
                worker.info.last_heartbeat = datetime.now(UTC)

    def get_metrics(self) -> dict[str, Any]:
        """Get worker pool metrics.

        Returns:
            Dictionary with metrics
        """
        workers = self.get_workers()

        total = len(workers)
        idle = sum(bool(w.status == WorkerStatus.IDLE) for w in workers)
        busy = sum(bool(w.status == WorkerStatus.BUSY) for w in workers)
        healthy = sum(bool(w.is_healthy) for w in workers)
        unhealthy = total - healthy

        total_completed = sum(w.jobs_completed for w in workers)
        total_failed = sum(w.jobs_failed for w in workers)

        return {
            "total": total,
            "idle": idle,
            "busy": busy,
            "healthy": healthy,
            "unhealthy": unhealthy,
            "avg_jobs_per_worker": total_completed / total if total > 0 else 0,
            "total_jobs_completed": total_completed,
            "total_jobs_failed": total_failed,
        }
