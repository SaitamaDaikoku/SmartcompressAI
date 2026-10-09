"""
History service for SmartCompress AI.
Provides querying, filtering, pagination, deletion, and CSV export for compression history.
"""

import io
import csv
from typing import Dict, Any, List, Tuple, Optional

from database.db import (
    list_history,
    get_record_by_id,
    get_record_by_operation_id,
    delete_record_by_id,
    export_all_records
)


class HistoryService:
    """Manages history records, pagination, deletion, and CSV export."""

    @staticmethod
    def get_history(
        search: Optional[str] = None,
        algorithm: Optional[str] = None,
        sort_by: str = "date_desc",
        page: int = 1,
        per_page: int = 10
    ) -> Dict[str, Any]:
        """
        Retrieve paginated compression operations.
        """
        records, total_count = list_history(
            search=search,
            algorithm=algorithm,
            sort_by=sort_by,
            page=page,
            per_page=per_page
        )

        total_pages = max(1, (total_count + per_page - 1) // per_page)

        return {
            "records": records,
            "total_count": total_count,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
            "search": search or "",
            "algorithm": algorithm or "ALL",
            "sort_by": sort_by
        }

    @staticmethod
    def get_details(operation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full details of an operation by UUID."""
        return get_record_by_operation_id(operation_id)

    @staticmethod
    def delete_record(record_id: int) -> bool:
        """Delete record from database."""
        return delete_record_by_id(record_id)

    @staticmethod
    def export_csv() -> str:
        """Export all historical compression operations as a CSV formatted string."""
        records = export_all_records()
        if not records:
            return "No records found."

        output = io.StringIO()
        fieldnames = [
            "id", "operation_id", "creation_timestamp", "original_filename",
            "file_extension", "file_category", "mime_type", "entropy",
            "original_size", "compressed_size", "bytes_saved", "compression_ratio",
            "compression_duration", "selected_algorithm", "recommendation_source",
            "model_confidence", "output_filename", "operation_status"
        ]

        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in records:
            writer.writerow(r)

        return output.getvalue()
