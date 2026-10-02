import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "acc-consultation-dev-secret-key-change-me")
    DATABASE = os.path.join(BASE_DIR, "instance", "acc_consultation.db")
    SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
