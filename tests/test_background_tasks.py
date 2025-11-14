from __future__ import annotations

import os
import time

import pytest

from researcharr.core.background import BackgroundTaskManager
from researcharr.backups_impl import create_backup_file


@pytest.mark.parametrize("count", [1, 2])
def test_background_simple_execution(count, tmp_path):
    mgr = BackgroundTaskManager(max_workers=2)
    results = []

    def work(x):
        time.sleep(0.05)
        return x * 2

    ids = [mgr.submit(work, i) for i in range(count)]
    # Poll until all complete
    deadline = time.time() + 5
    while time.time() < deadline:
        done = sum(1 for i in ids if mgr.get(i).status == "completed")
        if done == count:
            break
        time.sleep(0.02)
    assert all(mgr.get(i).status == "completed" for i in ids)
    assert [mgr.get(i).result for i in ids] == [i * 2 for i in range(count)]
    mgr.shutdown()


def test_background_backup_create(tmp_path, monkeypatch):
    config_root = tmp_path / "config"
    backups_dir = config_root / "backups"
    config_root.mkdir()
    backups_dir.mkdir()
    (config_root / "settings.yml").write_text("key: value\n")
    os.environ["CONFIG_DIR"] = str(config_root)
    mgr = BackgroundTaskManager(max_workers=1)
    tid = mgr.submit_backup_create(create_backup_file, str(config_root), str(backups_dir), "bg-")
    deadline = time.time() + 5
    while time.time() < deadline:
        task = mgr.get(tid)
        if task and task.status in ("completed", "failed"):
            break
        time.sleep(0.02)
    task = mgr.get(tid)
    assert task is not None
    assert task.status == "completed"
    assert isinstance(task.result, object)
    # Confirm backup file exists
    files = list(backups_dir.iterdir())
    assert any(f.name.startswith("bg-") and f.suffix == ".zip" for f in files)
    mgr.shutdown()
    os.environ.pop("CONFIG_DIR", None)


def test_background_ttl_cleanup(tmp_path):
    mgr = BackgroundTaskManager(max_workers=1, ttl_seconds=1)

    def quick():
        return "ok"

    tid = mgr.submit(quick)
    # Wait for completion
    deadline = time.time() + 5
    while time.time() < deadline:
        t = mgr.get(tid)
        if t and t.status in ("completed", "failed"):
            break
        time.sleep(0.01)
    assert mgr.get(tid) is not None
    # Force finished timestamp older than TTL
    t = mgr.get(tid)
    assert t is not None
    t.finished = t.finished - 5  # type: ignore
    # Trigger prune via get/list
    mgr.prune_expired()
    assert mgr.get(tid) is None
    mgr.shutdown()


def test_background_serialization_schema(tmp_path):
    mgr = BackgroundTaskManager(max_workers=1)

    def quick():
        return 42

    tid = mgr.submit(quick)
    deadline = time.time() + 5
    while time.time() < deadline:
        d = mgr.serialize(tid)
        if d and d["status"] == "completed":
            break
        time.sleep(0.01)
    data = mgr.serialize(tid)
    assert data is not None
    # Required unified fields
    for key in ["job_id", "status", "result", "error", "started_at", "completed_at", "duration", "type"]:
        assert key in data
    assert data["type"] == "background"
    mgr.shutdown()


def test_background_cancel_pending(tmp_path):
    # Use single worker; queue two tasks so second remains pending briefly
    mgr = BackgroundTaskManager(max_workers=1)

    def slow():
        time.sleep(0.2)
        return "slow"

    first_id = mgr.submit(slow)
    second_id = mgr.submit(lambda: "quick")
    # Immediately cancel second while likely still pending
    cancelled = mgr.cancel(second_id)
    assert cancelled is True
    # Wait for first to finish so pending second would otherwise start if not cancelled
    deadline = time.time() + 5
    while time.time() < deadline:
        if mgr.get(first_id).status in ("completed", "failed", "cancelled"):
            break
        time.sleep(0.01)
    second_task = mgr.get(second_id)
    assert second_task is not None
    assert second_task.status == "cancelled"
    mgr.shutdown()


def test_background_cancel_running_cooperative(tmp_path):
    mgr = BackgroundTaskManager(max_workers=1)

    def coop(cancel_event):  # cooperative cancellation
        # Loop until cancel requested
        while not cancel_event.is_set():
            time.sleep(0.01)
        return "stopped"

    tid = mgr.submit(coop)
    # Ensure task started
    deadline = time.time() + 5
    while time.time() < deadline:
        t = mgr.get(tid)
        if t and t.status == "running":
            break
        time.sleep(0.005)
    # Request cancellation
    assert mgr.cancel(tid) is True
    # Wait for task to observe cancel
    deadline = time.time() + 5
    while time.time() < deadline:
        t = mgr.get(tid)
        if t and t.status in ("cancelled", "failed", "completed"):
            break
        time.sleep(0.01)
    final = mgr.get(tid)
    assert final is not None
    assert final.status == "cancelled"
    mgr.shutdown()
