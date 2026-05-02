from sqlalchemy import func, select

from app.models.users import User


async def test_db_starts_clean_each_test(db_session):
    result = await db_session.execute(select(func.count()).select_from(User))
    assert result.scalar_one() == 0
