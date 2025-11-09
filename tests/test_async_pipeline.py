import asyncio

from researcharr.async_pipeline import Pipeline, Stage


class IncStage(Stage):
    def __init__(self, key: str = "v"):
        self.key = key

    async def process(self, item):
        # mutate item for test observation
        item[self.key] = item.get(self.key, 0) + 1
        await asyncio.sleep(0)  # yield control
        return item


class FlakyStage(Stage):
    def __init__(self):
        self._seen = set()

    async def process(self, item):
        # fail first time for an id, succeed next
        ident = item.get("id")
        if ident not in self._seen:
            self._seen.add(ident)
            raise RuntimeError("transient")
        return item


def run_async(coro):
    # Use asyncio.run for running top-level coroutines in tests
    return asyncio.run(coro)


def test_pipeline_basic():
    p = Pipeline()
    p.add_stage(IncStage("a"), concurrency=2)
    p.add_stage(IncStage("b"), concurrency=2)

    async def run():
        await p.start()
        for i in range(20):
            await p.push({"id": i})
        await p.shutdown(drain=True)

    run_async(run())
    # If we made it this far without error the pipeline processed items


def test_pipeline_retry():
    p = Pipeline()
    p.add_stage(FlakyStage(), concurrency=2, max_retries=1)

    results = []

    class CollectStage(Stage):
        async def process(self, item):
            results.append(item)
            return item

    p.add_stage(CollectStage(), concurrency=1)

    async def run():
        await p.start()
        await p.push({"id": "x"})
        await p.push({"id": "y"})
        await p.shutdown(drain=True)

    run_async(run())
    assert len(results) == 2
