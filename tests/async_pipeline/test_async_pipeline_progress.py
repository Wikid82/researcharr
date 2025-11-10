import asyncio

from researcharr.async_pipeline import Pipeline, Stage


class CountingStage(Stage):
    def __init__(self):
        self.count = 0

    async def process(self, item):
        self.count += 1
        await asyncio.sleep(0)
        return item


def test_progress_and_status():
    p = Pipeline()
    s = CountingStage()
    p.add_stage(s, concurrency=2)

    events = []

    def cb(ev):
        events.append(ev)

    p.subscribe_progress(cb)

    async def run():
        await p.start()
        # push a few items
        for i in range(5):
            await p.push({"id": i})
        await p.shutdown(drain=True)

    asyncio.run(run())

    status = p.get_status()
    assert status["started"] is True
    assert status["closed"] is True
    assert len(status["stages"]) == 1
    metrics = status["stages"][0]["metrics"]
    assert metrics.get("processed", 0) == 5
    # callbacks were emitted at least a few times
    assert any(e.get("type") == "processed" for e in events)
