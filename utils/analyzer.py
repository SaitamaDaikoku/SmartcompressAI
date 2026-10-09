"""
File analysis module for SmartCompress AI.
Extracts metadata, computes SHA-256 hash, determines MIME type, and calculates Shannon Entropy.
"""

import hashlib
import mimetypes
from pathlib import Path
from typing import Dict, Any, Union

from utils.entropy import calculate_entropy, interpret_entropy


# Pre-known pure archive containers
KNOWN_COMPRESSED_EXTENSIONS = {
    ".zip", ".tar", ".gz", ".tgz", ".bz2", ".tbz2", ".xz", ".txz", ".7z",
    ".rar", ".z"
}

EXTENSION_CATEGORY_MAP = {
    # Text / Code
    ".txt": "Text / Document",
    ".md": "Text / Document",
    ".rtf": "Text / Document",
    ".log": "Text / Document",
    ".py": "Structured Data / Code",
    ".js": "Structured Data / Code",
    ".html": "Structured Data / Code",
    ".css": "Structured Data / Code",
    ".c": "Structured Data / Code",
    ".cpp": "Structured Data / Code",
    ".java": "Structured Data / Code",
    ".json": "Structured Data / Code",
    ".xml": "Structured Data / Code",
    ".csv": "Structured Data / Code",
    ".sql": "Structured Data / Code",
    ".yaml": "Structured Data / Code",
    ".yml": "Structured Data / Code",
    
    # Documents
    ".pdf": "Document",
    ".doc": "Document",
    ".docx": "Document",
    ".xls": "Document",
    ".xlsx": "Document",
    ".ppt": "Document",
    ".pptx": "Document",

    # Images
    ".png": "Image / Graphics",
    ".jpg": "Image / Graphics",
    ".jpeg": "Image / Graphics",
    ".gif": "Image / Graphics",
    ".bmp": "Image / Graphics",
    ".svg": "Image / Graphics",
    ".webp": "Image / Graphics",
    ".tiff": "Image / Graphics",

    # Audio & Video
    ".mp3": "Audio / Sound",
    ".wav": "Audio / Sound",
    ".flac": "Audio / Sound",
    ".mp4": "Video / Multimedia",
    ".mkv": "Video / Multimedia",
    ".avi": "Video / Multimedia",

    # Archives
    ".zip": "Archive / Compressed",
    ".tar": "Archive / Compressed",
    ".gz": "Archive / Compressed",
    ".bz2": "Archive / Compressed",
    ".xz": "Archive / Compressed",
    ".7z": "Archive / Compressed",
    ".rar": "Archive / Compressed",

    # Binary / Executables
    ".exe": "Binary / Executable",
    ".dll": "Binary / Executable",
    ".so": "Binary / Executable",
    ".bin": "Binary / Executable",
    ".iso": "Binary / Disk Image",
}


def calculate_sha256(file_path: Union[str, Path], chunk_size: int = 65536) -> str:
    """Calculate SHA-256 checksum using chunked streaming."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def format_file_size(size_bytes: int) -> Dict[str, Union[int, float, str]]:
    """Return file size in formatted representations (Bytes, KB, MB, readable string)."""
    kb = size_bytes / 1024
    mb = size_bytes / (1024 * 1024)

    if size_bytes < 1024:
        display = f"{size_bytes} Bytes"
    elif kb < 1024:
        display = f"{kb:.2f} KB"
    else:
        display = f"{mb:.2f} MB"

    return {
        "bytes": size_bytes,
        "kb": round(kb, 2),
        "mb": round(mb, 2),
        "display": display
    }


def determine_category(extension: str, mime_type: str) -> str:
    """Categorize file based on extension and MIME type."""
    ext = extension.lower()
    if ext in EXTENSION_CATEGORY_MAP:
        return EXTENSION_CATEGORY_MAP[ext]

    if mime_type:
        if mime_type.startswith("text/"):
            return "Text / Document"
        elif mime_type.startswith("image/"):
            return "Image / Graphics"
        elif mime_type.startswith("audio/"):
            return "Audio / Sound"
        elif mime_type.startswith("video/"):
            return "Video / Multimedia"
        elif "zip" in mime_type or "tar" in mime_type or "compressed" in mime_type or "7z" in mime_type:
            return "Archive / Compressed"
        elif "application/json" in mime_type or "application/xml" in mime_type:
            return "Structured Data / Code"
        elif "application/pdf" in mime_type:
            return "Document"

    return "Binary / General Data"


def analyze_file(file_path: Union[str, Path], original_filename: str = None) -> Dict[str, Any]:
    """
    Perform complete metadata analysis and Shannon entropy computation on a file or folder directory.
    
    Returns structured analysis dictionary.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File or directory not found: {file_path}")

    filename = original_filename if original_filename else path.name

    # Handle Directory / Folder analysis
    if path.is_dir():
        all_files = [f for f in path.rglob("*") if f.is_file()]
        file_count = len(all_files)
        size_bytes = sum(f.stat().st_size for f in all_files)
        size_info = format_file_size(size_bytes)

        # Entropy of entire directory byte stream
        entropy_val = calculate_entropy(path)
        entropy_details = interpret_entropy(entropy_val)

        # Aggregate SHA-256 for directory structure & contents
        hasher = hashlib.sha256()
        for f in sorted(all_files, key=lambda p: str(p.relative_to(path))):
            rel_str = str(f.relative_to(path)).replace("\\", "/")
            hasher.update(rel_str.encode("utf-8", errors="replace"))
            try:
                with open(f, "rb") as fp:
                    while True:
                        chunk = fp.read(65536)
                        if not chunk:
                            break
                        hasher.update(chunk)
            except OSError:
                pass
        sha256_hash = hasher.hexdigest()

        category = "Folder / Multi-File Archive"
        mime_type = "application/x-directory"
        extension = "folder"
        is_precompressed = (entropy_val >= 7.92)

        return {
            "filename": filename,
            "extension": extension,
            "mime_type": mime_type,
            "size_bytes": size_bytes,
            "size_kb": size_info["kb"],
            "size_mb": size_info["mb"],
            "size_display": size_info["display"],
            "entropy": entropy_val,
            "entropy_details": entropy_details,
            "category": category,
            "sha256": sha256_hash,
            "is_precompressed": is_precompressed,
            "is_directory": True,
            "file_count": file_count
        }

    # Handle single file analysis
    extension = Path(filename).suffix.lower()

    # Determine MIME type
    mime_type, _ = mimetypes.guess_type(filename)
    if not mime_type:
        mime_type = "application/octet-stream"

    # Size measurements
    size_bytes = path.stat().st_size
    size_info = format_file_size(size_bytes)

    # Entropy computation
    entropy_val = calculate_entropy(path)
    entropy_details = interpret_entropy(entropy_val)

    # File category
    category = determine_category(extension, mime_type)

    # SHA-256
    sha256_hash = calculate_sha256(path)

    # Check if file is already a packaged archive or has near-maximal ceiling entropy (>= 7.92 bits/byte)
    is_precompressed = (extension in KNOWN_COMPRESSED_EXTENSIONS and entropy_val >= 7.80) or (entropy_val >= 7.92)

    return {
        "filename": filename,
        "extension": extension if extension else "none",
        "mime_type": mime_type,
        "size_bytes": size_bytes,
        "size_kb": size_info["kb"],
        "size_mb": size_info["mb"],
        "size_display": size_info["display"],
        "entropy": entropy_val,
        "entropy_details": entropy_details,
        "category": category,
        "sha256": sha256_hash,
        "is_precompressed": is_precompressed,
        "is_directory": False,
        "file_count": 1
    }

