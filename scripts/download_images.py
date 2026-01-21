#!/usr/bin/env python3
"""Download thumbnail images from sample TSV dataset."""

import csv
import asyncio
import aiohttp
from pathlib import Path


async def download_image(session: aiohttp.ClientSession, url: str, filepath: Path) -> bool:
    """Download a single image."""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status == 200:
                content = await response.read()
                filepath.write_bytes(content)
                return True
            else:
                print(f"  Failed ({response.status}): {url[:80]}...")
                return False
    except Exception as e:
        print(f"  Error: {e}")
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
    row_num: str,
    urls: list[str],
    output_dir: Path,
) -> int:
    """Download all images for a row.
    
    Naming: 69.png, 69_1.png, 69_2.png for row 69 with 3 images.
    """
    downloaded = 0
    tasks = []
    
    for idx, url in enumerate(urls):
        if not url:
            continue
        
        ext = get_extension(url)
        # First image: {row_num}.ext, subsequent: {row_num}_{idx}.ext
        if idx == 0:
            filename = f"{row_num}{ext}"
        else:
            filename = f"{row_num}_{idx}{ext}"
        
        filepath = output_dir / filename
        if filepath.exists():
            downloaded += 1
            continue
        
        tasks.append((download_image(session, url, filepath), filepath))
    
    if tasks:
        results = await asyncio.gather(*[t[0] for t in tasks], return_exceptions=True)
        downloaded += sum(1 for r in results if r is True)
    
    return downloaded


async def main():
    tsv_path = Path(__file__).parent.parent / "dataset" / "sample200.tsv"
    output_dir = Path(__file__).parent.parent / "dataset" / "images"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Read TSV - first column (index 0) is the row number
    rows = []
    with open(tsv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        header = next(reader)  # Skip header
        
        # Find thumbnail_urls column index
        try:
            url_col_idx = header.index("thumbnail_urls")
        except ValueError:
            print("Error: thumbnail_urls column not found")
            return
        
        for row in reader:
            if len(row) > url_col_idx:
                row_num = row[0]  # First column is the row number
                thumbnail_urls = row[url_col_idx]
                if row_num and thumbnail_urls:
                    urls = [u.strip() for u in thumbnail_urls.split("|") if u.strip()]
                    rows.append((row_num, urls))
    
    print(f"Found {len(rows)} rows with images")
    
    # Download images
    connector = aiohttp.TCPConnector(limit=10)
    async with aiohttp.ClientSession(connector=connector) as session:
        total_downloaded = 0
        for i, (row_num, urls) in enumerate(rows):
            downloaded = await download_row_images(session, row_num, urls, output_dir)
            total_downloaded += downloaded
            print(f"[{i+1}/{len(rows)}] Row {row_num}: {downloaded}/{len(urls)} images")
    
    print(f"\nTotal: {total_downloaded} images downloaded to {output_dir}")


if __name__ == "__main__":
    asyncio.run(main())
