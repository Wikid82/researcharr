"""Lightweight in-process background task execution.

This manager provides a simple thread-pool backed facility for executing
callables outside the request/foreground context when the full job queue
is disabled. It is intentionally minimal and keeps all state in-memory.

It is NOT a replacement for the distributed job queue; it serves as a
fallback so endpoints can still return quickly while longer work runs.
"""

from __future__ import annotations

import concurrent.futures as _futures
import threading
import time
import uuid
from dataclasses import dataclass, field
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


class BackgroundTaskManager:
    def __init__(self, max_workers: int = 4):
        self._executor = _futures.ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="bg-task")
        self._tasks: Dict[str, BackgroundTask] = {}
        self._lock = threading.Lock()

    def submit(self, fn: Callable[..., Any], *args, **kwargs) -> str:
        tid = uuid.uuid4().hex
        task = BackgroundTask(id=tid, created=time.time(), func_repr=repr(fn))
        with self._lock:
            self._tasks[tid] = task

        def _run():
            task.started = time.time()
            task.status = "running"
            try:
                task.result = fn(*args, **kwargs)
                task.status = "completed"
            except Exception as e:  # pragma: no cover - broad resilience
                task.error = f"{type(e).__name__}: {e}"
                task.status = "failed"
            finally:
                task.finished = time.time()

        self._executor.submit(_run)
        return tid

    def get(self, task_id: str) -> Optional[BackgroundTask]:
        with self._lock:
            return self._tasks.get(task_id)

    def list(self) -> list[BackgroundTask]:  # pragma: no cover - debug helper
        with self._lock:
            return list(self._tasks.values())

    def shutdown(self, wait: bool = True):  # pragma: no cover - app lifecycle
        self._executor.shutdown(wait=wait, cancel_futures=False)

    # Convenience wrapper mirroring job queue style for backups
    def submit_backup_create(self, create_fn: Callable[..., Any], config_root: str, backups_dir: str, prefix: str = "") -> str:
        return self.submit(create_fn, config_root, backups_dir, prefix)

    def submit_backup_restore(self, restore_fn: Callable[..., Any], backup_path: str, config_root: str) -> str:
        return self.submit(restore_fn, backup_path, config_root)

__all__ = ["BackgroundTaskManager", "BackgroundTask"]
