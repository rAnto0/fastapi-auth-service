import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.rbac import Permission, Resource, Role, UserRole
from app.models.users import User


async def get_or_create_role(name: str, description: str, session):
    result = await session.execute(select(Role).where(Role.name == name))
    role = result.scalar_one_or_none()
    if role:
        return role
    role = Role(name=name, description=description)
    session.add(role)
    await session.flush()
    return role


async def get_or_create_resource(name: str, description: str, session):
    result = await session.execute(select(Resource).where(Resource.name == name))
    resource = result.scalar_one_or_none()
    if resource:
        return resource
    resource = Resource(name=name, description=description)
    session.add(resource)
    await session.flush()
    return resource


async def get_or_create_permission(
    role_id: int, resource_id: int, action: str, session
):
    result = await session.execute(
        select(Permission).where(
            Permission.role_id == role_id,
            Permission.resource_id == resource_id,
            Permission.action == action,
        )
    )
    if result.scalar_one_or_none() is None:
        session.add(Permission(role_id=role_id, resource_id=resource_id, action=action))


async def attach_role_to_user(email: str, role_id: int, session):
    user_result = await session.execute(select(User).where(User.email == email))
    user = user_result.scalar_one_or_none()
    if user is None:
        return

    existing = await session.execute(
        select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role_id)
    )
    if existing.scalar_one_or_none() is None:
        session.add(UserRole(user_id=user.id, role_id=role_id))


async def get_or_create_user(
    email: str,
    first_name: str,
    last_name: str,
    password: str,
    session,
):
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user:
        user.first_name = first_name
        user.last_name = last_name
        user.patronymic = None
        user.hashed_password = get_password_hash(password)
        user.is_active = True
        return user

    user = User(
        first_name=first_name,
        last_name=last_name,
        patronymic=None,
        email=email,
        hashed_password=get_password_hash(password),
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user


async def main() -> None:
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        admin_role = await get_or_create_role("admin", "Full system access", session)
        moderator_role = await get_or_create_role(
            "moderator", "Moderation access", session
        )
        user_role = await get_or_create_role("user", "Default user role", session)

        profile_resource = await get_or_create_resource(
            "profile", "User profile management", session
        )
        auth_resource = await get_or_create_resource("auth", "Authentication", session)

        for action in ["read", "write", "delete"]:
            await get_or_create_permission(
                admin_role.id, profile_resource.id, action, session
            )
            await get_or_create_permission(
                admin_role.id, auth_resource.id, action, session
            )

        for action in ["read", "write"]:
            await get_or_create_permission(
                moderator_role.id, profile_resource.id, action, session
            )
        await get_or_create_permission(
            moderator_role.id, auth_resource.id, "read", session
        )

        await get_or_create_permission(
            user_role.id, profile_resource.id, "read", session
        )
        await get_or_create_permission(
            user_role.id, profile_resource.id, "write", session
        )
        await get_or_create_permission(user_role.id, auth_resource.id, "read", session)

        await get_or_create_user(
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
            password="AdminPass123!",
            session=session,
        )
        await get_or_create_user(
            email="moderator@example.com",
            first_name="Moderator",
            last_name="User",
            password="ModeratorPass123!",
            session=session,
        )
        await get_or_create_user(
            email="user@example.com",
            first_name="Regular",
            last_name="User",
            password="UserPass123!",
            session=session,
        )

        await attach_role_to_user("admin@example.com", admin_role.id, session)
        await attach_role_to_user("moderator@example.com", moderator_role.id, session)
        await attach_role_to_user("user@example.com", user_role.id, session)

        await session.commit()

    await engine.dispose()
    print("RBAC seed completed")


if __name__ == "__main__":
    asyncio.run(main())
