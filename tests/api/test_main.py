from httpx import ASGITransport, AsyncClient

from app.core.database import get_async_session
from app.main import app


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar(self):
        return self._value


class _OkSession:
    async def execute(self, _query):
        return _ScalarResult(1)


class _BadSession:
    async def execute(self, _query):
        raise RuntimeError("db down")


async def test_root_endpoint(async_client):
    resp = await async_client.get("/")
    assert resp.status_code == 200
    assert resp.json()["message"] == "Welcome to the Auth service"


async def test_health_ok_override():
    async def _dep():
        yield _OkSession()

    app.dependency_overrides[get_async_session] = _dep
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/health")
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_health_db_error_override():
    async def _dep():
        yield _BadSession()

    app.dependency_overrides[get_async_session] = _dep
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/health")
    app.dependency_overrides.clear()

    assert resp.status_code == 503
    assert resp.json() == {"status": "error"}
