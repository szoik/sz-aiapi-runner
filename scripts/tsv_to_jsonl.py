#!/usr/bin/env python3
"""Convert sample TSV to JSONL format for weight_volume.py."""

import csv
import json
from pathlib import Path


def main():
    tsv_path = Path(__file__).parent.parent / "dataset" / "sample200.tsv"
    jsonl_path = Path(__file__).parent.parent / "dataset" / "sample200.jsonl"
    
    rows = []
    with open(tsv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            row_num = row.get("0", "")  # First column header is "0"
            product_name = row.get("product_title_origin", "")
            category = row.get("product_category", "")
            thumbnail_urls = row.get("thumbnail_urls", "")
            
            # Get first image URL
            image_url = ""
            if thumbnail_urls:
                urls = thumbnail_urls.split("|")
                if urls:
                    image_url = urls[0].strip()
            
            if row_num and product_name:
                rows.append({
                    "id": row_num,
                    "productName": product_name,
                    "category": category,
                    "imageUrl": image_url,
                })
    
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    
    print(f"Converted {len(rows)} rows to {jsonl_path}")


if __name__ == "__main__":
    main()
