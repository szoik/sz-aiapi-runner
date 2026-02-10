#!/usr/bin/env python3
"""Download thumbnail images with failover mechanism.

Usage:
    # Download first 1000 items
    python scripts/image_proxy/download_images.py --limit 1000
    
    # Continue from where it stopped
    python scripts/image_proxy/download_images.py --limit 1000
    
    # Start over from beginning
    python scripts/image_proxy/download_images.py --startover
    
    # Retry only failed items
    python scripts/image_proxy/download_images.py --retry-failed
    
    # Slower, gentler download
    python scripts/image_proxy/download_images.py --concurrent 5 --delay 0.2
"""

import argparse
import csv
import asyncio
import aiohttp
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from common import PROJECT_ROOT


@dataclass
class DownloadStats:
    attempted: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0  # Already exists


# Default paths
BASE_DIR = PROJECT_ROOT / ".local" / "basedata"
DEFAULT_INPUT = BASE_DIR / "image_download_list.tsv"
DEFAULT_OUTPUT_DIR = BASE_DIR / "images"
RESUME_FILE = BASE_DIR / "image_download_resume.txt"
FAILED_FILE = BASE_DIR / "image_download_failed.tsv"


async def download_image(
    session: aiohttp.ClientSession,
    url: str,
    filepath: Path,
    max_retries: int = 3,
    delay: float = 0,
) -> bool:
    """Download a single image with retry logic."""
    for attempt in range(max_retries):
        try:
            if delay > 0:
                await asyncio.sleep(delay)
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    content = await response.read()
                    filepath.write_bytes(content)
                    return True
                elif response.status == 404:
                    # Don't retry 404s
                    return False
        except Exception as e:
            if attempt == max_retries - 1:
                pass  # Final attempt failed
        
        # Wait before retry
        if attempt < max_retries - 1:
            await asyncio.sleep(1 * (attempt + 1))
    
    return False


def get_extension(url: str) -> str:
    """Determine file extension from URL."""
    url_lower = url.lower()
    if ".png" in url_lower:
        return ".png"
    elif ".webp" in url_lower:
        return ".webp"
    elif ".gif" in url_lower:
        return ".gif"
    return ".jpg"


async def download_row_images(
    session: aiohttp.ClientSession,
    row_id: str,
    urls: list[str],
    output_dir: Path,
    stats: DownloadStats,
    delay: float = 0,
) -> list[str]:
    """Download all images for a row.
    
    Returns list of failed URLs.
    """
    failed_urls = []
    
    for idx, url in enumerate(urls):
        if not url:
            continue
        
        ext = get_extension(url)
        # First image: {id}.ext, subsequent: {id}_01.ext, {id}_02.ext, ...
        if idx == 0:
            filename = f"{row_id}{ext}"
        else:
            filename = f"{row_id}_{idx:02d}{ext}"
        
        filepath = output_dir / filename
        
        if filepath.exists():
            stats.skipped += 1
            continue
        
        stats.attempted += 1
        success = await download_image(session, url, filepath, delay=delay)
        
        if success:
            stats.succeeded += 1
        else:
            stats.failed += 1
            failed_urls.append(url)
    
    return failed_urls


def load_resume_point() -> Optional[str]:
    """Load the resume point (last processed ID)."""
    if RESUME_FILE.exists():
        content = RESUME_FILE.read_text().strip()
        if content:
            return content
    return None


def save_resume_point(row_id: str):
    """Save resume point."""
    RESUME_FILE.write_text(row_id)


def clear_resume_point():
    """Clear resume point."""
    if RESUME_FILE.exists():
        RESUME_FILE.unlink()


def append_failed_items(row_id: str, failed_urls: list[str]):
    """Append failed items to the failed file."""
    file_exists = FAILED_FILE.exists()
    
    with open(FAILED_FILE, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        if not file_exists:
            writer.writerow(["id", "thumbnail_urls"])
        writer.writerow([row_id, "|".join(failed_urls)])


def clear_failed_file():
    """Clear failed file."""
    if FAILED_FILE.exists():
        FAILED_FILE.unlink()


def load_input_file(filepath: Path) -> list[tuple[str, list[str]]]:
    """Load input TSV file."""
    rows = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        header = next(reader)
        
        try:
            id_col_idx = header.index("id")
            url_col_idx = header.index("thumbnail_urls")
        except ValueError as e:
            raise ValueError(f"Required column not found: {e}")
        
        for row in reader:
            if len(row) > max(id_col_idx, url_col_idx):
                row_id = row[id_col_idx]
                thumbnail_urls = row[url_col_idx]
                if row_id and thumbnail_urls:
                    urls = [u.strip() for u in thumbnail_urls.split("|") if u.strip()]
                    rows.append((row_id, urls))
    
    return rows


async def main():
    parser = argparse.ArgumentParser(description="Download thumbnail images with failover")
    parser.add_argument("--limit", type=int, default=0, help="Max items to download (0=unlimited)")
    parser.add_argument("--startover", action="store_true", help="Ignore resume point, start from beginning")
    parser.add_argument("--retry-failed", action="store_true", help="Retry only failed items")
    parser.add_argument("--concurrent", type=int, default=10, help="Concurrent downloads (default: 10)")
    parser.add_argument("--delay", type=float, default=0, help="Delay between requests in seconds")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Input TSV file")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output directory")
    
    args = parser.parse_args()
    
    # Determine input file
    if args.retry_failed:
        if not FAILED_FILE.exists():
            print("No failed items file found. Nothing to retry.")
            return
        input_file = FAILED_FILE
        print(f"Retrying failed items from: {FAILED_FILE}")
        # Clear failed file since we're retrying - new failures will be appended
        failed_items = load_input_file(FAILED_FILE)
        clear_failed_file()
        rows = failed_items
    else:
        input_file = args.input
        rows = load_input_file(input_file)
    
    args.output.mkdir(parents=True, exist_ok=True)
    
    print(f"Input file: {input_file}")
    print(f"Output directory: {args.output}")
    print(f"Total items in file: {len(rows)}")
    
    # Handle resume point
    start_idx = 0
    if not args.startover and not args.retry_failed:
        resume_id = load_resume_point()
        if resume_id:
            # Find the index of the resume point
            for i, (row_id, _) in enumerate(rows):
                if row_id == resume_id:
                    start_idx = i + 1  # Start from next item
                    break
            print(f"Resuming from item {start_idx} (after {resume_id})")
    
    if args.startover:
        clear_resume_point()
        clear_failed_file()
        print("Starting over from beginning")
    
    # Apply limit
    if args.limit > 0:
        end_idx = min(start_idx + args.limit, len(rows))
    else:
        end_idx = len(rows)
    
    rows_to_process = rows[start_idx:end_idx]
    print(f"Items to process: {len(rows_to_process)} (index {start_idx} to {end_idx - 1})")
    
    if not rows_to_process:
        print("Nothing to download.")
        return
    
    # Download images
    stats = DownloadStats()
    connector = aiohttp.TCPConnector(limit=args.concurrent)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        for i, (row_id, urls) in enumerate(rows_to_process):
            failed_urls = await download_row_images(
                session, row_id, urls, args.output, stats, delay=args.delay
            )
            
            # Record failed items
            if failed_urls:
                append_failed_items(row_id, failed_urls)
            
            # Save resume point every 100 items
            if (i + 1) % 100 == 0:
                save_resume_point(row_id)
                print(f"[{i + 1}/{len(rows_to_process)}] "
                      f"Success: {stats.succeeded}, Failed: {stats.failed}, Skipped: {stats.skipped}")
        
        # Final resume point
        if rows_to_process:
            save_resume_point(rows_to_process[-1][0])
    
    # Summary
    print("\n" + "=" * 50)
    print("Download Summary")
    print("=" * 50)
    print(f"Attempted:  {stats.attempted}")
    print(f"Succeeded:  {stats.succeeded}")
    print(f"Failed:     {stats.failed}")
    print(f"Skipped:    {stats.skipped} (already exist)")
    print(f"Total:      {stats.succeeded + stats.skipped} images available")
    
    if stats.failed > 0:
        print(f"\nFailed items saved to: {FAILED_FILE}")
        print("Run with --retry-failed to retry them.")
    
    remaining = len(rows) - end_idx
    if remaining > 0:
        print(f"\nRemaining items: {remaining}")
        print("Run again to continue downloading.")
    else:
        print("\nAll items processed!")
        clear_resume_point()


if __name__ == "__main__":
    asyncio.run(main())
