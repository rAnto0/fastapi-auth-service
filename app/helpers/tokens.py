import hashlib
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from jwt import ExpiredSignatureError, InvalidTokenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_jwt
from app.models.token_blacklist import TokenBlacklist
from app.schemas.users import TokenInfo, UserRead
from app.services.tokens import create_access_token, create_refresh_token


def create_access_refresh_tokens(user: UserRead) -> TokenInfo:
    access_token = create_access_token(user=user)
    refresh_token = create_refresh_token(user=user)

    return TokenInfo(
        access_token=access_token,
        refresh_token=refresh_token,
    )


def get_current_token_payload(token: str) -> dict[str, Any]:
    try:
        payload: dict[str, Any] = decode_jwt(token)
        return payload
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def token_to_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def is_token_blacklisted(token: str, session: AsyncSession) -> bool:
    token_hash = token_to_hash(token)
    result = await session.execute(
        select(TokenBlacklist).where(TokenBlacklist.token_hash == token_hash)
    )
    return result.scalar_one_or_none() is not None


async def blacklist_token(
    token: str,
    payload: dict[str, Any],
    session: AsyncSession,
) -> None:
    token_hash = token_to_hash(token)

    result = await session.execute(
        select(TokenBlacklist).where(TokenBlacklist.token_hash == token_hash)
    )
    if result.scalar_one_or_none() is not None:
        return

    exp = payload.get("exp")
    expires_at = None
    if isinstance(exp, (int, float)):
        expires_at = datetime.fromtimestamp(exp, tz=UTC)

    user_id = payload.get("sub")
    parsed_user_id: UUID | None = None
    if isinstance(user_id, str):
        try:
            parsed_user_id = UUID(user_id)
        except ValueError:
            parsed_user_id = None

    session.add(
        TokenBlacklist(
            token_hash=token_hash,
            token_type=str(payload.get("type", "unknown")),
            user_id=parsed_user_id,
            expires_at=expires_at,
        )
    )
    await session.commit()
