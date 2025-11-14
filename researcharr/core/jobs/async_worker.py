"""Asyncio-based worker pool implementation."""

from __future__ import annotations

import asyncio
import inspect
import importlib
import logging
import os
import traceback
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from .queue import JobQueue
from .types import JobDefinition, JobProgress, JobResult, JobStatus
from .worker import WorkerInfo, WorkerPool, WorkerStatus

logger = logging.getLogger(__name__)


class AsyncWorker:
    """Single async worker that processes jobs from queue."""

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
            event_callback: Optional callback for events (async function)
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

        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._heartbeat_task: asyncio.Task | None = None

    async def _emit(self, name: str, payload: dict[str, Any]) -> None:
        if not self.event_callback:
            return
        try:
            result = self.event_callback(name, payload)
            if inspect.isawaitable(result):
                await result
        except Exception:
            logger.exception("Event callback error for %s", name)

    async def start(self) -> None:
        """Start the worker."""
        if self._task and not self._task.done():
            logger.warning(f"Worker {self.worker_id} already running")
            return

        self.info.status = WorkerStatus.IDLE
        self.info.started_at = datetime.now(UTC)
        self._stop_event.clear()

        # Start worker loop
        self._task = asyncio.create_task(self._run_loop())

        # Start heartbeat
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        logger.info(f"Worker {self.worker_id} started (PID: {self.info.pid})")

    async def stop(self, graceful: bool = True, timeout: float = 30.0) -> None:
        """Stop the worker.

        Args:
            graceful: Wait for current job to complete
            timeout: Max time to wait
        """
        if not self._task or self._task.done():
            return

        self.info.status = WorkerStatus.STOPPING
        self._stop_event.set()

        if graceful:
            try:
                await asyncio.wait_for(self._task, timeout=timeout)
            except TimeoutError:
                logger.warning(f"Worker {self.worker_id} did not stop gracefully, cancelling")
                self._task.cancel()
        else:
            self._task.cancel()

        # Stop heartbeat
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()

        self.info.status = WorkerStatus.STOPPED
        logger.info(f"Worker {self.worker_id} stopped")

    async def _run_loop(self) -> None:
        """Main worker loop."""
        while not self._stop_event.is_set():
            try:
                # Get next job
                job = await self.queue.get_next(self.worker_id)

                if job is None:
                    # No jobs available, wait a bit
                    await asyncio.sleep(0.5)
                    continue

                # Execute job
                await self._execute_job(job)

            except asyncio.CancelledError:
                logger.info(f"Worker {self.worker_id} cancelled")
                break
            except Exception as e:
                logger.error(f"Worker {self.worker_id} error in main loop: {e}")
                self.info.status = WorkerStatus.ERROR
                await asyncio.sleep(1)  # Brief pause before retrying

    async def _execute_job(self, job: JobDefinition) -> None:
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
        await self._emit("job.started", {
            "job_id": str(job.id),
            "worker_id": self.worker_id,
            "handler": job.handler,
            "attempt": result.attempts + 1,
        })

        try:
            # Get handler
            handler = self._get_handler(job.handler)

            # Create progress callback
            async def progress_callback(current: int, total: int | None = None, message: str = ""):
                progress = JobProgress(
                    job_id=job.id,
                    current=current,
                    total=total,
                    message=message,
                )
                await self._emit("job.progress", progress.to_dict())

            # Execute with timeout
            if job.timeout:
                output = await asyncio.wait_for(
                    handler(job, progress_callback),
                    timeout=job.timeout,
                )
            else:
                output = await handler(job, progress_callback)

            # Job succeeded
            result.status = JobStatus.COMPLETED
            result.result = output
            result.completed_at = datetime.now(UTC)

            await self.queue.complete(job.id, result)

            self.info.jobs_completed += 1

            logger.info(
                f"Worker {self.worker_id} completed job {job.id} in {result.duration:.2f}s"
            )

            # Publish job completed event
            await self._emit("job.completed", {
                "job_id": str(job.id),
                "duration": result.duration,
                "worker_id": self.worker_id,
            })

        except TimeoutError:
            error_msg = f"Job timed out after {job.timeout}s"
            logger.error(f"Worker {self.worker_id} job {job.id} timed out")

            await self.queue.fail(job.id, error_msg, retry=True)
            self.info.jobs_failed += 1

            await self._emit("job.failed", {
                "job_id": str(job.id),
                "error": error_msg,
                "will_retry": True,
            })

        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
            logger.error(f"Worker {self.worker_id} job {job.id} failed: {e}")

            await self.queue.fail(job.id, error_msg, retry=True)
            self.info.jobs_failed += 1

            await self._emit("job.failed", {
                "job_id": str(job.id),
                "error": str(e),
                "will_retry": True,
            })

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
            handler = getattr(module, func_name)
            return handler
        except (ValueError, ImportError, AttributeError) as e:
            raise ValueError(f"Handler not found: {handler_name}") from e

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats."""
        while not self._stop_event.is_set():
            try:
                self.info.last_heartbeat = datetime.now(UTC)
                await asyncio.sleep(10)  # Heartbeat every 10 seconds
            except asyncio.CancelledError:
                break


class AsyncWorkerPool(WorkerPool):
    """Asyncio-based worker pool."""

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

        self._workers: dict[str, AsyncWorker] = {}
        self._worker_counter = 0

    def register_handler(self, name: str, handler: Callable) -> None:
        """Register a job handler.

        Args:
            name: Handler name
            handler: Async callable(job, progress_callback)
        """
        self.handlers[name] = handler
        logger.debug(f"Registered handler: {name}")

    async def start(self, count: int = 1) -> None:
        """Start worker processes.

        Args:
            count: Number of workers to start

        Raises:
            ValueError: If count < 1
        """
        if count < 1:
            raise ValueError("Worker count must be at least 1")

        logger.info(f"Starting {count} workers")

        for _ in range(count):
            worker_id = f"worker-{self._worker_counter}"
            self._worker_counter += 1

            worker = AsyncWorker(
                worker_id=worker_id,
                queue=self.queue,
                handlers=self.handlers,
                event_callback=self.event_callback,
            )

            await worker.start()
            self._workers[worker_id] = worker

        logger.info(f"Worker pool started with {len(self._workers)} workers")

    async def stop(self, graceful: bool = True, timeout: float = 30.0) -> None:
        """Stop all workers.

        Args:
            graceful: Wait for current jobs to complete
            timeout: Max time to wait for graceful shutdown
        """
        if not self._workers:
            return

        logger.info(f"Stopping {len(self._workers)} workers (graceful={graceful})")

        # Stop all workers concurrently
        await asyncio.gather(
            *[worker.stop(graceful, timeout) for worker in self._workers.values()],
            return_exceptions=True,
        )

        self._workers.clear()
        logger.info("Worker pool stopped")

    async def scale(self, target_count: int) -> None:
        """Scale workers to target count.

        Args:
            target_count: Desired number of workers
        """
        current_count = len(self._workers)

        if target_count == current_count:
            return

        if target_count > current_count:
            # Scale up
            await self.start(target_count - current_count)
        else:
            # Scale down
            stop_count = current_count - target_count
            workers_to_stop = list(self._workers.values())[:stop_count]

            await asyncio.gather(
                *[w.stop(graceful=True) for w in workers_to_stop],
                return_exceptions=True,
            )

            for worker in workers_to_stop:
                self._workers.pop(worker.worker_id, None)

        logger.info(f"Scaled worker pool from {current_count} to {target_count}")

    async def get_workers(self) -> list[WorkerInfo]:
        """Get information about all workers.

        Returns:
            List of worker information objects
        """
        return [worker.info for worker in self._workers.values()]

    async def get_worker(self, worker_id: str) -> WorkerInfo | None:
        """Get information about a specific worker.

        Args:
            worker_id: Worker identifier

        Returns:
            WorkerInfo if found, None otherwise
        """
        worker = self._workers.get(worker_id)
        return worker.info if worker else None

    async def restart_worker(self, worker_id: str) -> bool:
        """Restart a specific worker.

        Args:
            worker_id: Worker identifier

        Returns:
            True if restarted, False if worker not found
        """
        worker = self._workers.get(worker_id)
        if not worker:
            return False

        # Stop and restart
        await worker.stop(graceful=True)
        await worker.start()

        logger.info(f"Restarted worker {worker_id}")
        return True

    async def heartbeat(self, worker_id: str) -> None:
        """Update worker heartbeat timestamp.

        Args:
            worker_id: Worker identifier
        """
        worker = self._workers.get(worker_id)
        if worker:
            worker.info.last_heartbeat = datetime.now(UTC)

    async def get_metrics(self) -> dict[str, Any]:
        """Get worker pool metrics.

        Returns:
            Dictionary with metrics
        """
        workers = await self.get_workers()

        total = len(workers)
        idle = sum(1 for w in workers if w.status == WorkerStatus.IDLE)
        busy = sum(1 for w in workers if w.status == WorkerStatus.BUSY)
        healthy = sum(1 for w in workers if w.is_healthy)
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
