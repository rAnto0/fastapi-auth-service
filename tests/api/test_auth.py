from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import get_password_hash
from app.models.rbac import Role, UserRole
from tests.helpers import assert_user_in_db


async def test_register_user_success(
    async_client: AsyncClient,
    user_registration_data_factory,
    db_session,
):
    registration_data = user_registration_data_factory()

    resp = await async_client.post("/auth/register", json=registration_data)
    assert resp.status_code == 201
    data = resp.json()

    assert data["first_name"] == registration_data["first_name"]
    assert data["last_name"] == registration_data["last_name"]
    assert data["email"] == registration_data["email"]
    assert data["is_active"] is True

    await assert_user_in_db(
        db_session=db_session,
        email=registration_data["email"],
        password=registration_data["password"],
    )


async def test_register_user_duplicate_email(
    async_client: AsyncClient,
    user_factory,
    user_registration_data_factory,
):
    await user_factory(email="existing@example.com")

    registration_data = user_registration_data_factory(email="existing@example.com")

    resp = await async_client.post("/auth/register", json=registration_data)
    assert resp.status_code == 400


async def test_login_user_success(
    async_client: AsyncClient,
    user_factory,
    user_login_data_factory,
):
    password = "SecurePass123!"
    await user_factory(
        email="test@example.com",
        hashed_password=get_password_hash(password),
    )

    login_data = user_login_data_factory(username="test@example.com", password=password)

    resp = await async_client.post("/auth/login", data=login_data)
    assert resp.status_code == 200
    data = resp.json()

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "Bearer"


async def test_logout_blacklists_token(async_client: AsyncClient, user_factory):
    password = "SecurePass123!"
    await user_factory(
        email="logout@example.com", hashed_password=get_password_hash(password)
    )

    login_resp = await async_client.post(
        "/auth/login", data={"username": "logout@example.com", "password": password}
    )
    access_token = login_resp.json()["access_token"]

    logout_resp = await async_client.post(
        "/auth/logout", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert logout_resp.status_code == 204

    me_resp = await async_client.get(
        "/users/me", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert me_resp.status_code == 401


async def test_update_profile_me(async_client: AsyncClient, user_factory):
    password = "SecurePass123!"
    await user_factory(
        email="profile@example.com", hashed_password=get_password_hash(password)
    )

    login_resp = await async_client.post(
        "/auth/login", data={"username": "profile@example.com", "password": password}
    )
    access_token = login_resp.json()["access_token"]

    update_resp = await async_client.put(
        "/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"first_name": "Updated", "last_name": "User"},
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["first_name"] == "Updated"
    assert data["last_name"] == "User"


async def test_delete_me_deactivates_user_and_blocks_next_login(
    async_client: AsyncClient, user_factory
):
    password = "SecurePass123!"
    await user_factory(
        email="delete@example.com", hashed_password=get_password_hash(password)
    )

    login_resp = await async_client.post(
        "/auth/login", data={"username": "delete@example.com", "password": password}
    )
    access_token = login_resp.json()["access_token"]

    delete_resp = await async_client.delete(
        "/users/me", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert delete_resp.status_code == 204

    me_resp = await async_client.get(
        "/users/me", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert me_resp.status_code == 401

    login_again_resp = await async_client.post(
        "/auth/login", data={"username": "delete@example.com", "password": password}
    )
    assert login_again_resp.status_code == 403


async def test_check_admin_role_success(
    async_client: AsyncClient, user_factory, db_session
):
    password = "SecurePass123!"
    user = await user_factory(
        email="admin-check@example.com", hashed_password=get_password_hash(password)
    )

    role_result = await db_session.execute(select(Role).where(Role.name == "admin"))
    admin_role = role_result.scalar_one_or_none()
    if admin_role is None:
        admin_role = Role(name="admin", description="admin role")
        db_session.add(admin_role)
        await db_session.flush()

    db_session.add(UserRole(user_id=user.id, role_id=admin_role.id))
    await db_session.commit()

    login_resp = await async_client.post(
        "/auth/login",
        data={"username": "admin-check@example.com", "password": password},
    )
    access_token = login_resp.json()["access_token"]

    check_resp = await async_client.get(
        "/users/check/admin", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert check_resp.status_code == 200


async def test_check_admin_role_forbidden_for_user(
    async_client: AsyncClient, user_factory
):
    password = "SecurePass123!"
    await user_factory(
        email="user-check@example.com", hashed_password=get_password_hash(password)
    )

    login_resp = await async_client.post(
        "/auth/login", data={"username": "user-check@example.com", "password": password}
    )
    access_token = login_resp.json()["access_token"]

    check_resp = await async_client.get(
        "/users/check/admin", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert check_resp.status_code == 403
