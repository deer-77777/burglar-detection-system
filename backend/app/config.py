from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "production"
    APP_SECRET_KEY: str = "change-me"
    JWT_ACCESS_TTL_MIN: int = 15
    JWT_REFRESH_TTL_DAYS: int = 7
    LOGIN_LOCK_THRESHOLD: int = 5
    LOGIN_LOCK_WINDOW_SEC: int = 300
    LOGIN_LOCK_DURATION_SEC: int = 900
    DEFAULT_LOCALE: str = "en"

    MYSQL_HOST: str = "mysql"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "burglar"
    MYSQL_PASSWORD: str = "burglar"
    MYSQL_DATABASE: str = "burglar"

    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379

    CAMERA_CRED_KEY_FILE: str = "/run/secrets/camera_cred.key"

    DEFAULT_DWELL_LIMIT_SEC: int = 180
    DEFAULT_COUNT_LIMIT: int = 3
    DEFAULT_COUNT_WINDOW_SEC: int = 86400
    PERSON_GID_TTL_SEC: int = 86400
    RING_BUFFER_SEC: int = 10
    TARGET_FPS: int = 8
    REID_THRESHOLD: float = 0.35

    CLIPS_DIR: str = "/data/clips"
    SNAPS_DIR: str = "/data/snaps"

    PUBLIC_ORIGIN: str = "https://burglar.local"

    DEV_SKIP_RTSP_PROBE: bool = False

    @property
    def db_url(self) -> str:
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}?charset=utf8mb4"
        )

    @property
    def camera_cred_key(self) -> bytes:
        p = Path(self.CAMERA_CRED_KEY_FILE)
        return p.read_bytes().strip()


settings = Settings()


def _validate_secret() -> None:
    if settings.APP_ENV == "production":
        if (
            len(settings.APP_SECRET_KEY) < 32
            or settings.APP_SECRET_KEY in {"change-me", "change-me-32-chars-minimum-please-rotate"}
        ):
            raise RuntimeError(
                "APP_SECRET_KEY must be set to a strong random value (>=32 chars) in production. "
                "Generate one with `python -c 'import secrets; print(secrets.token_urlsafe(48))'`."
            )


_validate_secret()
