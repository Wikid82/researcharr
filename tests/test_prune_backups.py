import os
import time
from pathlib import Path

from researcharr.backups import prune_backups


def touch(p: Path, mtime: float):
    p.write_text("x")
    os.utime(str(p), (mtime, mtime))


def test_prune_by_age_and_pre_restore(tmp_path):
    backups = tmp_path / "backups"
    backups.mkdir()
    now = time.time()

    # recent file (should remain)
    recent = backups / "recent.zip"
    touch(recent, now)

    # old file (should be removed)
    old = backups / "old.zip"
    touch(old, now - (3 * 86400))

    # pre-restore recent (should be kept even if within pre_keep window)
    pre = backups / "pre-restore.zip"
    touch(pre, now - (2 * 86400))

    cfg = {"retain_days": 2, "pre_restore_keep_days": 3}
    prune_backups(str(backups), cfg)

    remaining = set(os.listdir(str(backups)))
    assert "recent.zip" in remaining
    # old should be removed
    assert "old.zip" not in remaining
    # pre-restore was within keep window -> kept
    assert "pre-restore.zip" in remaining


def test_prune_by_count(tmp_path):
    backups = tmp_path / "backups"
    backups.mkdir()
    now = time.time()

    # create 5 backups with descending mtimes
    files = []
    for i in range(5):
        p = backups / f"b{i}.zip"
        touch(p, now - i)
        files.append(p)

    cfg = {"retain_count": 2}
    prune_backups(str(backups), cfg)

    remaining = sorted(os.listdir(str(backups)))
    # Only 2 newest should remain
    assert len(remaining) == 2
