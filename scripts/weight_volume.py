#!/usr/bin/env python3
"""
Weight and Volume Estimation Script

Estimates product weight and volume using OpenAI GPT-4o-mini.
Supports multimodal input (text + image).

Usage:
    uv run python scripts/weight_volume.py --name "Product Name" --category "Category"
    uv run python scripts/weight_volume.py --name "Product Name" --category "Category" --image "https://..."
    uv run python scripts/weight_volume.py --json '{"productName": "...", "category": "...", "imageUrl": "..."}'
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


def main():
    parser = argparse.ArgumentParser(
        description="Estimate product weight and volume using OpenAI"
    )
    parser.add_argument("--name", "-n", help="Product name/title")
    parser.add_argument("--category", "-c", help="Product category")
    parser.add_argument("--image", "-i", help="Image URL (optional)")
    parser.add_argument("--json", "-j", help="JSON input with productName, category, imageUrl")
    parser.add_argument("--output", "-o", choices=["json", "text"], default="json", help="Output format")
    
    args = parser.parse_args()
    
    # Parse input
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
        parser.error("Either --json or both --name and --category are required")
        return
    
    # Estimate
    try:
        result = estimate_weight_volume(product_name, category, image_url)
        
        if args.output == "json":
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        else:
            print(f"Product: {product_name}")
            print(f"Category: {category}")
            print(f"Volume: {result.volume}")
            print(f"Packed Volume: {result.packed_volume}")
            print(f"Weight: {result.weight} kg")
            print(f"Reason: {result.reason}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
