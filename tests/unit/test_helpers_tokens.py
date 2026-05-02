from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from jwt import ExpiredSignatureError, InvalidTokenError
from sqlalchemy import select

from app.helpers import tokens as tokens_helper
from app.models.token_blacklist import TokenBlacklist


def test_get_current_token_payload_expired(monkeypatch):
    def _raise(_):
        raise ExpiredSignatureError()

    monkeypatch.setattr(tokens_helper, "decode_jwt", _raise)

    with pytest.raises(HTTPException) as exc:
        tokens_helper.get_current_token_payload("bad")

    assert exc.value.status_code == 401
    assert exc.value.detail == "Token has expired"


def test_get_current_token_payload_invalid(monkeypatch):
    def _raise(_):
        raise InvalidTokenError()

    monkeypatch.setattr(tokens_helper, "decode_jwt", _raise)

    with pytest.raises(HTTPException) as exc:
        tokens_helper.get_current_token_payload("bad")

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid token"


def test_get_current_token_payload_unknown_error(monkeypatch):
    def _raise(_):
        raise RuntimeError("boom")

    monkeypatch.setattr(tokens_helper, "decode_jwt", _raise)

    with pytest.raises(HTTPException) as exc:
        tokens_helper.get_current_token_payload("bad")

    assert exc.value.status_code == 401
    assert exc.value.detail == "Could not validate credentials"


@pytest.mark.asyncio
async def test_blacklist_token_handles_invalid_uuid_and_duplicate(db_session):
    token = "tok-1"
    payload = {
        "sub": "not-a-uuid",
        "type": "access",
        "exp": datetime.now(tz=UTC).timestamp(),
    }

    await tokens_helper.blacklist_token(
        token=token, payload=payload, session=db_session
    )
    await tokens_helper.blacklist_token(
        token=token, payload=payload, session=db_session
    )

    result = await db_session.execute(select(TokenBlacklist))
    items = result.scalars().all()
    assert len(items) == 1
    assert items[0].user_id is None


@pytest.mark.asyncio
async def test_is_token_blacklisted_false_true(db_session, user_factory):
    token = "tok-2"
    assert await tokens_helper.is_token_blacklisted(token, db_session) is False
    user = await user_factory()

    await tokens_helper.blacklist_token(
        token=token,
        payload={"sub": str(user.id), "type": "access"},
        session=db_session,
    )

    assert await tokens_helper.is_token_blacklisted(token, db_session) is True
