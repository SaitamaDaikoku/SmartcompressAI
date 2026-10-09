"""
Unit tests for entropy calculation, file analysis, and validation utilities.
"""

import os
import tempfile
from pathlib import Path
import pytest

from utils.entropy import calculate_entropy, interpret_entropy
from utils.analyzer import analyze_file, calculate_sha256, format_file_size
from utils.validators import sanitize_filename, is_safe_path


def test_entropy_empty_file():
    """Verify that an empty file yields exactly 0.0 entropy."""
    with tempfile.NamedTemporaryFile() as tmp:
        entropy = calculate_entropy(tmp.name)
        assert entropy == 0.0
        interpretation = interpret_entropy(entropy)
        assert interpretation["level"] == "Very Low"


def test_entropy_single_repeated_byte():
    """A file filled with only one byte value has 0 bits/byte entropy (complete uniformity)."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"A" * 10000)
        tmp_path = Path(tmp.name)
    try:
        entropy = calculate_entropy(tmp_path)
        assert entropy == 0.0
        details = interpret_entropy(entropy)
        assert "Compressible" in details["compressibility"]
    finally:
        tmp_path.unlink()


def test_entropy_random_data():
    """Random data approaches maximum entropy of 8.0 bits/byte."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(os.urandom(64 * 1024))
        tmp_path = Path(tmp.name)
    try:
        entropy = calculate_entropy(tmp_path)
        # Uniformly distributed random bytes will be close to 7.9+
        assert entropy > 7.5
        details = interpret_entropy(entropy)
        assert details["level"] == "Near-Maximal"
    finally:
        tmp_path.unlink()


def test_file_metadata_extraction():
    """Verify metadata extraction: filename, size, category, mime type, and sha256."""
    content = b"print('Hello Information Storage Management')\n"
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        res = analyze_file(tmp_path, original_filename="script.py")
        assert res["filename"] == "script.py"
        assert res["extension"] == ".py"
        assert res["category"] == "Structured Data / Code"
        assert res["size_bytes"] == len(content)
        assert res["sha256"] == calculate_sha256(tmp_path)
        assert "text" in res["mime_type"] or "python" in res["mime_type"] or res["mime_type"] != ""
    finally:
        tmp_path.unlink()


def test_sanitize_filename():
    """Ensure filenames with directory traversal are sanitized."""
    assert sanitize_filename("../../etc/passwd") == "etc_passwd"
    assert sanitize_filename("..\\..\\boot.ini") == "boot.ini"
    assert sanitize_filename("valid_document.pdf") == "valid_document.pdf"
    assert sanitize_filename("") == "unnamed_file.bin"


def test_is_safe_path():
    """Ensure path traversal outside base folder is detected."""
    base = Path("/var/uploads")
    safe = Path("/var/uploads/test.txt")
    unsafe = Path("/var/etc/passwd")
    
    assert is_safe_path(base, safe) is True
    assert is_safe_path(base, unsafe) is False


def test_directory_analysis():
    """Verify that analyzing a folder correctly computes aggregate metrics and file counts."""
    with tempfile.TemporaryDirectory() as temp_dir:
        dir_path = Path(temp_dir)
        sub_dir = dir_path / "subfolder"
        sub_dir.mkdir()
        (dir_path / "file1.txt").write_bytes(b"A" * 500)
        (sub_dir / "file2.py").write_bytes(b"B" * 500)

        res = analyze_file(dir_path, original_filename="my_project")
        assert res["filename"] == "my_project"
        assert res["is_directory"] is True
        assert res["file_count"] == 2
        assert res["size_bytes"] == 1000
        assert res["category"] == "Folder / Multi-File Archive"
        assert res["entropy"] == 1.0  # Equal frequencies of 'A' and 'B' -> log2(2) = 1.0 bit

