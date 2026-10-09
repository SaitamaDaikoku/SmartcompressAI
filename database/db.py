"""
SQLite database management module for SmartCompress AI.
Provides persistent storage for file compression metadata, history, and analytics.
Uses strictly parameterized SQL queries.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from config import Config

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS compression_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_id TEXT UNIQUE NOT NULL,
    original_filename TEXT NOT NULL,
    file_extension TEXT,
    file_category TEXT,
    mime_type TEXT,
    entropy REAL,
    original_size INTEGER NOT NULL,
    compressed_size INTEGER NOT NULL,
    bytes_saved INTEGER NOT NULL,
    compression_ratio REAL NOT NULL,
    compression_duration REAL NOT NULL,
    selected_algorithm TEXT NOT NULL,
    recommendation_source TEXT,
    model_confidence REAL,
    output_filename TEXT NOT NULL,
    creation_timestamp TEXT NOT NULL,
    operation_status TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_operation_id ON compression_history(operation_id);
CREATE INDEX IF NOT EXISTS idx_algorithm ON compression_history(selected_algorithm);
CREATE INDEX IF NOT EXISTS idx_creation_timestamp ON compression_history(creation_timestamp);
"""


def get_db_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Create and return a configured sqlite3 connection with Row factory."""
    path = db_path if db_path else Config.DATABASE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    """Initialize database tables and indexes."""
    path = db_path if db_path else Config.DATABASE_PATH
    with get_db_connection(path) as conn:
        conn.executescript(SCHEMA_SQL)
        conn.commit()


def insert_compression_record(record: Dict[str, Any], db_path: Optional[Path] = None) -> int:
    """
    Insert a newly executed compression operation into compression_history.
    Returns the new row ID.
    """
    timestamp = record.get("creation_timestamp")
    if not timestamp:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    query = """
    INSERT INTO compression_history (
        operation_id, original_filename, file_extension, file_category,
        mime_type, entropy, original_size, compressed_size, bytes_saved,
        compression_ratio, compression_duration, selected_algorithm,
        recommendation_source, model_confidence, output_filename,
        creation_timestamp, operation_status
    ) VALUES (
        ?, ?, ?, ?,
        ?, ?, ?, ?, ?,
        ?, ?, ?,
        ?, ?, ?,
        ?, ?
    )
    """

    params = (
        record["operation_id"],
        record["original_filename"],
        record.get("file_extension", ""),
        record.get("file_category", "General"),
        record.get("mime_type", "application/octet-stream"),
        record.get("entropy", 0.0),
        record["original_size"],
        record["compressed_size"],
        record["bytes_saved"],
        record["compression_ratio"],
        record["compression_duration"],
        record["selected_algorithm"],
        record.get("recommendation_source", "Unknown"),
        record.get("model_confidence"),
        record["output_filename"],
        timestamp,
        record.get("operation_status", "SUCCESS")
    )

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor.lastrowid


def get_record_by_id(record_id: int, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Retrieve history record by primary key."""
    query = "SELECT * FROM compression_history WHERE id = ?"
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query, (record_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_record_by_operation_id(operation_id: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Retrieve history record by unique operation UUID."""
    query = "SELECT * FROM compression_history WHERE operation_id = ?"
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query, (operation_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def list_history(
    search: Optional[str] = None,
    algorithm: Optional[str] = None,
    sort_by: str = "date_desc",
    page: int = 1,
    per_page: int = 10,
    db_path: Optional[Path] = None
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Query compression history with optional search, algorithm filter, sorting, and pagination.
    Returns (list of records, total record count).
    """
    conditions = []
    params: List[Any] = []

    if search and search.strip():
        conditions.append("(original_filename LIKE ? OR operation_id LIKE ?)")
        term = f"%{search.strip()}%"
        params.extend([term, term])

    if algorithm and algorithm.strip() and algorithm.upper() != "ALL":
        conditions.append("selected_algorithm = ?")
        params.append(algorithm.strip().upper())

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

    # Sort mapping
    sort_mapping = {
        "date_desc": "creation_timestamp DESC",
        "date_asc": "creation_timestamp ASC",
        "savings_desc": "bytes_saved DESC",
        "savings_asc": "bytes_saved ASC",
        "size_desc": "original_size DESC",
        "size_asc": "original_size ASC"
    }
    order_clause = f" ORDER BY {sort_mapping.get(sort_by, 'creation_timestamp DESC')}"

    count_query = f"SELECT COUNT(*) FROM compression_history{where_clause}"

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]

        offset = max(0, (page - 1) * per_page)
        data_query = f"SELECT * FROM compression_history{where_clause}{order_clause} LIMIT ? OFFSET ?"
        data_params = params + [per_page, offset]

        cursor.execute(data_query, data_params)
        rows = cursor.fetchall()
        records = [dict(r) for r in rows]

        # Calculate space saving percentage on the fly for display
        for r in records:
            if r["original_size"] > 0:
                r["space_saving_pct"] = round(((r["original_size"] - r["compressed_size"]) / r["original_size"]) * 100, 2)
            else:
                r["space_saving_pct"] = 0.0

        return records, total_count


def delete_record_by_id(record_id: int, db_path: Optional[Path] = None) -> bool:
    """Delete a history record by ID."""
    query = "DELETE FROM compression_history WHERE id = ?"
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query, (record_id,))
        conn.commit()
        return cursor.rowcount > 0


def get_dashboard_statistics(db_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Compute real aggregated metrics from the compression history table for dashboard presentation.
    Never returns fabricated data.
    """
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()

        # Overall totals
        cursor.execute("""
            SELECT 
                COUNT(*) as total_files,
                COALESCE(SUM(original_size), 0) as total_orig_bytes,
                COALESCE(SUM(compressed_size), 0) as total_comp_bytes,
                COALESCE(SUM(bytes_saved), 0) as total_saved_bytes,
                COALESCE(AVG(compression_duration), 0.0) as avg_duration
            FROM compression_history
            WHERE operation_status = 'SUCCESS'
        """)
        totals = dict(cursor.fetchone())

        total_files = totals["total_files"]
        total_orig = totals["total_orig_bytes"]
        total_comp = totals["total_comp_bytes"]
        total_saved = totals["total_saved_bytes"]

        if total_orig > 0:
            avg_savings_pct = round(((total_orig - total_comp) / total_orig) * 100, 2)
        else:
            avg_savings_pct = 0.0

        # Distribution of algorithm usage
        cursor.execute("""
            SELECT selected_algorithm, COUNT(*) as count
            FROM compression_history
            WHERE operation_status = 'SUCCESS'
            GROUP BY selected_algorithm
            ORDER BY count DESC
        """)
        algo_distribution = [dict(r) for r in cursor.fetchall()]

        # Savings by category
        cursor.execute("""
            SELECT file_category, 
                   COUNT(*) as count,
                   COALESCE(SUM(original_size), 0) as orig_bytes,
                   COALESCE(SUM(compressed_size), 0) as comp_bytes
            FROM compression_history
            WHERE operation_status = 'SUCCESS'
            GROUP BY file_category
        """)
        category_rows = cursor.fetchall()
        category_stats = []
        for r in category_rows:
            orig = r["orig_bytes"]
            comp = r["comp_bytes"]
            pct = round(((orig - comp) / orig) * 100, 2) if orig > 0 else 0.0
            category_stats.append({
                "category": r["file_category"],
                "count": r["count"],
                "saving_pct": pct
            })

        # Recent 10 operations for timeline chart
        cursor.execute("""
            SELECT original_filename, selected_algorithm, original_size, compressed_size, bytes_saved, creation_timestamp
            FROM compression_history
            WHERE operation_status = 'SUCCESS'
            ORDER BY creation_timestamp DESC
            LIMIT 10
        """)
        recent_ops = [dict(r) for r in cursor.fetchall()]

        return {
            "total_files": total_files,
            "total_original_bytes": total_orig,
            "total_compressed_bytes": total_comp,
            "total_saved_bytes": total_saved,
            "avg_savings_pct": avg_savings_pct,
            "avg_duration": round(totals["avg_duration"], 3),
            "algorithm_distribution": algo_distribution,
            "category_stats": category_stats,
            "recent_operations": recent_ops
        }


def export_all_records(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Export all records for CSV export."""
    query = "SELECT * FROM compression_history ORDER BY creation_timestamp DESC"
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        return [dict(r) for r in cursor.fetchall()]
