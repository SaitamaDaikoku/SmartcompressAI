"""
Rule-based recommendation engine for SmartCompress AI.
Evaluates file characteristics, Information Storage Management (ISM) principles,
Shannon entropy, and user preferences to recommend suitable compression algorithms.
"""

from typing import Dict, Any, List

# Compatibility table for lossless algorithms
# Compatibility table for lossless algorithms
ALL_ALGORITHMS = ["PDF-Deflate", "7Z", "ZIP", "GZIP", "BZIP2", "LZMA"]

ALGORITHM_PROFILES = {
    "PDF-Deflate": {
        "name": "PDF-Deflate (Stream & Image Optimizer)",
        "strengths": "Deflates content streams, purges garbage objects, deduplicates fonts, and optimizes high-res raster images for 50%+ reduction.",
        "best_for": "Scanned PDFs, research papers, reports, eBooks with heavy embedded images."
    },
    "ZIP": {
        "name": "ZIP (Deflate)",
        "strengths": "Ubiquitous compatibility across all platforms and operating systems; fast extraction; solid compression.",
        "best_for": "General documents, cross-platform distribution, small-to-medium files."
    },
    "GZIP": {
        "name": "GZIP (GNU Zip)",
        "strengths": "Ultra-fast compression and decompression; minimal CPU and memory footprint; streaming support.",
        "best_for": "Web assets, log files, HTTP transfer, fast archival."
    },
    "BZIP2": {
        "name": "BZIP2 (Burrows-Wheeler)",
        "strengths": "Block-sorting algorithm excels on repetitive patterns, source code, and structured text; superior to Deflate.",
        "best_for": "Source code, structured text, configuration dumps, CSV tables."
    },
    "LZMA": {
        "name": "LZMA / XZ (Lempel-Ziv-Markov)",
        "strengths": "Very high compression ratio, large sliding dictionary; exceptional on medium-to-large files.",
        "best_for": "Linux distribution tarballs, binary executables, software distribution packages."
    },
    "7Z": {
        "name": "7Z (LZMA2 / 7-Zip)",
        "strengths": "State-of-the-art compression ratio, dynamic multi-threaded dictionary compression, solid archive support.",
        "best_for": "Maximum storage reduction, large datasets, multi-file backups, archival storage."
    }
}


def recommend_rule_based(analysis: Dict[str, Any], preference: str = "balanced") -> Dict[str, Any]:
    """
    Evaluate file analysis metadata and user preference using deterministic ISM rules.

    Args:
        analysis: Dictionary from analyze_file (entropy, size_bytes, category, extension, is_precompressed)
        preference: 'balanced', 'max_compression', or 'fastest'

    Returns:
        Dict containing recommended algorithm, explanation, suitability rankings, and warnings.
    """
    entropy = analysis.get("entropy", 0.0)
    size_bytes = analysis.get("size_bytes", 0)
    category = analysis.get("category", "")
    extension = analysis.get("extension", "").lower()
    is_precompressed = analysis.get("is_precompressed", False)

    warning = None
    pref = preference.lower().strip()
    if pref not in ["balanced", "max_compression", "fastest"]:
        pref = "balanced"

    # Rule 0A: PDF Documents (Optimize internal streams, images, and fonts)
    if extension == ".pdf":
        recommended = "PDF-Deflate"
        warning = (
            f"Notice: This PDF contains high-density content streams ({entropy:.2f} bits/byte). "
            "Standard container archiving (ZIP/GZIP) cannot compress already-deflated byte streams. "
            "Use PDF-Deflate (Stream & Image Optimizer) to achieve dramatic 50%+ reduction, or 7Z (LZMA2) for archival packaging."
        )
        explanation = (
            "PDF Document detected. PDF-Deflate performs in-depth stream deflation, dead object garbage collection, "
            "font deduplication, and high-resolution image optimization to achieve substantial space reduction (often 50% or more)."
        )

    # Rule 0B: Pure pre-compressed archive or true near-maximal ceiling entropy (>= 7.92)
    elif is_precompressed or entropy >= 7.92:
        warning = (
            f"Notice: This file exhibits near-maximal entropy ({entropy:.2f} bits/byte, close to 8.0 bits/byte theoretical limit). "
            "Data is already packed or encrypted. Further compression with standard Deflate may yield minimal savings; "
            "7Z (LZMA2) is recommended if attempting to extract deep multi-block dictionary redundancies."
        )
        if pref == "fastest":
            recommended = "GZIP"
            explanation = (
                "File has near-maximal entropy. GZIP container format is selected for rapid packaging with minimal CPU overhead."
            )
        else:
            recommended = "7Z"
            explanation = (
                f"File has high entropy ({entropy:.2f} bits/byte). 7Z (LZMA2) provides the highest dictionary depth "
                "to squeeze whatever residual redundancy remains without causing excessive container bloating."
            )

    # Rule 1: User explicitly requests Fastest compression
    elif pref == "fastest":
        recommended = "GZIP"
        explanation = (
            "GZIP (Deflate) chosen for 'Fastest' preference. It delivers high-throughput stream compression with minimal latency."
        )

    # Rule 2: User explicitly requests Maximum Compression
    elif pref == "max_compression":
        recommended = "7Z"
        explanation = (
            "7Z (LZMA2 preset 9) chosen for 'Maximum Compression' mode. Its massive sliding dictionary and context modeling "
            "are mathematically tuned to maximize space savings, frequently cutting uncompressed data in half or more."
        )

    # Rule 3: Balanced preference (Default)
    else:
        # Balanced logic: prioritize strong space reduction (7Z / LZMA / BZIP2)
        if analysis.get("is_directory") or category == "Folder / Multi-File Archive":
            recommended = "7Z"
            file_count = analysis.get("file_count", "multiple")
            explanation = (
                f"Multi-file directory tree containing {file_count} files. 7Z (LZMA2 solid archive) enables cross-file "
                "redundancy elimination across the directory hierarchy, achieving maximum storage footprint reduction."
            )
        elif category in ["Structured Data / Code", "Text / Document"]:
            if size_bytes > 30 * 1024 or entropy < 6.5:
                recommended = "7Z"
                explanation = (
                    f"Text/document data with entropy {entropy:.2f} bits/byte. 7Z (LZMA2) delivers dramatic space reduction, "
                    "often cutting file size in half or better while maintaining solid throughput."
                )
            else:
                recommended = "ZIP"
                explanation = (
                    f"For small document snippet ({analysis.get('size_display', '')}), ZIP offers universal compatibility "
                    "and rapid turnaround."
                )
        elif category in ["Binary / Executable", "Document"]:
            recommended = "7Z"
            explanation = (
                f"High-density {category.lower()} format. 7Z with LZMA2 sliding dictionary discovers inter-block "
                "redundancies that standard ZIP misses, maximizing byte reduction."
            )
        elif size_bytes > 100 * 1024:
            recommended = "7Z"
            explanation = (
                "For files exceeding 100 KB, 7Z (LZMA2) provides state-of-the-art compression ratios to minimize storage consumption."
            )
        else:
            recommended = "ZIP"
            explanation = (
                "ZIP provides the optimal equilibrium between fast compression time and standard compatibility for small payloads."
            )

    # Compile algorithm comparison suitability
    ranked_algos = []
    for algo in ALL_ALGORITHMS:
        profile = ALGORITHM_PROFILES[algo]
        is_rec = (algo == recommended)
        ranked_algos.append({
            "algorithm": algo,
            "name": profile["name"],
            "strengths": profile["strengths"],
            "best_for": profile["best_for"],
            "is_recommended": is_rec
        })

    return {
        "recommended_algorithm": recommended,
        "explanation": explanation,
        "recommendation_source": "Rule-Based Engine",
        "warning": warning,
        "user_preference": pref,
        "ranked_algorithms": ranked_algos,
        "model_confidence": None
    }
