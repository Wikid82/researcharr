import asyncio

import pytest

from researcharr.async_pipeline import Pipeline, get_prometheus_exporter

prom = pytest.importorskip("prometheus_client")


def test_prometheus_exporter_records_metrics():
    # Import at runtime to satisfy E402 (imports at top) while still allowing
    # importorskip to gate the test based on environment.
    from prometheus_client import CollectorRegistry, generate_latest

    registry = CollectorRegistry()
    exporter = get_prometheus_exporter(pipeline_name="p1", registry=registry)

    async def run_pipeline():
        p = Pipeline()

        async def echo(x):
            return x

        p.add_stage(echo, concurrency=1, max_retries=0)
        p.register_metrics_exporter(exporter)
        await p.start()
        await p.push("a")
        await p.push("b")
        await p.shutdown(drain=True)

    asyncio.run(run_pipeline())

    text = generate_latest(registry).decode()
    assert "pipeline_stage_processed_total" in text
    assert "pipeline_stage_in_flight" in text
    assert "pipeline_stage_queue_size" in text
