from sqlalchemy import select

from app.core.security import verify_password
from app.models.users import User


async def assert_user_in_db(db_session, email, password):
    result = await db_session.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    assert user is not None
    assert verify_password(password, user.hashed_password) is True
    assert user.is_active is True
