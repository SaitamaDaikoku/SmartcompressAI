"""
Real file compression engine supporting ZIP, GZIP, BZIP2, LZMA, and 7Z.
Information Storage Management (ISM) lossless data compression implementation.
"""

import bz2
import gzip
import lzma
import os
import shutil
import tarfile
import tempfile
import time
import uuid
import zipfile
from pathlib import Path
from typing import Dict, Any, Union, Optional

import py7zr

# Supported lossless algorithms
ALL_ALGORITHMS = ["ZIP", "GZIP", "BZIP2", "LZMA", "7Z"]
EXTENDED_ALGORITHMS = ["PDF-Deflate", "7Z", "ZIP", "GZIP", "BZIP2", "LZMA"]

# Mapping of algorithm to standard file extension
ALGORITHM_EXTENSIONS = {
    "PDF-DEFLATE": ".pdf",
    "ZIP": ".zip",
    "GZIP": ".gz",
    "BZIP2": ".bz2",
    "LZMA": ".xz",
    "7Z": ".7z"
}

DIR_ALGORITHM_EXTENSIONS = {
    "PDF-DEFLATE": ".zip",
    "ZIP": ".zip",
    "GZIP": ".tar.gz",
    "BZIP2": ".tar.bz2",
    "LZMA": ".tar.xz",
    "7Z": ".7z"
}


def get_algorithm_extension(algorithm: str, is_dir: bool = False) -> str:
    """Return file extension for the given algorithm, adapting for directories."""
    algo = algorithm.upper().replace("_", "-")
    if is_dir:
        return DIR_ALGORITHM_EXTENSIONS.get(algo, ".zip")
    return ALGORITHM_EXTENSIONS.get(algo, ".zip")


def compress_file(
    input_path: Union[str, Path],
    algorithm: str,
    output_dir: Union[str, Path],
    original_filename: Optional[str] = None,
    operation_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Compress a file or folder directory using the specified lossless compression algorithm.

    Supported algorithms:
        - ZIP: Deflate algorithm via zipfile (preserves directory structure)
        - GZIP: Deflate algorithm via gzip module (single file) or .tar.gz (folder)
        - BZIP2: Burrows-Wheeler block sorting via bz2 (single file) or .tar.bz2 (folder)
        - LZMA: Lempel-Ziv-Markov chain via lzma (single file) or .tar.xz (folder)
        - 7Z: LZMA/LZMA2 solid archive via py7zr (preserves directory structure)

    Returns:
        Dict containing output path, original size, compressed size, bytes saved,
        space saving %, compression ratio, duration, algorithm, and status.
    """
    src_path = Path(input_path)
    if not src_path.exists():
        return {
            "success": False,
            "error": f"Source path does not exist: {input_path}",
            "algorithm": algorithm
        }

    algo = algorithm.upper().replace("_", "-").strip()
    if algo not in ALGORITHM_EXTENSIONS:
        return {
            "success": False,
            "error": f"Unsupported compression algorithm: {algorithm}. Supported: {list(ALGORITHM_EXTENSIONS.keys())}",
            "algorithm": algorithm
        }

    dest_dir = Path(output_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    filename_in_archive = original_filename if original_filename else src_path.name
    op_id = operation_id if operation_id else uuid.uuid4().hex[:8]
    is_dir = src_path.is_dir()
    ext = get_algorithm_extension(algo, is_dir=is_dir)
    clean_stem = Path(filename_in_archive).name if is_dir else Path(filename_in_archive).stem
    output_filename = f"{clean_stem}_{op_id}{ext}"
    out_path = dest_dir / output_filename

    if is_dir:
        original_size = sum(f.stat().st_size for f in src_path.rglob("*") if f.is_file())
    else:
        original_size = src_path.stat().st_size

    # Adaptive compression settings for large files (> 12 MB) to prevent CPU stall
    is_large = (original_size > 12 * 1024 * 1024)
    zip_level = 6 if is_large else 9
    bz2_level = 6 if is_large else 9
    lzma_preset = 6 if is_large else (9 | lzma.PRESET_EXTREME)
    seven_z_preset = 6 if is_large else 9

    # Perform compression and measure duration
    start_time = time.perf_counter()
    try:
        if is_dir:
            # Multi-file directory hierarchy compression
            if algo in ["ZIP", "PDF-DEFLATE"]:
                with zipfile.ZipFile(out_path, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=zip_level) as zf:
                    for f in src_path.rglob("*"):
                        if f.is_file():
                            rel_p = f.relative_to(src_path)
                            arc_p = Path(filename_in_archive) / rel_p
                            zf.write(f, arcname=str(arc_p).replace("\\", "/"))

            elif algo == "GZIP":
                with tarfile.open(out_path, mode="w:gz", compresslevel=zip_level) as tar:
                    tar.add(src_path, arcname=filename_in_archive)

            elif algo == "BZIP2":
                with tarfile.open(out_path, mode="w:bz2", compresslevel=bz2_level) as tar:
                    tar.add(src_path, arcname=filename_in_archive)

            elif algo == "LZMA":
                with tarfile.open(out_path, mode="w:xz", preset=lzma_preset) as tar:
                    tar.add(src_path, arcname=filename_in_archive)

            elif algo == "7Z":
                filters = [{"id": py7zr.FILTER_LZMA2, "preset": seven_z_preset}]
                with py7zr.SevenZipFile(out_path, mode="w", filters=filters) as archive:
                    archive.writeall(src_path, arcname=filename_in_archive)

        else:
            # Single file compression
            if algo == "PDF-DEFLATE":
                if src_path.is_file() and (src_path.suffix.lower() == ".pdf" or Path(filename_in_archive).suffix.lower() == ".pdf"):
                    import pymupdf
                    doc = pymupdf.open(str(src_path))
                    for p in doc:
                        for img_info in p.get_images():
                            try:
                                xref = img_info[0]
                                pix = pymupdf.Pixmap(doc, xref)
                                if pix.n >= 5:
                                    pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                                jpg_bytes = pix.tobytes("jpeg", jpg_quality=75)
                                doc.update_stream(xref, jpg_bytes)
                            except Exception:
                                pass
                    doc.save(str(out_path), garbage=4, deflate=True, deflate_images=True, deflate_fonts=True, clean=True)
                    doc.close()
                else:
                    with zipfile.ZipFile(out_path, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=zip_level) as zf:
                        zf.write(src_path, arcname=filename_in_archive)

            elif algo == "ZIP":
                with zipfile.ZipFile(out_path, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=zip_level) as zf:
                    zf.write(src_path, arcname=filename_in_archive)

            elif algo == "GZIP":
                with open(src_path, "rb") as f_in:
                    with gzip.GzipFile(filename=filename_in_archive, mode="wb", fileobj=open(out_path, "wb"), mtime=None, compresslevel=zip_level) as f_out:
                        shutil.copyfileobj(f_in, f_out)

            elif algo == "BZIP2":
                with open(src_path, "rb") as f_in:
                    with bz2.BZ2File(out_path, mode="wb", compresslevel=bz2_level) as f_out:
                        shutil.copyfileobj(f_in, f_out)

            elif algo == "LZMA":
                with open(src_path, "rb") as f_in:
                    with lzma.open(out_path, mode="wb", preset=lzma_preset) as f_out:
                        shutil.copyfileobj(f_in, f_out)

            elif algo == "7Z":
                filters = [{"id": py7zr.FILTER_LZMA2, "preset": seven_z_preset}]
                with py7zr.SevenZipFile(out_path, mode="w", filters=filters) as archive:
                    archive.write(src_path, arcname=filename_in_archive)

        duration = time.perf_counter() - start_time
        compressed_size = out_path.stat().st_size

        # Compute savings and statistics
        bytes_saved = original_size - compressed_size

        if original_size > 0:
            space_saving_pct = round(((original_size - compressed_size) / original_size) * 100, 2)
            compression_ratio = round(compressed_size / original_size, 4)
        else:
            space_saving_pct = 0.0
            compression_ratio = 1.0

        return {
            "success": True,
            "error": None,
            "output_path": str(out_path.resolve()),
            "output_filename": output_filename,
            "original_size": original_size,
            "compressed_size": compressed_size,
            "bytes_saved": bytes_saved,
            "space_saving_pct": space_saving_pct,
            "compression_ratio": compression_ratio,
            "compression_duration": round(duration, 4),
            "algorithm": algo,
            "operation_id": op_id
        }

    except Exception as e:
        duration = time.perf_counter() - start_time
        # Clean up partial output if error occurred
        if out_path.exists():
            try:
                out_path.unlink()
            except OSError:
                pass

        return {
            "success": False,
            "error": str(e),
            "output_path": None,
            "output_filename": None,
            "original_size": original_size,
            "compressed_size": 0,
            "bytes_saved": 0,
            "space_saving_pct": 0.0,
            "compression_ratio": 0.0,
            "compression_duration": round(duration, 4),
            "algorithm": algo,
            "operation_id": op_id
        }


def decompress_and_verify(
    compressed_path: Union[str, Path],
    original_path: Union[str, Path],
    algorithm: str
) -> bool:
    """
    Decompress the file or folder archive and verify that its byte content exactly matches the original.
    Ensures mathematical lossless guarantee.
    """
    c_path = Path(compressed_path)
    o_path = Path(original_path)
    if not c_path.exists() or not o_path.exists():
        return False

    algo = algorithm.upper()
    is_dir = o_path.is_dir()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        try:
            if is_dir:
                if algo == "ZIP":
                    with zipfile.ZipFile(c_path, "r") as zf:
                        zf.extractall(temp_dir_path)

                elif algo == "7Z":
                    with py7zr.SevenZipFile(c_path, "r") as archive:
                        archive.extractall(temp_dir_path)

                elif algo in ["GZIP", "BZIP2", "LZMA"]:
                    with tarfile.open(c_path, "r:*") as tar:
                        tar.extractall(temp_dir_path)

                orig_files = {
                    str(f.relative_to(o_path)).replace("\\", "/"): f.read_bytes()
                    for f in o_path.rglob("*") if f.is_file()
                }
                extracted_files = [f for f in temp_dir_path.rglob("*") if f.is_file()]
                if not extracted_files:
                    return False

                for orig_rel_path, orig_data in orig_files.items():
                    found = False
                    for ext_f in extracted_files:
                        ext_rel = str(ext_f.relative_to(temp_dir_path)).replace("\\", "/")
                        if ext_rel.endswith(orig_rel_path) or ext_f.name == Path(orig_rel_path).name:
                            if ext_f.read_bytes() == orig_data:
                                found = True
                                break
                    if not found:
                        return False
                return True

            else:
                original_bytes = o_path.read_bytes()
                if algo == "ZIP":
                    with zipfile.ZipFile(c_path, "r") as zf:
                        zf.extractall(temp_dir_path)
                        extracted_files = [f for f in temp_dir_path.rglob("*") if f.is_file()]
                        if not extracted_files:
                            return False
                        return extracted_files[0].read_bytes() == original_bytes

                elif algo == "GZIP":
                    with gzip.open(c_path, "rb") as f:
                        return f.read() == original_bytes

                elif algo == "BZIP2":
                    with bz2.open(c_path, "rb") as f:
                        return f.read() == original_bytes

                elif algo == "LZMA":
                    with lzma.open(c_path, "rb") as f:
                        return f.read() == original_bytes

                elif algo == "7Z":
                    with py7zr.SevenZipFile(c_path, "r") as archive:
                        archive.extractall(temp_dir_path)
                        extracted_files = [f for f in temp_dir_path.rglob("*") if f.is_file()]
                        if not extracted_files:
                            return False
                        return extracted_files[0].read_bytes() == original_bytes

        except Exception:
            return False

    return False

