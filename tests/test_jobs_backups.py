"""Integration tests for backup job handlers."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

from researcharr.core.jobs import JobService, register_backup_job_handlers, JobStatus


@pytest.fixture
async def temp_config_root(tmp_path):
    cfg = tmp_path / "config"
    backups_dir = cfg / "backups"
    cfg.mkdir()
    backups_dir.mkdir()
    # Create a dummy file in config root
    (cfg / "settings.yml").write_text("key: value\n")
    os.environ["CONFIG_DIR"] = str(cfg)
    yield cfg
    os.environ.pop("CONFIG_DIR", None)


@pytest.fixture
async def job_service(temp_config_root):
    svc = JobService(redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/15"))
    await svc.initialize()
    register_backup_job_handlers(svc)
    await svc.start_workers(count=1)
    yield svc
    await svc.shutdown(graceful=True)


@pytest.mark.asyncio
async def test_backup_create_job(job_service, temp_config_root):
    job_id = await job_service.submit_job("backup.create", kwargs={"prefix": "test-"})
    for _ in range(50):
        status = await job_service.get_job_status(job_id)
        if status == JobStatus.COMPLETED:
            break
        await asyncio.sleep(0.1)
    result = await job_service.get_job_result(job_id)
    assert result is not None
    assert result.status == JobStatus.COMPLETED
    assert result.result.get("backup_name", "").startswith("test-")
    backups_dir = Path(os.environ["CONFIG_DIR"]) / "backups"
    backup_name = result.result.get("backup_name", "")
    assert backup_name.startswith("test-")
    created_path = backups_dir / backup_name
    assert created_path.exists()


@pytest.mark.asyncio
async def test_backup_restore_job(job_service, temp_config_root):
    create_id = await job_service.submit_job("backup.create")
    for _ in range(50):
        if await job_service.get_job_status(create_id) == JobStatus.COMPLETED:
            break
        await asyncio.sleep(0.1)
    create_res = await job_service.get_job_result(create_id)
    name = create_res.result.get("backup_name")  # type: ignore[assignment]
    assert name
    settings_path = Path(os.environ["CONFIG_DIR"]) / "settings.yml"
    settings_path.unlink(missing_ok=True)
    restore_id = await job_service.submit_job("backup.restore", args=(name,))
    for _ in range(80):
        if await job_service.get_job_status(restore_id) in (JobStatus.COMPLETED, JobStatus.FAILED):
            break
        await asyncio.sleep(0.1)
    restore_res = await job_service.get_job_result(restore_id)
    assert restore_res is not None
    assert restore_res.status == JobStatus.COMPLETED
    assert settings_path.exists()
