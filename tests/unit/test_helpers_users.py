from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.helpers.users import get_user_by_email, get_user_from_sub


@pytest.mark.asyncio
async def test_get_user_by_email_not_found(db_session):
    with pytest.raises(HTTPException) as exc:
        await get_user_by_email("missing@example.com", db_session)

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_user_from_sub_missing_sub(db_session):
    with pytest.raises(HTTPException) as exc:
        await get_user_from_sub({}, db_session)

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_user_from_sub_not_found(db_session):
    with pytest.raises(HTTPException) as exc:
        await get_user_from_sub({"sub": str(uuid4())}, db_session)

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_user_from_sub_inactive(db_session, user_factory):
    user = await user_factory(is_active=False)

    with pytest.raises(HTTPException) as exc:
        await get_user_from_sub({"sub": str(user.id)}, db_session)

    assert exc.value.status_code == 403
