import asyncio

from researcharr.async_pipeline import (
    Pipeline,
    register_handler,
    unregister_handler,
)


def test_handler_registry_and_serialization():
    called = []

    def my_handler(exc, item):
        called.append((str(exc), item))

    # register handler
    register_handler("my_handler", my_handler)

    async def flaky(item):
        raise RuntimeError("boom")

    p = Pipeline()
    # specify error handler by name
    p.add_stage(flaky, concurrency=1, max_retries=0, error_handler="my_handler")

    # run pipeline
    async def run():
        await p.start()
        await p.push("a")
        await p.shutdown(drain=True)

    asyncio.run(run())

    # handler should have been invoked
    assert called and called[0][1] == "a"

    unregister_handler("my_handler")


def test_dead_letter_and_drain():
    p = Pipeline()

    async def flaky(item):
        raise RuntimeError("boom")

    p.add_stage(flaky, concurrency=1, max_retries=0)

    async def run():
        await p.start()
        await p.push("x")
        await p.shutdown(drain=True)

    asyncio.run(run())

    # dead letter present
    d = p.get_dead_letters(0)
    assert d == ["x"]

    drained = []

    async def sink(item):
        drained.append(item)

    asyncio.run(p.drain_dead_letters(0, sink))
    assert drained == ["x"]
    assert p.get_dead_letters(0) == []
