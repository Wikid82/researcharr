"""Lightweight in-process background task execution.

This manager provides a simple thread-pool backed facility for executing
callables outside the request/foreground context when the full job queue
is disabled. It is intentionally minimal and keeps all state in-memory.

Features:
    - ThreadPool execution (no asyncio loop dependency)
    - Lifecycle events (submitted, started, completed, failed)
    - Automatic TTL-based cleanup of terminal tasks
    - Unified status serialization aligned with JobResult schema

It is NOT a replacement for the distributed job queue; it serves as a
fallback so endpoints can still return quickly while longer work runs.
"""

from __future__ import annotations

import concurrent.futures as _futures
import os
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional


@dataclass
class BackgroundTask:
    id: str
    created: float
    func_repr: str
    status: str = "pending"  # pending|running|completed|failed|cancelled
    result: Any = None
    error: Optional[str] = None
    started: Optional[float] = None
    finished: Optional[float] = None
    cancel_requested: bool = False
    _cancel_event: Optional[threading.Event] = None  # internal cooperative flag

    def to_dict(self) -> Dict[str, Any]:
        """Serialize task similar to JobResult schema for UI consistency."""
        return {
            "job_id": self.id,
            "status": self.status,
            "result": self.result if self.status == "completed" else None,
            "error": self.error,
            "started_at": _iso(self.started),
            "completed_at": _iso(self.finished),
            "attempts": 1,
            "worker_id": "background",
            "duration": (self.finished - self.started) if self.started and self.finished else None,
            "type": "background",
            "cancel_requested": self.cancel_requested,
            "cancellable": self.status in ("pending", "running"),
        }


def _iso(ts: Optional[float]) -> Optional[str]:  # pragma: no cover - trivial
    if ts is None:
        return None
    try:
        from datetime import datetime, UTC
        return datetime.fromtimestamp(ts, UTC).isoformat()
    except Exception:
        return None


class BackgroundTaskManager:
    def __init__(self, max_workers: int = 4, *, event_bus: Any | None = None, ttl_seconds: int | None = None):
        self._executor = _futures.ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="bg-task")
        self._tasks: Dict[str, BackgroundTask] = {}
        self._futures: Dict[str, _futures.Future] = {}
        self._lock = threading.Lock()
        self._event_bus = event_bus
        # TTL for terminal tasks (completed/failed); default from env or 300s
        self._ttl = ttl_seconds if ttl_seconds is not None else int(os.getenv("BACKGROUND_TASK_TTL", "300"))

    def submit(self, fn: Callable[..., Any], *args, **kwargs) -> str:
        tid = uuid.uuid4().hex
        task = BackgroundTask(id=tid, created=time.time(), func_repr=repr(fn))
        with self._lock:
            self._tasks[tid] = task
        self._emit("background.task.submitted", task)
        self._prune_expired_locked()

        def _run():
            task.started = time.time()
            task.status = "running"
            self._emit("background.task.started", task)
            try:
                # Cooperative cancellation support: if function accepts cancel_event kw
                import inspect
                sig = None
                try:
                    sig = inspect.signature(fn)
                except Exception:
                    sig = None
                if sig and "cancel_event" in sig.parameters:
                    task._cancel_event = threading.Event()
                    kwargs = dict(kwargs)
                    kwargs.setdefault("cancel_event", task._cancel_event)
                task.result = fn(*args, **kwargs)
                if task.cancel_requested and task._cancel_event and task._cancel_event.is_set():
                    # Function returned after seeing cancellation; treat as cancelled
                    task.status = "cancelled"
                    self._emit("background.task.cancelled", task)
                else:
                    task.status = "completed"
                    self._emit("background.task.completed", task)
            except Exception as e:  # pragma: no cover - broad resilience
                task.error = f"{type(e).__name__}: {e}"
                task.status = "failed"
                self._emit("background.task.failed", task)
            finally:
                task.finished = time.time()
                # Final prune pass
                with self._lock:
                    self._prune_expired_locked()

        fut = self._executor.submit(_run)
        self._futures[tid] = fut
        return tid

    def get(self, task_id: str) -> Optional[BackgroundTask]:
        with self._lock:
            task = self._tasks.get(task_id)
            self._prune_expired_locked()
            return task

    def list(self) -> list[BackgroundTask]:  # pragma: no cover - debug helper
        with self._lock:
            self._prune_expired_locked()
            return list(self._tasks.values())

    def shutdown(self, wait: bool = True):  # pragma: no cover - app lifecycle
        self._executor.shutdown(wait=wait, cancel_futures=False)

    # Convenience wrapper mirroring job queue style for backups
    def submit_backup_create(self, create_fn: Callable[..., Any], config_root: str, backups_dir: str, prefix: str = "") -> str:
        return self.submit(create_fn, config_root, backups_dir, prefix)

    def submit_backup_restore(self, restore_fn: Callable[..., Any], backup_path: str, config_root: str) -> str:
        return self.submit(restore_fn, backup_path, config_root)

    # Internal helpers -------------------------------------------------
    def _emit(self, event: str, task: BackgroundTask):  # pragma: no cover - simple publish
        if not self._event_bus:
            return None
        try:
            self._event_bus.publish(event, {"task": task.to_dict()})
        except Exception:
            return None

    def _prune_expired_locked(self):  # assumes caller holds _lock
        now = time.time()
        if self._ttl <= 0:
            return None
        remove: list[str] = []
        for tid, t in self._tasks.items():
            if t.status in ("completed", "failed", "cancelled") and t.finished:
                if (now - t.finished) > self._ttl:
                    remove.append(tid)
        for tid in remove:
            self._tasks.pop(tid, None)

    # Public prune (manual trigger) ------------------------------------
    def prune_expired(self):  # pragma: no cover - manual utility
        with self._lock:
            self._prune_expired_locked()

    # Unified serialization convenience --------------------------------
    def serialize(self, task_id: str) -> Dict[str, Any] | None:
        t = self.get(task_id)
        return t.to_dict() if t else None

    # Cancellation ------------------------------------------------------
    def cancel(self, task_id: str) -> bool:
        """Attempt to cancel a task.

        Returns True if cancellation succeeded or was requested. Pending
        tasks are cancelled immediately. Running tasks set a cooperative
        flag if supported; otherwise we mark cancel_requested and allow
        normal completion.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False
            # Pending: attempt future cancellation
            if task.status == "pending":
                fut = self._futures.get(task_id)
                # Mark cancelled regardless; Python may have already scheduled _run.
                # If future.cancel() returns False the task likely started; we will
                # proceed to running cancellation logic below.
                cancelled_future = bool(fut.cancel() if fut else False)
                if cancelled_future:
                    task.status = "cancelled"
                    task.finished = time.time()
                    self._emit("background.task.cancelled", task)
                    return True
                # Treat as running if scheduled
            if task.status == "running":
                task.cancel_requested = True
                if task._cancel_event:
                    task._cancel_event.set()
                self._emit("background.task.cancel.requested", task)
                return True
            # Already terminal
            return False

__all__ = ["BackgroundTaskManager", "BackgroundTask"]
