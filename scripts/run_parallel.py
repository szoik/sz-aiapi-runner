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
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ProcessPoolExecutor, Future
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.table import Table
from rich.text import Text


def get_project_root() -> Path:
    """Get project root directory."""
    return Path(__file__).parent.parent.resolve()


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
    # Ensure absolute path for subprocess
    chunk_dir = chunk_dir.resolve()
    chunk_id = chunk_dir.name
    input_file = chunk_dir / "input.tsv"
    result_file = chunk_dir / "result.tsv"
    done_marker = chunk_dir / ".done"
    
    if not input_file.exists():
        return (chunk_id, False, "input.tsv not found")
    
    # Get project root for script path
    project_root = get_project_root()
    script_path = project_root / "scripts" / "weight_volume_newprompt.py"
    
    # Use project's venv python directly
    venv_dir = project_root / ".venv"
    venv_python = venv_dir / "bin" / "python"
    
    # Set up environment to activate venv
    env = os.environ.copy()
    env["VIRTUAL_ENV"] = str(venv_dir)
    env["PATH"] = f"{venv_dir}/bin:{env.get('PATH', '')}"
    env["PYTHONUNBUFFERED"] = "1"  # Disable stdout buffering
    
    # Log file for subprocess output
    log_file = chunk_dir / "run.log"
    
    try:
        with open(log_file, "w", encoding="utf-8") as log_f:
            result = subprocess.run(
                [
                    str(venv_python),
                    str(script_path),
                    "-i", str(input_file),
                    "-o", str(result_file),
                    "-p", prompt_file,
                ],
                stdout=log_f,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(project_root),
                env=env,
            )
        
        if result.returncode == 0:
            # Mark as done
            done_marker.touch()
            return (chunk_id, True, "completed")
        else:
            # Read last part of log for error message
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    error_msg = "".join(lines[-5:])[:200] if lines else "unknown error"
            except Exception:
                error_msg = "unknown error"
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


def read_chunk_progress(chunk_dir: Path) -> tuple[int, int]:
    """Read progress from chunk's progress.json file or estimate from result.tsv."""
    progress_file = chunk_dir / "progress.json"
    input_file = chunk_dir / "input.tsv"
    result_file = chunk_dir / "result.tsv"
    
    # Get total from input.tsv
    total = 0
    if input_file.exists():
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                total = sum(1 for _ in f) - 1  # minus header
        except Exception:
            pass
    
    # Try reading progress.json first
    try:
        if progress_file.exists() and progress_file.stat().st_size > 0:
            with open(progress_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Support multiple formats:
                # Format 1: {"current": N, "total": M, "status": "..."}
                # Format 2: {"processed": N, "total": M, "percentage": ...}
                # Format 3: {"last_processed_index": N, "total_processed": M}
                current = (
                    data.get("current") or 
                    data.get("processed") or 
                    data.get("total_processed", 0)
                )
                if data.get("total", 0) > 0:
                    total = data.get("total")
                return current, total
    except Exception:
        pass
    
    # Fallback: estimate progress from result.tsv line count
    current = 0
    if result_file.exists():
        try:
            with open(result_file, "r", encoding="utf-8") as f:
                current = sum(1 for _ in f) - 1  # minus header
                if current < 0:
                    current = 0
        except Exception:
            pass
    
    return current, total


def create_display(
    workers: dict[int, dict],
    overall_progress: Progress,
    overall_task_id: int,
    completed_chunks: list[str],
    failed_chunks: list[str],
    max_workers: int,
) -> Table:
    """Create the live display table."""
    # Main layout table
    layout = Table.grid(padding=(0, 0))
    layout.add_column()
    
    # Worker status table
    worker_table = Table(
        show_header=True,
        header_style="bold cyan",
        box=None,
        padding=(0, 2),
    )
    worker_table.add_column("Worker", style="dim", width=10)
    worker_table.add_column("Chunk", width=8)
    worker_table.add_column("Progress", width=28)
    worker_table.add_column("Elapsed", width=10)
    
    for worker_id in range(1, max_workers + 1):
        worker_info = workers.get(worker_id, {})
        status = worker_info.get("status", "idle")
        chunk_id = worker_info.get("chunk_id", "-")
        chunk_dir = worker_info.get("chunk_dir")
        start_time = worker_info.get("start_time")
        
        if status == "running" and start_time:
            elapsed = time.time() - start_time
            elapsed_str = f"{elapsed:.1f}s"
            
            # Read chunk progress and create bar
            if chunk_dir:
                current, total = read_chunk_progress(chunk_dir)
                if total > 0:
                    pct = int(current / total * 100)
                    bar_width = 20
                    filled = int(bar_width * current / total)
                    bar = "█" * filled + "░" * (bar_width - filled)
                    progress_str = Text()
                    progress_str.append(bar, style="yellow")
                    progress_str.append(f" {pct:3d}%", style="bold")
                else:
                    progress_str = Text("starting...", style="dim")
            else:
                progress_str = Text("-", style="dim")
        elif status == "idle":
            elapsed_str = "-"
            progress_str = Text("idle", style="dim")
        else:
            elapsed_str = "-"
            progress_str = Text("-", style="dim")
        
        worker_table.add_row(
            f"[Worker {worker_id}]",
            str(chunk_id),
            progress_str,
            elapsed_str,
        )
    
    layout.add_row(worker_table)
    layout.add_row("")
    
    # Overall progress
    layout.add_row(overall_progress)
    layout.add_row("")
    
    # Completed chunks (show last 10)
    if completed_chunks or failed_chunks:
        status_parts = []
        
        # Show recent completions
        recent_completed = completed_chunks[-15:] if len(completed_chunks) > 15 else completed_chunks
        if recent_completed:
            completed_text = " ".join([f"[green]✓{c}[/green]" for c in recent_completed])
            if len(completed_chunks) > 15:
                completed_text = f"... {completed_text}"
            status_parts.append(completed_text)
        
        # Show failures
        if failed_chunks:
            failed_text = " ".join([f"[red]✗{c}[/red]" for c in failed_chunks[-5:]])
            status_parts.append(failed_text)
        
        if status_parts:
            layout.add_row(Text.from_markup("  ".join(status_parts)))
    
    return layout


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
    console = Console()
    job_dir = get_jobs_dir() / job_id
    meta = load_job_meta(job_id)
    
    if not meta:
        console.print(f"[red]ERROR: Job not found: {job_id}[/red]")
        return 0
    
    # Check if chunks are ready
    ready_marker = job_dir / ".chunks_ready"
    if not ready_marker.exists():
        console.print("[red]ERROR: Chunks not ready (missing .chunks_ready marker)[/red]")
        return 0
    
    prompt_file = meta["prompt_file"]
    pending = get_pending_chunks(job_dir)
    completed = get_completed_chunks(job_dir)
    total_chunks = meta["chunk_count"]
    
    console.print(f"[bold]Job:[/bold] {job_id}")
    console.print(f"[bold]Prompt:[/bold] {prompt_file}")
    console.print(f"[bold]Total chunks:[/bold] {total_chunks}")
    console.print(f"[bold]Completed:[/bold] {len(completed)}")
    console.print(f"[bold]Pending:[/bold] {len(pending)}")
    console.print(f"[bold]Workers:[/bold] {max_workers}")
    console.print("-" * 60)
    
    if not pending:
        console.print("[green]All chunks completed![/green]")
        return len(completed)
    
    if dry_run:
        console.print("[yellow]Dry run - would process:[/yellow]")
        for chunk_dir in pending[:10]:
            console.print(f"  {chunk_dir.name}")
        if len(pending) > 10:
            console.print(f"  ... and {len(pending) - 10} more")
        return 0
    
    # State tracking - include already completed chunks
    workers: dict[int, dict] = {}
    completed_chunks: list[str] = [c.name for c in completed]  # Pre-fill with already done
    failed_chunks: list[str] = []
    success_count = len(completed)  # Count already completed
    fail_count = 0
    lock = threading.Lock()
    
    # Map futures to worker IDs
    future_to_worker: dict[Future, int] = {}
    future_to_chunk: dict[Future, Path] = {}
    available_workers: list[int] = list(range(1, max_workers + 1))
    
    # Overall progress bar - total includes already completed + pending
    overall_progress = Progress(
        TextColumn("[bold blue]Overall:"),
        BarColumn(bar_width=40),
        TaskProgressColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
        TextColumn("<"),
        TimeRemainingColumn(),
    )
    overall_task_id = overall_progress.add_task(
        "overall", 
        total=len(completed) + len(pending),
        completed=len(completed)  # Start with already completed count
    )
    
    def update_display() -> Table:
        return create_display(
            workers, overall_progress, overall_task_id,
            completed_chunks, failed_chunks, max_workers
        )
    
    with Live(update_display(), refresh_per_second=4, console=console) as live:
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit initial batch of tasks
            pending_iter = iter(pending)
            
            def submit_next() -> Optional[Future]:
                """Submit next chunk if workers available."""
                if not available_workers:
                    return None
                try:
                    chunk_dir = next(pending_iter)
                except StopIteration:
                    return None
                
                worker_id = available_workers.pop(0)
                future = executor.submit(run_chunk, chunk_dir, prompt_file)
                future_to_worker[future] = worker_id
                future_to_chunk[future] = chunk_dir
                
                with lock:
                    workers[worker_id] = {
                        "status": "running",
                        "chunk_id": chunk_dir.name,
                        "chunk_dir": chunk_dir,
                        "start_time": time.time(),
                    }
                
                live.update(update_display())
                return future
            
            # Submit initial batch
            active_futures: set[Future] = set()
            for _ in range(max_workers):
                f = submit_next()
                if f:
                    active_futures.add(f)
            
            # Process as futures complete
            while active_futures:
                # Check for completed futures
                done_futures = set()
                for future in active_futures:
                    if future.done():
                        done_futures.add(future)
                
                for future in done_futures:
                    active_futures.remove(future)
                    worker_id = future_to_worker[future]
                    chunk_dir = future_to_chunk[future]
                    
                    try:
                        chunk_id, success, message = future.result()
                        with lock:
                            if success:
                                success_count += 1
                                completed_chunks.append(chunk_id)
                            else:
                                fail_count += 1
                                failed_chunks.append(chunk_id)
                            
                            workers[worker_id] = {"status": "idle", "chunk_id": "-"}
                    except Exception as e:
                        with lock:
                            fail_count += 1
                            failed_chunks.append(chunk_dir.name)
                            workers[worker_id] = {"status": "idle", "chunk_id": "-"}
                    
                    # Free worker
                    available_workers.append(worker_id)
                    overall_progress.update(overall_task_id, advance=1)
                    
                    # Submit next task
                    f = submit_next()
                    if f:
                        active_futures.add(f)
                    
                    live.update(update_display())
                
                if active_futures and not done_futures:
                    time.sleep(0.1)
                    live.update(update_display())
    
    console.print("-" * 60)
    console.print(f"[green]Completed: {success_count}[/green], [red]Failed: {fail_count}[/red]")
    
    # Check if all done
    remaining = get_pending_chunks(job_dir)
    if not remaining:
        console.print("[bold green]All chunks completed![/bold green]")
        console.print()
        console.print("To merge results:")
        console.print(f"  python scripts/run_parallel.py {job_id} --merge")
    
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
