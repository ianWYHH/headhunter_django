from cryptography.fernet import Fernet
from django.conf import settings

# 初始化加密器
cipher_suite = Fernet(settings.ENCRYPTION_KEY.encode())

def encrypt_key(api_key: str) -> bytes:
    """加密API Key"""
    if not api_key:
        return b''
    return cipher_suite.encrypt(api_key.encode())

def decrypt_key(encrypted_key: bytes) -> str:
    """解密API Key"""
    if not encrypted_key:
        return ''
    return cipher_suite.decrypt(encrypted_key).decode()