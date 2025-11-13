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
import importlib
import json
import logging
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


class Stage:
    """Abstract stage type: implement `async def process(self, item)`.

    Subclasses may optionally implement `async def setup(self)` and
    `async def teardown(self)` for lifecycle management. Default
    implementations are no-ops.
    """

    async def process(self, item: Any) -> Any:  # pragma: no cover - abstract
        raise NotImplementedError()

    async def setup(self) -> None:  # pragma: no cover - trivial default
        return None

    async def teardown(self) -> None:  # pragma: no cover - trivial default
        return None


def _callable_to_stage(fn: Callable[[Any], Any] | Callable[[Any], Awaitable[Any]]) -> Stage:
    """Wrap a callable (sync or async) into a Stage instance."""

    class _FnStage(Stage):
        async def process(self, item: Any) -> Any:
            res = fn(item)
            if asyncio.iscoroutine(res):
                return await res
            return res

    return _FnStage()


@dataclass
class _StageSpec:
    stage: Stage
    concurrency: int
    max_queue: int
    max_retries: int
    backoff_base: float = 0.1
    backoff_jitter: float = 0.0
    queue_full_policy: str | None = None
    queue_full_handler: Callable[[Any], Any] | None = None
    error_handler: Callable[[Exception, Any], Any] | None = None
    error_handler_name: str | None = None
    # runtime metrics
    metrics: dict[str, int] = field(default_factory=dict)


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
        self._stage_specs: list[_StageSpec] = []
        self._queues: list[asyncio.Queue] = []
        self._workers: list[asyncio.Task] = []
        self._progress_callbacks: list[Callable[[dict], Any]] = []
        self._started = False
        self._closed = False
        # monitoring / debugging
        self.debug: bool = False
        self._metrics_exporters: list[Callable[[dict], Any]] = []
        self._metrics_task: asyncio.Task | None = None
        # dead-letter items per-stage index: list of items that were dropped
        self._dead_letters: list[list[Any]] = []

    # handler registry is module-level; pipeline may reference names

    # Progress subscription --------------------------------------------------
    def subscribe_progress(self, cb: Callable[[dict], Any]) -> None:
        """Subscribe to progress events. Callback receives a single dict."""
        if cb not in self._progress_callbacks:
            self._progress_callbacks.append(cb)

    def unsubscribe_progress(self, cb: Callable[[dict], Any]) -> None:
        try:
            self._progress_callbacks.remove(cb)
        except ValueError:
            pass

    def _emit_progress(self, event: dict) -> None:
        # In debug mode, also log progress events at DEBUG level
        if self.debug:
            try:
                logger.debug("Progress event: %s", event)
            except Exception:  # nosec B110 -- intentional broad except for resilience
                pass
        for cb in list(self._progress_callbacks):
            try:
                cb(event)
            except Exception:  # nosec B110 -- intentional broad except for resilience
                logger.exception("Progress callback failed: %s", cb)

    def get_status(self) -> dict:
        """Return a snapshot of pipeline status and per-stage metrics."""
        stages = []
        for idx, spec in enumerate(self._stage_specs):
            stages.append(
                {
                    "index": idx,
                    "class": f"{spec.stage.__class__.__module__}.{spec.stage.__class__.__qualname__}",
                    "concurrency": spec.concurrency,
                    "queue_size": self._queues[idx].qsize() if self._queues else 0,
                    "metrics": dict(spec.metrics) if spec.metrics is not None else {},
                }
            )
        return {"started": self._started, "closed": self._closed, "stages": stages}

    def get_metrics(self) -> dict:
        """Return aggregated metrics and dead-letter counts.

        Returns a dict with per-stage metrics and dead-letter lists.
        """
        return {
            "stages": [
                {
                    "index": idx,
                    "metrics": dict(spec.metrics) if spec.metrics is not None else {},
                    "dead_letters": (
                        list(self._dead_letters[idx]) if idx < len(self._dead_letters) else []
                    ),
                }
                for idx, spec in enumerate(self._stage_specs)
            ]
        }

    # Dead-letter API -------------------------------------------------------
    def get_dead_letters(self, stage_index: int) -> list[Any]:
        if stage_index < 0 or stage_index >= len(self._dead_letters):
            raise IndexError("stage_index out of range")
        return list(self._dead_letters[stage_index])

    async def drain_dead_letters(self, stage_index: int, sink_cb: Callable[[Any], Any]) -> None:
        """Call sink_cb(item) for every dead-letter item and clear the list.

        sink_cb may be a sync or async callable.
        """
        items = self.get_dead_letters(stage_index)
        for item in items:
            try:
                res = sink_cb(item)
                if asyncio.iscoroutine(res):
                    await res
            except Exception:  # nosec B110 -- intentional broad except for resilience
                logger.exception("Dead-letter sink failed for item=%r", item)
        # clear
        self._dead_letters[stage_index].clear()

    def add_stage(
        self,
        stage: Stage | Callable[[Any], Any],
        *,
        concurrency: int = 1,
        max_queue: int = 100,
        max_retries: int = 0,
        backoff_base: float = 0.1,
        backoff_jitter: float = 0.0,
        error_handler: Callable[[Exception, Any], Any] | str | None = None,
        queue_full_policy: str | None = None,
        queue_full_handler: Callable[[Any], Any] | None = None,
    ) -> None:
        if self._started:
            raise RuntimeError("cannot add stage after start")
        if concurrency < 1:
            raise ValueError("concurrency must be >= 1")
        # Allow plain callables (sync/async) as stages by wrapping them
        if not isinstance(stage, Stage) and callable(stage):
            stage = _callable_to_stage(stage)
        # resolve error_handler if a name was provided
        resolved_error_handler = None
        error_handler_name = None
        if isinstance(error_handler, str):
            error_handler_name = error_handler
            resolved_error_handler = get_registered_handler(error_handler)
        elif callable(error_handler):
            resolved_error_handler = error_handler
            # try to find a registered name for this callable
            for nm, fn in HANDLER_REGISTRY.items():
                if fn is error_handler:
                    error_handler_name = nm
                    break

        spec = _StageSpec(
            stage=stage,
            concurrency=concurrency,
            max_queue=max_queue,
            max_retries=max_retries,
            backoff_base=backoff_base,
            backoff_jitter=backoff_jitter,
            error_handler=resolved_error_handler,
            error_handler_name=error_handler_name,
            queue_full_policy=queue_full_policy,
            queue_full_handler=queue_full_handler,
            metrics={
                "processed": 0,
                "failed": 0,
                "retried": 0,
                "dropped": 0,
                "in_flight": 0,
            },
        )

        self._stage_specs.append(spec)
        # maintain dead-letter placeholder
        self._dead_letters.append([])

    async def start(self) -> None:
        if self._started:
            return
        self._started = True
        # Create queues: one input queue per stage, plus a final output queue
        self._queues = [asyncio.Queue(spec.max_queue) for spec in self._stage_specs] + [
            asyncio.Queue(0)
        ]
        # Start workers for each stage
        for idx, spec in enumerate(self._stage_specs):
            # run setup lifecycle if present on the stage
            setup = getattr(spec.stage, "setup", None)
            if callable(setup):
                try:
                    maybe = setup()
                    if asyncio.iscoroutine(maybe):
                        await maybe
                except Exception:  # nosec B110 -- intentional broad except for resilience
                    logger.exception("Stage.setup failed for %s", spec.stage)

            for _ in range(spec.concurrency):
                t = asyncio.create_task(self._run_stage(idx, spec))
                self._workers.append(t)

        # start periodic metrics exporter if any exporters registered
        if self._metrics_exporters and self._metrics_task is None:
            self._metrics_task = asyncio.create_task(self._metrics_loop())

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
                except Exception:  # nosec B110 -- intentional broad except for resilience
                    pass
                in_q.task_done()
                break
            item, attempts_left = wrapper
            # update in-flight metric
            try:
                spec.metrics["in_flight"] += 1
                self._emit_progress(
                    {"type": "in_flight_inc", "stage": idx, "metrics": dict(spec.metrics or {})}
                )
            except Exception:  # nosec B110 -- intentional broad except for resilience
                pass
            try:
                res = await spec.stage.process(item)
                # push result forward (allow None to mean drop)
                if res is not None:
                    await out_q.put((res, spec.max_retries))
                # success
                try:
                    spec.metrics["processed"] += 1
                    self._emit_progress(
                        {"type": "processed", "stage": idx, "metrics": dict(spec.metrics or {})}
                    )
                except Exception:  # nosec B110 -- intentional broad except for resilience
                    pass
            except Exception as exc:  # noqa: BLE001 - we want to catch stage errors  # nosec B110 -- intentional broad except for resilience
                logger.exception("Stage %s failed for item=%r", spec.stage, item)
                if attempts_left > 0:
                    # exponential backoff: base * 2**attempts_done
                    attempts_done = spec.max_retries - attempts_left
                    delay = spec.backoff_base * (2**attempts_done)
                    # apply jitter if configured: +/- fraction of delay
                    try:
                        jitter_frac = getattr(spec, "backoff_jitter", 0.0) or 0.0
                        if jitter_frac and jitter_frac > 0.0:
                            jitter = delay * float(jitter_frac)
                            # Use of `random.uniform` here is intentional: this jitter is
                            # applied to an internal backoff delay for retry behaviour and
                            # is NOT used for any security- or cryptographic-related
                            # purpose. Mark as nosec so Bandit does not flag it (B311).
                            delay = max(
                                0.0,
                                delay + random.uniform(-jitter, jitter),  # nosec: B311 - non-crypto jitter
                            )
                    except Exception:  # nosec B110 -- intentional broad except for resilience
                        pass
                    try:
                        await asyncio.sleep(delay)
                        await in_q.put((item, attempts_left - 1))
                        try:
                            spec.metrics["retried"] += 1
                            self._emit_progress(
                                {
                                    "type": "retried",
                                    "stage": idx,
                                    "metrics": dict(spec.metrics or {}),
                                }
                            )
                        except Exception:  # nosec B110 -- intentional broad except for resilience
                            pass
                    except Exception:  # nosec B110 -- intentional broad except for resilience
                        logger.exception("Failed to re-enqueue item for retry: %r", item)
                else:
                    # final failure: call error handler if present, otherwise log and drop
                    try:
                        spec.metrics["failed"] += 1
                        if spec.error_handler:
                            maybe = spec.error_handler(exc, item)
                            if asyncio.iscoroutine(maybe):
                                await maybe
                        else:
                            spec.metrics["dropped"] += 1
                            logger.error("Dropping item after retries exhausted: %r", item)
                            # record dead-letter for monitoring
                            try:
                                self._dead_letters[idx].append(item)
                            except Exception:  # nosec B110 -- intentional broad except for resilience
                                pass
                        self._emit_progress(
                            {"type": "failed", "stage": idx, "metrics": dict(spec.metrics or {})}
                        )
                    except Exception:  # nosec B110 -- intentional broad except for resilience
                        logger.exception("Error handler failed for item=%r", item)
            finally:
                try:
                    spec.metrics["in_flight"] -= 1
                    self._emit_progress(
                        {"type": "in_flight_dec", "stage": idx, "metrics": dict(spec.metrics or {})}
                    )
                except Exception:  # nosec B110 -- intentional broad except for resilience
                    pass
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
        q = self._queues[0]
        policy = (first_spec.queue_full_policy or "block").lower()
        handler = first_spec.queue_full_handler

        # helper to call handler (sync or async)
        async def _call_handler(it: Any) -> None:
            if handler is None:
                return
            try:
                res = handler(it)
                if asyncio.iscoroutine(res):
                    await res
            except Exception:  # nosec B110 -- intentional broad except for resilience
                logger.exception("queue_full_handler failed for item=%r", it)

        # Apply policies
        if policy == "block" or not policy:
            await q.put((item, first_spec.max_retries))
            return

        if policy == "reject":
            try:
                q.put_nowait((item, first_spec.max_retries))
            except asyncio.QueueFull:
                raise RuntimeError("pipeline queue is full")
            return

        if policy == "drop_oldest":
            try:
                # remove oldest waiting item
                try:
                    _ = q.get_nowait()
                    # account for removal in join-count
                    try:
                        q.task_done()
                    except Exception:  # nosec B110 -- intentional broad except for resilience
                        pass
                except asyncio.QueueEmpty:
                    pass
                q.put_nowait((item, first_spec.max_retries))
                try:
                    first_spec.metrics["dropped"] += 1
                except Exception:  # nosec B110 -- intentional broad except for resilience
                    pass
            except asyncio.QueueFull:
                # if still full, call handler if present
                await _call_handler(item)
            return

        if policy == "drop_newest":
            # do not enqueue the new item; call handler if present and record drop
            try:
                first_spec.metrics["dropped"] += 1
            except Exception:  # nosec B110 -- intentional broad except for resilience
                pass
            await _call_handler(item)
            # record dead-letter
            try:
                self._dead_letters[0].append(item)
            except Exception:  # nosec B110 -- intentional broad except for resilience
                pass
            return

        # fallback: block
        await q.put((item, first_spec.max_retries))

    async def shutdown(self, *, drain: bool = True, timeout: float | None = 5.0) -> None:
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
            # propagate sentinel to each stage input queue according to that
            # stage's concurrency so every worker sees a sentinel and exits.
            for idx, spec in enumerate(self._stage_specs):
                q = self._queues[idx]
                for _ in range(spec.concurrency):
                    try:
                        await q.put(None)
                    except Exception:  # nosec B110 -- intentional broad except for resilience
                        pass
            # wait for workers to exit
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._workers, return_exceptions=True), timeout=timeout
                )
            except Exception:  # nosec B110 -- intentional broad except for resilience
                # best-effort cancel
                for t in self._workers:
                    t.cancel()
            # call teardown lifecycle on stages that implement it
            for spec in self._stage_specs:
                teardown = getattr(spec.stage, "teardown", None)
                if callable(teardown):
                    try:
                        maybe = teardown()
                        if asyncio.iscoroutine(maybe):
                            await maybe
                    except Exception:  # nosec B110 -- intentional broad except for resilience
                        logger.exception("Stage.teardown failed for %s", spec.stage)
        else:
            for t in self._workers:
                t.cancel()
            # give them a moment
            await asyncio.sleep(0)

        # cancel metrics exporter task
        if self._metrics_task is not None:
            try:
                self._metrics_task.cancel()
                await asyncio.sleep(0)
            except Exception:  # nosec B110 -- intentional broad except for resilience
                pass
            self._metrics_task = None

    # Convenience helper to run a synchronous iterable source
    async def run_from_iterable(self, iterable) -> None:
        await self.start()
        for item in iterable:
            await self.push(item)
        await self.shutdown(drain=True)

    # Async context manager support ----------------------------------------
    async def __aenter__(self) -> Pipeline:
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.shutdown(drain=True)

    async def run(self, async_iterable) -> None:
        """Convenience helper: start the pipeline, iterate an async iterable and push items, then shutdown."""
        await self.start()
        async for item in async_iterable:
            await self.push(item)
        await self.shutdown(drain=True)

    # --- Serialization helpers -------------------------------------------------
    def to_dict(self) -> dict:
        """Serialize pipeline configuration to a plain dict.

        Stage instances are represented by their import path. If a stage
        implementation exposes a `_config` attribute (a dict) it will be used
        as the init kwargs during deserialization. Otherwise an empty dict is
        used and the stage will be created without arguments.
        """
        stages = []
        for spec in self._stage_specs:
            cls = spec.stage.__class__
            cls_path = f"{cls.__module__}.{cls.__qualname__}"
            init_kwargs = getattr(spec.stage, "_config", {})
            entry = {
                "class": cls_path,
                "init_kwargs": init_kwargs,
                "concurrency": spec.concurrency,
                "max_queue": spec.max_queue,
                "max_retries": spec.max_retries,
                "backoff_base": getattr(spec, "backoff_base", 0.1),
                "backoff_jitter": getattr(spec, "backoff_jitter", 0.0),
            }
            # if the stage has an associated error handler name, include it
            if getattr(spec, "error_handler_name", None):
                entry["error_handler"] = spec.error_handler_name
            stages.append(entry)
        return {"stages": stages}

    def to_json(self, path: str) -> None:
        with open(path, "w", encoding="utf8") as fh:
            json.dump(self.to_dict(), fh, indent=2)

    @classmethod
    def from_template_dict(
        cls,
        template: dict[str, Any],
        variables: dict[str, Any] | None = None,
        schema: dict[str, Any] | None = None,
        expand_env: bool = False,
    ) -> Pipeline:
        """
        Create a Pipeline from a template dict, performing substitution on string
        values. Supports both `{var}` style formatting via Python's
        `str.format_map` and optional `${VAR}` or `${VAR:-default}` expansion
        from environment variables when `expand_env=True`.

        If `schema` is provided it will be used to validate the substituted
        template via `jsonschema.validate`. For backward compatibility if the
        template itself contains a top-level `schema` key and no explicit
        `schema` argument is given, that schema will be used but a
        DeprecationWarning will be emitted.
        """
        vars_map = variables or {}

        import os
        import re

        env_pattern = re.compile(r"\$\{([^}:]+?)(:-([^}]*))?\}")

        def _interp_str(s: str) -> str:
            # first apply {var} style formatting
            try:
                s2 = s.format_map(vars_map)
            except Exception:  # nosec B110 -- intentional broad except for resilience
                s2 = s

            if not expand_env:
                return s2

            def _repl(m: re.Match) -> str:
                name = m.group(1)
                has_default = m.group(2) is not None
                default = m.group(3) if has_default else None
                if name in (vars_map or {}):
                    return str((vars_map or {})[name])
                val = os.environ.get(name)
                if val is not None:
                    return val
                if has_default:
                    return default or ""
                return ""

            return env_pattern.sub(_repl, s2)

        def substitute(obj: Any) -> Any:
            if isinstance(obj, str):
                return _interp_str(obj)
            if isinstance(obj, dict):
                return {k: substitute(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [substitute(v) for v in obj]
            return obj

        substituted = substitute(template)

        # Prefer explicit schema argument, otherwise fall back to in-template
        # schema (deprecated).
        use_schema = schema
        if use_schema is None and isinstance(substituted, dict) and "schema" in substituted:
            import warnings

            warnings.warn(
                "Template contains top-level 'schema' key; pass schema explicitly via from_template_dict(..., schema=...) in future",
                DeprecationWarning,
            )
            use_schema = substituted.get("schema")

        if use_schema is not None:
            import jsonschema  # type: ignore

            jsonschema.validate(instance=substituted, schema=use_schema)

        return cls.from_dict(substituted)

    @classmethod
    def from_template_file(
        cls,
        path: str,
        variables: dict[str, Any] | None = None,
        schema: dict[str, Any] | None = None,
        expand_env: bool = False,
    ) -> Pipeline:
        """Load a template file (JSON or YAML) and create a Pipeline after substitution.

        Detection: if the file extension is .yml or .yaml we attempt to load
        using PyYAML (yaml.safe_load). JSON files are loaded with the stdlib
        json module. The loaded template is passed to `from_template_dict` with
        the provided `schema` and `expand_env` flags.
        """
        lower = path.lower()
        if lower.endswith(".yml") or lower.endswith(".yaml"):
            import yaml  # type: ignore

            with open(path, encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
        else:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        return cls.from_template_dict(
            data, variables=variables, schema=schema, expand_env=expand_env
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Pipeline:
        """Create a Pipeline from a config dict produced by `to_dict()`.

        Expected format:
        {"stages": [{"class": "module.StageClass", "init_kwargs": {...},
                     "concurrency": 1, "max_queue": 100, ...}, ...]}
        """
        p = cls()
        stages = data.get("stages", []) or []
        for entry in stages:
            cls_path = entry.get("class")
            init_kwargs = entry.get("init_kwargs", {}) or {}
            concurrency = int(entry.get("concurrency", 1))
            max_queue = int(entry.get("max_queue", 100))
            max_retries = int(entry.get("max_retries", 0))
            backoff_base = float(entry.get("backoff_base", 0.1))
            backoff_jitter = float(entry.get("backoff_jitter", 0.0))
            error_handler = entry.get("error_handler")

            # import class
            stage_obj = None
            if isinstance(cls_path, str) and cls_path:
                try:
                    mod_name, _, qual = cls_path.rpartition(".")
                    mod = importlib.import_module(mod_name)
                    StageCls = getattr(mod, qual)
                    stage_obj = StageCls(**init_kwargs) if init_kwargs else StageCls()
                except Exception:  # nosec B110 -- intentional broad except for resilience
                    raise ImportError(f"Cannot import stage class '{cls_path}'")
            else:
                raise ValueError("stage class path must be a string")

            p.add_stage(
                stage_obj,
                concurrency=concurrency,
                max_queue=max_queue,
                max_retries=max_retries,
                backoff_base=backoff_base,
                backoff_jitter=backoff_jitter,
                error_handler=error_handler,
            )
        return p

    @classmethod
    def from_config(
        cls,
        name_or_path: str,
        variables: dict[str, Any] | None = None,
        schema: dict[str, Any] | None = None,
        expand_env: bool = True,
    ) -> Pipeline:
        """Load a pipeline configuration from the repository `config/` directory or a path.

        If `name_or_path` is an existing file path it will be loaded directly.
        Otherwise the function will search the directory specified by the
        `CONFIG_DIR` environment variable (default: ./config) for files with
        the given name and common extensions (.yml, .yaml, .json).
        """
        import os

        # direct file
        if os.path.exists(name_or_path):
            return cls.from_template_file(
                name_or_path, variables=variables, schema=schema, expand_env=expand_env
            )

        cfg_dir = os.getenv("CONFIG_DIR", "config")
        candidates = [
            os.path.join(cfg_dir, name_or_path),
            os.path.join(cfg_dir, f"{name_or_path}.yml"),
            os.path.join(cfg_dir, f"{name_or_path}.yaml"),
            os.path.join(cfg_dir, f"{name_or_path}.json"),
        ]
        for c in candidates:
            if os.path.exists(c):
                return cls.from_template_file(
                    c, variables=variables, schema=schema, expand_env=expand_env
                )

        raise FileNotFoundError(f"Pipeline config '{name_or_path}' not found in {cfg_dir}")

    @classmethod
    def from_json(cls, path: str) -> Pipeline:
        """Load a pipeline config previously written with `to_json()`.

        This convenience reads the JSON file and delegates to `from_dict()`.
        """
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return cls.from_dict(data)

    def register_metrics_exporter(self, exporter: Callable[[dict], Any]) -> None:
        """Register a callable that will be invoked periodically with a
        metrics snapshot from `get_metrics()`.

        The exporter may be sync or async. If the pipeline is already started
        the periodic exporter loop is started automatically.
        """
        if exporter not in self._metrics_exporters:
            self._metrics_exporters.append(exporter)
        # start metrics task if pipeline already running
        if self._started and self._metrics_task is None:
            self._metrics_task = asyncio.create_task(self._metrics_loop())

    async def _metrics_loop(self) -> None:
        """Periodically call registered exporters with the current metrics
        snapshot. This is a best-effort loop and ignores exporter errors.
        """
        try:
            while True:
                snapshot = self.get_metrics()
                for exp in list(self._metrics_exporters):
                    try:
                        res = exp(snapshot)
                        if asyncio.iscoroutine(res):
                            await res
                    except Exception:  # nosec B110 -- intentional broad except for resilience
                        logger.exception("metrics exporter failed")
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            return


# Handler registry for serializing named handlers (error handlers, sinks, etc.)
HANDLER_REGISTRY: dict[str, Callable[..., Any]] = {}


def register_handler(name: str, fn: Callable[..., Any]) -> None:
    """Register a named handler that can be referenced in pipeline configs.

    Handlers are serialized by name by `to_dict()` (when the stage's
    `error_handler_name` is set) and resolved during `from_dict()`.
    """
    HANDLER_REGISTRY[name] = fn


def unregister_handler(name: str) -> None:
    HANDLER_REGISTRY.pop(name, None)


def get_registered_handler(name: str) -> Callable[..., Any] | None:
    return HANDLER_REGISTRY.get(name)


# Backwards-compatibility: some older code/tests refer to 'Step'. Keep a
# lightweight alias so both names work.
Step = Stage

__all__ = ["Pipeline", "Stage", "Step"]


# Simple built-in stage useful for config round-trips and tests
class IdentityStage(Stage):
    """A no-op stage that returns items unchanged."""

    async def process(self, item: Any) -> Any:
        return item


def get_prometheus_exporter(pipeline_name: str | None = None, registry: Any | None = None):
    """Return an exporter function that updates Prometheus metrics from a snapshot.

    This function lazily imports prometheus_client. If prometheus_client is not
    installed, it raises ImportError. The returned exporter accepts the dict
    returned by `Pipeline.get_metrics()`.

    The exporter uses simple delta-tracking for Counters so it can be invoked
    with snapshots.
    """
    try:
        from prometheus_client import CollectorRegistry, Counter, Gauge
    except Exception as exc:  # pragma: no cover - optional dependency  # nosec B110 -- intentional broad except for resilience
        raise ImportError("prometheus_client is required for Prometheus exporter") from exc

    reg = registry or CollectorRegistry()

    # metrics (labels: pipeline, stage_index, stage_class)
    C_PROCESSED = Counter(
        "pipeline_stage_processed_total",
        "Total processed by stage",
        ["pipeline", "stage_index", "stage_class"],
        registry=reg,
    )
    C_RETRIED = Counter(
        "pipeline_stage_retried_total",
        "Total retried by stage",
        ["pipeline", "stage_index", "stage_class"],
        registry=reg,
    )
    C_FAILED = Counter(
        "pipeline_stage_failed_total",
        "Total failed by stage",
        ["pipeline", "stage_index", "stage_class"],
        registry=reg,
    )
    C_DROPPED = Counter(
        "pipeline_stage_dropped_total",
        "Total dropped by stage",
        ["pipeline", "stage_index", "stage_class"],
        registry=reg,
    )

    G_IN_FLIGHT = Gauge(
        "pipeline_stage_in_flight",
        "In-flight processing count by stage",
        ["pipeline", "stage_index", "stage_class"],
        registry=reg,
    )
    G_QUEUE = Gauge(
        "pipeline_stage_queue_size",
        "Input queue size by stage",
        ["pipeline", "stage_index", "stage_class"],
        registry=reg,
    )

    # closure state for delta tracking
    last_seen: dict[int, dict[str, int]] = {}

    def _label_values(stage_idx: int, stage_cls: str):
        return {
            "pipeline": pipeline_name or "",
            "stage_index": str(stage_idx),
            "stage_class": stage_cls,
        }

    def exporter(snapshot: dict) -> None:
        for s in snapshot.get("stages", []):
            idx = s.get("index")
            metrics = s.get("metrics", {}) or {}
            stage_cls = s.get("class") or ""
            labels = _label_values(idx, stage_cls)

            prev = last_seen.get(idx, {"processed": 0, "retried": 0, "failed": 0, "dropped": 0})
            # counters: increment by delta
            p_val = int(metrics.get("processed", 0))
            r_val = int(metrics.get("retried", 0))
            f_val = int(metrics.get("failed", 0))
            d_val = int(metrics.get("dropped", 0))

            if p_val - prev.get("processed", 0) > 0:
                C_PROCESSED.labels(**labels).inc(p_val - prev.get("processed", 0))
            if r_val - prev.get("retried", 0) > 0:
                C_RETRIED.labels(**labels).inc(r_val - prev.get("retried", 0))
            if f_val - prev.get("failed", 0) > 0:
                C_FAILED.labels(**labels).inc(f_val - prev.get("failed", 0))
            if d_val - prev.get("dropped", 0) > 0:
                C_DROPPED.labels(**labels).inc(d_val - prev.get("dropped", 0))

            # gauges: set current values
            G_IN_FLIGHT.labels(**labels).set(float(metrics.get("in_flight", 0)))
            # queue size: we didn't include queue_size in per-stage metrics snapshot; try to read from s
            qsz = s.get("queue_size")
            if qsz is None:
                qsz = 0
            G_QUEUE.labels(**labels).set(float(qsz))

            last_seen[idx] = {
                "processed": p_val,
                "retried": r_val,
                "failed": f_val,
                "dropped": d_val,
            }

    return exporter
