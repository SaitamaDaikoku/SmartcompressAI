"""
Flask Web Application for SmartCompress AI.
Intelligent File Compression Recommendation System.
Information Storage Management (ISM) Project.
"""

import json
from pathlib import Path
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_file,
    jsonify,
    Response,
    abort
)

from config import Config, UPLOAD_DIR, COMPRESSED_DIR, REPORT_DIR
from database.db import init_db, get_dashboard_statistics, get_record_by_operation_id
from services.analysis_service import AnalysisService
from services.compression_service import CompressionService
from services.history_service import HistoryService
from services.report_service import ReportService
from services.batch_compressor_service import BatchCompressorService
from utils.validators import is_safe_path, validate_file_upload


def create_app(config_class=Config):
    """Application factory for SmartCompress AI."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize SQLite database schema automatically on startup
    with app.app_context():
        init_db(app.config.get("DATABASE_PATH"))

    # ==========================================
    # ROUTES: CORE WORKFLOW
    # ==========================================

    @app.route("/")
    def index():
        """Home page with drag-and-drop upload, size limit, and preferences."""
        max_mb = app.config.get("MAX_FILE_SIZE_MB", 50)
        preferences = app.config.get("COMPRESSION_PREFERENCES", [])
        return render_template("index.html", max_file_size_mb=max_mb, preferences=preferences)

    @app.route("/analyze", methods=["POST"])
    def analyze():
        """Handle uploaded file or folder, perform metadata analysis & entropy calculation."""
        upload_mode = request.form.get("upload_mode", "file")
        preference = request.form.get("preference", "balanced")
        upload_dir = app.config.get("UPLOAD_DIR", Config.UPLOAD_DIR)

        # Check if folder files were submitted
        folder_files = request.files.getlist("folder_files")
        folder_files = [f for f in folder_files if f and f.filename]

        # If user explicitly opted for folder mode or uploaded via folderInput
        if upload_mode == "folder" or len(folder_files) > 0:
            if not folder_files:
                # Fallback to "file" field if user dragged folder entries into primary input
                fallback_files = [f for f in request.files.getlist("file") if f and f.filename]
                if fallback_files:
                    folder_files = fallback_files

            if not folder_files:
                flash("No files found in folder upload.", "danger")
                return redirect(url_for("index"))

            # Parse optional client relative paths
            raw_rel_paths = request.form.get("relative_paths", "[]")
            try:
                rel_paths = json.loads(raw_rel_paths)
            except Exception:
                rel_paths = []

            folder_name = request.form.get("folder_name", "").strip()
            if not folder_name and folder_files:
                first_path = rel_paths[0] if rel_paths else folder_files[0].filename
                first_parts = Path(first_path.replace("\\", "/")).parts
                if len(first_parts) > 1:
                    folder_name = first_parts[0]
                else:
                    folder_name = "archive_folder"

            success, error, result = AnalysisService.process_uploaded_folder(
                folder_files,
                folder_name=folder_name,
                relative_paths=rel_paths,
                preference=preference,
                upload_dir=upload_dir
            )

            if not success:
                flash(error or "Failed to analyze the folder.", "danger")
                return redirect(url_for("index"))

            return redirect(url_for("result", operation_id=result["operation_id"]))

        # Single file upload flow
        if "file" not in request.files:
            flash("No file part in the request.", "danger")
            return redirect(url_for("index"))

        file_obj = request.files["file"]
        is_valid, err_msg = validate_file_upload(file_obj, app.config["MAX_CONTENT_LENGTH"])
        if not is_valid:
            flash(err_msg, "danger")
            return redirect(url_for("index"))

        success, error, result = AnalysisService.process_uploaded_file(
            file_obj,
            preference=preference,
            upload_dir=upload_dir
        )

        if not success:
            flash(error or "Failed to analyze the file.", "danger")
            return redirect(url_for("index"))

        return redirect(url_for("result", operation_id=result["operation_id"]))

    @app.route("/result/<operation_id>")
    def result(operation_id):
        """Display file analysis, Shannon entropy, recommendations, and compression status."""
        state = AnalysisService.get_analysis_state(
            operation_id,
            upload_dir=app.config.get("UPLOAD_DIR", Config.UPLOAD_DIR),
            db_path=app.config.get("DATABASE_PATH", Config.DATABASE_PATH)
        )
        if not state:
            flash(f"Session or operation {operation_id} not found or expired.", "warning")
            return redirect(url_for("index"))

        # Check if compression was already performed for this operation
        db_record = get_record_by_operation_id(operation_id, app.config.get("DATABASE_PATH"))

        return render_template(
            "result.html",
            operation_id=operation_id,
            analysis=state["analysis"],
            recommendation=state["recommendation"],
            preference=state.get("preference", "balanced"),
            compressed_record=db_record or state.get("compressed_record"),
            supported_algorithms=app.config.get("SUPPORTED_ALGORITHMS", ["ZIP", "GZIP", "BZIP2", "LZMA", "7Z"])
        )

    @app.route("/compress/<operation_id>", methods=["POST"])
    def compress(operation_id):
        """Execute real file compression using selected or recommended algorithm."""
        algorithm = request.form.get("algorithm", "ZIP").upper().strip()
        result = CompressionService.execute_compression(
            operation_id,
            algorithm,
            output_dir=app.config.get("COMPRESSED_DIR", Config.COMPRESSED_DIR),
            db_path=app.config.get("DATABASE_PATH", Config.DATABASE_PATH),
            upload_dir=app.config.get("UPLOAD_DIR", Config.UPLOAD_DIR)
        )

        if not result["success"]:
            flash(f"Compression error: {result.get('error', 'Unknown failure')}", "danger")
            return redirect(url_for("result", operation_id=operation_id))

        flash(f"File successfully compressed using {algorithm}! Storage savings calculated.", "success")
        return redirect(url_for("result", operation_id=operation_id))

    @app.route("/api/benchmark/<operation_id>", methods=["POST"])
    def api_benchmark(operation_id):
        """AJAX endpoint to benchmark all compatible algorithms on the uploaded file."""
        bench_result = CompressionService.benchmark_all_algorithms(
            operation_id,
            upload_dir=app.config.get("UPLOAD_DIR", Config.UPLOAD_DIR),
            compressed_dir=app.config.get("COMPRESSED_DIR", Config.COMPRESSED_DIR)
        )
        return jsonify(bench_result)

    # ==========================================
    # ROUTES: SECURE DOWNLOADS
    # ==========================================

    @app.route("/download/<operation_id>")
    def download_compressed(operation_id):
        """Securely download the compressed file for a valid operation."""
        record = get_record_by_operation_id(operation_id, app.config.get("DATABASE_PATH"))
        if not record:
            flash("File not found or unauthorized operation.", "danger")
            return redirect(url_for("history"))

        output_filename = record["output_filename"]
        compressed_dir = app.config.get("COMPRESSED_DIR", Config.COMPRESSED_DIR)
        target_path = compressed_dir / output_filename

        # Prevent directory traversal
        if not is_safe_path(compressed_dir, target_path) or not target_path.exists():
            flash("Compressed file is missing or path is invalid.", "danger")
            return redirect(url_for("history"))

        return send_file(
            target_path,
            as_attachment=True,
            download_name=output_filename
        )

    @app.route("/download_report/<operation_id>")
    def download_report(operation_id):
        """Generate on-the-fly and download PDF academic technical report."""
        record = get_record_by_operation_id(operation_id, app.config.get("DATABASE_PATH"))
        state = AnalysisService.get_analysis_state(operation_id, upload_dir=app.config.get("UPLOAD_DIR", Config.UPLOAD_DIR))

        # Merge available data
        combined_data = {}
        if record:
            combined_data.update(record)
        if state:
            combined_data.update(state)
            if "analysis" in state:
                combined_data["analysis"] = state["analysis"]
            if "recommendation" in state:
                combined_data["recommendation"] = state["recommendation"]

        if not combined_data:
            flash("Operation details not found for report generation.", "danger")
            return redirect(url_for("history"))

        report_dir = app.config.get("REPORT_DIR", Config.REPORT_DIR)
        target_report_file = report_dir / f"SmartCompress_Report_{operation_id}.pdf"
        report_path = ReportService.generate_pdf_report(combined_data, output_path=target_report_file)
        return send_file(
            report_path,
            as_attachment=True,
            download_name=f"SmartCompress_Report_{operation_id}.pdf",
            mimetype="application/pdf"
        )

    # ==========================================
    # ROUTES: DASHBOARD & HISTORY
    # ==========================================

    @app.route("/dashboard")
    def dashboard():
        """View global storage optimization metrics, chart distributions, and totals."""
        stats = get_dashboard_statistics(app.config.get("DATABASE_PATH"))
        return render_template("dashboard.html", stats=stats)

    @app.route("/history")
    def history():
        """Searchable, filterable, and paginated compression history."""
        search = request.args.get("search", "").strip()
        algorithm = request.args.get("algorithm", "ALL").strip()
        sort_by = request.args.get("sort_by", "date_desc").strip()
        page = request.args.get("page", 1, type=int)

        data = HistoryService.get_history(
            search=search,
            algorithm=algorithm,
            sort_by=sort_by,
            page=page,
            per_page=10
        )

        return render_template(
            "history.html",
            records=data["records"],
            total_count=data["total_count"],
            page=data["page"],
            total_pages=data["total_pages"],
            has_next=data["has_next"],
            has_prev=data["has_prev"],
            search=data["search"],
            algorithm=data["algorithm"],
            sort_by=data["sort_by"],
            supported_algorithms=app.config.get("SUPPORTED_ALGORITHMS", ["ZIP", "GZIP", "BZIP2", "LZMA", "7Z"])
        )

    @app.route("/history/delete/<int:record_id>", methods=["POST"])
    def delete_history_item(record_id):
        """Delete an operation from history."""
        success = HistoryService.delete_record(record_id)
        if success:
            flash(f"History record #{record_id} deleted successfully.", "success")
        else:
            flash("Failed to delete record.", "danger")
        return redirect(url_for("history"))

    @app.route("/export_history")
    def export_history():
        """Export full compression history table to CSV."""
        csv_data = HistoryService.export_csv()
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=SmartCompress_History.csv"}
        )

    # ==========================================
    # ROUTES: VISUAL STUDIO BATCH API
    # ==========================================

    @app.route("/api/upload_file", methods=["POST"])
    def api_upload_file():
        """Handle AJAX upload of one or more files for visual card studio."""
        uploaded_files = request.files.getlist("files")
        if not uploaded_files:
            if "file" in request.files:
                uploaded_files = [request.files["file"]]

        if not uploaded_files:
            return jsonify({"success": False, "error": "No file received."}), 400

        results = []
        upload_dir = app.config.get("UPLOAD_DIR", Config.UPLOAD_DIR)

        for file_obj in uploaded_files:
            if file_obj and file_obj.filename:
                res = BatchCompressorService.process_file_upload(file_obj, upload_dir=upload_dir)
                results.append(res)

        return jsonify({"success": True, "files": results})

    @app.route("/api/compress_file", methods=["POST"])
    def api_compress_file():
        """Compress a specific queued file with the requested compression level and algorithm."""
        data = request.get_json(silent=True) or request.form
        operation_id = data.get("operation_id")
        if not operation_id:
            return jsonify({"success": False, "error": "Missing operation_id."}), 400

        try:
            compression_level = int(data.get("compression_level", 100))
        except (ValueError, TypeError):
            compression_level = 100

        algorithm = data.get("algorithm", "AUTO")

        result = BatchCompressorService.compress_single(
            operation_id=operation_id,
            compression_level=compression_level,
            algorithm=algorithm,
            upload_dir=app.config.get("UPLOAD_DIR", Config.UPLOAD_DIR),
            compressed_dir=app.config.get("COMPRESSED_DIR", Config.COMPRESSED_DIR),
            db_path=app.config.get("DATABASE_PATH", Config.DATABASE_PATH)
        )
        return jsonify(result)

    @app.route("/api/download_batch_zip", methods=["POST"])
    def api_download_batch_zip():
        """Create and download a ZIP containing all batch-compressed outputs."""
        data = request.get_json(silent=True) or {}
        operation_ids = data.get("operation_ids", [])
        if not operation_ids:
            return jsonify({"success": False, "error": "No files selected for batch ZIP."}), 400

        zip_path = BatchCompressorService.create_batch_zip(
            operation_ids=operation_ids,
            compressed_dir=app.config.get("COMPRESSED_DIR", Config.COMPRESSED_DIR),
            db_path=app.config.get("DATABASE_PATH", Config.DATABASE_PATH)
        )

        if not zip_path or not zip_path.exists():
            return jsonify({"success": False, "error": "No compressed files found to package."}), 404

        return send_file(
            zip_path,
            as_attachment=True,
            download_name=zip_path.name
        )

    @app.route("/api/delete_file/<operation_id>", methods=["DELETE", "POST"])
    def api_delete_file(operation_id):
        """Delete an uploaded / queued item."""
        upload_dir = app.config.get("UPLOAD_DIR", Config.UPLOAD_DIR)
        compressed_dir = app.config.get("COMPRESSED_DIR", Config.COMPRESSED_DIR)

        for folder in [upload_dir, compressed_dir]:
            for p in folder.glob(f"*{operation_id}*"):
                try:
                    if p.is_file():
                        p.unlink()
                    elif p.is_dir():
                        import shutil
                        shutil.rmtree(p, ignore_errors=True)
                except OSError:
                    pass

        return jsonify({"success": True, "operation_id": operation_id})

    # ==========================================
    # ROUTES: PWA & STATIC
    # ==========================================

    @app.route("/manifest.json")
    def manifest():
        """PWA Web Manifest."""
        return send_file(app.static_folder + "/manifest.json", mimetype="application/manifest+json")

    @app.route("/service-worker.js")
    def service_worker():
        """PWA Service Worker."""
        return send_file(app.static_folder + "/service-worker.js", mimetype="application/javascript")

    @app.route("/offline")
    def offline():
        """PWA offline fallback notice."""
        return render_template("error.html", error_code="Offline", error_title="Offline Mode",
                               error_message="SmartCompress AI requires server connectivity to perform compression analysis and operations.")

    # ==========================================
    # ERROR HANDLERS
    # ==========================================

    @app.errorhandler(413)
    def request_entity_too_large(error):
        flash(f"File size exceeds maximum upload limit ({app.config['MAX_FILE_SIZE_MB']} MB).", "danger")
        return redirect(url_for("index")), 413

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template("error.html", error_code=404, error_title="Page Not Found",
                               error_message="The requested page or resource could not be found."), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template("error.html", error_code=500, error_title="Internal Server Error",
                               error_message="An unexpected server error occurred. Please try again."), 500

    return app


# Application entry point
app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
