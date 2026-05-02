import pytest

from app.core import database


@pytest.mark.asyncio
async def test_get_async_session_raises_when_not_initialized(monkeypatch):
    monkeypatch.setattr(database, "async_session_factory", None)

    with pytest.raises(RuntimeError, match="not initialized"):
        async for _ in database.get_async_session():
            pass


def test_init_engine_idempotent(monkeypatch):
    class _DummyEngine:
        pass

    created = {"count": 0}

    def _fake_create_async_engine(*args, **kwargs):
        created["count"] += 1
        return _DummyEngine()

    monkeypatch.setattr(database, "engine", None)
    monkeypatch.setattr(database, "create_async_engine", _fake_create_async_engine)

    database.init_engine()
    database.init_engine()

    assert created["count"] == 1
    assert database.engine is not None
    assert database.async_session_factory is not None


@pytest.mark.asyncio
async def test_dispose_engine_noop_when_none(monkeypatch):
    monkeypatch.setattr(database, "engine", None)
    monkeypatch.setattr(database, "async_session_factory", None)

    await database.dispose_engine()


@pytest.mark.asyncio
async def test_dispose_engine_clears_globals(monkeypatch):
    class _DummyEngine:
        def __init__(self):
            self.disposed = False

        async def dispose(self):
            self.disposed = True

    dummy = _DummyEngine()
    monkeypatch.setattr(database, "engine", dummy)
    monkeypatch.setattr(database, "async_session_factory", object())

    await database.dispose_engine()

    assert dummy.disposed is True
    assert database.engine is None
    assert database.async_session_factory is None
