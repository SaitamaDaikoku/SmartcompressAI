"""
Shannon Entropy calculation and statistical analysis module.
Information Storage Management (ISM) concept implementation.
"""

import math
from pathlib import Path
from typing import Dict, Any, Union


def calculate_entropy(file_path: Union[str, Path], chunk_size: int = 65536) -> float:
    """
    Calculate Shannon entropy of a file's byte stream.

    Formula:
        H(X) = - sum(p(x) * log2(p(x))) for each byte value x in [0, 255]
    where p(x) = count(x) / total_bytes.

    Returns:
        float: Entropy in bits per byte, strictly in the range [0.0, 8.0].
    """
    path = Path(file_path)
    if not path.exists():
        return 0.0

    # Collect all files to process (single file or directory tree)
    if path.is_dir():
        files_to_scan = [f for f in path.rglob("*") if f.is_file()]
    else:
        if path.stat().st_size == 0:
            return 0.0
        files_to_scan = [path]

    if not files_to_scan:
        return 0.0

    # Initialize frequency counts for 256 possible byte values
    byte_counts = [0] * 256
    total_bytes = 0

    for f_path in files_to_scan:
        try:
            with open(f_path, "rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    for byte in chunk:
                        byte_counts[byte] += 1
        except OSError:
            continue

    if total_bytes == 0:
        return 0.0

    entropy = 0.0
    for count in byte_counts:
        if count > 0:
            probability = count / total_bytes
            entropy -= probability * math.log2(probability)

    # Shannon entropy is theoretically bounded between 0 and 8 bits per byte
    entropy = max(0.0, min(8.0, entropy))
    return round(entropy, 4)


def interpret_entropy(entropy_val: float) -> Dict[str, Any]:
    """
    Provide an Information Storage Management (ISM) interpretation of the entropy value.

    Shannon entropy measures average information density / randomness:
    - 0.0 to 3.0: Very Low entropy (high redundancy, uniform sequences; excellent compression ratio)
    - 3.0 to 6.0: Moderate entropy (structured text, code, uncompressed tabular data; solid compression ratio)
    - 6.0 to 7.5: High entropy (rich binary formats, raw media; modest compression ratio)
    - 7.5 to 8.0: Near-maximal entropy (already compressed archives, encrypted data, high-density media;
                  further compression is unlikely to yield savings and may increase file size)
    """
    if entropy_val < 4.0:
        level = "Very Low"
        compressible = "Extremely Compressible (60%–95% Savings)"
        color = "success"
        explanation = (
            f"Entropy is {entropy_val:.2f} bits/byte. Data shows massive redundancy and uniform patterns. "
            "Algorithms like 7Z, LZMA, and BZIP2 will achieve dramatic space savings, easily cutting file size in half or more."
        )
    elif entropy_val < 6.8:
        level = "Moderate"
        compressible = "Highly Compressible (40%–80% Savings)"
        color = "info"
        explanation = (
            f"Entropy is {entropy_val:.2f} bits/byte. Typical of natural text, code, structured data, and documents. "
            "High-dictionary algorithms like 7Z (LZMA2) and LZMA can substantially compress this data by 50% or more."
        )
    elif entropy_val < 7.90:
        level = "High Density"
        compressible = "Compressible via Deep Dictionary (20%–55% Savings)"
        color = "primary"
        explanation = (
            f"Entropy is {entropy_val:.2f} bits/byte. Data exhibits high byte diversity. "
            "While standard ZIP Deflate achieves modest results, 7Z (LZMA2) and LZMA with larger 64MB sliding dictionaries "
            "excel at finding long-range redundancies and reducing storage footprint significantly."
        )
    else:
        level = "Near-Maximal"
        compressible = "Pre-Compressed / Encrypted Stream"
        color = "warning"
        explanation = (
            f"Entropy is {entropy_val:.2f} bits/byte, approaching theoretical ceiling (8.0 bits/byte). "
            "Typical of pre-existing archive packages (.zip, .7z) or encrypted payloads. "
            "Further lossless compression may produce minimal savings or slight header overhead."
        )

    return {
        "entropy": entropy_val,
        "level": level,
        "compressibility": compressible,
        "badge_color": color,
        "explanation": explanation,
        "max_entropy": 8.0,
        "percentage_of_max": round((entropy_val / 8.0) * 100, 1)
    }
