#!/usr/bin/env python3
"""
Weight and Volume Estimation Script

Estimates product weight and volume using OpenAI GPT-4o-mini.
Supports multimodal input (text + image).

Usage:
    # Single item
    uv run python scripts/weight_volume.py --name "Product Name" --category "Category"
    uv run python scripts/weight_volume.py --name "Product Name" --category "Category" --image "https://..."
    uv run python scripts/weight_volume.py --json '{"productName": "...", "category": "...", "imageUrl": "..."}'

    # Batch mode (JSONL file)
    uv run python scripts/weight_volume.py --file samples/weight_volume_samples.jsonl
    uv run python scripts/weight_volume.py --file samples/weight_volume_samples.jsonl --limit 3
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Optional

from common import (
    get_openai_client,
    load_prompt_template,
    build_user_content,
    call_openai_json,
)


@dataclass
class WeightVolumeResult:
    """Result of weight/volume estimation."""
    volume: str
    packed_volume: str
    weight: float
    reason: str

    def to_dict(self) -> dict:
        return {
            "volume": self.volume,
            "packed_volume": self.packed_volume,
            "weight": self.weight,
            "reason": self.reason,
        }


def estimate_weight_volume(
    product_name: str,
    category: str,
    image_url: Optional[str] = None,
) -> WeightVolumeResult:
    """
    Estimate weight and volume for a product.
    
    Args:
        product_name: Name/title of the product
        category: Product category
        image_url: Optional image URL for visual analysis
    
    Returns:
        WeightVolumeResult with estimation data
    """
    client = get_openai_client()
    system_prompt = load_prompt_template("weight-volume.system.txt")
    
    user_text = f"Please analyze this product and provide volume and weight estimates:\n\nTitle: {product_name}\nCategory: {category}"
    user_content = build_user_content(user_text, image_url)
    
    result = call_openai_json(client, system_prompt, user_content)
    
    return WeightVolumeResult(
        volume=result.get("volume", ""),
        packed_volume=result.get("packed_volume", ""),
        weight=result.get("weight", 0.0),
        reason=result.get("reason", ""),
    )


def process_single_item(
    product_name: str,
    category: str,
    image_url: Optional[str],
    output_format: str,
) -> bool:
    """Process a single item and print result. Returns True on success."""
    try:
        result = estimate_weight_volume(product_name, category, image_url)
        
        if output_format == "json":
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        else:
            print(f"Product: {product_name}")
            print(f"Category: {category}")
            print(f"Volume: {result.volume}")
            print(f"Packed Volume: {result.packed_volume}")
            print(f"Weight: {result.weight} kg")
            print(f"Reason: {result.reason}")
        return True
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False


def process_batch(file_path: str, limit: Optional[int], output_format: str) -> int:
    """
    Process items from a JSONL file.
    
    Args:
        file_path: Path to JSONL file
        limit: Maximum number of items to process (None = all)
        output_format: Output format (json or text)
    
    Returns:
        Number of successfully processed items
    """
    success_count = 0
    processed_count = 0
    
    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            if limit is not None and processed_count >= limit:
                break
            
            try:
                data = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"Line {line_num}: JSON parse error: {e}", file=sys.stderr)
                processed_count += 1
                continue
            
            product_name = data.get("productName", "")
            category = data.get("category", "")
            image_url = data.get("imageUrl")
            
            if output_format == "text":
                print(f"\n--- Item {line_num} ---")
            
            if process_single_item(product_name, category, image_url, output_format):
                success_count += 1
            
            processed_count += 1
    
    if output_format == "text":
        print(f"\n=== Processed {processed_count} items, {success_count} succeeded ===")
    
    return success_count


def main():
    parser = argparse.ArgumentParser(
        description="Estimate product weight and volume using OpenAI"
    )
    # Single item arguments
    parser.add_argument("--name", "-n", help="Product name/title")
    parser.add_argument("--category", "-c", help="Product category")
    parser.add_argument("--image", "-i", help="Image URL (optional)")
    parser.add_argument("--json", "-j", help="JSON input with productName, category, imageUrl")
    
    # Batch mode arguments
    parser.add_argument("--file", "-f", help="JSONL file path for batch processing")
    parser.add_argument("--limit", "-l", type=int, help="Maximum number of items to process")
    
    # Output format
    parser.add_argument("--output", "-o", choices=["json", "text"], default="json", help="Output format")
    
    args = parser.parse_args()
    
    # Batch mode
    if args.file:
        success_count = process_batch(args.file, args.limit, args.output)
        sys.exit(0 if success_count > 0 else 1)
    
    # Single item mode
    if args.json:
        data = json.loads(args.json)
        product_name = data.get("productName", "")
        category = data.get("category", "")
        image_url = data.get("imageUrl")
    elif args.name and args.category:
        product_name = args.name
        category = args.category
        image_url = args.image
    else:
        parser.error("Either --file, --json, or both --name and --category are required")
        return
    
    success = process_single_item(product_name, category, image_url, args.output)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
