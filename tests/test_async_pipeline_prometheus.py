import asyncio

import pytest

prom = pytest.importorskip("prometheus_client")
from prometheus_client import CollectorRegistry, generate_latest

from researcharr.async_pipeline import Pipeline, get_prometheus_exporter


def test_prometheus_exporter_records_metrics():
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
