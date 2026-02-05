#!/usr/bin/env python3
"""
Split TSV dataset into chunks for parallel processing.

Creates job directory structure compatible with run_parallel.py:
    .local/parallel_jobs/{job_id}/
        meta.json           - Job metadata
        .chunks_ready       - Marker that splitting is complete
        chunks/
            0001/input.tsv  - Chunk 1
            0002/input.tsv  - Chunk 2
            ...

Usage:
    python scripts/split_for_parallel.py -i inputs/datasource_complete.tsv -p weight-volume.v2.system.txt
    python scripts/split_for_parallel.py -i inputs/datasource_complete.tsv -p weight-volume.v2.system.txt --chunk-size 50
"""

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path


def get_project_root() -> Path:
    """Get project root directory."""
    return Path(__file__).parent.parent


def get_jobs_dir() -> Path:
    """Get parallel jobs directory."""
    return get_project_root() / ".local" / "parallel_jobs"


def count_records(tsv_path: Path) -> int:
    """Count records in TSV file (excluding header)."""
    with open(tsv_path, "r", encoding="utf-8") as f:
        return sum(1 for _ in f) - 1  # Subtract header


def split_dataset(
    input_file: Path,
    prompt_file: str,
    chunk_size: int = 100,
) -> str:
    """
    Split dataset into chunks for parallel processing.
    
    Returns:
        Job ID
    """
    # Generate job ID
    job_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    job_dir = get_jobs_dir() / job_id
    chunks_dir = job_dir / "chunks"
    
    # Create directories
    job_dir.mkdir(parents=True, exist_ok=True)
    chunks_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Job ID: {job_id}")
    print(f"Input: {input_file}")
    print(f"Prompt: {prompt_file}")
    print(f"Chunk size: {chunk_size}")
    print("-" * 60)
    
    # Read input TSV
    with open(input_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        fieldnames = reader.fieldnames
        rows = list(reader)
    
    total_records = len(rows)
    print(f"Total records: {total_records}")
    
    # Calculate number of chunks
    num_chunks = (total_records + chunk_size - 1) // chunk_size
    print(f"Number of chunks: {num_chunks}")
    
    # Split into chunks
    for i in range(num_chunks):
        chunk_id = f"{i + 1:04d}"
        chunk_dir = chunks_dir / chunk_id
        chunk_dir.mkdir(parents=True, exist_ok=True)
        
        start_idx = i * chunk_size
        end_idx = min((i + 1) * chunk_size, total_records)
        chunk_rows = rows[start_idx:end_idx]
        
        # Write chunk TSV
        chunk_file = chunk_dir / "input.tsv"
        with open(chunk_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
            writer.writeheader()
            writer.writerows(chunk_rows)
        
        print(f"  Chunk {chunk_id}: {len(chunk_rows)} records")
    
    # Write metadata
    meta = {
        "job_id": job_id,
        "input_file": str(input_file),
        "prompt_file": prompt_file,
        "total_records": total_records,
        "chunk_size": chunk_size,
        "chunk_count": num_chunks,
        "created_at": datetime.now().isoformat(),
    }
    
    meta_file = job_dir / "meta.json"
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    
    # Mark chunks as ready
    ready_marker = job_dir / ".chunks_ready"
    ready_marker.touch()
    
    print("-" * 60)
    print(f"Job created: {job_id}")
    print(f"Job directory: {job_dir}")
    print()
    print("To run:")
    print(f"  python scripts/run_parallel.py {job_id} --workers 5")
    
    return job_id


def main():
    parser = argparse.ArgumentParser(
        description="Split TSV dataset into chunks for parallel processing"
    )
    parser.add_argument(
        "-i", "--input", required=True,
        help="Input TSV file path"
    )
    parser.add_argument(
        "-p", "--prompt", required=True,
        help="Prompt file name (in prompts/ directory)"
    )
    parser.add_argument(
        "--chunk-size", type=int, default=100,
        help="Number of records per chunk (default: 100)"
    )
    
    args = parser.parse_args()
    
    input_file = Path(args.input)
    if not input_file.exists():
        print(f"ERROR: Input file not found: {input_file}")
        return 1
    
    job_id = split_dataset(
        input_file=input_file,
        prompt_file=args.prompt,
        chunk_size=args.chunk_size,
    )
    
    return 0


if __name__ == "__main__":
    exit(main())
