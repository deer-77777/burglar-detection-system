from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

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

    WORKER_GPU_DEVICE: int = 0
    WORKER_MAX_CAMERAS: int = 8

    YOLO_MODEL_PATH: str = "/app/models/yolo11n.pt"
    REID_MODEL_NAME: str = "osnet_x0_25"
    REID_MODEL_PATH: str = "/app/models/osnet_x0_25.pth"

    STREAM_HTTP_PORT: int = 9000

    @property
    def db_url(self) -> str:
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}?charset=utf8mb4"
        )

    @property
    def camera_cred_key(self) -> bytes:
        return Path(self.CAMERA_CRED_KEY_FILE).read_bytes().strip()


settings = WorkerSettings()
