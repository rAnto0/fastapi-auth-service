from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.security import get_password_hash
from app.helpers.tokens import (
    blacklist_token,
    get_current_token_payload,
    is_token_blacklisted,
)
from app.helpers.users import get_user_by_email, get_user_from_sub
from app.models.rbac import Role, UserRole
from app.models.users import User
from app.schemas.users import UserCreate, UserUpdate
from app.services.tokens import ACCESS_TOKEN_TYPE, REFRESH_TOKEN_TYPE
from app.validations.tokens import validate_token_type
from app.validations.users import validate_email_unique, validate_password


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def authenticate_user(self, email: str, password: str) -> User:
        user = await get_user_by_email(email=email, session=self.session)

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Аккаунт деактивирован",
            )

        await validate_password(password=password, user=user)
        return user

    async def register_user(self, data: UserCreate) -> User:
        await validate_email_unique(email=data.email, session=self.session)

        hashed_password: bytes = get_password_hash(data.password)
        new_user = User(
            first_name=data.first_name,
            last_name=data.last_name,
            patronymic=data.patronymic,
            email=data.email,
            hashed_password=hashed_password,
            is_active=True,
        )
        self.session.add(new_user)
        await self.session.flush()

        await self._assign_default_role(user_id=new_user.id)

        await self.session.commit()
        await self.session.refresh(new_user)
        return new_user

    async def get_current_auth_user(self, token: str) -> User:
        return await self._user_getter_from_token(
            token=token, token_type=ACCESS_TOKEN_TYPE
        )

    async def get_current_refresh_user(self, token: str) -> User:
        return await self._user_getter_from_token(
            token=token, token_type=REFRESH_TOKEN_TYPE
        )

    async def logout(self, token: str) -> None:
        payload = get_current_token_payload(token=token)
        await blacklist_token(token=token, payload=payload, session=self.session)

    async def update_current_user(self, user: User, data: UserUpdate) -> User:
        update_data = data.model_dump(exclude_unset=True)

        if "email" in update_data:
            await validate_email_unique(
                email=update_data["email"],
                session=self.session,
                exclude_user_id=user.id,
            )

        for field, value in update_data.items():
            setattr(user, field, value)

        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def deactivate_current_user(self, user: User, token: str) -> None:
        user.is_active = False
        payload = get_current_token_payload(token=token)
        await blacklist_token(token=token, payload=payload, session=self.session)
        await self.session.commit()

    async def _assign_default_role(self, user_id) -> None:
        role_result = await self.session.execute(
            select(Role).where(Role.name == "user")
        )
        role = role_result.scalar_one_or_none()
        if role is None:
            role = Role(name="user", description="Default role for registered users")
            self.session.add(role)
            await self.session.flush()

        self.session.add(UserRole(user_id=user_id, role_id=role.id))

    async def _user_getter_from_token(self, token: str, token_type: str) -> User:
        if await is_token_blacklisted(token=token, session=self.session):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been invalidated",
                headers={"WWW-Authenticate": "Bearer"},
            )

        payload = get_current_token_payload(token=token)
        validate_token_type(payload=payload, token_type=token_type)
        return await get_user_from_sub(payload=payload, session=self.session)


async def get_auth_service(
    session: AsyncSession = Depends(get_async_session),
) -> AuthService:
    return AuthService(session=session)
