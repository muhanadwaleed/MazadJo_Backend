"""
Django settings for core project.

Loads from environment / `.env` (see `.env.example`).
"""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, True),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CELERY_TASK_EAGER_PROPAGATES=(bool, True),
)

environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env(
    "SECRET_KEY",
    default="django-insecure-dev-only-change-in-production",
)

DEBUG = env("DEBUG")

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = env.bool("CORS_ALLOW_CREDENTIALS", default=True)
if CORS_ALLOWED_ORIGINS:
    CORS_ALLOW_ALL_ORIGINS = False
else:
    CORS_ALLOW_ALL_ORIGINS = env.bool("CORS_ALLOW_ALL_ORIGINS", default=DEBUG)

ALLOWED_HOSTS = env("ALLOWED_HOSTS")


def _database_config():
    """PostgreSQL if DATABASE_URL or POSTGRES_DB is set; else SQLite."""
    database_url = env("DATABASE_URL", default="").strip()
    postgres_db = env("POSTGRES_DB", default="").strip()

    if database_url:
        return {"default": env.db("DATABASE_URL")}

    if postgres_db:
        return {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": postgres_db,
                "USER": env("POSTGRES_USER", default="postgres"),
                "PASSWORD": env("POSTGRES_PASSWORD", default=""),
                "HOST": env("POSTGRES_HOST", default="localhost"),
                "PORT": env("POSTGRES_PORT", default="5432"),
                "CONN_MAX_AGE": env.int("POSTGRES_CONN_MAX_AGE", default=60),
            }
        }

    sqlite_name = env("SQLITE_PATH", default="db.sqlite3")
    sqlite_path = Path(sqlite_name)
    if not sqlite_path.is_absolute():
        sqlite_path = BASE_DIR / sqlite_path

    return {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": sqlite_path,
        }
    }


DATABASES = _database_config()

INSTALLED_APPS = [
    "daphne",
    "corsheaders",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "rest_framework_simplejwt",
    "channels",
    "accounts",
    "catalog",
    "payments",
    "auctions",
    "cms",
    "configuration",
    "subscriptions",
    "bidding",
    "ratings",
    "notifications",
    "audit",
    "django_celery_beat",
    "observability",
    "fraud",
]

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "accounts.middleware.FingerprintMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"

REDIS_URL = env("REDIS_URL", default="").strip()

if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        },
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        },
    }

if REDIS_URL:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [REDIS_URL],
            },
        },
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        },
    }


def _default_celery_broker() -> str:
    explicit = env("CELERY_BROKER_URL", default="").strip()
    if explicit:
        return explicit
    if REDIS_URL:
        u = REDIS_URL.rstrip("/")
        if u.endswith("/0"):
            return u[:-2] + "/1"
        if "/" not in u.split("://", 1)[-1]:
            return u + "/1"
        return u.rsplit("/", 1)[0] + "/1"
    return "redis://127.0.0.1:6379/1"


CELERY_BROKER_URL = _default_celery_broker()
CELERY_RESULT_BACKEND = (
    env(
        "CELERY_RESULT_BACKEND",
        default=CELERY_BROKER_URL,
    ).strip()
    or CELERY_BROKER_URL
)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = env("CELERY_TIMEZONE", default="UTC")
_celery_eager_default = not (
    bool(REDIS_URL) or bool(env("CELERY_BROKER_URL", default="").strip())
)
CELERY_TASK_ALWAYS_EAGER = env.bool(
    "CELERY_TASK_ALWAYS_EAGER",
    default=_celery_eager_default,
)
CELERY_TASK_EAGER_PROPAGATES = env.bool("CELERY_TASK_EAGER_PROPAGATES")

CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

SMS_GATEWAY_URL = env("SMS_GATEWAY_URL", default="").strip()
SMS_GATEWAY_API_KEY = env("SMS_GATEWAY_API_KEY", default="").strip()
SMS_FORM_FIELD_TO = env("SMS_FORM_FIELD_TO", default="to")
SMS_FORM_FIELD_MESSAGE = env("SMS_FORM_FIELD_MESSAGE", default="message")
SMS_HTTP_TIMEOUT = env.int("SMS_HTTP_TIMEOUT", default=5)

OTP_TTL_MINUTES = env.int("OTP_TTL_MINUTES", default=10)
# How long a verified register OTP remains valid for POST /auth/register/
REGISTRATION_OTP_MAX_AGE_MINUTES = env.int("REGISTRATION_OTP_MAX_AGE_MINUTES", default=30)
OTP_RATE_LIMIT_MAX = env.int("OTP_RATE_LIMIT_MAX", default=3)
OTP_RATE_LIMIT_WINDOW_MINUTES = env.int("OTP_RATE_LIMIT_WINDOW_MINUTES", default=10)
FIXED_OTP = env.bool("FIXED_OTP", default=False)

ANTI_SNIPE_FORCE_SECONDS = env.int("ANTI_SNIPE_FORCE_SECONDS", default=10)

BID_MAX_PER_SECOND_PER_USER = env.int("BID_MAX_PER_SECOND_PER_USER", default=3)
BID_VELOCITY_WINDOW_SEC = env.int("BID_VELOCITY_WINDOW_SEC", default=1)

AUCTION_MEDIA_MAX_BYTES = env.int("AUCTION_MEDIA_MAX_BYTES", default=10 * 1024 * 1024)

# Risk scoring (measurable; enforcement flags default off — enable gradually)
RISK_SCORE_MAX = env.int("RISK_SCORE_MAX", default=100)
RISK_SHADOW_BAN_SCORE = env.int("RISK_SHADOW_BAN_SCORE", default=50)
RISK_HARD_BAN_SCORE = env.int("RISK_HARD_BAN_SCORE", default=80)
RISK_ENFORCE_SHADOW_FROM_SCORE = env.bool(
    "RISK_ENFORCE_SHADOW_FROM_SCORE", default=False
)
RISK_ENFORCE_HARD_DEACTIVATE = env.bool("RISK_ENFORCE_HARD_DEACTIVATE", default=False)
RISK_RATE_LIMIT_CACHE_BUMP = env.int("RISK_RATE_LIMIT_CACHE_BUMP", default=0)
RISK_SELF_OUTBID_BUMP = env.int("RISK_SELF_OUTBID_BUMP", default=0)
RISK_SELF_OUTBID_MIN_PRIOR_RUN = env.int("RISK_SELF_OUTBID_MIN_PRIOR_RUN", default=2)
RISK_PUMPING_BUMP = env.int("RISK_PUMPING_BUMP", default=20)
RISK_SHARED_IP_ACCOUNT_THRESHOLD = env.int(
    "RISK_SHARED_IP_ACCOUNT_THRESHOLD", default=3
)
RISK_SHARED_IP_BUMP = env.int("RISK_SHARED_IP_BUMP", default=30)
RISK_WIN_RATIO_MIN_TOTAL_BIDS = env.int("RISK_WIN_RATIO_MIN_TOTAL_BIDS", default=10)
RISK_WIN_RATIO_THRESHOLD = float(env("RISK_WIN_RATIO_THRESHOLD", default="0.8"))
RISK_WIN_RATIO_BUMP = env.int("RISK_WIN_RATIO_BUMP", default=15)
FRAUD_ANALYZE_BID_ASYNC = env.bool("FRAUD_ANALYZE_BID_ASYNC", default=True)
# Bid pumping: only consider bids within this many seconds (reduces stale-pattern false positives)
RISK_PUMPING_WINDOW_SECONDS = env.int("RISK_PUMPING_WINDOW_SECONDS", default=15)
# When UserStats.total_bids is 0, one-shot recount from DB for win-ratio heuristic
RISK_STATS_FALLBACK_WHEN_ZERO = env.bool("RISK_STATS_FALLBACK_WHEN_ZERO", default=True)

# Shadow bids: when True, restricted users get HTTP 201 but bid is hidden and does not move price/WS
SHADOW_BID_SILENT_PUBLICATION = env.bool("SHADOW_BID_SILENT_PUBLICATION", default=True)

# Risk score decay (Celery beat: fraud-decay-risk-scores after seed_celery_beat)
RISK_DECAY_ENABLED = env.bool("RISK_DECAY_ENABLED", default=True)
RISK_DECAY_MODE = env("RISK_DECAY_MODE", default="linear")  # linear | multiply
RISK_DECAY_LINEAR_POINTS = env.int("RISK_DECAY_LINEAR_POINTS", default=1)
RISK_DECAY_MULTIPLY_FACTOR = float(env("RISK_DECAY_MULTIPLY_FACTOR", default="0.95"))

FINGERPRINT_MIDDLEWARE_ENABLED = env.bool(
    "FINGERPRINT_MIDDLEWARE_ENABLED", default=False
)
FINGERPRINT_MIN_INTERVAL_SECONDS = env.int(
    "FINGERPRINT_MIN_INTERVAL_SECONDS", default=3600
)

ENABLE_PROMETHEUS_METRICS = env.bool("ENABLE_PROMETHEUS_METRICS", default=False)
METRICS_SCRAPE_TOKEN = env("METRICS_SCRAPE_TOKEN", default="").strip()

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    # CommonPasswordValidator omitted so dev/staging can use familiar test passwords.
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = env("LANGUAGE_CODE", default="en-us")
TIME_ZONE = env("TIME_ZONE", default="UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = env("STATIC_URL", default="static/")
STATIC_ROOT = env("STATIC_ROOT", default=str(BASE_DIR / "staticfiles"))

MEDIA_URL = env("MEDIA_URL", default="media/")
MEDIA_ROOT = env("MEDIA_ROOT", default=str(BASE_DIR / "media"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="webmaster@localhost")

DJANGO_LOG_LEVEL = env("DJANGO_LOG_LEVEL", default="INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "mazadjo": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "mazadjo",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": DJANGO_LOG_LEVEL,
    },
    "loggers": {
        "mazadjo.bids": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "mazadjo.otp": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "mazadjo.fraud": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

_default_renderers = ["rest_framework.renderers.JSONRenderer"]
if DEBUG:
    _default_renderers.append("rest_framework.renderers.BrowsableAPIRenderer")

REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "core.exceptions.mazadjo_exception_handler",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "accounts.authentication.ActiveUnblockedJWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_RENDERER_CLASSES": _default_renderers,
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "MazadJo API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SECURITY": [{"jwtAuth": []}],
    "APPEND_COMPONENTS": {
        "securitySchemes": {
            "jwtAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        }
    },
}

WEBHOOK_PAYMENT_SECRET = env("WEBHOOK_PAYMENT_SECRET", default="").strip()

_jwt_signing_key = env("JWT_SIGNING_KEY", default="").strip() or SECRET_KEY

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=env.int("JWT_ACCESS_MINUTES", default=60),
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=env.int("JWT_REFRESH_DAYS", default=7),
    ),
    "ROTATE_REFRESH_TOKENS": env.bool("JWT_ROTATE_REFRESH_TOKENS", default=False),
    "BLACKLIST_AFTER_ROTATION": env.bool("JWT_BLACKLIST_AFTER_ROTATION", default=False),
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": env("JWT_ALGORITHM", default="HS256"),
    "SIGNING_KEY": _jwt_signing_key,
    "AUTH_HEADER_TYPES": (env("JWT_AUTH_HEADER_TYPE", default="Bearer"),),
    "AUTH_HEADER_NAME": env("JWT_AUTH_HEADER_NAME", default="HTTP_AUTHORIZATION"),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

_secure_proxy = env("SECURE_PROXY_SSL_HEADER", default="").strip()
if _secure_proxy:
    _h, _v = [x.strip() for x in _secure_proxy.split(",", 1)]
    SECURE_PROXY_SSL_HEADER = (_h, _v)
else:
    SECURE_PROXY_SSL_HEADER = None

USE_X_FORWARDED_HOST = env.bool("USE_X_FORWARDED_HOST", default=False)
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
