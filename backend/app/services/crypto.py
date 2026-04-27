from cryptography.fernet import Fernet

from app.config import settings


def _fernet() -> Fernet:
    return Fernet(settings.camera_cred_key)


def encrypt_str(plaintext: str) -> bytes:
    return _fernet().encrypt(plaintext.encode("utf-8"))


def decrypt_str(blob: bytes) -> str:
    return _fernet().decrypt(blob).decode("utf-8")
