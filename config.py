"""
Configuration settings for SmartCompress AI.
Information Storage Management (ISM) Academic Project.
"""

import os
from pathlib import Path

# Base project directory
BASE_DIR = Path(__file__).resolve().parent

# Application directories
UPLOAD_DIR = BASE_DIR / "uploads"
COMPRESSED_DIR = BASE_DIR / "compressed"
REPORT_DIR = BASE_DIR / "reports"
DATABASE_DIR = BASE_DIR / "database"
MODEL_DIR = BASE_DIR / "model"
DATASET_DIR = BASE_DIR / "dataset"

# Ensure runtime directories exist
for directory in [UPLOAD_DIR, COMPRESSED_DIR, REPORT_DIR, DATABASE_DIR, MODEL_DIR, DATASET_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "smartcompress-ai-secret-key-ism-2026")
    
    # Directory paths
    UPLOAD_DIR = UPLOAD_DIR
    COMPRESSED_DIR = COMPRESSED_DIR
    REPORT_DIR = REPORT_DIR
    DATABASE_DIR = DATABASE_DIR
    MODEL_DIR = MODEL_DIR
    DATASET_DIR = DATASET_DIR

    DATABASE_PATH = DATABASE_DIR / "database.db"
    MODEL_PATH = MODEL_DIR / "saved_model.joblib"
    DATASET_PATH = DATASET_DIR / "compression_dataset.csv"

    # Upload constraints
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 150 * 1024 * 1024))  # 150 MB
    MAX_FILE_SIZE_MB = MAX_CONTENT_LENGTH / (1024 * 1024)

    # Temporary file retention (in hours)
    TEMP_FILE_RETENTION_HOURS = int(os.environ.get("TEMP_FILE_RETENTION_HOURS", 24))

    # Supported compression algorithms
    SUPPORTED_ALGORITHMS = ["PDF-Deflate", "7Z", "ZIP", "GZIP", "BZIP2", "LZMA"]

    # Allowed user preferences
    COMPRESSION_PREFERENCES = [
        ("balanced", "Balanced (Default - Good compression & speed)"),
        ("max_compression", "Maximum Compression (Best space saving)"),
        ("fastest", "Fastest Compression (Prioritize rapid speed)")
    ]

    # Benchmark size limit to avoid blocking the server (e.g. 150 MB max for all-algorithm benchmark)
    MAX_BENCHMARK_FILE_SIZE = int(os.environ.get("MAX_BENCHMARK_FILE_SIZE", 150 * 1024 * 1024))  # 150 MB

    # Security settings
    DEBUG = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


class TestConfig(Config):
    """Configuration for automated test suite."""
    TESTING = True
    DATABASE_PATH = DATABASE_DIR / "test_database.db"
    UPLOAD_DIR = BASE_DIR / "tests" / "test_uploads"
    COMPRESSED_DIR = BASE_DIR / "tests" / "test_compressed"
    REPORT_DIR = BASE_DIR / "tests" / "test_reports"
