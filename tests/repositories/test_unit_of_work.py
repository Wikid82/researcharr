from researcharr.repositories.uow import UnitOfWork
from researcharr.storage.database import init_db


def test_unit_of_work_managed_session(tmp_path):
    # Use a temporary sqlite database
    db_path = str(tmp_path / "uow.db")
    init_db(db_path)
    with UnitOfWork() as uow:
        # Lazy initialization of repositories; exercise get_or_create default path
        settings_repo = uow.settings
        settings = settings_repo.get_or_create()
        assert settings.id == 1
        # Update a field and persist via repository update
        settings.items_per_cycle = 7
        settings_repo.update(settings)
        refreshed = settings_repo.get_by_id(1)
        assert refreshed.items_per_cycle == 7


def test_unit_of_work_external_session(tmp_path):
    db_path = str(tmp_path / "uow_ext.db")
    init_db(db_path)
    # Acquire external session via context manager
    from researcharr.storage.database import get_session

    with get_session() as session:
        uow = UnitOfWork(session=session)
        with uow:
            assert uow.session is session
            # Exercise commit/rollback paths (no changes needed)
            uow.commit()
            uow.rollback()
