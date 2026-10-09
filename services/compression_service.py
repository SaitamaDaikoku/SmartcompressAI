"""
Compression service for SmartCompress AI.
Coordinates actual compression execution, multi-algorithm benchmarking,
and database record persistence.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional

from config import Config
from engines.compression_engine import compress_file, ALL_ALGORITHMS
from database.db import insert_compression_record, get_record_by_operation_id
from services.analysis_service import AnalysisService


class CompressionService:
    """Manages file compression operations and algorithm benchmarks."""

    @staticmethod
    def execute_compression(
        operation_id: str,
        selected_algorithm: str,
        output_dir: Optional[Path] = None,
        db_path: Optional[Path] = None,
        upload_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Execute real compression using selected algorithm for an existing analyzed upload,
        and persist record into SQLite.
        """
        state = AnalysisService.get_analysis_state(operation_id, upload_dir=upload_dir)
        if not state:
            return {
                "success": False,
                "error": f"Invalid or expired operation ID: {operation_id}"
            }

        file_path = Path(state["temp_file_path"])
        if not file_path.exists():
            return {
                "success": False,
                "error": "Uploaded source file no longer exists on server."
            }

        original_filename = state["original_filename"]
        analysis = state["analysis"]
        recommendation = state["recommendation"]

        algo_input = selected_algorithm.upper().replace("_", "-").strip()
        supported = ["PDF-Deflate", "7Z", "ZIP", "GZIP", "BZIP2", "LZMA"]
        canonical_map = {a.upper().replace("_", "-"): a for a in supported}
        if algo_input not in canonical_map:
            return {
                "success": False,
                "error": f"Invalid algorithm selected: {selected_algorithm}."
            }
        algo = canonical_map[algo_input]

        dest_dir = output_dir if output_dir else Config.COMPRESSED_DIR

        # Perform real compression
        comp_result = compress_file(
            input_path=file_path,
            algorithm=algo,
            output_dir=dest_dir,
            original_filename=original_filename,
            operation_id=operation_id
        )

        if not comp_result["success"]:
            return comp_result

        # Determine recommendation source and model confidence
        rec_source = recommendation.get("recommendation_source", "Rule-Based Engine")
        confidence = recommendation.get("model_confidence")

        # Save record to SQLite
        record = {
            "operation_id": operation_id,
            "original_filename": original_filename,
            "file_extension": analysis.get("extension", ""),
            "file_category": analysis.get("category", "General"),
            "mime_type": analysis.get("mime_type", ""),
            "entropy": analysis.get("entropy", 0.0),
            "original_size": comp_result["original_size"],
            "compressed_size": comp_result["compressed_size"],
            "bytes_saved": comp_result["bytes_saved"],
            "compression_ratio": comp_result["compression_ratio"],
            "compression_duration": comp_result["compression_duration"],
            "selected_algorithm": algo,
            "recommendation_source": rec_source,
            "model_confidence": confidence,
            "output_filename": comp_result["output_filename"],
            "operation_status": "SUCCESS"
        }

        try:
            row_id = insert_compression_record(record, db_path=db_path)
            comp_result["db_id"] = row_id
        except Exception as e:
            print(f"[CompressionService] Error saving to database: {e}")

        # Combine with analysis and recommendation for complete result display
        comp_result["analysis"] = analysis
        comp_result["recommendation"] = recommendation
        comp_result["original_filename"] = original_filename

        return comp_result

    @staticmethod
    def benchmark_all_algorithms(
        operation_id: str,
        upload_dir: Optional[Path] = None,
        compressed_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Benchmark all 5 lossless algorithms on the uploaded file.
        Measures real compressed size, savings, duration, and throughput (MB/s).
        Enforces size safety limits to prevent denial of service.
        """
        state = AnalysisService.get_analysis_state(operation_id, upload_dir=upload_dir)
        if not state:
            return {"success": False, "error": "Invalid operation ID."}

        file_path = Path(state["temp_file_path"]) if state.get("temp_file_path") else Path("")
        if not file_path.exists():
            active_upload_dir = upload_dir if upload_dir else Config.UPLOAD_DIR
            matches = [m for m in active_upload_dir.glob(f"{operation_id}_*") if not m.name.endswith("_meta.json")]
            if matches:
                file_path = matches[0]
            else:
                return {"success": False, "error": "Uploaded file not found on server."}

        if file_path.is_dir():
            orig_size = sum(f.stat().st_size for f in file_path.rglob("*") if f.is_file())
        else:
            orig_size = file_path.stat().st_size

        if orig_size > Config.MAX_BENCHMARK_FILE_SIZE:
            max_mb = Config.MAX_BENCHMARK_FILE_SIZE / (1024 * 1024)
            return {
                "success": False,
                "error": f"Size ({orig_size / (1024 * 1024):.1f} MB) exceeds benchmark limit ({max_mb:.0f} MB) to ensure server responsiveness."
            }

        original_filename = state["original_filename"]
        is_pdf = (file_path.suffix.lower() == ".pdf" or original_filename.lower().endswith(".pdf"))
        algos_to_test = ["PDF-Deflate", "7Z", "ZIP", "GZIP", "BZIP2", "LZMA"] if is_pdf else ["7Z", "ZIP", "GZIP", "BZIP2", "LZMA"]

        benchmarks: List[Dict[str, Any]] = []
        active_comp_dir = compressed_dir if compressed_dir else Config.COMPRESSED_DIR

        for algo in algos_to_test:
            # Run compression in temporary output directory
            safe_algo_id = algo.lower().replace("-", "_")
            res = compress_file(
                input_path=file_path,
                algorithm=algo,
                output_dir=active_comp_dir / "benchmarks",
                original_filename=original_filename,
                operation_id=f"bench_{safe_algo_id}_{operation_id}"
            )

            if res["success"]:
                duration = res["compression_duration"]
                speed_mb_s = round((orig_size / (1024 * 1024)) / duration, 2) if duration > 0 else 0.0

                benchmarks.append({
                    "algorithm": algo,
                    "compressed_size": res["compressed_size"],
                    "compressed_size_display": f"{res['compressed_size'] / 1024:.2f} KB" if res['compressed_size'] < 1024*1024 else f"{res['compressed_size'] / (1024*1024):.2f} MB",
                    "bytes_saved": res["bytes_saved"],
                    "space_saving_pct": res["space_saving_pct"],
                    "duration": duration,
                    "speed_mb_s": speed_mb_s,
                    "compression_ratio": res["compression_ratio"]
                })

                # Remove benchmark test archive after measurement
                b_path = Path(res["output_path"])
                if b_path.exists():
                    try:
                        b_path.unlink()
                    except OSError:
                        pass

        # Sort benchmarks by space savings descending
        benchmarks.sort(key=lambda x: x["space_saving_pct"], reverse=True)

        return {
            "success": True,
            "original_size": orig_size,
            "benchmarks": benchmarks
        }
