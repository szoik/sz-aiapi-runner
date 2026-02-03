#!/usr/bin/env python3
"""
Run parallel estimation on chunked dataset.

Executes weight_volume_newprompt.py on each chunk in parallel.
Tracks completion via .done marker files in each chunk directory.

Usage:
    # Run with default workers (5)
    python scripts/run_parallel.py 20260203-171500

    # Custom number of workers
    python scripts/run_parallel.py 20260203-171500 --workers 8

    # Dry run (show what would be executed)
    python scripts/run_parallel.py 20260203-171500 --dry-run

    # Merge results after completion
    python scripts/run_parallel.py 20260203-171500 --merge
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Optional


def get_project_root() -> Path:
    """Get project root directory."""
    return Path(__file__).parent.parent


def get_jobs_dir() -> Path:
    """Get parallel jobs directory."""
    return get_project_root() / ".local" / "parallel_jobs"


def load_job_meta(job_id: str) -> Optional[dict]:
    """Load job metadata."""
    job_dir = get_jobs_dir() / job_id
    meta_file = job_dir / "meta.json"
    
    if not meta_file.exists():
        return None
    
    with open(meta_file, "r", encoding="utf-8") as f:
        return json.load(f)


def get_pending_chunks(job_dir: Path) -> list[Path]:
    """Get list of chunks that haven't completed yet."""
    chunks_dir = job_dir / "chunks"
    pending = []
    
    for chunk_dir in sorted(chunks_dir.iterdir()):
        if not chunk_dir.is_dir():
            continue
        
        done_marker = chunk_dir / ".done"
        if not done_marker.exists():
            pending.append(chunk_dir)
    
    return pending


def get_completed_chunks(job_dir: Path) -> list[Path]:
    """Get list of completed chunks."""
    chunks_dir = job_dir / "chunks"
    completed = []
    
    for chunk_dir in sorted(chunks_dir.iterdir()):
        if not chunk_dir.is_dir():
            continue
        
        done_marker = chunk_dir / ".done"
        if done_marker.exists():
            completed.append(chunk_dir)
    
    return completed


def run_chunk(chunk_dir: Path, prompt_file: str) -> tuple[str, bool, str]:
    """
    Run estimation on a single chunk.
    
    Returns:
        (chunk_id, success, message)
    """
    chunk_id = chunk_dir.name
    input_file = chunk_dir / "input.tsv"
    result_file = chunk_dir / "result.tsv"
    done_marker = chunk_dir / ".done"
    
    if not input_file.exists():
        return (chunk_id, False, "input.tsv not found")
    
    # Get project root for script path
    project_root = get_project_root()
    script_path = project_root / "scripts" / "weight_volume_newprompt.py"
    
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                "-i", str(input_file),
                "-o", str(result_file),
                "-p", prompt_file,
            ],
            capture_output=True,
            text=True,
            cwd=str(project_root),
        )
        
        if result.returncode == 0:
            # Mark as done
            done_marker.touch()
            return (chunk_id, True, "completed")
        else:
            error_msg = result.stderr[:200] if result.stderr else "unknown error"
            return (chunk_id, False, f"exit code {result.returncode}: {error_msg}")
    
    except Exception as e:
        return (chunk_id, False, str(e))


def merge_results(job_dir: Path) -> Optional[Path]:
    """Merge all chunk results into final result file."""
    chunks_dir = job_dir / "chunks"
    completed = get_completed_chunks(job_dir)
    
    if not completed:
        print("No completed chunks to merge")
        return None
    
    # Output file
    output_file = job_dir / "final_result.tsv"
    
    # Get fieldnames from first result
    first_result = completed[0] / "result.tsv"
    if not first_result.exists():
        print(f"Result file not found: {first_result}")
        return None
    
    with open(first_result, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        fieldnames = reader.fieldnames
    
    # Merge all results
    total_rows = 0
    with open(output_file, "w", encoding="utf-8", newline="") as out_f:
        writer = csv.DictWriter(out_f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        
        for chunk_dir in completed:
            result_file = chunk_dir / "result.tsv"
            if not result_file.exists():
                print(f"  Warning: {chunk_dir.name}/result.tsv not found, skipping")
                continue
            
            with open(result_file, "r", encoding="utf-8") as in_f:
                reader = csv.DictReader(in_f, delimiter="\t")
                for row in reader:
                    writer.writerow(row)
                    total_rows += 1
    
    print(f"Merged {len(completed)} chunks, {total_rows:,} records")
    print(f"Output: {output_file}")
    
    return output_file


def run_parallel(
    job_id: str,
    max_workers: int = 5,
    dry_run: bool = False,
) -> int:
    """
    Run parallel estimation on job.
    
    Returns:
        Number of successfully completed chunks
    """
    job_dir = get_jobs_dir() / job_id
    meta = load_job_meta(job_id)
    
    if not meta:
        print(f"ERROR: Job not found: {job_id}")
        return 0
    
    # Check if chunks are ready
    ready_marker = job_dir / ".chunks_ready"
    if not ready_marker.exists():
        print(f"ERROR: Chunks not ready (missing .chunks_ready marker)")
        return 0
    
    prompt_file = meta["prompt_file"]
    pending = get_pending_chunks(job_dir)
    completed = get_completed_chunks(job_dir)
    total_chunks = meta["chunk_count"]
    
    print(f"Job: {job_id}")
    print(f"Prompt: {prompt_file}")
    print(f"Total chunks: {total_chunks}")
    print(f"Completed: {len(completed)}")
    print(f"Pending: {len(pending)}")
    print(f"Workers: {max_workers}")
    print("-" * 60)
    
    if not pending:
        print("All chunks completed!")
        return len(completed)
    
    if dry_run:
        print("Dry run - would process:")
        for chunk_dir in pending[:10]:
            print(f"  {chunk_dir.name}")
        if len(pending) > 10:
            print(f"  ... and {len(pending) - 10} more")
        return 0
    
    # Run in parallel
    success_count = 0
    fail_count = 0
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(run_chunk, chunk_dir, prompt_file): chunk_dir
            for chunk_dir in pending
        }
        
        for future in as_completed(futures):
            chunk_dir = futures[future]
            try:
                chunk_id, success, message = future.result()
                if success:
                    success_count += 1
                    print(f"✓ Chunk {chunk_id}: {message}")
                else:
                    fail_count += 1
                    print(f"✗ Chunk {chunk_id}: {message}")
            except Exception as e:
                fail_count += 1
                print(f"✗ Chunk {chunk_dir.name}: {e}")
    
    print("-" * 60)
    print(f"Completed: {success_count}, Failed: {fail_count}")
    
    # Check if all done
    remaining = get_pending_chunks(job_dir)
    if not remaining:
        print("All chunks completed!")
        print()
        print("To merge results:")
        print(f"  python scripts/run_parallel.py {job_id} --merge")
    
    return success_count


def main():
    parser = argparse.ArgumentParser(
        description="Run parallel estimation on chunked dataset"
    )
    parser.add_argument(
        "job_id",
        help="Job ID (from split_dataset.py output)"
    )
    parser.add_argument(
        "--workers", type=int, default=5,
        help="Number of parallel workers (default: 5)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be executed without running"
    )
    parser.add_argument(
        "--merge", action="store_true",
        help="Merge completed chunk results into final file"
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Show job status without running"
    )
    
    args = parser.parse_args()
    
    job_dir = get_jobs_dir() / args.job_id
    
    if args.status:
        meta = load_job_meta(args.job_id)
        if not meta:
            print(f"Job not found: {args.job_id}")
            sys.exit(1)
        
        pending = get_pending_chunks(job_dir)
        completed = get_completed_chunks(job_dir)
        
        print(f"Job: {args.job_id}")
        print(f"Input: {meta['input_file']}")
        print(f"Prompt: {meta['prompt_file']}")
        print(f"Total records: {meta['total_records']:,}")
        print(f"Chunk size: {meta['chunk_size']}")
        print(f"Total chunks: {meta['chunk_count']}")
        print(f"Completed: {len(completed)}")
        print(f"Pending: {len(pending)}")
        
        if pending:
            print(f"\nPending chunks: {', '.join(c.name for c in pending[:10])}")
            if len(pending) > 10:
                print(f"  ... and {len(pending) - 10} more")
        
        sys.exit(0)
    
    if args.merge:
        output = merge_results(job_dir)
        sys.exit(0 if output else 1)
    
    success = run_parallel(
        job_id=args.job_id,
        max_workers=args.workers,
        dry_run=args.dry_run,
    )
    
    sys.exit(0 if success > 0 else 1)


if __name__ == "__main__":
    main()
