"""
Temporary file cleanup utility for SmartCompress AI.
Cleans up temporary uploaded, compressed, and benchmark files older than retention policy.
"""

import time
from pathlib import Path
from typing import Dict, Any

from config import Config


def cleanup_expired_files(retention_hours: int = None) -> Dict[str, Any]:
    """
    Remove temporary upload, benchmark, and report files older than retention window.
    Default retention configured in Config.TEMP_FILE_RETENTION_HOURS.
    """
    hours = retention_hours if retention_hours is not None else Config.TEMP_FILE_RETENTION_HOURS
    max_age_seconds = hours * 3600
    now = time.time()

    deleted_count = 0
    reclaimed_bytes = 0

    directories_to_clean = [
        Config.UPLOAD_DIR,
        Config.COMPRESSED_DIR / "benchmarks",
        Config.REPORT_DIR
    ]

    for directory in directories_to_clean:
        if not directory.exists():
            continue
        for file_path in directory.iterdir():
            if file_path.is_file():
                try:
                    file_stat = file_path.stat()
                    file_age = now - file_stat.st_mtime
                    if file_age > max_age_seconds:
                        size = file_stat.st_size
                        file_path.unlink()
                        deleted_count += 1
                        reclaimed_bytes += size
                except OSError as e:
                    print(f"[Cleanup] Error removing {file_path}: {e}")

    return {
        "deleted_count": deleted_count,
        "reclaimed_bytes": reclaimed_bytes,
        "reclaimed_mb": round(reclaimed_bytes / (1024 * 1024), 2),
        "retention_hours": hours
    }


if __name__ == "__main__":
    result = cleanup_expired_files()
    print(f"[Cleanup] Removed {result['deleted_count']} expired files, reclaiming {result['reclaimed_mb']} MB.")
