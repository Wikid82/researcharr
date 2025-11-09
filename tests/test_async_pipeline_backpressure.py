import asyncio

import pytest

from researcharr.async_pipeline import IdentityStage, Pipeline, _StageSpec


def test_reject_policy_raises():
    async def _coro():
        p = Pipeline()
        # manually configure stage spec and queue so we can simulate full queue without running workers
        spec = _StageSpec(
            stage=IdentityStage(),
            concurrency=1,
            max_queue=1,
            max_retries=0,
            metrics={"processed": 0, "failed": 0, "retried": 0, "dropped": 0, "in_flight": 0},
        )
        spec.queue_full_policy = "reject"
        q = asyncio.Queue(maxsize=1)
        # pre-fill queue to capacity
        q.put_nowait(("old", 0))
        p._stage_specs = [spec]
        p._dead_letters = [[]]
        p._queues = [q, asyncio.Queue(0)]
        p._started = True

        with pytest.raises(RuntimeError):
            await p.push("new")

    asyncio.run(_coro())


def test_drop_oldest_replaces_item():
    async def _coro():
        p = Pipeline()
        spec = _StageSpec(
            stage=IdentityStage(),
            concurrency=1,
            max_queue=1,
            max_retries=0,
            metrics={"processed": 0, "failed": 0, "retried": 0, "dropped": 0, "in_flight": 0},
        )
        spec.queue_full_policy = "drop_oldest"
        q = asyncio.Queue(maxsize=1)
        q.put_nowait(("old", 0))
        p._stage_specs = [spec]
        p._dead_letters = [[]]
        p._queues = [q, asyncio.Queue(0)]
        p._started = True

        await p.push("new")
        # now queue should contain the new item
        item, attempts = p._queues[0].get_nowait()
        assert item == "new"
        assert attempts == 0

    asyncio.run(_coro())


def test_drop_newest_calls_handler_and_records_dead_letter():
    async def _coro():
        p = Pipeline()
        called = []

        async def handler(item):
            called.append(item)

        spec = _StageSpec(
            stage=IdentityStage(),
            concurrency=1,
            max_queue=1,
            max_retries=0,
            metrics={"processed": 0, "failed": 0, "retried": 0, "dropped": 0, "in_flight": 0},
        )
        spec.queue_full_policy = "drop_newest"
        spec.queue_full_handler = handler
        q = asyncio.Queue(maxsize=1)
        q.put_nowait(("old", 0))
        p._stage_specs = [spec]
        p._dead_letters = [[]]
        p._queues = [q, asyncio.Queue(0)]
        p._started = True

        await p.push("new")
        # handler should have been called and dead-letter recorded
        assert called == ["new"]
        assert p._dead_letters[0] == ["new"]

    asyncio.run(_coro())
