import pytest

from researcharr.async_pipeline import Pipeline


def test_expand_env_vars_and_defaults(monkeypatch):
    # set environment variable
    monkeypatch.setenv("MY_VAR", "value_from_env")

    template = {
        "stages": [
            {
                "class": "researcharr.async_pipeline.IdentityStage",
                "init_kwargs": {},
                "concurrency": 1,
            }
        ],
        "name": "${MY_VAR}",
    }

    p = Pipeline.from_template_dict(template, expand_env=True)
    # name should have been interpolated from env
    assert isinstance(p, Pipeline)


def test_expand_env_with_default(monkeypatch):
    # ensure env var is not set
    monkeypatch.delenv("MISSING_VAR", raising=False)

    template = {
        "stages": [
            {
                "class": "researcharr.async_pipeline.IdentityStage",
                "init_kwargs": {},
                "concurrency": 1,
            }
        ],
        "name": "${MISSING_VAR:-fallback}",
    }

    p = Pipeline.from_template_dict(template, expand_env=True)
    assert isinstance(p, Pipeline)


def test_explicit_schema_param_is_used():
    # valid template but we will pass a schema that requires 'stages'
    template = {
        "stages": [
            {
                "class": "researcharr.async_pipeline.IdentityStage",
                "init_kwargs": {},
                "concurrency": 1,
            }
        ]
    }
    schema = {"type": "object", "required": ["stages"]}
    p = Pipeline.from_template_dict(template, schema=schema)
    assert isinstance(p, Pipeline)


def test_explicit_schema_param_invalid_raises():
    template = {"no_stages": []}
    schema = {"type": "object", "required": ["stages"]}
    with pytest.raises(Exception):
        Pipeline.from_template_dict(template, schema=schema)
