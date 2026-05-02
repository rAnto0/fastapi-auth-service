import pytest
import pytest_asyncio

from app.core.security import get_password_hash
from app.models.users import User


@pytest_asyncio.fixture
async def user_factory(db_session, faker):
    async def _factory(**kwargs):
        defaults = {
            "first_name": faker.first_name(),
            "last_name": faker.last_name(),
            "patronymic": faker.first_name(),
            "email": f"test_{faker.word()}@example.com",
            "hashed_password": get_password_hash("TestPass123!"),
            "is_active": True,
        }
        user_data = {**defaults, **kwargs}

        user = User(**user_data)
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    return _factory


@pytest.fixture
def user_registration_data_factory(faker):
    def _factory(**kwargs):
        base_data = {
            "first_name": faker.first_name(),
            "last_name": faker.last_name(),
            "patronymic": faker.first_name(),
            "email": f"test_{faker.word()}@example.com",
            "password": "SecurePass123!",
        }
        return {**base_data, **kwargs}

    return _factory


@pytest.fixture
def user_login_data_factory():
    def _factory(**kwargs):
        base_data = {"username": "test@example.com", "password": "SecurePass123!"}
        return {**base_data, **kwargs}

    return _factory
