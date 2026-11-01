import os
from pathlib import Path

class Config:
    """Base configuration for CA Onboarding Backend."""
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    BACKEND_DIR = Path(__file__).resolve().parent.parent
    UPLOAD_DIR = BASE_DIR / "uploads"
    SAMPLE_DIR = BASE_DIR / "Adams_sample_pack"
    DB_PATH = BASE_DIR / "onboarding.db"
    DEBUG = False
    TESTING = False
    CORS_HEADERS = "Content-Type"

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig
}
