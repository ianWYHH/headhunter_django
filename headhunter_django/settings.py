import os
from pathlib import Path
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('DJANGO_SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DJANGO_DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'jobs',
    'django_htmx',
    'widget_tweaks',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
]

ROOT_URLCONF = 'headhunter_django.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'headhunter_django.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT', default='3306'),
        'OPTIONS': { 'charset': 'utf8mb4' },
    }
}

# ==============================================================================
# 加密密钥
# ==============================================================================
ENCRYPTION_KEY = config('ENCRYPTION_KEY')


# ==============================================================================
# AI 模型统一配置
# ==============================================================================
AI_MODELS = {
    'qwen_plus': {'name': '通义千问-Plus (推荐)', 'provider': 'qwen', 'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1', 'model_name': 'qwen-plus'},
    'qwen_turbo': {'name': '通义千问-Turbo (高速)', 'provider': 'qwen', 'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1', 'model_name': 'qwen-turbo'},
    'qwen_max': {'name': '通义千问-Max (长文本)', 'provider': 'qwen', 'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1', 'model_name': 'qwen-max'},
    'kimi_32k': {'name': 'Kimi (32K上下文)', 'provider': 'kimi', 'base_url': 'https://api.moonshot.cn/v1', 'model_name': 'moonshot-v1-32k'},
    'kimi_128k': {'name': 'Kimi (128K上下文)', 'provider': 'kimi', 'base_url': 'https://api.moonshot.cn/v1', 'model_name': 'moonshot-v1-128k'},
    'doubao_pro_32k': {'name': '豆包-Pro (32K)', 'provider': 'doubao', 'base_url': 'https://ark.cn-beijing.volces.com/api/v3', 'model_name': 'doubao-pro-32k'},
    'doubao_pro_128k': {'name': '豆包-Pro (128K)', 'provider': 'doubao', 'base_url': 'https://ark.cn-beijing.volces.com/api/v3', 'model_name': 'doubao-pro-128k'},
    'hunyuan_pro': {'name': '腾讯混元-Pro', 'provider': 'hunyuan', 'base_url': 'https://hunyuan.cloud.tencent.com/openapi/v1', 'model_name': 'hunyuan-pro'},
    'deepseek_chat': {'name': '深度求索-V2 (通用)', 'provider': 'deepseek', 'base_url': 'https://api.deepseek.com/v1', 'model_name': 'deepseek-chat'},
    'deepseek_coder': {'name': '深度求索-Coder (代码)', 'provider': 'deepseek', 'base_url': 'https://api.deepseek.com/v1', 'model_name': 'deepseek-coder'},
    'minimax_abab6_5': {'name': 'MiniMax (abab6.5)', 'provider': 'minimax', 'base_url': 'https://api.minimax.chat/v1/text/chatcompletion-pro', 'model_name': 'abab6.5-chat'},
    'together_mixtral': {'name': 'Together AI (Mixtral-8x22B)', 'provider': 'together', 'base_url': 'https://api.together.xyz/v1', 'model_name': 'mistralai/Mixtral-8x22B-Instruct-v0.1'},
    'together_llama3_1_70b': {'name': 'Together AI (Llama3.1-70B)', 'provider': 'together', 'base_url': 'https://api.together.xyz/v1', 'model_name': 'meta-llama/Llama-3.1-70B-Instruct'},
}

# ==============================================================================
# 认证系统配置
# ==============================================================================
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'jobs:index'
LOGOUT_REDIRECT_URL = 'login'

# ==============================================================================
# 邮件发送配置 (已补全)
# ==============================================================================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='localhost')
EMAIL_PORT = config('EMAIL_PORT', default=25, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=False, cast=bool)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=False, cast=bool)
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default=EMAIL_HOST_USER)

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'static'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
