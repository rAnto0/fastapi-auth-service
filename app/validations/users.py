from uuid import UUID

from fastapi import HTTPException, status
from pydantic import EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.models.users import User


async def validate_email_unique(
    email: EmailStr,
    session: AsyncSession,
    exclude_user_id: UUID | None = None,
) -> None:
    query = select(User).where(User.email == email)
    if exclude_user_id:
        query = query.where(User.id != exclude_user_id)

    result = await session.execute(query)
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует",
        )


async def validate_password(password: str, user: User) -> None:
    if not verify_password(
        plain_password=password, hashed_password=user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный пароль",
        )
