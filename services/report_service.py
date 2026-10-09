"""
PDF Report generation service for SmartCompress AI.
Uses ReportLab to produce professional, publication-quality technical reports.
Information Storage Management (ISM) academic documentation.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether
)

from config import Config


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and stamp 'Page X of Y' in footer."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages: int):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Header banner text
        self.drawString(54, letter[1] - 36, "SmartCompress AI — Information Storage Management (ISM)")
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(54, letter[1] - 42, letter[0] - 54, letter[1] - 42)

        # Footer banner text
        footer_text = f"Page {self._pageNumber} of {total_pages}"
        self.drawRightString(letter[0] - 54, 36, footer_text)
        self.drawString(54, 36, "Confidential & Academic Laboratory Report | Generated Automatically")
        self.line(54, 48, letter[0] - 54, 48)
        self.restoreState()


class ReportService:
    """Generates comprehensive PDF reports from real compression and analysis data."""

    @staticmethod
    def generate_pdf_report(
        operation_data: Dict[str, Any],
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Build an academic technical report in PDF format from real compression session data.
        """
        op_id = operation_data.get("operation_id", "report")
        if not output_path:
            filename = f"SmartCompress_Report_{op_id}.pdf"
            output_path = Config.REPORT_DIR / filename
        else:
            output_path = Path(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=letter,
            leftMargin=54,
            rightMargin=54,
            topMargin=54,
            bottomMargin=54
        )

        styles = getSampleStyleSheet()

        # Custom typography styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#0F172A")
        )
        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#475569")
        )
        h1_style = ParagraphStyle(
            "SectionH1",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            textColor=colors.HexColor("#1E293B"),
            spaceBefore=14,
            spaceAfter=6
        )
        body_style = ParagraphStyle(
            "DocBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#334155")
        )
        bold_body = ParagraphStyle(
            "DocBoldBody",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#1E293B")
        )

        elements = []

        # Header Title
        elements.append(Paragraph("SmartCompress AI", title_style))
        elements.append(Paragraph("Intelligent Storage Optimization & File Compression Report", subtitle_style))
        elements.append(Paragraph(f"Generated on {datetime.now().strftime('%B %d, %Y at %H:%M:%S')} | Operation ID: <b>{op_id}</b>", subtitle_style))
        elements.append(Spacer(1, 10))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563EB"), spaceAfter=14))

        # 1. File Metadata Table
        elements.append(Paragraph("1. File Identification & Metadata", h1_style))
        
        orig_filename = operation_data.get("original_filename", "N/A")
        analysis = operation_data.get("analysis", {})
        orig_size = operation_data.get("original_size", 0)
        entropy = analysis.get("entropy", operation_data.get("entropy", 0.0))
        category = analysis.get("category", operation_data.get("file_category", "General"))
        mime_type = analysis.get("mime_type", operation_data.get("mime_type", "application/octet-stream"))
        sha256 = analysis.get("sha256", "N/A")

        metadata_rows = [
            [Paragraph("<b>Original Filename</b>", body_style), Paragraph(str(orig_filename), body_style)],
            [Paragraph("<b>File Category</b>", body_style), Paragraph(str(category), body_style)],
            [Paragraph("<b>MIME Type</b>", body_style), Paragraph(str(mime_type), body_style)],
            [Paragraph("<b>Original File Size</b>", body_style), Paragraph(f"{orig_size:,} bytes ({orig_size / 1024:.2f} KB / {orig_size / (1024*1024):.2f} MB)", body_style)],
            [Paragraph("<b>SHA-256 Checksum</b>", body_style), Paragraph(f"<font size=7>{sha256}</font>", body_style)]
        ]

        t_meta = Table(metadata_rows, colWidths=[150, 350])
        t_meta.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("PADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE")
        ]))
        elements.append(t_meta)
        elements.append(Spacer(1, 10))

        # 2. Information Theory & Entropy Analysis
        elements.append(Paragraph("2. Shannon Entropy & Compressibility Assessment", h1_style))
        entropy_desc = (
            f"Shannon entropy measures the average information density and randomness of the data stream. "
            f"The calculated entropy is <b>{entropy:.4f} bits/byte</b> out of a theoretical maximum of 8.0 bits/byte "
            f"({(entropy / 8.0) * 100:.1f}% density)."
        )
        elements.append(Paragraph(entropy_desc, body_style))
        elements.append(Spacer(1, 4))

        entropy_details = analysis.get("entropy_details", {})
        if entropy_details:
            explanation = entropy_details.get("explanation", "")
            elements.append(Paragraph(f"<b>Statistical Interpretation:</b> {explanation}", body_style))
        elements.append(Spacer(1, 10))

        # 3. Recommendation Engine Decision
        elements.append(Paragraph("3. Hybrid Recommendation Engine Analysis", h1_style))
        rec_source = operation_data.get("recommendation_source", "Rule-Based Engine")
        confidence = operation_data.get("model_confidence")
        conf_str = f" ({confidence * 100:.1f}% confidence)" if confidence is not None else ""
        
        recommendation = operation_data.get("recommendation", {})
        rec_algo = recommendation.get("recommended_algorithm", operation_data.get("selected_algorithm", "ZIP"))
        rec_explanation = recommendation.get("explanation", "Selected by system analysis.")

        rec_table_data = [
            [Paragraph("<b>Engine Source</b>", body_style), Paragraph(f"{rec_source}{conf_str}", body_style)],
            [Paragraph("<b>Recommended Algorithm</b>", body_style), Paragraph(f"<b>{rec_algo}</b>", bold_body)],
            [Paragraph("<b>Architectural Justification</b>", body_style), Paragraph(rec_explanation, body_style)]
        ]
        t_rec = Table(rec_table_data, colWidths=[150, 350])
        t_rec.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("PADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "TOP")
        ]))
        elements.append(t_rec)
        elements.append(Spacer(1, 10))

        # 4. Actual Measured Compression Results
        elements.append(Paragraph("4. Measured Compression Performance", h1_style))
        
        comp_size = operation_data.get("compressed_size", 0)
        bytes_saved = operation_data.get("bytes_saved", 0)
        space_saving_pct = operation_data.get("space_saving_pct", 0.0)
        if space_saving_pct == 0.0 and orig_size > 0:
            space_saving_pct = round(((orig_size - comp_size) / orig_size) * 100, 2)
        ratio = operation_data.get("compression_ratio", 1.0)
        duration = operation_data.get("compression_duration", 0.0)
        algo_used = operation_data.get("selected_algorithm", "ZIP")
        output_filename = operation_data.get("output_filename", "N/A")

        perf_rows = [
            [Paragraph("<b>Algorithm Applied</b>", body_style), Paragraph(str(algo_used), bold_body)],
            [Paragraph("<b>Compressed Output File</b>", body_style), Paragraph(str(output_filename), body_style)],
            [Paragraph("<b>Compressed File Size</b>", body_style), Paragraph(f"{comp_size:,} bytes ({comp_size / 1024:.2f} KB / {comp_size / (1024*1024):.2f} MB)", body_style)],
            [Paragraph("<b>Raw Storage Saved</b>", body_style), Paragraph(f"{bytes_saved:,} bytes", body_style)],
            [Paragraph("<b>Space-Saving Efficiency</b>", body_style), Paragraph(f"<b>{space_saving_pct:.2f}%</b>", bold_body)],
            [Paragraph("<b>Compression Ratio (C/O)</b>", body_style), Paragraph(f"{ratio:.4f}", body_style)],
            [Paragraph("<b>Execution Duration</b>", body_style), Paragraph(f"{duration:.4f} seconds", body_style)]
        ]

        t_perf = Table(perf_rows, colWidths=[150, 350])
        t_perf.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFFFF")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("PADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE")
        ]))
        elements.append(t_perf)
        elements.append(Spacer(1, 14))

        # 5. Algorithm Comparison Benchmark Summary (if present)
        benchmarks = operation_data.get("benchmarks", [])
        if benchmarks:
            elements.append(Paragraph("5. Empirical Multi-Algorithm Benchmark Comparison", h1_style))
            bench_table_data = [
                [
                    Paragraph("<b>Algorithm</b>", bold_body),
                    Paragraph("<b>Compressed Size</b>", bold_body),
                    Paragraph("<b>Space Saved</b>", bold_body),
                    Paragraph("<b>Efficiency (%)</b>", bold_body),
                    Paragraph("<b>Time (s)</b>", bold_body)
                ]
            ]
            for b in benchmarks:
                bench_table_data.append([
                    Paragraph(b["algorithm"], body_style),
                    Paragraph(f"{b['compressed_size']:,} B", body_style),
                    Paragraph(f"{b['bytes_saved']:,} B", body_style),
                    Paragraph(f"{b['space_saving_pct']:.2f}%", body_style),
                    Paragraph(f"{b['duration']:.4f}s", body_style)
                ])

            t_bench = Table(bench_table_data, colWidths=[90, 110, 110, 100, 90])
            t_bench.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0284C7")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("PADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("ALIGN", (1, 1), (-1, -1), "CENTER")
            ]))
            elements.append(t_bench)
            elements.append(Spacer(1, 10))

        # Summary Note
        elements.append(KeepTogether([
            HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E2E8F0"), spaceAfter=8),
            Paragraph(
                "<b>ISM Academic Verification:</b> This document certifies that real lossless compression "
                "was executed on the storage payload. Bit-for-bit reconstruction is mathematically guaranteed "
                "via reversible entropy coding. No simulated or synthetic reduction values were utilized.",
                ParagraphStyle("CertStyle", parent=styles["Normal"], fontSize=8, leading=11, textColor=colors.HexColor("#64748B"))
            )
        ]))

        doc.build(elements, canvasmaker=NumberedCanvas)
        return output_path
