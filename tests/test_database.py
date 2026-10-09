"""
Unit tests for SQLite database operations, queries, and dashboard metrics.
"""

import tempfile
from pathlib import Path
import pytest

from database.db import (
    init_db,
    insert_compression_record,
    get_record_by_id,
    get_record_by_operation_id,
    list_history,
    delete_record_by_id,
    get_dashboard_statistics,
    export_all_records
)


@pytest.fixture
def temp_db():
    """Create a temporary test database path and initialize schema."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)
    init_db(db_path)
    yield db_path
    if db_path.exists():
        try:
            db_path.unlink()
        except OSError:
            pass


def test_insert_and_retrieve_record(temp_db):
    """Test inserting a record and reading it back by ID and operation_id."""
    record = {
        "operation_id": "test_op_001",
        "original_filename": "data.csv",
        "file_extension": ".csv",
        "file_category": "Structured Data / Code",
        "mime_type": "text/csv",
        "entropy": 3.84,
        "original_size": 100000,
        "compressed_size": 25000,
        "bytes_saved": 75000,
        "compression_ratio": 0.25,
        "compression_duration": 0.045,
        "selected_algorithm": "7Z",
        "recommendation_source": "Random Forest ML",
        "model_confidence": 0.92,
        "output_filename": "data_test_op_001.7z",
        "operation_status": "SUCCESS"
    }

    row_id = insert_compression_record(record, db_path=temp_db)
    assert row_id is not None
    assert row_id > 0

    fetched = get_record_by_id(row_id, db_path=temp_db)
    assert fetched["operation_id"] == "test_op_001"
    assert fetched["original_filename"] == "data.csv"
    assert fetched["selected_algorithm"] == "7Z"
    assert fetched["bytes_saved"] == 75000

    by_op = get_record_by_operation_id("test_op_001", db_path=temp_db)
    assert by_op["id"] == row_id


def test_list_history_filtering_and_sorting(temp_db):
    """Test searching, filtering by algorithm, and pagination."""
    # Insert 3 records
    for i, (name, algo, saved) in enumerate([
        ("report.pdf", "ZIP", 1000),
        ("backup.sql", "7Z", 50000),
        ("image.png", "GZIP", -50)
    ]):
        insert_compression_record({
            "operation_id": f"op_{i}",
            "original_filename": name,
            "file_extension": f".{name.split('.')[-1]}",
            "file_category": "Doc",
            "mime_type": "application/octet-stream",
            "entropy": 4.5,
            "original_size": 10000,
            "compressed_size": 10000 - saved,
            "bytes_saved": saved,
            "compression_ratio": 0.5,
            "compression_duration": 0.01,
            "selected_algorithm": algo,
            "recommendation_source": "Rule-Based Engine",
            "model_confidence": None,
            "output_filename": f"out_{i}.zip",
            "operation_status": "SUCCESS"
        }, db_path=temp_db)

    # Search by filename
    results, count = list_history(search="backup", db_path=temp_db)
    assert count == 1
    assert results[0]["original_filename"] == "backup.sql"

    # Filter by algorithm
    results, count = list_history(algorithm="7Z", db_path=temp_db)
    assert count == 1
    assert results[0]["selected_algorithm"] == "7Z"

    # Sort by savings descending
    results, count = list_history(sort_by="savings_desc", db_path=temp_db)
    assert count == 3
    assert results[0]["bytes_saved"] == 50000


def test_delete_record(temp_db):
    """Test deleting a record by primary key."""
    row_id = insert_compression_record({
        "operation_id": "to_delete",
        "original_filename": "temp.txt",
        "original_size": 100,
        "compressed_size": 50,
        "bytes_saved": 50,
        "compression_ratio": 0.5,
        "compression_duration": 0.01,
        "selected_algorithm": "ZIP",
        "output_filename": "temp.zip"
    }, db_path=temp_db)

    assert delete_record_by_id(row_id, db_path=temp_db) is True
    assert get_record_by_id(row_id, db_path=temp_db) is None


def test_dashboard_statistics(temp_db):
    """Test computation of aggregated storage metrics."""
    insert_compression_record({
        "operation_id": "stat_1",
        "original_filename": "f1.txt",
        "file_category": "Text / Document",
        "original_size": 200,
        "compressed_size": 100,
        "bytes_saved": 100,
        "compression_ratio": 0.5,
        "compression_duration": 0.02,
        "selected_algorithm": "ZIP",
        "output_filename": "f1.zip",
        "operation_status": "SUCCESS"
    }, db_path=temp_db)

    insert_compression_record({
        "operation_id": "stat_2",
        "original_filename": "f2.log",
        "file_category": "Text / Document",
        "original_size": 800,
        "compressed_size": 200,
        "bytes_saved": 600,
        "compression_ratio": 0.25,
        "compression_duration": 0.04,
        "selected_algorithm": "7Z",
        "output_filename": "f2.7z",
        "operation_status": "SUCCESS"
    }, db_path=temp_db)

    stats = get_dashboard_statistics(db_path=temp_db)
    assert stats["total_files"] == 2
    assert stats["total_original_bytes"] == 1000
    assert stats["total_compressed_bytes"] == 300
    assert stats["total_saved_bytes"] == 700
    assert stats["avg_savings_pct"] == 70.0
    assert len(stats["algorithm_distribution"]) == 2
