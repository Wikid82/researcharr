import os
import tempfile

import pytest

from researcharr.async_pipeline import Pipeline


def test_load_yaml_template_and_validate():
    yaml = pytest.importorskip("yaml")
    pytest.importorskip("jsonschema")

    template = {
        "schema": {
            "type": "object",
            "properties": {"stages": {"type": "array"}},
            "required": ["stages"],
        },
        "stages": [
            {
                "class": "researcharr.async_pipeline.IdentityStage",
                "init_kwargs": {},
                "concurrency": 1,
            }
        ],
    }

    # write YAML file
    fd, path = tempfile.mkstemp(suffix=".yml")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(template, fh)

    try:
        p = Pipeline.from_template_file(path)
        # Pipeline should be created with one stage
        assert len(p._stage_specs) == 1
    finally:
        os.remove(path)
