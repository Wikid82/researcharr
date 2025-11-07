import asyncio
import json
import tempfile

from researcharr.async_pipeline import Pipeline


def test_template_dict_substitution_and_from_dict_roundtrip():
    template = {
        "stages": [
            {
                "class": "researcharr.async_pipeline.IdentityStage",
                "init_kwargs": {},
                "concurrency": "{c}",
                "max_queue": "{mq}",
            }
        ]
    }
    variables = {"c": 2, "mq": 10}
    p = Pipeline.from_template_dict(template, variables)
    assert len(p._stage_specs) == 1
    spec = p._stage_specs[0]
    assert spec.concurrency == 2
    assert spec.max_queue == 10


def test_template_file_loads_json_and_runs():
    template = {
        "stages": [
            {
                "class": "researcharr.async_pipeline.IdentityStage",
                "init_kwargs": {},
                "concurrency": "{c}",
                "max_queue": "{mq}",
            }
        ]
    }
    variables = {"c": 1, "mq": 5}
    with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as fh:
        json.dump(template, fh)
        path = fh.name

    p = Pipeline.from_template_file(path, variables)
    assert len(p._stage_specs) == 1

    async def run_once():
        await p.start()
        await p.push("hello")
        await p.shutdown(drain=True)

    asyncio.run(run_once())
