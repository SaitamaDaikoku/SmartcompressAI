"""
Analysis service for processing uploaded files and generating intelligent recommendations.
Separates analysis workflow from route handling.
"""

import json
import shutil
import uuid
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
from werkzeug.datastructures import FileStorage

from config import Config
from utils.analyzer import analyze_file
from utils.validators import sanitize_filename
from engines.ml_engine import get_recommendation


class AnalysisService:
    """Manages file and folder storage, metadata analysis, and hybrid algorithm recommendation."""

    @staticmethod
    def process_uploaded_file(
        file_storage: FileStorage,
        preference: str = "balanced",
        upload_dir: Optional[Path] = None
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Validate, securely store, analyze file entropy & metadata, and generate recommendation.

        Returns:
            Tuple of (success: bool, error_message: Optional[str], result_data: Optional[Dict])
        """
        if not file_storage or not file_storage.filename:
            return False, "No file provided.", None

        original_filename = file_storage.filename
        safe_name = sanitize_filename(original_filename)
        
        # Generate unique operation ID
        op_id = uuid.uuid4().hex[:12]
        stored_filename = f"{op_id}_{safe_name}"
        active_upload_dir = upload_dir if upload_dir else Config.UPLOAD_DIR
        active_upload_dir.mkdir(parents=True, exist_ok=True)
        target_path = active_upload_dir / stored_filename

        try:
            # Save file to uploads folder
            file_storage.save(str(target_path))

            # Run analyzer
            analysis_data = analyze_file(target_path, original_filename=original_filename)

            # Run hybrid recommendation engine
            recommendation_data = get_recommendation(analysis_data, preference=preference)

            # Bundle full state
            result = {
                "operation_id": op_id,
                "temp_file_path": str(target_path),
                "stored_filename": stored_filename,
                "original_filename": original_filename,
                "is_directory": False,
                "analysis": analysis_data,
                "recommendation": recommendation_data,
                "preference": preference
            }

            # Save state metadata JSON alongside upload for recovery across requests
            meta_path = active_upload_dir / f"{op_id}_meta.json"
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)

            return True, None, result

        except Exception as e:
            # Clean up on failure
            if target_path.exists():
                try:
                    target_path.unlink()
                except OSError:
                    pass
            return False, f"Analysis failure: {str(e)}", None

    @staticmethod
    def process_uploaded_folder(
        file_storages: List[FileStorage],
        folder_name: str,
        relative_paths: Optional[List[str]] = None,
        preference: str = "balanced",
        upload_dir: Optional[Path] = None
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Securely store an uploaded directory hierarchy, analyze aggregate entropy & metadata,
        and generate intelligent recommendation.

        Returns:
            Tuple of (success: bool, error_message: Optional[str], result_data: Optional[Dict])
        """
        if not file_storages:
            return False, "No files found in folder upload.", None

        clean_folder_name = sanitize_filename(folder_name)
        if not clean_folder_name:
            clean_folder_name = "uploaded_folder"

        op_id = uuid.uuid4().hex[:12]
        stored_folder_name = f"{op_id}_{clean_folder_name}"
        active_upload_dir = upload_dir if upload_dir else Config.UPLOAD_DIR
        active_upload_dir.mkdir(parents=True, exist_ok=True)
        target_folder_path = active_upload_dir / stored_folder_name
        target_folder_path.mkdir(parents=True, exist_ok=True)

        try:
            saved_count = 0
            for idx, file_obj in enumerate(file_storages):
                if not file_obj or not file_obj.filename:
                    continue

                # Determine relative subpath
                raw_rel_path = ""
                if relative_paths and idx < len(relative_paths):
                    raw_rel_path = relative_paths[idx]
                if not raw_rel_path:
                    raw_rel_path = file_obj.filename

                # Sanitize path to prevent directory traversal
                parts = [p for p in Path(raw_rel_path.replace("\\", "/")).parts if p not in ("..", ".", "/", "\\", "")]
                if not parts:
                    parts = [sanitize_filename(file_obj.filename)]

                # If first component is the folder name itself, trim it to avoid duplicate nesting
                if len(parts) > 1 and parts[0] in (clean_folder_name, folder_name):
                    dest_rel = Path(*parts[1:])
                else:
                    dest_rel = Path(*parts)

                dest_file_path = target_folder_path / dest_rel
                dest_file_path.parent.mkdir(parents=True, exist_ok=True)
                file_obj.save(str(dest_file_path))
                saved_count += 1

            if saved_count == 0:
                shutil.rmtree(target_folder_path, ignore_errors=True)
                return False, "No valid files were extracted from the folder.", None

            # Run analyzer on the saved folder directory
            analysis_data = analyze_file(target_folder_path, original_filename=clean_folder_name)

            # Run hybrid recommendation engine
            recommendation_data = get_recommendation(analysis_data, preference=preference)

            result = {
                "operation_id": op_id,
                "temp_file_path": str(target_folder_path),
                "stored_filename": stored_folder_name,
                "original_filename": clean_folder_name,
                "is_directory": True,
                "analysis": analysis_data,
                "recommendation": recommendation_data,
                "preference": preference
            }

            # Save state metadata JSON
            meta_path = active_upload_dir / f"{op_id}_meta.json"
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)

            return True, None, result

        except Exception as e:
            if target_folder_path.exists():
                shutil.rmtree(target_folder_path, ignore_errors=True)
            return False, f"Folder analysis failure: {str(e)}", None

    @staticmethod
    def get_analysis_state(
        operation_id: str,
        upload_dir: Optional[Path] = None,
        db_path: Optional[Path] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached analysis state by operation ID.
        Resilient: if meta.json is missing, reconstructs from active upload file or SQLite ledger.
        """
        active_upload_dir = upload_dir if upload_dir else Config.UPLOAD_DIR
        meta_path = active_upload_dir / f"{operation_id}_meta.json"

        # 1. Check existing metadata JSON file
        if meta_path.exists():
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

        # 2. Check if the uploaded file/directory still exists on disk in uploads/
        matches = [m for m in active_upload_dir.glob(f"{operation_id}_*") if not m.name.endswith("_meta.json")]
        if matches:
            target_path = matches[0]
            original_filename = target_path.name[len(operation_id) + 1:]
            try:
                analysis_data = analyze_file(target_path, original_filename=original_filename)
                recommendation_data = get_recommendation(analysis_data, preference="balanced")
                result = {
                    "operation_id": operation_id,
                    "temp_file_path": str(target_path),
                    "stored_filename": target_path.name,
                    "original_filename": original_filename,
                    "is_directory": target_path.is_dir(),
                    "analysis": analysis_data,
                    "recommendation": recommendation_data,
                    "preference": "balanced"
                }
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2)
                return result
            except Exception as e:
                print(f"[AnalysisService] Recovery from upload notice: {e}")

        # 3. Check SQLite compression history ledger for previous operations
        try:
            from database.db import get_record_by_operation_id
            from utils.analyzer import format_file_size
            from utils.entropy import interpret_entropy

            db_record = get_record_by_operation_id(operation_id, db_path=db_path)
            if db_record:
                orig_size = db_record.get("original_size", 0)
                entropy_val = float(db_record.get("entropy", 0.0) or 0.0)
                entropy_details = interpret_entropy(entropy_val)
                size_info = format_file_size(orig_size)

                result = {
                    "operation_id": operation_id,
                    "temp_file_path": "",
                    "stored_filename": db_record.get("original_filename", "file"),
                    "original_filename": db_record.get("original_filename", "file"),
                    "is_directory": (db_record.get("file_extension") == "folder"),
                    "analysis": {
                        "filename": db_record.get("original_filename", "file"),
                        "extension": db_record.get("file_extension", ""),
                        "mime_type": db_record.get("mime_type", "application/octet-stream"),
                        "size_bytes": orig_size,
                        "size_kb": size_info["kb"],
                        "size_mb": size_info["mb"],
                        "size_display": size_info["display"],
                        "entropy": entropy_val,
                        "entropy_details": entropy_details,
                        "category": db_record.get("file_category", "General"),
                        "sha256": "Historical Record (Logged in SQLite Ledger)",
                        "is_precompressed": (entropy_val >= 7.90),
                        "is_directory": (db_record.get("file_extension") == "folder"),
                        "file_count": 1
                    },
                    "recommendation": {
                        "recommended_algorithm": db_record.get("selected_algorithm", "ZIP"),
                        "recommendation_source": db_record.get("recommendation_source", "Database History"),
                        "explanation": f"Retrieved from persistent compression history ledger. Compressed using {db_record.get('selected_algorithm')}.",
                        "model_confidence": db_record.get("model_confidence", 0.95) or 0.95,
                        "model_confidence_pct": round(float(db_record.get("model_confidence", 0.95) or 0.95) * 100, 1),
                        "warning": None
                    },
                    "preference": "balanced"
                }

                # Cache reconstructed metadata JSON
                try:
                    with open(meta_path, "w", encoding="utf-8") as f:
                        json.dump(result, f, indent=2)
                except Exception:
                    pass

                return result
        except Exception as e:
            print(f"[AnalysisService] Recovery from DB history notice: {e}")

        return None

