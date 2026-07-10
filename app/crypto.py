import base64
import hashlib

from cryptography.fernet import Fernet

from app.config import JWT_SECRET_KEY


def _get_fernet() -> Fernet:
    key = hashlib.sha256(JWT_SECRET_KEY.encode("utf-8")).digest()
    key_b64 = base64.urlsafe_b64encode(key)
    return Fernet(key_b64)


def encrypt_api_key(plaintext: str) -> str:
    if not plaintext:
        return ""
    f = _get_fernet()
    return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_api_key(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    f = _get_fernet()
    return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
