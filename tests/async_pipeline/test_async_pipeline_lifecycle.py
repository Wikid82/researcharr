import asyncio

from researcharr.async_pipeline import Pipeline, Step


class LifecycleStep(Step):
    def __init__(self):
        self.setup_called = False
        self.teardown_called = False
        self.processed = []

    async def setup(self):
        # simulate async init
        await asyncio.sleep(0)
        self.setup_called = True

    async def teardown(self):
        await asyncio.sleep(0)
        self.teardown_called = True

    async def process(self, item):
        self.processed.append(item)
        return item


async def _run_pipeline():
    p = Pipeline()
    s = LifecycleStep()
    p.add_stage(s, concurrency=2)
    await p.start()
    assert s.setup_called is True
    await p.push({"id": 1})
    await p.push({"id": 2})
    await p.shutdown(drain=True)
    assert s.teardown_called is True


def test_lifecycle():
    asyncio.run(_run_pipeline())
