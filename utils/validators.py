"""
File validation and security utility functions.
Ensures path security, size limits, and filename sanitization.
"""

import os
import re
from pathlib import Path
from typing import Tuple, Optional
from werkzeug.utils import secure_filename


def sanitize_filename(filename: str) -> str:
    """
    Sanitize an uploaded filename to prevent directory traversal or injection attacks.
    Preserves a clean extension and falls back to a default name if empty.
    """
    if not filename:
        return "unnamed_file.bin"

    # Use werkzeug's secure_filename
    cleaned = secure_filename(filename)
    if not cleaned:
        # If secure_filename stripped everything (e.g. Unicode-only filename)
        cleaned = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
        cleaned = cleaned.strip("._-")
        if not cleaned:
            cleaned = "unnamed_file.bin"

    return cleaned


def is_safe_path(base_dir: Path, target_path: Path) -> bool:
    """
    Verify that target_path is strictly inside base_dir to prevent path traversal attacks.
    """
    try:
        resolved_base = base_dir.resolve()
        resolved_target = target_path.resolve()
        return resolved_base in resolved_target.parents or resolved_base == resolved_target
    except Exception:
        return False


def validate_file_upload(file_obj, max_size_bytes: int) -> Tuple[bool, Optional[str]]:
    """
    Validate that an uploaded file object has a filename and does not exceed size limits.
    """
    if not file_obj or file_obj.filename == "":
        return False, "No file selected. Please choose a file to upload."

    # Inspect stream length if available
    file_obj.seek(0, os.SEEK_END)
    size = file_obj.tell()
    file_obj.seek(0)

    if size > max_size_bytes:
        max_mb = max_size_bytes / (1024 * 1024)
        return False, f"File size ({size / (1024 * 1024):.2f} MB) exceeds maximum allowed limit ({max_mb:.1f} MB)."

    return True, None
