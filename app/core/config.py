from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).parent.parent


class AuthJWT(BaseModel):
    private_key_path: Path = BASE_DIR / "core" / "certs" / "jwt-private.pem"
    public_key_path: Path = BASE_DIR / "core" / "certs" / "jwt-public.pem"


class Settings(BaseSettings):
    SERVICE_NAME: str = "auth-service"
    DATABASE_URL: str = ""
    DATABASE_SYNC_URL: str = ""
    DATABASE_TEST_URL: str = ""
    LOG_LEVEL: str = "INFO"
    SQL_DEBUG: bool = False
    SECRET_KEY: str = ""
    ALGORITHM: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    AUTH_JWT_KEYS: AuthJWT = AuthJWT()


settings = Settings()
