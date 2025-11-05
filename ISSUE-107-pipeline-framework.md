# Issue #107 — Processing Pipeline Framework (brainstorm)

Goal
----
Design and implement a lightweight, pluggable processing pipeline framework to support streaming/queued processing of items from sources (Radarr/Sonarr/other), allow plugin-based processors, and provide observability and graceful shutdown.

Why
---
This centralizes item processing and decouples acquisition, transformation, and output, enabling retries, rate-limiting, parallelism, and easier plugin development.

Contract (minimal)
------------------
- Inputs: an async iterator or sync iterable of "items" (dicts) or typed objects.
- Outputs: processed results emitted to sinks; or in-place mutation.
- Error modes: per-item failures should be captured and routed to a configurable error handler; pipeline should support retry/backoff.
- Success criteria: throughput comparable to naive loop; tests for correct order preservation (when ordered), retry behaviour, and plugin isolation.

Design ideas
------------
- Core Pipeline object that accepts a list of `Stage` objects. Each Stage exposes a `.process(item)` which may be sync or async.
- Support concurrency per-stage via worker pools (ThreadPoolExecutor / asyncio tasks) with configurable concurrency.
- Backpressure: bounded internal queues between stages; backpressure/backoff when full.
- Retry policy: per-stage configurable retry/backoff with jitter.
- Observability: metrics hooks (counters/timers), logging, and ability to plug in Prometheus client.
- Plugin model: entry point registration or simple `Pipeline.register_processor(plugin)` method.

Edge cases
----------
- Long-running tasks and cancellation: pipeline must respect shutdown/cancellation and drain or abort gracefully.
- Mixed sync/async stages: provide wrappers to run sync functions in executors.
- Ordering vs concurrency: make ordering optional.

Next steps
----------
- Create a `researcharr.pipeline` module with interfaces and a minimal sync implementation.
- Add unit tests: ordered processing, retry behavior, backpressure.
- Experiment with an integration test connecting run.py producers to the pipeline.

Notes
-----
This is a sketch — we should iterate on API shape. I'll commit this file on a new branch so we can iterate.
