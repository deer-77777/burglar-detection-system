from cryptography.fernet import Fernet

from worker.config import settings


def decrypt_str(blob: bytes) -> str:
    return Fernet(settings.camera_cred_key).decrypt(blob).decode("utf-8")
