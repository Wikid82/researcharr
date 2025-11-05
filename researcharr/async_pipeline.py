"""Async-first processing pipeline (minimal prototype).

This provides a small, well-documented async Pipeline and Stage interface so
we can iterate on the API for Issue #107.

Design notes:
- Stages are async callables or objects with `async def process(self, item)`.
- Pipeline connects stages with asyncio.Queues. Each stage runs `concurrency`
  tasks consuming from its input queue and producing to the next queue.
- Basic per-stage retry support (retry attempts + simple backoff).
- Provides start/stop semantics and a simple push(item) API.

This is intentionally small: we can extend with metrics, ordering guarantees,
backpressure strategies and sync-callable wrappers later.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, List, Optional

logger = logging.getLogger(__name__)


class Stage:
    """Abstract stage type: implement `async def process(self, item)`."""

    async def process(self, item: Any) -> Any:
        raise NotImplementedError()


@dataclass
class _StageSpec:
    stage: Stage
    concurrency: int
    max_queue: int
    max_retries: int


class Pipeline:
    """An async-first pipeline composed of stages.

    Usage:
        p = Pipeline()
        p.add_stage(MyStage(), concurrency=4)
        await p.start()
        await p.push(item)
        await p.shutdown(drain=True)
    """

    def __init__(self) -> None:
        self._stage_specs: List[_StageSpec] = []
        self._queues: List[asyncio.Queue] = []
        self._workers: List[asyncio.Task] = []
        self._started = False
        self._closed = False

    def add_stage(self, stage: Stage, *, concurrency: int = 1, max_queue: int = 100, max_retries: int = 0) -> None:
        if self._started:
            raise RuntimeError("cannot add stage after start")
        if concurrency < 1:
            raise ValueError("concurrency must be >= 1")
        self._stage_specs.append(_StageSpec(stage=stage, concurrency=concurrency, max_queue=max_queue, max_retries=max_retries))

    async def start(self) -> None:
        if self._started:
            return
        self._started = True
        # Create queues: one input queue per stage, plus a final output queue
        self._queues = [asyncio.Queue(spec.max_queue) for spec in self._stage_specs] + [asyncio.Queue(0)]
        # Start workers for each stage
        for idx, spec in enumerate(self._stage_specs):
            for _ in range(spec.concurrency):
                t = asyncio.create_task(self._run_stage(idx, spec))
                self._workers.append(t)

    async def _run_stage(self, idx: int, spec: _StageSpec) -> None:
        in_q = self._queues[idx]
        out_q = self._queues[idx + 1]
        while True:
            try:
                wrapper = await in_q.get()
            except asyncio.CancelledError:
                break
            if wrapper is None:
                # sentinel: pass downstream and exit
                try:
                    await out_q.put(None)
                except Exception:
                    pass
                in_q.task_done()
                break
            item, attempts_left = wrapper
            try:
                res = await spec.stage.process(item)
                # push result forward (allow None to mean drop)
                if res is not None:
                    await out_q.put((res, spec.max_retries))
            except Exception:  # noqa: BLE001 - we want to catch stage errors
                logger.exception("Stage %s failed for item=%r", spec.stage, item)
                if attempts_left > 0:
                    # simple retry: re-enqueue with attempts_left-1 after backoff
                    delay = 0.1
                    try:
                        await asyncio.sleep(delay)
                        await in_q.put((item, attempts_left - 1))
                    except Exception:
                        logger.exception("Failed to re-enqueue item for retry: %r", item)
                else:
                    # final failure: log and drop
                    logger.error("Dropping item after retries exhausted: %r", item)
            finally:
                in_q.task_done()

    async def push(self, item: Any) -> None:
        if not self._started:
            raise RuntimeError("pipeline not started")
        if self._closed:
            raise RuntimeError("pipeline is closed")
        # Enqueue into first stage with attempts_left = spec.max_retries
        if not self._stage_specs:
            # no stages: nothing to do
            return
        first_spec = self._stage_specs[0]
        await self._queues[0].put((item, first_spec.max_retries))

    async def shutdown(self, *, drain: bool = True, timeout: Optional[float] = 5.0) -> None:
        """Shutdown the pipeline.

        If drain=True, wait for all queues to be processed. Otherwise, cancel workers.
        """
        if not self._started or self._closed:
            return
        self._closed = True
        if drain:
            # wait for input queues to be empty and then send sentinel None to each stage
            for q in self._queues[:-1]:
                await q.join()
            # propagate sentinel through pipeline: put None into first queue for each worker
            for _ in range(len(self._workers)):
                try:
                    await self._queues[0].put(None)
                except Exception:
                    pass
            # wait for workers to exit
            try:
                await asyncio.wait_for(asyncio.gather(*self._workers, return_exceptions=True), timeout=timeout)
            except Exception:
                # best-effort cancel
                for t in self._workers:
                    t.cancel()
        else:
            for t in self._workers:
                t.cancel()
            # give them a moment
            await asyncio.sleep(0)

    # Convenience helper to run a synchronous iterable source
    async def run_from_iterable(self, iterable) -> None:
        await self.start()
        for item in iterable:
            await self.push(item)
        await self.shutdown(drain=True)


__all__ = ["Pipeline", "Stage"]
