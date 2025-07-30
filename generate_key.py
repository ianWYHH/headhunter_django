#!/usr/bin/env python3
"""
生成加密密钥的脚本
运行此脚本可以生成一个安全的加密密钥，用于加密API密钥等敏感信息
"""

from cryptography.fernet import Fernet

def generate_encryption_key():
    """生成一个新的加密密钥"""
    key = Fernet.generate_key()
    print("=" * 50)
    print("生成的加密密钥:")
    print("=" * 50)
    print(key.decode())
    print("=" * 50)
    print("请将此密钥复制到您的 .env 文件中的 ENCRYPTION_KEY 变量")
    print("=" * 50)
    return key

if __name__ == "__main__":
    generate_encryption_key() 