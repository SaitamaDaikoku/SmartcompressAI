import os
import random
import string
import sys
import tempfile
import time
from pathlib import Path
from typing import List, Dict, Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from config import Config
from utils.analyzer import analyze_file
from engines.compression_engine import compress_file, ALL_ALGORITHMS


def generate_synthetic_samples(temp_dir: Path) -> List[Dict[str, Any]]:
    """
    Generate representative sample files covering diverse entropy levels, sizes, and formats.
    """
    samples = []
    
    # 1. Very Low Entropy Files (Repetitive text, zeros, uniform patterns)
    # 1a. Highly repetitive log file
    p1 = temp_dir / "server_access.log"
    p1.write_text("[2026-10-09 00:00:01] GET /api/v1/health HTTP/1.1 200 OK 0.002s\n" * 2000, encoding="utf-8")
    samples.append({"path": p1, "category": "Text / Document", "ext": ".log"})

    # 1b. Zero-padded binary data
    p2 = temp_dir / "sparse_memory.bin"
    p2.write_bytes(b"\x00" * (128 * 1024) + b"\x01\x02\x03\x04" * 1024 + b"\x00" * (128 * 1024))
    samples.append({"path": p2, "category": "Binary / Executable", "ext": ".bin"})

    # 1c. Simple repeating sequence text
    p3 = temp_dir / "dna_repeats.txt"
    p3.write_text("ATCGATCGATCGATCGATCGATCG" * 5000, encoding="utf-8")
    samples.append({"path": p3, "category": "Text / Document", "ext": ".txt"})

    # 2. Moderate Entropy Files (Natural language, source code, structured data)
    # 2a. Python source code
    p4 = temp_dir / "algorithm_simulation.py"
    code_body = """
import math
import collections

class CompressionSimulator:
    def __init__(self, buffer_size=1024):
        self.buffer_size = buffer_size
        self.history = collections.deque(maxlen=buffer_size)

    def process_stream(self, data_stream):
        tokens = []
        for symbol in data_stream:
            if symbol in self.history:
                tokens.append((self.history.index(symbol), len(symbol)))
            else:
                self.history.append(symbol)
                tokens.append((0, symbol))
        return tokens

def main():
    sim = CompressionSimulator(4096)
    for epoch in range(100):
        sim.process_stream([f"symbol_{i%50}" for i in range(200)])
"""
    p4.write_text(code_body * 80, encoding="utf-8")
    samples.append({"path": p4, "category": "Structured Data / Code", "ext": ".py"})

    # 2b. JSON dataset
    p5 = temp_dir / "user_records.json"
    json_lines = ['{"user_id": ' + str(i) + ', "name": "User_' + str(i) + '", "role": "admin", "active": true, "score": ' + str(i * 1.5) + '}' for i in range(1500)]
    p5.write_text("[\n" + ",\n".join(json_lines) + "\n]", encoding="utf-8")
    samples.append({"path": p5, "category": "Structured Data / Code", "ext": ".json"})

    # 2c. CSV Table data
    p6 = temp_dir / "sensor_telemetry.csv"
    csv_rows = ["timestamp,sensor_id,temperature,humidity,status"]
    for i in range(3000):
        csv_rows.append(f"2026-10-09T12:{i%60:02d}:00,SEN_{i%10:03d},{20.5 + (i%15)*0.2:.2f},{45.0 + (i%20)*0.5:.2f},NORMAL")
    p6.write_text("\n".join(csv_rows), encoding="utf-8")
    samples.append({"path": p6, "category": "Structured Data / Code", "ext": ".csv"})

    # 2d. Markdown prose document
    p7 = temp_dir / "ism_lecture_notes.md"
    prose = """
# Information Storage and Management: Lecture on Data Compression
Data compression reduces the number of bits required to represent data. Storage systems benefit 
from data reduction by minimizing raw storage costs, network transmission delays, and backup windows.
Lossless compression guarantees exact bit-for-bit reconstruction of original data upon decompression.
Shannon entropy defines the theoretical limit of lossless data compression.
When entropy is high, compression algorithms encounter fewer repeating patterns in their dictionary windows.
""" * 120
    p7.write_text(prose, encoding="utf-8")
    samples.append({"path": p7, "category": "Text / Document", "ext": ".md"})

    # 2e. HTML web page
    p8 = temp_dir / "landing_page.html"
    html_sample = """<!DOCTYPE html><html><head><title>ISM Compression</title></head><body>
<div class="container"><header><h1>Smart Storage Systems</h1></header><main><p>Storage optimization.</p></main></div>
</body></html>\n""" * 200
    p8.write_text(html_sample, encoding="utf-8")
    samples.append({"path": p8, "category": "Structured Data / Code", "ext": ".html"})

    # 2f. SQL Dump
    p9 = temp_dir / "database_backup.sql"
    sql_sample = """INSERT INTO telemetry (device_id, metric, val, recorded_at) VALUES ('DEV001', 'voltage', 3.32, CURRENT_TIMESTAMP);\n""" * 2500
    p9.write_text(sql_sample, encoding="utf-8")
    samples.append({"path": p9, "category": "Structured Data / Code", "ext": ".sql"})

    # 3. High Entropy Files (Simulating binary files, compiled machine code)
    # 3a. Simulated executable binary with mixed patterns and instructions
    p10 = temp_dir / "compiled_binary.exe"
    rand_part = os.urandom(64 * 1024)
    code_part = (b"\x55\x89\xe5\x83\xec\x10\x8b\x45\x08" * 500)
    p10.write_bytes(code_part + rand_part + code_part)
    samples.append({"path": p10, "category": "Binary / Executable", "ext": ".exe"})

    # 3b. Mixed binary stream
    p11 = temp_dir = temp_dir / "firmware.bin"
    p11.write_bytes((os.urandom(256) * 100) + (b"\xFF\xFE\x00\x01" * 2000))
    samples.append({"path": p11, "category": "Binary / Executable", "ext": ".bin"})

    # 4. Near-Maximal Entropy Files (Random byte stream / encrypted / pre-compressed)
    # 4a. Pure random byte file (Entropy ~ 7.99)
    p12 = temp_dir.parent / "encrypted_payload.dat"
    p12.write_bytes(os.urandom(128 * 1024))
    samples.append({"path": p12, "category": "Archive / Compressed", "ext": ".dat"})

    # 4b. Pseudo-compressed container
    p13 = temp_dir.parent / "compressed_archive.zip"
    p13.write_bytes(b"PK\x03\x04" + os.urandom(80 * 1024))
    samples.append({"path": p13, "category": "Archive / Compressed", "ext": ".zip"})

    # 5. Scaled variations (Different file sizes to teach size sensitivity)
    # 5a. Small text snippet (1.5 KB)
    p14 = temp_dir.parent / "readme_snippet.txt"
    p14.write_text("SmartCompress AI - Information Storage Management Project\n" * 25, encoding="utf-8")
    samples.append({"path": p14, "category": "Text / Document", "ext": ".txt"})

    # 5b. Large repetitive log (3 MB)
    p15 = temp_dir.parent / "large_system_trace.log"
    p15.write_text(("TRACE [worker-node-1] Event ID 4022 status SUCCESS response_time=12ms\n" * 15000), encoding="utf-8")
    samples.append({"path": p15, "category": "Text / Document", "ext": ".log"})

    # 5c. Large source file
    p16 = temp_dir.parent / "monolithic_module.js"
    js_code = """function calculateTax(subtotal, rate) { return subtotal * rate; }\n""" * 8000
    p16.write_text(js_code, encoding="utf-8")
    samples.append({"path": p16, "category": "Structured Data / Code", "ext": ".js"})

    # 5d. Large CSV dataset (2.5 MB)
    p17 = temp_dir.parent / "financial_ledger.csv"
    ledger = ["txn_id,account,amount,type,status"]
    for i in range(20000):
        ledger.append(f"TXN_{i:06d},ACC_{i%50:03d},{100 + (i%500)}.{i%99:02d},CREDIT,CLEARED")
    p17.write_text("\n".join(ledger), encoding="utf-8")
    samples.append({"path": p17, "category": "Structured Data / Code", "ext": ".csv"})

    return samples


def determine_best_algorithm(
    measured_runs: Dict[str, Dict[str, Any]],
    preference: str,
    original_size: int,
    entropy: float
) -> str:
    """
    Explicit mathematical objective function to determine the optimal algorithm
    based on measured experimental results and user preference.

    Criteria:
    - max_compression: Highest space saving percentage (smallest compressed size).
      Ties broken by shorter duration.
    - fastest: Lowest compression duration among runs that achieved valid compression
      (or minimum duration if entropy >= 7.6).
    - balanced: Maximizes multi-objective score:
        Score = space_saving_pct - (duration_weight * duration_seconds)
    """
    # If file is true near-maximal ceiling entropy (>= 7.95), further compression cannot reduce size
    if entropy >= 7.95:
        if preference == "fastest":
            return "GZIP"
        return "ZIP"

    if preference == "max_compression":
        # Strictly best space saving %
        best_algo = max(
            measured_runs.keys(),
            key=lambda a: (measured_runs[a]["space_saving_pct"], -measured_runs[a]["duration"])
        )
        return best_algo

    elif preference == "fastest":
        # Lowest duration that doesn't severely sacrifice savings
        # Filter for positive savings if any algorithm produced positive savings
        positive_savings = [a for a in measured_runs if measured_runs[a]["space_saving_pct"] > 5.0]
        pool = positive_savings if positive_savings else list(measured_runs.keys())
        best_algo = min(pool, key=lambda a: measured_runs[a]["duration"])
        return best_algo

    else:  # balanced
        # Objective score function: balance space savings with time penalty
        # Time penalty scales with original size
        time_penalty_factor = 10.0 if original_size < 100 * 1024 else 2.5
        scores = {}
        for algo, data in measured_runs.items():
            savings = data["space_saving_pct"]
            duration = data["duration"]
            # Score formula
            score = savings - (time_penalty_factor * duration)
            # Give slight preference bonus to universal ZIP for small files if savings are nearly equal
            if algo == "ZIP" and original_size < 100 * 1024:
                score += 3.0
            scores[algo] = score

        best_algo = max(scores.keys(), key=lambda a: scores[a])
        return best_algo


def generate_dataset(output_csv: Path = Config.DATASET_PATH) -> pd.DataFrame:
    """
    Run empirical compression experiments on representative sample files,
    measure real performance, and compile the training dataset CSV.
    """
    print(f"[Dataset Generation] Initializing experimental benchmark pipeline...")
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        samples = generate_synthetic_samples(temp_dir)
        print(f"[Dataset Generation] Generated {len(samples)} representative sample files.")

        records = []
        raw_runs = []

        for idx, sample in enumerate(samples, 1):
            path = sample["path"]
            analysis = analyze_file(path)
            orig_size = analysis["size_bytes"]
            entropy = analysis["entropy"]
            category = analysis["category"]
            ext = analysis["extension"]

            # Run all 5 algorithms on this sample
            measured_runs = {}
            for algo in ALL_ALGORITHMS:
                comp_res = compress_file(
                    input_path=path,
                    algorithm=algo,
                    output_dir=temp_dir / "compressed_output",
                    original_filename=path.name
                )
                if comp_res["success"]:
                    measured_runs[algo] = {
                        "compressed_size": comp_res["compressed_size"],
                        "space_saving_pct": comp_res["space_saving_pct"],
                        "duration": comp_res["compression_duration"],
                        "bytes_saved": comp_res["bytes_saved"]
                    }
                    raw_runs.append({
                        "file_name": path.name,
                        "file_size": orig_size,
                        "entropy": entropy,
                        "category": category,
                        "extension": ext,
                        "algorithm": algo,
                        "compressed_size": comp_res["compressed_size"],
                        "space_saving_pct": comp_res["space_saving_pct"],
                        "duration": comp_res["compression_duration"]
                    })

            # For each of the 3 user preferences, determine best algorithm based on experimental measurements
            for pref in ["balanced", "max_compression", "fastest"]:
                best_algo = determine_best_algorithm(measured_runs, pref, orig_size, entropy)
                best_metrics = measured_runs.get(best_algo, {"space_saving_pct": 0.0, "duration": 0.0})

                records.append({
                    "sample_name": path.name,
                    "file_size": orig_size,
                    "file_size_kb": round(orig_size / 1024, 2),
                    "entropy": entropy,
                    "category": category,
                    "extension": ext,
                    "preference": pref,
                    "best_algorithm": best_algo,
                    "measured_saving_pct": best_metrics["space_saving_pct"],
                    "measured_duration": best_metrics["duration"]
                })

        df = pd.DataFrame(records)
        df.to_csv(output_csv, index=False)
        print(f"[Dataset Generation] Successfully generated measured dataset with {len(df)} records at: {output_csv}")

        # Also save raw benchmark runs for scientific transparency
        raw_df = pd.DataFrame(raw_runs)
        raw_csv = output_csv.parent / "raw_benchmark_measurements.csv"
        raw_df.to_csv(raw_csv, index=False)
        print(f"[Dataset Generation] Raw experimental measurements stored at: {raw_csv}")

        return df


if __name__ == "__main__":
    generate_dataset()
