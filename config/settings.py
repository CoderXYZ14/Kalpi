from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
if (BASE_DIR / ".env").exists():
    environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="dev-only-insecure-key")
DEBUG = env.bool("DEBUG", default=True)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "brokers",
    "executions",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {"default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.TokenAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "EXCEPTION_HANDLER": "common.exceptions.exception_handler",
    "DEFAULT_THROTTLE_RATES": {"anon": "10/min"},
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}

BYPASS_MARKET_HOURS = env.bool("BYPASS_MARKET_HOURS", default=False)
ENGINE_POLL_INTERVAL = env.float("ENGINE_POLL_INTERVAL", default=2)
ENGINE_POLL_TIMEOUT = env.float("ENGINE_POLL_TIMEOUT", default=30)
ENGINE_RETRY_ATTEMPTS = env.int("ENGINE_RETRY_ATTEMPTS", default=4)
ENGINE_RETRY_WAIT = env.float("ENGINE_RETRY_WAIT", default=1)
ENGINE_ORDERS_PER_SECOND = env.int("ENGINE_ORDERS_PER_SECOND", default=8)

WEBHOOK_URL = env("WEBHOOK_URL", default="")

KITE_API_KEY = env("KITE_API_KEY", default="")
KITE_API_SECRET = env("KITE_API_SECRET", default="")
GROWW_API_KEY = env("GROWW_API_KEY", default="")
GROWW_API_SECRET = env("GROWW_API_SECRET", default="")
UPSTOX_API_KEY = env("UPSTOX_API_KEY", default="")
UPSTOX_API_SECRET = env("UPSTOX_API_SECRET", default="")
UPSTOX_REDIRECT_URI = env("UPSTOX_REDIRECT_URI", default="")
FYERS_APP_ID = env("FYERS_APP_ID", default="")
FYERS_SECRET_KEY = env("FYERS_SECRET_KEY", default="")
FYERS_REDIRECT_URI = env("FYERS_REDIRECT_URI", default="")
