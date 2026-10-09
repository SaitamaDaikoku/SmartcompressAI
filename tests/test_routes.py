"""
Integration tests for Flask application routes, uploads, compression, and downloads.
"""

import io
import tempfile
from pathlib import Path
import pytest

from app import create_app
from config import TestConfig
from engines.recommendation_engine import recommend_rule_based


@pytest.fixture
def app():
    """Create Flask test application instance with temporary directories."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        temp_path = Path(temp_dir)
        test_db = temp_path / "test.db"

        class RuntimeTestConfig(TestConfig):
            DATABASE_PATH = test_db
            UPLOAD_DIR = temp_path / "uploads"
            COMPRESSED_DIR = temp_path / "compressed"
            REPORT_DIR = temp_path / "reports"

        RuntimeTestConfig.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        RuntimeTestConfig.COMPRESSED_DIR.mkdir(parents=True, exist_ok=True)
        RuntimeTestConfig.REPORT_DIR.mkdir(parents=True, exist_ok=True)

        flask_app = create_app(RuntimeTestConfig)
        yield flask_app


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


def test_home_page(client):
    """Verify home page loads with 200 OK."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"SmartCompress" in response.data
    assert b"Information Theory" in response.data


def test_upload_and_analysis_flow(client):
    """Test full workflow: upload file -> analyze -> result page."""
    data = {
        "file": (io.BytesIO(b"Hello ISM Information Storage Management!\n" * 50), "test_doc.txt"),
        "preference": "balanced"
    }

    response = client.post("/analyze", data=data, content_type="multipart/form-data", follow_redirects=False)
    assert response.status_code == 302
    assert "/result/" in response.headers["Location"]

    # Follow redirect to result page
    result_page = client.get(response.headers["Location"])
    assert result_page.status_code == 200
    assert b"test_doc.txt" in result_page.data
    assert b"Shannon Entropy" in result_page.data
    assert b"Recommended:" in result_page.data


def test_compression_and_download_flow(client):
    """Test executing compression and downloading the resulting archive and PDF report."""
    data = {
        "file": (io.BytesIO(b"Data for compression testing\n" * 100), "sample.txt"),
        "preference": "max_compression"
    }
    upload_res = client.post("/analyze", data=data, content_type="multipart/form-data")
    op_url = upload_res.headers["Location"]
    op_id = op_url.split("/")[-1]

    # Execute compression
    compress_res = client.post(f"/compress/{op_id}", data={"algorithm": "ZIP"}, follow_redirects=True)
    assert compress_res.status_code == 200
    assert b"Compression Succeeded" in compress_res.data

    # Download compressed file
    download_res = client.get(f"/download/{op_id}")
    assert download_res.status_code == 200
    assert download_res.headers.get("Content-Disposition") is not None

    # Download PDF report
    report_res = client.get(f"/download_report/{op_id}")
    assert report_res.status_code == 200
    assert report_res.mimetype == "application/pdf"
    assert len(report_res.data) > 1000  # Non-empty PDF document


def test_benchmark_api(client):
    """Test the AJAX multi-algorithm benchmark endpoint."""
    data = {
        "file": (io.BytesIO(b"Benchmarking algorithms\n" * 50), "benchmark_test.txt"),
        "preference": "balanced"
    }
    upload_res = client.post("/analyze", data=data, content_type="multipart/form-data")
    op_id = upload_res.headers["Location"].split("/")[-1]

    api_res = client.post(f"/api/benchmark/{op_id}")
    assert api_res.status_code == 200
    json_data = api_res.get_json()
    assert json_data["success"] is True
    assert len(json_data["benchmarks"]) == 5  # All 5 algorithms benchmarked


def test_missing_model_fallback():
    """Ensure rule-based recommender executes reliably as fallback."""
    analysis = {
        "entropy": 3.2,
        "size_bytes": 10240,
        "category": "Text / Document",
        "extension": ".txt",
        "is_precompressed": False
    }
    rec = recommend_rule_based(analysis, preference="balanced")
    assert rec["recommended_algorithm"] in ["ZIP", "GZIP", "BZIP2", "LZMA", "7Z"]
    assert rec["recommendation_source"] == "Rule-Based Engine"
    assert rec["explanation"] is not None


def test_dashboard_and_history_routes(client):
    """Verify dashboard, history, and CSV export routes render successfully."""
    dash_res = client.get("/dashboard")
    assert dash_res.status_code == 200

    hist_res = client.get("/history")
    assert hist_res.status_code == 200

    csv_res = client.get("/export_history")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.mimetype


def test_unauthorized_download(client):
    """Attempting to download a non-existent operation returns redirect or error."""
    res = client.get("/download/invalid_operation_id", follow_redirects=True)
    assert res.status_code == 200
    assert b"File not found or unauthorized operation" in res.data


def test_folder_upload_and_compression_flow(client):
    """Test uploading an entire folder hierarchy, analyzing it, compressing it with 7Z, and downloading."""
    import json
    data = {
        "upload_mode": "folder",
        "folder_name": "test_folder_project",
        "relative_paths": json.dumps(["test_folder_project/a.txt", "test_folder_project/sub/b.py"]),
        "folder_files": [
            (io.BytesIO(b"Folder text content\n" * 100), "a.txt"),
            (io.BytesIO(b"def process():\n    return 42\n" * 100), "b.py")
        ],
        "preference": "balanced"
    }

    upload_res = client.post("/analyze", data=data, content_type="multipart/form-data")
    assert upload_res.status_code == 302
    op_url = upload_res.headers["Location"]
    op_id = op_url.split("/")[-1]

    # Result page should show folder hierarchy info
    result_page = client.get(op_url)
    assert result_page.status_code == 200
    assert b"test_folder_project" in result_page.data
    assert b"Folder Hierarchy" in result_page.data

    # Compress the folder using 7Z solid archive
    comp_res = client.post(f"/compress/{op_id}", data={"algorithm": "7Z"}, follow_redirects=True)
    assert comp_res.status_code == 200
    assert b"Compression Succeeded" in comp_res.data

    # Download compressed 7Z folder archive
    dl_res = client.get(f"/download/{op_id}")
    assert dl_res.status_code == 200
    assert "7z" in dl_res.headers.get("Content-Disposition", "")


def test_visual_studio_api_workflow(client):
    """Test full Visual Studio AJAX workflow: upload file -> compress -> download batch ZIP -> delete."""
    import reportlab.pdfgen.canvas as canvas

    # Create a small valid test PDF
    pdf_buf = io.BytesIO()
    c = canvas.Canvas(pdf_buf)
    c.drawString(100, 700, "Momentum-Based Algorithmic Trading & Portfolio Optimization")
    c.drawString(100, 680, "Academic Research Paper on Lossless Optimization")
    c.save()
    pdf_bytes = pdf_buf.getvalue()

    # 1. Test /api/upload_file
    upload_res = client.post(
        "/api/upload_file",
        data={"files": [(io.BytesIO(pdf_bytes), "sample_paper.pdf")]},
        content_type="multipart/form-data"
    )
    assert upload_res.status_code == 200
    upload_json = upload_res.get_json()
    assert upload_json["success"] is True
    assert len(upload_json["files"]) == 1
    file_item = upload_json["files"][0]
    op_id = file_item["operation_id"]
    assert file_item["is_pdf"] is True
    assert file_item["thumbnail_url"].startswith("data:image/png;base64,")

    # 2. Verify Analytics page is immediately accessible for this uploaded studio file
    analytics_res = client.get(f"/result/{op_id}")
    assert analytics_res.status_code == 200
    assert b"sample_paper.pdf" in analytics_res.data
    assert b"Benchmark Algorithms" in analytics_res.data

    # 3. Test /api/compress_file with explicit algorithm selection (e.g. 7Z)
    comp_res = client.post(
        "/api/compress_file",
        json={"operation_id": op_id, "compression_level": 100, "algorithm": "7Z"}
    )
    assert comp_res.status_code == 200
    comp_json = comp_res.get_json()
    assert comp_json["success"] is True
    assert comp_json["compressed_size"] > 0
    assert comp_json["space_saving_pct"] >= 0

    # Verify Analytics page now shows compression succeeded
    analytics_after = client.get(f"/result/{op_id}")
    assert analytics_after.status_code == 200
    assert b"Compression Succeeded" in analytics_after.data

    # 4. Test /api/download_batch_zip
    zip_res = client.post(
        "/api/download_batch_zip",
        json={"operation_ids": [op_id]}
    )
    assert zip_res.status_code == 200
    assert zip_res.headers.get("Content-Disposition") is not None
    assert zip_res.mimetype in ["application/zip", "application/x-zip-compressed"]

    # 5. Test /api/delete_file/<operation_id>
    del_res = client.post(f"/api/delete_file/{op_id}")
    assert del_res.status_code == 200
    assert del_res.get_json()["success"] is True


def test_analytics_resilience_recovers_from_sqlite_history(client):
    """Test that /result/<operation_id> never fails with 'expired' if the record is in SQLite."""
    # Compress a file to generate a database history record
    data = {
        "file": (io.BytesIO(b"Persistent database history test payload\n" * 40), "history_doc.txt"),
        "preference": "balanced"
    }
    upload_res = client.post("/analyze", data=data, content_type="multipart/form-data")
    op_id = upload_res.headers["Location"].split("/")[-1]

    client.post(f"/compress/{op_id}", data={"algorithm": "ZIP"})

    # Even if we access result, it succeeds
    res_before = client.get(f"/result/{op_id}")
    assert res_before.status_code == 200
    assert b"history_doc.txt" in res_before.data

    # Now verify that even if meta.json is deleted, it recovers from SQLite
    upload_dir = Path(client.application.config["UPLOAD_DIR"])
    meta_file = upload_dir / f"{op_id}_meta.json"
    if meta_file.exists():
        meta_file.unlink()

    res_after = client.get(f"/result/{op_id}")
    assert res_after.status_code == 200
    assert b"history_doc.txt" in res_after.data
    assert b"Compression Succeeded" in res_after.data



