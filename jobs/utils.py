from cryptography.fernet import Fernet
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# 初始化加密器
try:
    # 如果ENCRYPTION_KEY已经是bytes，直接使用；如果是字符串，则编码
    encryption_key = settings.ENCRYPTION_KEY
    if isinstance(encryption_key, str):
        encryption_key = encryption_key.encode()
    cipher_suite = Fernet(encryption_key)
except Exception as e:
    logger.error(f"加密密钥初始化失败: {e}")
    # 使用临时密钥作为后备方案，但记录警告
    logger.warning("使用临时加密密钥，请检查ENCRYPTION_KEY配置")
    cipher_suite = Fernet(Fernet.generate_key())

def encrypt_key(api_key: str) -> bytes:
    """加密API Key"""
    if not api_key:
        return b''
    try:
        return cipher_suite.encrypt(api_key.encode())
    except Exception as e:
        logger.error(f"加密API密钥失败: {e}")
        return b''

def decrypt_key(encrypted_key: bytes) -> str:
    """解密API Key"""
    if not encrypted_key:
        return ''
    try:
        return cipher_suite.decrypt(encrypted_key).decode()
    except Exception as e:
        logger.error(f"解密API密钥失败: {e}")
        return ''