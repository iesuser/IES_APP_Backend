import os
from os import pardir, path, sep

from dotenv import load_dotenv
from sqlalchemy.engine import URL

BASE_DIR = path.abspath(path.dirname(__file__) + sep + pardir)

load_dotenv(dotenv_path=path.join(BASE_DIR, ".env"), override=True)


def _postgres_uri():
    # URL.create escapes special characters in the password.
    return URL.create(
        "postgresql+psycopg",
        username=Config.POSTGRES_USER,
        password=Config.POSTGRES_PASSWORD,
        host=Config.POSTGRES_HOST,
        port=Config.POSTGRES_PORT,
        database=Config.POSTGRES_DB,
        query={"sslmode": Config.POSTGRES_SSLMODE},
    ).render_as_string(hide_password=False)


class Config:
    BASE_DIR = BASE_DIR
    APP_ENV = (os.getenv("APP_ENV") or "development").lower()

    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "127.0.0.1")
    POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB = os.getenv("POSTGRES_DB", "ies_app")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "ies_app")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
    POSTGRES_SSLMODE = os.getenv("POSTGRES_SSLMODE", "prefer")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 1800,
        "hide_parameters": True,
        "connect_args": {
            "connect_timeout": 5,
            "application_name": "ies_app_backend",
        },
    }

    RESTX_MASK_SWAGGER = False


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv("DEV_DATABASE_URI") or _postgres_uri()


class ProductionConfig(Config):
    DEBUG = False
    APP_ENV = "production"
    SQLALCHEMY_DATABASE_URI = os.getenv("PROD_DATABASE_URI") or _postgres_uri()


def get_config():
    if Config.POSTGRES_USER in {"postgres", "root"}:
        raise RuntimeError("Use a dedicated database role, not a superuser.")
    if not Config.POSTGRES_PASSWORD.strip():
        raise RuntimeError("POSTGRES_PASSWORD is required and must stay in .env.")
    allowed_ssl = {"disable", "allow", "prefer", "require", "verify-ca", "verify-full"}
    if Config.POSTGRES_SSLMODE not in allowed_ssl:
        raise RuntimeError("POSTGRES_SSLMODE is not a recognized value.")

    if Config.APP_ENV == "production":
        return ProductionConfig
    return DevelopmentConfig
