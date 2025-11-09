import asyncio

from researcharr.async_pipeline import Pipeline


async def _run_pipeline_and_collect_exports(p: Pipeline):
    exports = []

    async def exporter(snapshot):
        exports.append(snapshot)

    p.register_metrics_exporter(exporter)
    await p.start()
    await p.push("a")
    await p.push("b")
    await p.shutdown(drain=True)
    return exports


def test_metrics_export_and_dead_letter_recording():
    p = Pipeline()
    # simple stage that raises for a single item to exercise dead-letter

    async def flaky(item):
        if item == "b":
            raise RuntimeError("boom")
        return item

    p.add_stage(flaky, concurrency=1, max_retries=0)

    exports = asyncio.run(_run_pipeline_and_collect_exports(p))
    # exporter should have been invoked at least once
    assert isinstance(exports, list)
    assert len(exports) >= 1

    metrics = p.get_metrics()
    assert "stages" in metrics
    assert len(metrics["stages"]) == 1
    stage0 = metrics["stages"][0]
    # since 'b' failed, dead_letters should contain it
    assert any(item == "b" for item in stage0.get("dead_letters", []))
