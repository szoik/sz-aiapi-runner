#!/usr/bin/env python3
"""
New Prompt Estimation Script

Run weight/volume estimation with a new prompt and save results to TSV.
This script only calls API and saves results - no comparison logic.

Output directory structure:
    .local/prompt_results/{prompt_name}/{timestamp}-{input_name}/
        - result.tsv

Usage:
    # Run on full dataset
    uv run python scripts/weight_volume_newprompt.py \
        -i inputs/datasource.tsv \
        -p weight-volume.v2.system.txt

    # Run on category subset
    uv run python scripts/weight_volume_newprompt.py \
        -i .local/tmp/category_datasets/로봇완구.tsv \
        -p weight-volume.v2.system.txt

    # With limit (for testing)
    uv run python scripts/weight_volume_newprompt.py \
        -i inputs/datasource.tsv \
        -p weight-volume.v2.system.txt \
        -l 10

    # Custom output path
    uv run python scripts/weight_volume_newprompt.py \
        -i inputs/datasource.tsv \
        -p weight-volume.v2.system.txt \
        -o custom/path/result.tsv

    # Skip first N rows (start from row N+1)
    uv run python scripts/weight_volume_newprompt.py \
        -i inputs/datasource.tsv \
        -p weight-volume.v2.system.txt \
        --offset 100

    # Resume from existing result file (auto-detect last processed row)
    uv run python scripts/weight_volume_newprompt.py \
        -i inputs/datasource.tsv \
        -p weight-volume.v2.system.txt \
        -o .local/prompt_results/.../result.tsv \
        --resume
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from common import (
    get_openai_client,
    get_project_root,
    load_prompt_template,
    build_user_content,
    call_openai_json,
)


def generate_output_path(
    prompt_file: str,
    input_file: str,
) -> Path:
    """Generate output directory path based on prompt and input file name."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    prompt_name = Path(prompt_file).stem  # e.g., "weight-volume.v2.system"
    input_name = Path(input_file).stem    # e.g., "datasource" or "로봇완구"
    
    base = get_project_root() / ".local" / "prompt_results" / prompt_name
    output_dir = base / f"{timestamp}-{input_name}"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / "result.tsv"


def count_existing_results(output_file: str) -> int:
    """Count how many rows already exist in result file (for resume)."""
    output_path = Path(output_file)
    if not output_path.exists():
        return 0
    
    with open(output_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        # Skip header
        next(reader, None)
        count = sum(1 for _ in reader)
    
    return count


def get_processed_order_ids(output_file: str) -> set:
    """Get set of order_ids already processed (for more reliable resume).
    
    Handles corrupted/incomplete TSV files gracefully by:
    - Skipping malformed lines
    - Handling incomplete last line from interrupted writes
    """
    output_path = Path(output_file)
    if not output_path.exists():
        return set()
    
    order_ids = set()
    
    # Read file and handle potential corruption
    try:
        with open(output_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Warning: Could not read result file: {e}", file=sys.stderr)
        return set()
    
    if not lines:
        return set()
    
    # Parse header
    header_line = lines[0].strip()
    if not header_line:
        return set()
    
    fieldnames = header_line.split("\t")
    try:
        order_id_idx = fieldnames.index("order_id")
    except ValueError:
        print("Warning: 'order_id' column not found in result file", file=sys.stderr)
        return set()
    
    expected_field_count = len(fieldnames)
    
    # Parse data rows, skipping malformed ones
    for line_num, line in enumerate(lines[1:], start=2):
        line = line.strip()
        if not line:
            continue
        
        fields = line.split("\t")
        
        # Skip incomplete lines (must have all columns to be considered complete)
        # This ensures partially written rows are re-processed
        if len(fields) < expected_field_count:
            print(f"Warning: Skipping incomplete line {line_num} ({len(fields)}/{expected_field_count} fields)", file=sys.stderr)
            continue
        
        order_id = fields[order_id_idx]
        if order_id:
            order_ids.add(order_id)
    
    return order_ids


def estimate_weight_volume(
    client,
    system_prompt: str,
    product_name: str,
    category: str,
    image_url: Optional[str] = None,
) -> dict:
    """Run weight/volume estimation with given prompt."""
    user_text = f"Please analyze this product and provide volume and weight estimates:\n\nTitle: {product_name}\nCategory: {category}"
    user_content = build_user_content(user_text, image_url)
    return call_openai_json(client, system_prompt, user_content)


def iter_tsv(file_path: str) -> Iterator[tuple[int, dict]]:
    """Iterate over TSV file, yielding (line_num, row) tuples."""
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for line_num, row in enumerate(reader, 2):
            yield line_num, row


def parse_volume_string(vol_str: str) -> tuple[float, float, float]:
    """Parse volume string like '20x15x10' to (width, depth, height)."""
    if not vol_str:
        return (0.0, 0.0, 0.0)
    try:
        parts = vol_str.lower().replace(" ", "").split("x")
        if len(parts) == 3:
            return (float(parts[0]), float(parts[1]), float(parts[2]))
    except (ValueError, IndexError):
        pass
    return (0.0, 0.0, 0.0)


def run_estimation(
    input_file: str,
    output_file: str,
    prompt_file: str,
    limit: Optional[int] = None,
    offset: int = 0,
    resume: bool = False,
) -> int:
    """Run estimation on input file and save to output file.
    
    Args:
        input_file: Input TSV file path
        output_file: Output TSV file path
        prompt_file: Prompt template filename
        limit: Maximum number of items to process
        offset: Skip first N rows (start from row N+1)
        resume: Resume from existing result file (auto-detect)
    """
    
    client = get_openai_client()
    system_prompt = load_prompt_template(prompt_file)
    
    # Ensure output directory exists
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Determine skip count for resume mode
    skip_count = offset
    processed_ids = set()
    append_mode = False
    
    if resume and output_path.exists():
        processed_ids = get_processed_order_ids(output_file)
        existing_count = len(processed_ids)
        if existing_count > 0:
            print(f"Resume mode: found {existing_count} already processed items")
            append_mode = True
    elif offset > 0:
        print(f"Offset mode: skipping first {offset} rows")
    
    # Count total records for progress tracking
    input_path = Path(input_file)
    total_records = sum(1 for _ in iter_tsv(input_file))
    if limit:
        total_records = min(total_records, limit)
    
    # Progress file path (in same directory as input file)
    progress_file = input_path.parent / "progress.json"
    
    def write_progress(current: int, total: int, status: str = "running"):
        """Write progress to file for external monitoring."""
        try:
            progress_data = {
                "current": current,
                "total": total,
                "status": status,
            }
            with open(progress_file, "w", encoding="utf-8") as f:
                json.dump(progress_data, f)
                f.flush()
        except Exception as e:
            print(f"[PROGRESS ERROR] {e}", file=sys.stderr)
    
    print(f"Input: {input_file}")
    print(f"Output: {output_file}")
    print(f"Prompt: {prompt_file}")
    print(f"Limit: {limit if limit else 'all'}")
    print(f"Total records: {total_records}")
    if skip_count > 0:
        print(f"Skip: {skip_count} rows")
    if resume:
        print(f"Resume: {'append to existing' if append_mode else 'new file'}")
    print("-" * 80)
    
    # Initialize progress (include already processed items for resume)
    already_processed = len(processed_ids) if resume else 0
    write_progress(already_processed, total_records, "starting")
    
    # Output columns
    output_columns = [
        "order_id",
        "title_origin",
        "category",
        "new_volume",
        "new_packed_volume",
        "new_weight_kg",
        "new_width_cm",
        "new_depth_cm",
        "new_height_cm",
        "new_reason",
    ]
    
    processed = already_processed
    success = 0
    skipped = 0
    
    # Open in append mode if resuming, else write mode
    file_mode = "a" if append_mode else "w"
    with open(output_file, file_mode, encoding="utf-8", newline="") as out_f:
        writer = csv.DictWriter(out_f, fieldnames=output_columns, delimiter="\t")
        if not append_mode:
            writer.writeheader()
        
        for line_num, row in iter_tsv(input_file):
            if limit and processed >= limit:
                break
            
            # Extract data from TSV row
            order_id = row.get("order_id") or row.get("item_id", "")
            product_name = row.get("title_origin") or row.get("title_target", "")
            category = row.get("category", "")
            
            # Skip logic: either by offset count or by checking processed IDs
            if offset > 0 and skipped < offset:
                skipped += 1
                continue
            
            if resume and order_id in processed_ids:
                skipped += 1
                continue
            
            # Get image URL
            thumbnail_urls = row.get("thumbnail_urls", "")
            image_url = thumbnail_urls.split("|")[0] if thumbnail_urls else None
            
            # Run estimation
            try:
                result = estimate_weight_volume(
                    client, system_prompt, product_name, category, image_url
                )
                
                volume = result.get("volume", "")
                packed_volume = result.get("packed_volume", "")
                weight = float(result.get("weight", 0))
                reason = result.get("reason", "")
                
                # Parse volume dimensions
                w, d, h = parse_volume_string(packed_volume or volume)
                
                # Write result and flush immediately for crash safety
                writer.writerow({
                    "order_id": order_id,
                    "title_origin": product_name,
                    "category": category,
                    "new_volume": volume,
                    "new_packed_volume": packed_volume,
                    "new_weight_kg": weight,
                    "new_width_cm": w,
                    "new_depth_cm": d,
                    "new_height_cm": h,
                    "new_reason": reason,
                })
                out_f.flush()
                
                success += 1
                print(f"[{processed + 1}] ✓ {product_name[:40]} → {weight}kg")
                
            except Exception as e:
                print(f"[{processed + 1}] ✗ {product_name[:40]} - ERROR: {e}")
            
            processed += 1
            write_progress(processed, total_records, "running")
    
    # Mark as completed
    write_progress(processed, total_records, "completed")
    
    # Summary
    print("-" * 80)
    if skipped > 0:
        print(f"Skipped: {skipped}")
    print(f"Processed: {processed}, Success: {success}, Failed: {processed - success}")
    print(f"Output saved: {output_file}")
    if append_mode:
        total_in_file = len(processed_ids) + success
        print(f"Total rows in result file: {total_in_file}")
    
    return success


def main():
    parser = argparse.ArgumentParser(
        description="Run weight/volume estimation with new prompt"
    )
    parser.add_argument("-i", "--input", required=True,
                        help="Input TSV file (datasource or category subset)")
    parser.add_argument("-p", "--prompt", required=True,
                        help="Prompt template filename")
    parser.add_argument("-l", "--limit", type=int,
                        help="Maximum number of items to process (for testing)")
    parser.add_argument("-o", "--output",
                        help="Custom output TSV file path (default: auto-generated)")
    parser.add_argument("--offset", type=int, default=0,
                        help="Skip first N rows (start from row N+1)")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from existing result file (auto-detect last processed)")
    
    args = parser.parse_args()
    
    # Determine output path
    if args.output:
        output_file = args.output
    else:
        output_file = str(generate_output_path(
            prompt_file=args.prompt,
            input_file=args.input,
        ))
    
    success = run_estimation(
        input_file=args.input,
        output_file=output_file,
        prompt_file=args.prompt,
        limit=args.limit,
        offset=args.offset,
        resume=args.resume,
    )
    
    sys.exit(0 if success > 0 else 1)


if __name__ == "__main__":
    main()
