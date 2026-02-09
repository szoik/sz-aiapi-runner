#!/usr/bin/env python3
"""
Split dataset into chunks for parallel processing.

Creates:
- Job directory (artifacts/runs/{job_id}/):
  - meta.json: Job metadata (input file, prompt, chunk info)
- Temp directory (/tmp/sz-parallel-jobs/{job_id}/):
  - chunks/NNNN/input.tsv: Chunked input files
  - .chunks_ready: Marker file

Job ID format:
    vw-{serial}-{prompt_version}-{dataset_name}
    e.g., vw-001-v002-datasource_complete

With --name option:
    {name}-{serial}-{prompt_version}-{dataset_name}
    e.g., baseline-001-v002-datasource_complete (replaces vw- prefix)

Usage:
    # Basic usage
    python scripts/split_dataset.py \
        -i inputs/datasource_complete.tsv \
        -p volume-weight.v002.system.txt

    # With experiment name
    python scripts/split_dataset.py \
        -i inputs/datasource_complete.tsv \
        -p volume-weight.v002.system.txt \
        -n baseline

    # Custom chunk size
    python scripts/split_dataset.py \
        -i inputs/datasource_complete.tsv \
        -p volume-weight.v002.system.txt \
        --chunk-size 200
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path


# Temp directory for chunks
TMP_BASE = Path(tempfile.gettempdir()) / "sz-parallel-jobs"


def get_project_root() -> Path:
    """Get project root directory."""
    return Path(__file__).parent.parent


def get_runs_dir() -> Path:
    """Get runs directory."""
    return get_project_root() / "artifacts" / "runs"


def get_tmp_job_dir(job_id: str) -> Path:
    """Get temp directory for job chunks."""
    return TMP_BASE / job_id


def get_next_serial(runs_dir: Path) -> int:
    """Get next serial number by scanning existing job directories."""
    if not runs_dir.exists():
        return 1
    
    max_serial = 0
    # Pattern: optional name prefix (vw- or custom), then 3-digit serial
    # e.g., "vw-001-v002-dataset" or "baseline-001-v002-dataset"
    pattern = re.compile(r"(?:[\w]+-)?(\d{3})-v\d{3}-")
    
    for item in runs_dir.iterdir():
        if item.is_dir():
            match = pattern.match(item.name)
            if match:
                serial = int(match.group(1))
                max_serial = max(max_serial, serial)
    
    return max_serial + 1


def extract_prompt_version(prompt_file: str) -> str:
    """Extract version from prompt filename.
    
    e.g., "volume-weight.v002.system.txt" -> "v002"
    """
    match = re.search(r"\.(v\d{3})\.", prompt_file)
    if match:
        return match.group(1)
    
    # Fallback for old format (v2, v3, etc.)
    match = re.search(r"\.v(\d+)\.", prompt_file)
    if match:
        return f"v{int(match.group(1)):03d}"
    
    return "v000"


def extract_dataset_name(input_file: Path) -> str:
    """Extract dataset name from input file path.
    
    e.g., "inputs/datasource_complete.tsv" -> "datasource_complete"
    """
    return input_file.stem


def generate_job_id(
    runs_dir: Path,
    prompt_file: str,
    input_file: Path,
    name: str | None = None,
) -> str:
    """Generate job ID based on naming convention."""
    serial = get_next_serial(runs_dir)
    version = extract_prompt_version(prompt_file)
    dataset = extract_dataset_name(input_file)
    
    if name:
        return f"{name}-{serial:03d}-{version}-{dataset}"
    else:
        return f"vw-{serial:03d}-{version}-{dataset}"


def count_records(input_file: Path) -> int:
    """Count records in TSV file (excluding header)."""
    with open(input_file, "r", encoding="utf-8") as f:
        return sum(1 for _ in f) - 1  # subtract header


def split_dataset(
    input_file: Path,
    output_dir: Path,
    prompt_file: str,
    chunk_size: int = 100,
    name: str | None = None,
) -> dict:
    """
    Split TSV into chunks and create job metadata.
    
    Returns:
        dict with job info
    """
    # Count total records
    total_records = count_records(input_file)
    chunk_count = (total_records + chunk_size - 1) // chunk_size
    
    print(f"Input: {input_file}")
    print(f"Total records: {total_records:,}")
    print(f"Chunk size: {chunk_size}")
    print(f"Chunks to create: {chunk_count}")
    print("-" * 60)
    
    # Generate job ID
    job_id = generate_job_id(output_dir, prompt_file, input_file, name)
    job_dir = output_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    
    # Create temp directory for chunks
    tmp_job_dir = get_tmp_job_dir(job_id)
    chunks_dir = tmp_job_dir / "chunks"
    
    # Create all chunk directories first
    for i in range(1, chunk_count + 1):
        chunk_dir = chunks_dir / f"{i:04d}"
        chunk_dir.mkdir(parents=True, exist_ok=True)
    
    # Read and split input file
    with open(input_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        fieldnames = reader.fieldnames
        
        chunk_num = 1
        chunk_rows = []
        
        for row in reader:
            chunk_rows.append(row)
            
            if len(chunk_rows) >= chunk_size:
                # Write chunk
                chunk_dir = chunks_dir / f"{chunk_num:04d}"
                chunk_file = chunk_dir / "input.tsv"
                
                with open(chunk_file, "w", encoding="utf-8", newline="") as cf:
                    writer = csv.DictWriter(cf, fieldnames=fieldnames, delimiter="\t")
                    writer.writeheader()
                    writer.writerows(chunk_rows)
                
                print(f"  Chunk {chunk_num:04d}: {len(chunk_rows)} records")
                chunk_num += 1
                chunk_rows = []
        
        # Write remaining rows
        if chunk_rows:
            chunk_dir = chunks_dir / f"{chunk_num:04d}"
            chunk_file = chunk_dir / "input.tsv"
            
            with open(chunk_file, "w", encoding="utf-8", newline="") as cf:
                writer = csv.DictWriter(cf, fieldnames=fieldnames, delimiter="\t")
                writer.writeheader()
                writer.writerows(chunk_rows)
            
            print(f"  Chunk {chunk_num:04d}: {len(chunk_rows)} records")
    
    # Create metadata
    meta = {
        "job_id": job_id,
        "created_at": datetime.now().isoformat(),
        "input_file": str(input_file.absolute()),
        "prompt_file": prompt_file,
        "total_records": total_records,
        "chunk_size": chunk_size,
        "chunk_count": chunk_count,
        "status": "ready",
        "tmp_dir": str(tmp_job_dir),
    }
    
    if name:
        meta["name"] = name
    
    meta_file = job_dir / "meta.json"
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    
    # Mark chunks as ready (in tmp dir)
    ready_marker = tmp_job_dir / ".chunks_ready"
    ready_marker.touch()
    
    print("-" * 60)
    print(f"Job created: {job_id}")
    print(f"Job directory: {job_dir}")
    print(f"Chunks directory: {chunks_dir}")
    print(f"Metadata: {meta_file}")
    
    return meta


def main():
    parser = argparse.ArgumentParser(
        description="Split dataset into chunks for parallel processing"
    )
    parser.add_argument(
        "-i", "--input", required=True,
        help="Input TSV file"
    )
    parser.add_argument(
        "-p", "--prompt", required=True,
        help="Prompt template filename (e.g., volume-weight.v002.system.txt)"
    )
    parser.add_argument(
        "-n", "--name",
        help="Experiment name prefix (e.g., baseline, tuning)"
    )
    parser.add_argument(
        "--chunk-size", type=int, default=100,
        help="Records per chunk (default: 100)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output directory (default: artifacts/runs)"
    )
    
    args = parser.parse_args()
    
    input_file = Path(args.input)
    if not input_file.exists():
        print(f"ERROR: Input file not found: {input_file}")
        sys.exit(1)
    
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = get_runs_dir()
    
    meta = split_dataset(
        input_file=input_file,
        output_dir=output_dir,
        prompt_file=args.prompt,
        chunk_size=args.chunk_size,
        name=args.name,
    )
    
    print()
    print("Next step:")
    print(f"  uv run python scripts/run_parallel.py {meta['job_id']}")


if __name__ == "__main__":
    main()
