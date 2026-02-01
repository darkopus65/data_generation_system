# Superset configuration for Game Analytics course

import os

# Security
SECRET_KEY = os.environ.get('SUPERSET_SECRET_KEY', 'your-secret-key-change-in-production')

# Database connection for Superset metadata
SQLALCHEMY_DATABASE_URI = 'sqlite:////app/superset_home/superset.db'

# Flask-WTF flag for CSRF
WTF_CSRF_ENABLED = True
WTF_CSRF_EXEMPT_LIST = []
WTF_CSRF_TIME_LIMIT = 60 * 60 * 24 * 365

# Feature flags
FEATURE_FLAGS = {
    "ENABLE_TEMPLATE_PROCESSING": True,
    "DASHBOARD_NATIVE_FILTERS": True,
    "DASHBOARD_CROSS_FILTERS": True,
    "DASHBOARD_NATIVE_FILTERS_SET": True,
    "ENABLE_EXPLORE_DRAG_AND_DROP": True,
}

# Cache configuration (using Redis)
CACHE_CONFIG = {
    'CACHE_TYPE': 'RedisCache',
    'CACHE_DEFAULT_TIMEOUT': 300,
    'CACHE_KEY_PREFIX': 'superset_',
    'CACHE_REDIS_HOST': 'redis',
    'CACHE_REDIS_PORT': 6379,
    'CACHE_REDIS_DB': 1,
}

# Data cache
DATA_CACHE_CONFIG = {
    'CACHE_TYPE': 'RedisCache',
    'CACHE_DEFAULT_TIMEOUT': 60 * 60 * 24,  # 1 day
    'CACHE_KEY_PREFIX': 'superset_data_',
    'CACHE_REDIS_HOST': 'redis',
    'CACHE_REDIS_PORT': 6379,
    'CACHE_REDIS_DB': 2,
}

# ClickHouse specific settings
SQLLAB_TIMEOUT = 300
SUPERSET_WEBSERVER_TIMEOUT = 300

# Allow data upload
UPLOAD_FOLDER = '/app/superset_home/uploads/'
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'parquet'}

# Row limit for SQL Lab
SQL_MAX_ROW = 100000
DISPLAY_MAX_ROW = 10000

# Default language
BABEL_DEFAULT_LOCALE = 'ru'
LANGUAGES = {
    'en': {'flag': 'us', 'name': 'English'},
    'ru': {'flag': 'ru', 'name': 'Russian'},
}

# Theme
APP_NAME = "Game Analytics Course"

# Enable public dashboards
PUBLIC_ROLE_LIKE = "Gamma"

# Guest user for students
GUEST_ROLE_NAME = "Student"
GUEST_TOKEN_JWT_SECRET = "your-jwt-secret-change-in-production"
GUEST_TOKEN_JWT_ALGO = "HS256"
GUEST_TOKEN_HEADER_NAME = "X-GuestToken"
GUEST_TOKEN_JWT_EXP_SECONDS = 300

# Logging
LOG_LEVEL = 'INFO'
ENABLE_PROXY_FIX = True
