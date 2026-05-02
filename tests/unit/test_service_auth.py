import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.core.security import get_password_hash
from app.models.rbac import Role, UserRole
from app.models.token_blacklist import TokenBlacklist
from app.models.users import User
from app.schemas.users import UserCreate, UserUpdate
from app.services.auth import AuthService


@pytest.mark.asyncio
async def test_authenticate_user_inactive(db_session, monkeypatch):
    service = AuthService(db_session)
    user = User(
        first_name="A",
        last_name="B",
        patronymic=None,
        email="inactive@example.com",
        hashed_password=get_password_hash("Secret123"),
        is_active=False,
    )

    async def _fake_get_user_by_email(email, session):
        return user

    monkeypatch.setattr("app.services.auth.get_user_by_email", _fake_get_user_by_email)

    with pytest.raises(HTTPException) as exc:
        await service.authenticate_user("inactive@example.com", "Secret123")

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_authenticate_user_success_calls_password_validation(
    db_session, monkeypatch
):
    service = AuthService(db_session)
    user = User(
        first_name="A",
        last_name="B",
        patronymic=None,
        email="active@example.com",
        hashed_password=get_password_hash("Secret123"),
        is_active=True,
    )
    called = {"validate": False}

    async def _fake_get_user_by_email(email, session):
        return user

    async def _fake_validate_password(password, user):
        called["validate"] = True

    monkeypatch.setattr("app.services.auth.get_user_by_email", _fake_get_user_by_email)
    monkeypatch.setattr("app.services.auth.validate_password", _fake_validate_password)

    result = await service.authenticate_user("active@example.com", "Secret123")

    assert result is user
    assert called["validate"] is True


@pytest.mark.asyncio
async def test_register_user_creates_user_and_default_role(db_session):
    service = AuthService(db_session)

    data = UserCreate(
        first_name="John",
        last_name="Doe",
        patronymic="M",
        email="john@example.com",
        password="Password123",
    )

    user = await service.register_user(data)

    role_result = await db_session.execute(select(Role).where(Role.name == "user"))
    role = role_result.scalar_one_or_none()
    assert role is not None

    user_role_result = await db_session.execute(
        select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id)
    )
    assert user_role_result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_register_user_with_existing_default_role(db_session):
    existing_role = Role(name="user", description="existing")
    db_session.add(existing_role)
    await db_session.commit()

    service = AuthService(db_session)
    data = UserCreate(
        first_name="Jane",
        last_name="Roe",
        patronymic=None,
        email="jane@example.com",
        password="Password123",
    )

    user = await service.register_user(data)

    user_role_result = await db_session.execute(
        select(UserRole).where(
            UserRole.user_id == user.id,
            UserRole.role_id == existing_role.id,
        )
    )
    assert user_role_result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_update_current_user_email_and_fields(db_session, user_factory):
    service = AuthService(db_session)
    user = await user_factory(email="before@example.com")

    updated = await service.update_current_user(
        user=user,
        data=UserUpdate(first_name="After", email="after@example.com"),
    )

    assert updated.first_name == "After"
    assert updated.email == "after@example.com"


@pytest.mark.asyncio
async def test_logout_blacklists_token(db_session, user_factory):
    service = AuthService(db_session)
    user = await user_factory()
    token = "logout-token"

    # get_current_token_payload is sync function in production, keep same interface here
    def _payload(*, token):
        return {"sub": str(user.id), "type": "access"}

    from app.services import auth as auth_module

    original = auth_module.get_current_token_payload
    auth_module.get_current_token_payload = _payload
    try:
        await service.logout(token)
    finally:
        auth_module.get_current_token_payload = original

    result = await db_session.execute(select(TokenBlacklist))
    assert result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_deactivate_current_user(db_session, user_factory):
    service = AuthService(db_session)
    user = await user_factory(is_active=True)

    from app.services import auth as auth_module

    def _payload(*, token):
        return {"sub": str(user.id), "type": "access"}

    original = auth_module.get_current_token_payload
    auth_module.get_current_token_payload = _payload
    try:
        await service.deactivate_current_user(user=user, token="tok")
    finally:
        auth_module.get_current_token_payload = original

    assert user.is_active is False


@pytest.mark.asyncio
async def test_get_current_auth_user_blacklisted_token(db_session):
    service = AuthService(db_session)

    from app.services import auth as auth_module

    async def _blacklisted(token, session):
        return True

    original = auth_module.is_token_blacklisted
    auth_module.is_token_blacklisted = _blacklisted
    try:
        with pytest.raises(HTTPException) as exc:
            await service.get_current_auth_user("tok")
    finally:
        auth_module.is_token_blacklisted = original

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_refresh_user_wrong_token_type(db_session, user_factory):
    service = AuthService(db_session)
    user = await user_factory()

    from app.services import auth as auth_module

    async def _blacklisted(token, session):
        return False

    def _payload(*, token):
        return {"sub": str(user.id), "type": "access"}

    original_blacklisted = auth_module.is_token_blacklisted
    original_payload = auth_module.get_current_token_payload
    auth_module.is_token_blacklisted = _blacklisted
    auth_module.get_current_token_payload = _payload
    try:
        with pytest.raises(HTTPException) as exc:
            await service.get_current_refresh_user("tok")
    finally:
        auth_module.is_token_blacklisted = original_blacklisted
        auth_module.get_current_token_payload = original_payload

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_auth_user_success(db_session, user_factory):
    service = AuthService(db_session)
    user = await user_factory()

    from app.services import auth as auth_module

    async def _blacklisted(token, session):
        return False

    def _payload(*, token):
        return {"sub": str(user.id), "type": "access"}

    original_blacklisted = auth_module.is_token_blacklisted
    original_payload = auth_module.get_current_token_payload
    auth_module.is_token_blacklisted = _blacklisted
    auth_module.get_current_token_payload = _payload
    try:
        current = await service.get_current_auth_user("tok")
    finally:
        auth_module.is_token_blacklisted = original_blacklisted
        auth_module.get_current_token_payload = original_payload

    assert current.id == user.id
