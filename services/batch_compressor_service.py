"""
Batch Compressor Service for SmartCompress AI.
Provides card-based visual multi-file compression, high-reduction PDF and image optimization,
real-time thumbnail rendering, and batch ZIP archiving.
"""

import base64
import io
import json
import time
import uuid
import zipfile
from pathlib import Path
from typing import Dict, Any, List, Optional
import PIL.Image

import pymupdf

from config import Config
from utils.analyzer import analyze_file, format_file_size
from utils.validators import sanitize_filename
from database.db import insert_compression_record, get_record_by_operation_id
from engines.compression_engine import compress_file
from engines.ml_engine import get_recommendation


class BatchCompressorService:
    """Manages visual multi-file queuing, real thumbnails, and high-reduction optimization."""

    @staticmethod
    def generate_thumbnail(file_path: Path, filename: str) -> str:
        """
        Generate a base64 Data URL thumbnail for PDFs, images, and documents.
        """
        ext = Path(filename).suffix.lower()

        try:
            # 1. PDF Documents: Render first page at crisp resolution
            if ext == ".pdf":
                doc = pymupdf.open(str(file_path))
                if len(doc) > 0:
                    page = doc[0]
                    # Render at 96 DPI for crisp document preview
                    pix = page.get_pixmap(dpi=96)
                    png_bytes = pix.tobytes("png")
                    doc.close()
                    b64 = base64.b64encode(png_bytes).decode("ascii")
                    return f"data:image/png;base64,{b64}"

            # 2. Images: Create proportional thumbnail using Pillow
            elif ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff"]:
                im = PIL.Image.open(str(file_path))
                im.thumbnail((300, 380), PIL.Image.Resampling.LANCZOS)
                buf = io.BytesIO()
                im.save(buf, format="PNG")
                b64 = base64.b64encode(buf.getvalue()).decode("ascii")
                return f"data:image/png;base64,{b64}"

        except Exception as e:
            print(f"[BatchCompressorService] Thumbnail generation notice: {e}")

        # Fallback to None (UI will render styled icon card)
        return ""

    @staticmethod
    def process_file_upload(file_storage, upload_dir: Optional[Path] = None) -> Dict[str, Any]:
        """
        Handle single file upload for the interactive card studio:
        Store file, generate real thumbnail preview, and return initial metadata.
        """
        if not file_storage or not file_storage.filename:
            return {"success": False, "error": "No file uploaded."}

        original_filename = file_storage.filename
        safe_name = sanitize_filename(original_filename)
        op_id = uuid.uuid4().hex[:12]
        stored_filename = f"{op_id}_{safe_name}"

        active_upload_dir = upload_dir if upload_dir else Config.UPLOAD_DIR
        active_upload_dir.mkdir(parents=True, exist_ok=True)
        target_path = active_upload_dir / stored_filename

        file_storage.save(str(target_path))

        # Metadata analysis
        analysis = analyze_file(target_path, original_filename=original_filename)
        size_bytes = analysis["size_bytes"]
        size_display = analysis["size_display"]

        # Run hybrid recommendation engine
        recommendation_data = get_recommendation(analysis, preference="balanced")

        # Bundle full state and write {op_id}_meta.json so Analytics page is immediately accessible
        state_result = {
            "operation_id": op_id,
            "temp_file_path": str(target_path),
            "stored_filename": stored_filename,
            "original_filename": original_filename,
            "is_directory": False,
            "analysis": analysis,
            "recommendation": recommendation_data,
            "preference": "balanced"
        }
        meta_path = active_upload_dir / f"{op_id}_meta.json"
        try:
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(state_result, f, indent=2)
        except Exception as e:
            print(f"[BatchCompressorService] Meta save notice: {e}")

        # Generate real thumbnail preview
        thumbnail_url = BatchCompressorService.generate_thumbnail(target_path, original_filename)

        return {
            "success": True,
            "operation_id": op_id,
            "filename": original_filename,
            "stored_filename": stored_filename,
            "temp_file_path": str(target_path),
            "size_bytes": size_bytes,
            "size_display": size_display,
            "extension": analysis.get("extension", ""),
            "category": analysis.get("category", ""),
            "entropy": analysis.get("entropy", 0.0),
            "recommended_algorithm": recommendation_data.get("recommended_algorithm", "ZIP"),
            "model_confidence_pct": recommendation_data.get("model_confidence_pct", 95),
            "thumbnail_url": thumbnail_url,
            "is_pdf": (analysis.get("extension", "").lower() == ".pdf"),
            "status": "ready"
        }

    @staticmethod
    def compress_single(
        operation_id: str,
        compression_level: int = 100,
        algorithm: str = "AUTO",
        upload_dir: Optional[Path] = None,
        compressed_dir: Optional[Path] = None,
        db_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Perform high-reduction compression on a queued file:
        - If explicit algorithm given (ZIP, 7Z, GZIP, BZIP2, LZMA), uses that engine.
        - If AUTO:
          - For PDFs: PyMuPDF stream deflating, garbage cleanup, font deduplication, and image optimization.
          - For Images: Pillow quality and subsampling compression.
          - For others / folders: 7Z LZMA2 preset 9.
        """
        active_upload_dir = upload_dir if upload_dir else Config.UPLOAD_DIR
        active_compressed_dir = compressed_dir if compressed_dir else Config.COMPRESSED_DIR
        active_compressed_dir.mkdir(parents=True, exist_ok=True)

        # Locate uploaded file matching operation_id
        matches = list(active_upload_dir.glob(f"{operation_id}_*"))
        # Exclude meta.json files
        matches = [m for m in matches if not m.name.endswith("_meta.json")]
        if not matches:
            return {"success": False, "error": f"Uploaded file not found for ID {operation_id}."}

        src_path = matches[0]
        # Recover original filename by stripping op_id prefix
        original_name = src_path.name[len(operation_id) + 1:]
        stem = Path(original_name).stem
        ext = Path(original_name).suffix.lower()

        # Load existing analysis metadata if available
        meta_path = active_upload_dir / f"{operation_id}_meta.json"
        meta_state = {}
        if meta_path.exists():
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta_state = json.load(f)
            except Exception:
                pass

        file_entropy = meta_state.get("analysis", {}).get("entropy", 0.0) if meta_state else 0.0
        orig_size = sum(f.stat().st_size for f in src_path.rglob("*") if f.is_file()) if src_path.is_dir() else src_path.stat().st_size
        start_time = time.perf_counter()

        selected_algo = (algorithm or "AUTO").upper().replace("_", "-").strip()

        try:
            # ==========================================
            # 0. Explicit Algorithm Override
            # ==========================================
            if selected_algo in ["ZIP", "7Z", "GZIP", "BZIP2", "LZMA", "PDF-DEFLATE"]:
                algo_to_call = "PDF-Deflate" if selected_algo == "PDF-DEFLATE" else selected_algo
                res = compress_file(
                    input_path=src_path,
                    algorithm=algo_to_call,
                    output_dir=active_compressed_dir,
                    original_filename=original_name,
                    operation_id=operation_id
                )
                if not res["success"]:
                    return res
                out_path = Path(res["output_path"])
                output_filename = res["output_filename"]
                algo_used = f"{algo_to_call} ({'Stream & Image Optimization' if algo_to_call == 'PDF-Deflate' else 'Universal' if algo_to_call == 'ZIP' else 'High-Ratio' if algo_to_call == '7Z' else 'Lossless Engine'})"

            # ==========================================
            # 1. High-Reduction PDF Compression (AUTO mode)
            # ==========================================
            elif ext == ".pdf" and not src_path.is_dir():
                output_filename = f"{stem}_compressed_{operation_id}.pdf"
                out_path = active_compressed_dir / output_filename

                doc = pymupdf.open(str(src_path))
                
                # Image recompression for high compression levels
                if compression_level >= 60:
                    jpg_quality = max(45, 95 - int(compression_level * 0.45))
                    for p in doc:
                        for img_info in p.get_images():
                            try:
                                xref = img_info[0]
                                pix = pymupdf.Pixmap(doc, xref)
                                if pix.n >= 5: # CMYK to RGB
                                    pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                                jpg_bytes = pix.tobytes("jpeg", jpg_quality=jpg_quality)
                                doc.update_stream(xref, jpg_bytes)
                            except Exception:
                                pass

                # Clean garbage, deflate content streams, deflate fonts and images
                doc.save(
                    str(out_path),
                    garbage=4,
                    deflate=True,
                    deflate_images=True,
                    deflate_fonts=True,
                    clean=True
                )
                doc.close()

                algo_used = "PDF-Deflate / Stream Optimization"

            # ==========================================
            # 2. Image Optimization (JPG, PNG, WEBP) (AUTO mode)
            # ==========================================
            elif ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp"] and not src_path.is_dir():
                output_filename = f"{stem}_compressed_{operation_id}{ext}"
                out_path = active_compressed_dir / output_filename
                im = PIL.Image.open(str(src_path))

                quality = max(35, 95 - int(compression_level * 0.50))
                if ext in [".jpg", ".jpeg"]:
                    if im.mode not in ("RGB", "L"):
                        im = im.convert("RGB")
                    im.save(str(out_path), format="JPEG", quality=quality, optimize=True)
                elif ext == ".webp":
                    im.save(str(out_path), format="WEBP", quality=quality, method=6)
                elif ext == ".png":
                    if compression_level >= 75 and im.mode in ("RGB", "RGBA"):
                        # Quantize for massive byte savings
                        im_quant = im.quantize(colors=128, method=PIL.Image.Quantize.MEDIANCUT)
                        im_quant.save(str(out_path), format="PNG", optimize=True)
                    else:
                        im.save(str(out_path), format="PNG", optimize=True)
                else:
                    im.save(str(out_path), optimize=True)

                algo_used = f"Image-Lossless / {ext.upper()[1:]} Optimization"

            # ==========================================
            # 3. Documents, Code, Binaries, and Folders (7Z / LZMA2)
            # ==========================================
            else:
                # Use 7Z with extreme preset
                res = compress_file(
                    input_path=src_path,
                    algorithm="7Z",
                    output_dir=active_compressed_dir,
                    original_filename=original_name,
                    operation_id=operation_id
                )
                if not res["success"]:
                    return res
                out_path = Path(res["output_path"])
                output_filename = res["output_filename"]
                algo_used = "7Z (LZMA2 Solid Archive)"

            duration = round(time.perf_counter() - start_time, 4)
            compressed_size = out_path.stat().st_size
            bytes_saved = orig_size - compressed_size
            space_saving_pct = round(((orig_size - compressed_size) / orig_size) * 100, 2) if orig_size > 0 else 0.0
            compression_ratio = round(compressed_size / orig_size, 4) if orig_size > 0 else 1.0

            # Record in SQLite history
            record = {
                "operation_id": operation_id,
                "original_filename": original_name,
                "file_extension": ext or "folder",
                "file_category": "Document" if ext == ".pdf" else "General",
                "mime_type": "application/pdf" if ext == ".pdf" else "",
                "entropy": file_entropy,
                "original_size": orig_size,
                "compressed_size": compressed_size,
                "bytes_saved": bytes_saved,
                "compression_ratio": compression_ratio,
                "compression_duration": duration,
                "selected_algorithm": algo_used,
                "recommendation_source": f"Studio ({selected_algo} / Level {compression_level}%)",
                "model_confidence": 0.95,
                "output_filename": output_filename,
                "operation_status": "SUCCESS"
            }
            try:
                insert_compression_record(record, db_path=db_path)
            except Exception as e:
                print(f"[BatchCompressorService] DB logging warning: {e}")

            # Update cached meta_state
            if meta_state:
                meta_state["compressed_record"] = record
                try:
                    with open(meta_path, "w", encoding="utf-8") as f:
                        json.dump(meta_state, f, indent=2)
                except Exception:
                    pass

            orig_info = format_file_size(orig_size)
            comp_info = format_file_size(compressed_size)

            return {
                "success": True,
                "operation_id": operation_id,
                "original_size": orig_size,
                "original_size_display": orig_info["display"],
                "compressed_size": compressed_size,
                "compressed_size_display": comp_info["display"],
                "bytes_saved": bytes_saved,
                "space_saving_pct": space_saving_pct,
                "duration": duration,
                "algorithm": algo_used,
                "output_filename": output_filename,
                "download_url": f"/download/{operation_id}"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Compression failure: {str(e)}",
                "operation_id": operation_id
            }

    @staticmethod
    def create_batch_zip(
        operation_ids: List[str],
        compressed_dir: Optional[Path] = None,
        db_path: Optional[Path] = None
    ) -> Optional[Path]:
        """
        Package all compressed outputs for the given operation IDs into a single ZIP archive.
        """
        active_compressed_dir = compressed_dir if compressed_dir else Config.COMPRESSED_DIR
        batch_id = uuid.uuid4().hex[:8]
        zip_filename = f"SmartCompress_Batch_{batch_id}.zip"
        zip_path = active_compressed_dir / zip_filename

        added_count = 0
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for op_id in operation_ids:
                record = get_record_by_operation_id(op_id, db_path=db_path)
                if record:
                    target_file = active_compressed_dir / record["output_filename"]
                    if target_file.exists():
                        zf.write(target_file, arcname=record["output_filename"])
                        added_count += 1
                else:
                    # Search by pattern
                    matches = list(active_compressed_dir.glob(f"*_{op_id}.*"))
                    for m in matches:
                        if m.exists():
                            zf.write(m, arcname=m.name)
                            added_count += 1

        if added_count == 0:
            if zip_path.exists():
                zip_path.unlink()
            return None

        return zip_path
