#!/usr/bin/env python3
"""Upload images to S3 bucket with failover mechanism.

Usage:
    # Upload from default images folder (first 1000 items)
    python scripts/upload_images_s3.py --limit 1000

    # Upload from specific folder (ix1, ix2, etc.)
    python scripts/upload_images_s3.py --use ix1 --limit 1000
    python scripts/upload_images_s3.py --use ix2

    # Continue from where it stopped
    python scripts/upload_images_s3.py --use ix1 --limit 1000

    # Start over from beginning
    python scripts/upload_images_s3.py --use ix1 --startover

    # Retry only failed items
    python scripts/upload_images_s3.py --use ix1 --retry-failed

    # Upload specific files from a list
    python scripts/upload_images_s3.py --input-list .local/basedata/upload_list.txt
"""

import argparse
import boto3
from botocore.exceptions import ClientError
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import mimetypes


@dataclass
class UploadStats:
    attempted: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0  # Already exists in S3


# Default paths
BASE_DIR = Path(__file__).parent.parent / ".local" / "basedata"
DEFAULT_IMAGES_DIR = BASE_DIR / "images"
DEFAULT_UPLOAD_LIST = BASE_DIR / "upload_list.txt"

# These will be set based on --use option
RESUME_FILE = BASE_DIR / "image_upload_resume.txt"
FAILED_FILE = BASE_DIR / "image_upload_failed.txt"


def get_folder_path(folder_name: str) -> Path:
    """Get folder path from folder name."""
    return BASE_DIR / folder_name


def get_resume_file(folder_name: str) -> Path:
    """Get resume file path for a specific folder."""
    if folder_name == "images":
        return BASE_DIR / "image_upload_resume.txt"
    return BASE_DIR / f"image_upload_resume_{folder_name}.txt"


def get_failed_file(folder_name: str) -> Path:
    """Get failed file path for a specific folder."""
    if folder_name == "images":
        return BASE_DIR / "image_upload_failed.txt"
    return BASE_DIR / f"image_upload_failed_{folder_name}.txt"

# S3 settings - modify these or use environment variables
DEFAULT_BUCKET = "sazo-qa-ai-resources"  # Set your bucket name
DEFAULT_PREFIX = "img/"  # S3 key prefix


def get_content_type(filepath: Path) -> str:
    """Get content type from file extension."""
    content_type, _ = mimetypes.guess_type(str(filepath))
    return content_type or "application/octet-stream"


def upload_file(
    s3_client,
    filepath: Path,
    bucket: str,
    s3_key: str,
    skip_existing: bool = True,
) -> tuple[bool, str]:
    """Upload a single file to S3.

    Returns (success, error_message).
    """
    try:
        # Check if already exists
        if skip_existing:
            try:
                s3_client.head_object(Bucket=bucket, Key=s3_key)
                return True, "exists"
            except ClientError as e:
                if e.response['Error']['Code'] != '404':
                    raise

        # Upload
        content_type = get_content_type(filepath)
        s3_client.upload_file(
            str(filepath),
            bucket,
            s3_key,
            ExtraArgs={"ContentType": content_type}
        )
        return True, ""
    except Exception as e:
        return False, str(e)


def load_resume_point(resume_file: Path) -> Optional[str]:
    """Load the resume point (last processed filename)."""
    if resume_file.exists():
        content = resume_file.read_text().strip()
        if content:
            return content
    return None


def save_resume_point(resume_file: Path, filename: str):
    """Save resume point."""
    resume_file.write_text(filename)


def clear_resume_point(resume_file: Path):
    """Clear resume point."""
    if resume_file.exists():
        resume_file.unlink()


def append_failed_item(failed_file: Path, filename: str, error: str):
    """Append failed item to the failed file."""
    with open(failed_file, "a", encoding="utf-8") as f:
        f.write(f"{filename}\t{error}\n")


def clear_failed_file(failed_file: Path):
    """Clear failed file."""
    if failed_file.exists():
        failed_file.unlink()


def load_file_list(filepath: Path) -> list[str]:
    """Load file list (one filename per line)."""
    if not filepath.exists():
        return []

    files = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                files.append(line)
    return files


def get_all_images(images_dir: Path) -> list[str]:
    """Get all image files in directory."""
    extensions = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff", ".tif", ".avif"}
    files = []
    for f in sorted(images_dir.iterdir()):
        if f.is_file() and f.suffix.lower() in extensions:
            files.append(f.name)
    return files


def main():
    parser = argparse.ArgumentParser(description="Upload images to S3 with failover")
    parser.add_argument("--use", type=str, default="images", help="Folder to use: images, ix1, ix2, etc.")
    parser.add_argument("--limit", type=int, default=0, help="Max items to upload (0=unlimited)")
    parser.add_argument("--startover", action="store_true", help="Ignore resume point, start from beginning")
    parser.add_argument("--retry-failed", action="store_true", help="Retry only failed items")
    parser.add_argument("--input-list", type=Path, default=None, help="File list to upload (one filename per line)")
    parser.add_argument("--images-dir", type=Path, default=None, help="Local images directory (overrides --use)")
    parser.add_argument("--bucket", type=str, default=DEFAULT_BUCKET, help="S3 bucket name")
    parser.add_argument("--prefix", type=str, default=DEFAULT_PREFIX, help="S3 key prefix")
    parser.add_argument("--skip-existing", action="store_true", default=True, help="Skip files already in S3")
    parser.add_argument("--no-skip-existing", action="store_false", dest="skip_existing", help="Re-upload existing files")

    args = parser.parse_args()

    if not args.bucket:
        print("Error: S3 bucket not specified. Use --bucket or set DEFAULT_BUCKET in script.")
        return

    # Determine folder and per-folder files
    folder_name = args.use
    if args.images_dir:
        images_dir = args.images_dir
    else:
        images_dir = get_folder_path(folder_name)

    resume_file = get_resume_file(folder_name)
    failed_file = get_failed_file(folder_name)

    if not images_dir.exists():
        print(f"Error: Folder not found: {images_dir}")
        return

    print(f"Using folder: {folder_name} ({images_dir})")
    print(f"Resume file: {resume_file.name}")
    print(f"Failed file: {failed_file.name}")

    # Determine file list
    if args.retry_failed:
        if not failed_file.exists():
            print("No failed items file found. Nothing to retry.")
            return
        # Load failed items (first column is filename)
        files = []
        with open(failed_file, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("\t")
                if parts:
                    files.append(parts[0])
        clear_failed_file(failed_file)
        print(f"Retrying {len(files)} failed items")
    elif args.input_list:
        files = load_file_list(args.input_list)
        print(f"Using file list: {args.input_list}")
    else:
        files = get_all_images(images_dir)
        print(f"Scanning directory: {images_dir}")

    print(f"Total files: {len(files)}")
    print(f"S3 bucket: {args.bucket}")
    print(f"S3 prefix: {args.prefix}")

    # Handle resume point
    start_idx = 0
    if not args.startover and not args.retry_failed:
        resume_name = load_resume_point(resume_file)
        if resume_name:
            try:
                start_idx = files.index(resume_name) + 1
                print(f"Resuming from item {start_idx} (after {resume_name})")
            except ValueError:
                print(f"Resume point {resume_name} not found, starting from beginning")

    if args.startover:
        clear_resume_point(resume_file)
        clear_failed_file(failed_file)
        print("Starting over from beginning")

    # Apply limit
    if args.limit > 0:
        end_idx = min(start_idx + args.limit, len(files))
    else:
        end_idx = len(files)

    files_to_process = files[start_idx:end_idx]
    print(f"Files to process: {len(files_to_process)} (index {start_idx} to {end_idx - 1})")

    if not files_to_process:
        print("Nothing to upload.")
        return

    # Initialize S3 client
    s3_client = boto3.client("s3")
    stats = UploadStats()

    for i, filename in enumerate(files_to_process):
        filepath = images_dir / filename

        if not filepath.exists():
            stats.failed += 1
            append_failed_item(failed_file, filename, "file not found")
            continue

        s3_key = f"{args.prefix}{filename}"
        stats.attempted += 1

        success, error = upload_file(
            s3_client, filepath, args.bucket, s3_key, args.skip_existing
        )

        if success:
            if error == "exists":
                stats.skipped += 1
            else:
                stats.succeeded += 1
        else:
            stats.failed += 1
            append_failed_item(failed_file, filename, error)

        # Save resume point every 100 items
        if (i + 1) % 100 == 0:
            save_resume_point(resume_file, filename)
            print(f"[{i + 1}/{len(files_to_process)}] "
                  f"Success: {stats.succeeded}, Failed: {stats.failed}, Skipped: {stats.skipped}")

    # Final resume point
    if files_to_process:
        save_resume_point(resume_file, files_to_process[-1])

    # Summary
    print("\n" + "=" * 50)
    print("Upload Summary")
    print("=" * 50)
    print(f"Attempted:  {stats.attempted}")
    print(f"Succeeded:  {stats.succeeded}")
    print(f"Failed:     {stats.failed}")
    print(f"Skipped:    {stats.skipped} (already in S3)")
    print(f"Total:      {stats.succeeded + stats.skipped} images in S3")

    if stats.failed > 0:
        print(f"\nFailed items saved to: {failed_file}")
        print(f"Run with --use {folder_name} --retry-failed to retry them.")

    remaining = len(files) - end_idx
    if remaining > 0:
        print(f"\nRemaining items: {remaining}")
        print("Run again to continue uploading.")
    else:
        print("\nAll items processed!")
        clear_resume_point(resume_file)


if __name__ == "__main__":
    main()
