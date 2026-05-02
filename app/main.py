import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import dispose_engine, get_async_session, init_engine
from app.core.logging import setup_logging
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router

setup_logging()
logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.debug("Service startup: initializing dependencies")
    init_engine()
    logger.debug("Service startup: dependencies initialized")

    try:
        yield
    finally:
        logger.debug("Service shutdown: releasing resources")
        await dispose_engine()
        logger.debug("Service shutdown: complete")


app = FastAPI(title="Auth service", lifespan=lifespan)


app.include_router(auth_router)
app.include_router(users_router)


@app.get("/")
async def root():
    return {"message": "Welcome to the Auth service"}


@app.get("/health")
async def health(session: AsyncSession = Depends(get_async_session)):
    try:
        result = await session.execute(text("SELECT 1"))
        db_ok = result.scalar() == 1
    except Exception:
        logger.exception("Healthcheck failed: database query error")
        db_ok = False
    if not db_ok:
        return JSONResponse(status_code=503, content={"status": "error"})
    return {"status": "ok"}
