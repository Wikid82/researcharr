import asyncio
from pathlib import Path

from researcharr.async_pipeline import IdentityStage, Pipeline


def test_pipeline_serialize_roundtrip(tmp_path: Path):
    p = Pipeline()
    # use an IdentityStage which takes no args
    p.add_stage(IdentityStage(), concurrency=2, max_queue=10, max_retries=0)

    cfg = p.to_dict()
    assert "stages" in cfg
    fp = tmp_path / "p.json"
    p.to_json(str(fp))

    p2 = Pipeline.from_json(str(fp))
    assert len(p2._stage_specs) == 1
    spec = p2._stage_specs[0]
    assert spec.concurrency == 2

    # run a small pipeline to ensure deserialized stage works
    async def run():
        await p2.start()
        await p2.push({"id": 1})
        await p2.shutdown(drain=True)

    asyncio.run(run())
