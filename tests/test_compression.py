"""
Automated unit tests for real compression engine and lossless roundtrip verification.
"""

import os
import tempfile
from pathlib import Path
import pytest

from engines.compression_engine import (
    compress_file,
    decompress_and_verify,
    ALL_ALGORITHMS
)


@pytest.fixture
def sample_text_file():
    """Create a temporary text file with repetitive content."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        # Repetitive pattern suitable for high compression
        tmp.write(b"Information Storage Management - SmartCompress AI Research\n" * 1000)
        tmp_path = Path(tmp.name)
    yield tmp_path
    if tmp_path.exists():
        tmp_path.unlink()


@pytest.mark.parametrize("algorithm", ALL_ALGORITHMS)
def test_all_algorithms_compression_and_lossless_roundtrip(sample_text_file, algorithm):
    """
    Test real compression on all 5 algorithms and verify mathematical lossless reconstruction.
    """
    with tempfile.TemporaryDirectory() as out_dir:
        res = compress_file(
            input_path=sample_text_file,
            algorithm=algorithm,
            output_dir=out_dir,
            original_filename="sample.txt"
        )

        assert res["success"] is True
        assert res["error"] is None
        assert res["original_size"] > 0
        assert res["compressed_size"] > 0
        assert res["bytes_saved"] > 0
        assert res["space_saving_pct"] > 50.0  # Repetitive text easily yields > 50%
        assert res["compression_duration"] >= 0.0

        output_path = Path(res["output_path"])
        assert output_path.exists()
        assert output_path.stat().st_size == res["compressed_size"]

        # Critical: Verify roundtrip decompression matches original byte-for-byte!
        is_identical = decompress_and_verify(
            compressed_path=output_path,
            original_path=sample_text_file,
            algorithm=algorithm
        )
        assert is_identical is True, f"Lossless integrity check failed for {algorithm}!"


def test_empty_file_compression():
    """Ensure empty (0-byte) files are compressed without exceptions or division-by-zero."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        with tempfile.TemporaryDirectory() as out_dir:
            res = compress_file(
                input_path=tmp_path,
                algorithm="ZIP",
                output_dir=out_dir,
                original_filename="empty.txt"
            )
            assert res["success"] is True
            assert res["original_size"] == 0
            assert res["bytes_saved"] <= 0
            assert res["space_saving_pct"] == 0.0
    finally:
        tmp_path.unlink()


def test_negative_space_savings_on_tiny_file():
    """
    Tiny files (e.g. 5 bytes) when archived produce an archive larger than the file
    due to headers. Verify negative savings are accurately reported, not masked.
    """
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"Hi!")
        tmp_path = Path(tmp.name)

    try:
        with tempfile.TemporaryDirectory() as out_dir:
            res = compress_file(
                input_path=tmp_path,
                algorithm="ZIP",
                output_dir=out_dir,
                original_filename="tiny.txt"
            )
            assert res["success"] is True
            assert res["compressed_size"] > res["original_size"]
            assert res["bytes_saved"] < 0
            assert res["space_saving_pct"] < 0.0
    finally:
        tmp_path.unlink()


def test_invalid_algorithm():
    """Attempting to use an unsupported algorithm returns failure status."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"Test data")
        tmp_path = Path(tmp.name)

    try:
        with tempfile.TemporaryDirectory() as out_dir:
            res = compress_file(
                input_path=tmp_path,
                algorithm="NON_EXISTENT_FORMAT",
                output_dir=out_dir
            )
            assert res["success"] is False
            assert "Unsupported" in res["error"]
    finally:
        tmp_path.unlink()


@pytest.mark.parametrize("algorithm", ALL_ALGORITHMS)
def test_folder_compression_all_algorithms(algorithm):
    """
    Test compressing an entire directory hierarchy with all 5 lossless algorithms
    and verify lossless byte-for-byte roundtrip reconstruction.
    """
    with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as out_dir:
        src_path = Path(src_dir)
        sub_dir = src_path / "sub"
        sub_dir.mkdir()
        (src_path / "readme.txt").write_bytes(b"Information Storage Management\n" * 200)
        (sub_dir / "code.py").write_bytes(b"def optimize():\n    return True\n" * 200)

        res = compress_file(
            input_path=src_path,
            algorithm=algorithm,
            output_dir=out_dir,
            original_filename="sample_project"
        )

        assert res["success"] is True
        assert res["original_size"] > 0
        assert res["compressed_size"] > 0
        assert res["bytes_saved"] > 0
        assert res["space_saving_pct"] > 50.0

        out_file = Path(res["output_path"])
        assert out_file.exists()

        # Decompress and verify
        verified = decompress_and_verify(
            compressed_path=out_file,
            original_path=src_path,
            algorithm=algorithm
        )
        assert verified is True, f"Directory lossless roundtrip failed for {algorithm}"

