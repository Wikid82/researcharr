import sys
import types
from datetime import datetime, timedelta

from researcharr.compat import UTC
from researcharr.scheduling.backup_scheduler import BackupSchedulerService


class FakeScheduler:
    def __init__(self):
        self.jobs = []
        self.removed = []

    def add_job(self, func, trigger, id, name, replace_existing):
        self.jobs.append(
            {
                "func": func,
                "trigger": trigger,
                "id": id,
                "name": name,
                "replace_existing": replace_existing,
            }
        )

    def get_job(self, job_id):
        for j in self.jobs:
            if j["id"] == job_id:

                class J:
                    next_run_time = datetime.now(UTC) + timedelta(minutes=5)

                return J()
        return None

    def remove_job(self, job_id):
        self.removed.append(job_id)
        self.jobs = [j for j in self.jobs if j["id"] != job_id]


def _install_fake_cron_trigger(monkeypatch):
    # Provide a fake apscheduler CronTrigger for import
    cron_mod = types.ModuleType("cron")

    class CronTrigger:
        @staticmethod
        def from_crontab(expr, timezone=None):
            return (expr, str(timezone) if timezone is not None else None)

    cron_mod.CronTrigger = CronTrigger

    triggers_pkg = types.ModuleType("triggers")
    triggers_pkg.cron = cron_mod

    aps_pkg = types.ModuleType("apscheduler")
    aps_pkg.triggers = triggers_pkg

    monkeypatch.setitem(sys.modules, "apscheduler", aps_pkg)
    monkeypatch.setitem(sys.modules, "apscheduler.triggers", triggers_pkg)
    monkeypatch.setitem(sys.modules, "apscheduler.triggers.cron", cron_mod)


def _install_backup_deps(monkeypatch, result_type="success", pruned=0):
    # Stub researcharr.backups API used by the service
    backups_mod = types.ModuleType("researcharr.backups")

    def get_backup_config(config_root):
        return {"backups_dir": f"{config_root}/backups"}

    def create_backup_file(config_root, backups_dir, prefix="auto"):
        if result_type == "success":
            return f"{backups_dir}/{prefix}-backup.zip"
        elif result_type == "none":
            return None
        elif result_type == "raise":
            raise RuntimeError("create failed")

    def prune_backups(backups_dir, cfg):
        return pruned

    backups_mod.get_backup_config = get_backup_config
    backups_mod.create_backup_file = create_backup_file
    backups_mod.prune_backups = prune_backups

    # Minimal event bus and monitor
    events_mod = types.ModuleType("researcharr.core.events")

    class EventBus:
        def __init__(self):
            self.published = []

        def publish(self, name, payload):
            self.published.append((name, payload))

    def get_event_bus():
        return EventBus()

    events_mod.get_event_bus = get_event_bus
    events_mod.BACKUP_PRUNED = "backup_pruned"

    mon_mod = types.ModuleType("researcharr.monitoring.backup_monitor")

    class BackupHealthMonitor:
        def __init__(self, *a, **kw):
            pass

        def record_backup_created(self, file, success, error=None):
            return None

    mon_mod.BackupHealthMonitor = BackupHealthMonitor

    monkeypatch.setitem(sys.modules, "researcharr.backups", backups_mod)
    monkeypatch.setitem(sys.modules, "researcharr.core.events", events_mod)
    monkeypatch.setitem(sys.modules, "researcharr.monitoring.backup_monitor", mon_mod)


def test_setup_no_scheduler_does_nothing(caplog):
    svc = BackupSchedulerService(scheduler=None, config={})
    svc.setup()
    # No exceptions and log message is fine; nothing scheduled


def test_setup_disabled_auto_backup(monkeypatch):
    _install_fake_cron_trigger(monkeypatch)
    sched = FakeScheduler()
    svc = BackupSchedulerService(
        scheduler=sched, config={"backups": {"auto_backup_enabled": False}}
    )
    svc.setup()
    assert len(sched.jobs) == 0


def test_setup_enabled_schedules_backup_and_prune(monkeypatch):
    _install_fake_cron_trigger(monkeypatch)
    sched = FakeScheduler()
    cfg = {
        "backups": {
            "auto_backup_enabled": True,
            "auto_backup_cron": "*/5 * * * *",
            "prune_cron": "0 3 * * *",
        },
        "scheduling": {"timezone": "UTC"},
    }
    svc = BackupSchedulerService(scheduler=sched, config=cfg)
    svc.setup()
    ids = {j["id"] for j in sched.jobs}
    assert ids == {"automated_backup", "backup_prune"}


def test_setup_invalid_cron_is_caught(monkeypatch):
    # Fake CronTrigger that raises
    cron_mod = types.ModuleType("cron")

    class CronTrigger:
        @staticmethod
        def from_crontab(expr, timezone=None):
            raise ValueError("bad cron")

    cron_mod.CronTrigger = CronTrigger
    triggers_pkg = types.ModuleType("triggers")
    triggers_pkg.cron = cron_mod
    aps_pkg = types.ModuleType("apscheduler")
    aps_pkg.triggers = triggers_pkg
    monkeypatch.setitem(sys.modules, "apscheduler", aps_pkg)
    monkeypatch.setitem(sys.modules, "apscheduler.triggers", triggers_pkg)
    monkeypatch.setitem(sys.modules, "apscheduler.triggers.cron", cron_mod)

    sched = FakeScheduler()
    svc = BackupSchedulerService(scheduler=sched, config={"backups": {"auto_backup_enabled": True}})
    svc.setup()  # Should not raise; no jobs added
    assert len(sched.jobs) == 0


def test_trigger_backup_now_and_run_paths(monkeypatch, tmp_path, caplog):
    _install_backup_deps(monkeypatch, result_type="success")
    svc = BackupSchedulerService(config={})
    # Success path returns True
    assert svc.trigger_backup_now() is True

    # No-file path still returns True (internal handling), but exercises logging/metrics
    _install_backup_deps(monkeypatch, result_type="none")
    svc._run_backup()

    # Exception in create_backup_file covered
    _install_backup_deps(monkeypatch, result_type="raise")
    svc._run_backup()


def test_trigger_prune_now_and_run_paths(monkeypatch):
    _install_backup_deps(monkeypatch, result_type="success", pruned=3)
    svc = BackupSchedulerService(config={})
    assert svc.trigger_prune_now() is True
    svc._run_prune()


def test_remove_jobs(monkeypatch):
    _install_fake_cron_trigger(monkeypatch)
    sched = FakeScheduler()
    cfg = {"backups": {"auto_backup_enabled": True}}
    svc = BackupSchedulerService(scheduler=sched, config=cfg)
    svc.setup()
    assert {j["id"] for j in sched.jobs}  # jobs present
    svc.remove_jobs()
    assert set(sched.removed) == {"automated_backup", "backup_prune"}


def test_get_next_times(monkeypatch):
    _install_fake_cron_trigger(monkeypatch)
    sched = FakeScheduler()
    cfg = {"backups": {"auto_backup_enabled": True}}
    svc = BackupSchedulerService(scheduler=sched, config=cfg)
    svc.setup()
    assert svc.get_next_backup_time() is not None
    assert svc.get_next_prune_time() is not None
    info = svc.get_schedule_info()
    assert isinstance(info, dict)
    assert "enabled" in info


"""Tests for backup scheduling service."""

from unittest.mock import Mock, patch


def test_backup_scheduler_init():
    """Test BackupSchedulerService initialization."""
    from researcharr.scheduling.backup_scheduler import BackupSchedulerService

    scheduler = Mock()
    config = {"backups": {"auto_backup_enabled": True}}

    service = BackupSchedulerService(scheduler, config)

    assert service._scheduler == scheduler
    assert service._config == config


def test_backup_scheduler_setup_disabled():
    """Test setup when auto backup is disabled."""
    from researcharr.scheduling.backup_scheduler import BackupSchedulerService

    scheduler = Mock()
    config = {"backups": {"auto_backup_enabled": False}}

    service = BackupSchedulerService(scheduler, config)
    service.setup()

    # Should not add any jobs
    scheduler.add_job.assert_not_called()


def test_backup_scheduler_setup_no_scheduler():
    """Test setup when scheduler is None."""
    from researcharr.scheduling.backup_scheduler import BackupSchedulerService

    config = {"backups": {"auto_backup_enabled": True}}

    service = BackupSchedulerService(None, config)
    service.setup()

    # Should not crash


def test_backup_scheduler_setup_enabled():
    """Test setup when auto backup is enabled."""
    from researcharr.scheduling.backup_scheduler import BackupSchedulerService

    scheduler = Mock()
    config = {
        "backups": {
            "auto_backup_enabled": True,
            "auto_backup_cron": "0 2 * * *",
            "prune_cron": "0 3 * * *",
        },
        "scheduling": {"timezone": "UTC"},
    }

    service = BackupSchedulerService(scheduler, config)

    with patch("apscheduler.triggers.cron.CronTrigger") as mock_cron:
        mock_trigger = Mock()
        mock_cron.from_crontab.return_value = mock_trigger

        service.setup()

        # Should add backup and prune jobs
        assert scheduler.add_job.call_count == 2

        # Verify cron expressions
        mock_cron.from_crontab.assert_any_call("0 2 * * *", timezone="UTC")
        mock_cron.from_crontab.assert_any_call("0 3 * * *", timezone="UTC")


def test_backup_scheduler_trigger_backup_now():
    """Test manual backup trigger."""
    from researcharr.scheduling.backup_scheduler import BackupSchedulerService

    scheduler = Mock()
    service = BackupSchedulerService(scheduler)

    with patch.object(service, "_run_backup") as mock_run:
        result = service.trigger_backup_now()

        mock_run.assert_called_once()
        assert result is True


def test_backup_scheduler_trigger_backup_now_error():
    """Test manual backup trigger with error."""
    from researcharr.scheduling.backup_scheduler import BackupSchedulerService

    scheduler = Mock()
    service = BackupSchedulerService(scheduler)

    with patch.object(service, "_run_backup", side_effect=Exception("Test error")):
        result = service.trigger_backup_now()

        assert result is False


def test_backup_scheduler_trigger_prune_now():
    """Test manual prune trigger."""
    from researcharr.scheduling.backup_scheduler import BackupSchedulerService

    scheduler = Mock()
    service = BackupSchedulerService(scheduler)

    with patch.object(service, "_run_prune") as mock_run:
        result = service.trigger_prune_now()

        mock_run.assert_called_once()
        assert result is True


def test_backup_scheduler_get_next_backup_time():
    """Test getting next backup time."""
    from researcharr.scheduling.backup_scheduler import BackupSchedulerService

    scheduler = Mock()
    mock_job = Mock()
    mock_job.next_run_time.isoformat.return_value = "2025-01-10T02:00:00+00:00"
    scheduler.get_job.return_value = mock_job

    service = BackupSchedulerService(scheduler)
    next_time = service.get_next_backup_time()

    assert next_time == "2025-01-10T02:00:00+00:00"
    scheduler.get_job.assert_called_once_with("automated_backup")


def test_backup_scheduler_get_next_backup_time_no_scheduler():
    """Test getting next backup time without scheduler."""
    from researcharr.scheduling.backup_scheduler import BackupSchedulerService

    service = BackupSchedulerService(None)
    next_time = service.get_next_backup_time()

    assert next_time is None


def test_backup_scheduler_get_schedule_info():
    """Test getting schedule information."""
    from researcharr.scheduling.backup_scheduler import BackupSchedulerService

    scheduler = Mock()
    config = {
        "backups": {
            "auto_backup_enabled": True,
            "auto_backup_cron": "0 2 * * *",
            "prune_cron": "0 3 * * *",
        }
    }

    service = BackupSchedulerService(scheduler, config)

    with patch.object(service, "get_next_backup_time", return_value="2025-01-10T02:00:00"):
        with patch.object(service, "get_next_prune_time", return_value="2025-01-10T03:00:00"):
            info = service.get_schedule_info()

            assert info["enabled"] is True
            assert info["backup_schedule"] == "0 2 * * *"
            assert info["prune_schedule"] == "0 3 * * *"
            assert info["next_backup"] == "2025-01-10T02:00:00"
            assert info["next_prune"] == "2025-01-10T03:00:00"


def test_backup_scheduler_get_schedule_info_disabled():
    """Test getting schedule information when disabled."""
    from researcharr.scheduling.backup_scheduler import BackupSchedulerService

    scheduler = Mock()
    config = {"backups": {"auto_backup_enabled": False}}

    service = BackupSchedulerService(scheduler, config)
    info = service.get_schedule_info()

    assert info["enabled"] is False
    assert info["backup_schedule"] is None


def test_backup_scheduler_remove_jobs():
    """Test removing scheduled jobs."""
    from researcharr.scheduling.backup_scheduler import BackupSchedulerService

    scheduler = Mock()
    scheduler.get_job.return_value = Mock()

    service = BackupSchedulerService(scheduler)
    service.remove_jobs()

    # Should remove both jobs
    assert scheduler.remove_job.call_count == 2
    scheduler.remove_job.assert_any_call("automated_backup")
    scheduler.remove_job.assert_any_call("backup_prune")


def test_backup_scheduler_remove_jobs_no_scheduler():
    """Test removing jobs without scheduler."""
    from researcharr.scheduling.backup_scheduler import BackupSchedulerService

    service = BackupSchedulerService(None)
    service.remove_jobs()  # Should not crash
