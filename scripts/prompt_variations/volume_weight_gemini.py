#!/usr/bin/env python3
"""
Weight and Volume Estimation Script (Gemini Version)

Estimates product weight and volume using Google Gemini 2.5 Flash.
Supports multimodal input (text + image).

Usage:
    # Single item
    uv run python scripts/prompt_variations/volume_weight_gemini.py --name "Product Name" --category "Category"
    uv run python scripts/prompt_variations/volume_weight_gemini.py --name "Product Name" --category "Category" --image "https://..."
    uv run python scripts/prompt_variations/volume_weight_gemini.py --json '{"productName": "...", "category": "...", "imageUrl": "..."}'

    # Batch mode (JSONL file)
    uv run python scripts/prompt_variations/volume_weight_gemini.py --file samples/weight_volume_samples.jsonl
    uv run python scripts/prompt_variations/volume_weight_gemini.py --file samples/weight_volume_samples.jsonl --limit 3

    # Batch mode with storage
    uv run python scripts/prompt_variations/volume_weight_gemini.py --file dataset/sample200.jsonl --store


Key differences from the OpenAI version:
| Feature | OpenAI Version | Gemini Version |
|---------|----------------|----------------|
| Model | `gpt-4o-mini` | `gemini-2.5-flash` |
| API | OpenAI Chat Completions | Google Gemini via Vertex AI |
| Prompt | External file `weight-volume.system.txt` | Inline (from `gemini.service.ts`) |
| Output format | `volume`, `packed_volume`, `weight`, `reason` | `dimensions`, `weight`, `confidence`, `reasoning` |
| Auth | `OPENAI_API_KEY` | `GCP_PROJECT_ID` (+ `GCP_LOCATION` optional)

Required environment variables:**
- `GCP_PROJECT_ID` - Your Google Cloud project ID
- `GCP_LOCATION` (optional) - Defaults to `global
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Global logger
logger = logging.getLogger(__name__)

# Gemini configuration
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_TEMPERATURE = 0.3
GEMINI_MAX_OUTPUT_TOKENS = 4096

# System prompt from gemini.service.ts
SYSTEM_PROMPT = """You are a shipping and logistics specialist AI focused on accurate volumetric weight calculations and packaging optimization.

## Primary Objective
Provide precise dimensions and weight estimations optimized for shipping cost calculations, considering:
- Volumetric weight formulas (L*W*H/5000 for international, /6000 for domestic)
- Standard box sizes and packaging materials
- Actual vs volumetric weight comparison

## Input Data
You will receive:
- Product title
- Product category
- Product image (when available)

## Output Format
Return your estimation in the following JSON format:
```json
{
  "dimensions": {
    "length": [number in cm],
    "width": [number in cm],
    "height": [number in cm]
  },
  "weight": {
    "value": [number in kg]
  },
  "confidence": {
    "dimension_confidence": "[high/medium/low]",
    "weight_confidence": "[high/medium/low]"
  },
  "reasoning": "[Brief explanation, max 50 words]"
}
```

IMPORTANT: Return ONLY the JSON object, no additional text or explanations."""


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent


def _load_env() -> None:
    """Load environment variables from .env file."""
    env_path = get_project_root() / ".env"
    if env_path.exists():
        load_dotenv(env_path)


def get_gemini_client() -> genai.Client:
    """
    Initialize and return Gemini client using Vertex AI.
    """
    _load_env()
    project_id = os.environ.get("GCP_PROJECT_ID")
    location = os.environ.get("GCP_LOCATION", "global")

    if not project_id:
        raise ValueError("GCP_PROJECT_ID environment variable is not set")

    return genai.Client(
        vertexai=True,
        project=project_id,
        location=location,
    )


def detect_mime_type(data: bytes) -> str:
    """Detect MIME type from image bytes."""
    # JPEG
    if data[0:3] == b'\xff\xd8\xff':
        return 'image/jpeg'
    # PNG
    if data[0:4] == b'\x89PNG':
        return 'image/png'
    # WebP
    if len(data) > 12 and data[8:12] == b'WEBP':
        return 'image/webp'
    # GIF
    if data[0:4] == b'GIF8':
        return 'image/gif'
    # Default to JPEG
    return 'image/jpeg'


def download_image(url: str) -> Optional[tuple[bytes, str]]:
    """
    Download image from URL.

    Returns:
        Tuple of (image_bytes, mime_type) or None if failed
    """
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url)
            if response.status_code == 200:
                data = response.content
                mime_type = detect_mime_type(data)
                return (data, mime_type)
    except Exception as e:
        logger.warning(f"Failed to download image from {url}: {e}")
    return None


@dataclass
class WeightVolumeResult:
    """Result of weight/volume estimation."""
    dimensions: dict  # {"length": float, "width": float, "height": float}
    weight: float
    confidence: dict  # {"dimension_confidence": str, "weight_confidence": str}
    reasoning: str

    def to_dict(self) -> dict:
        return {
            "dimensions": self.dimensions,
            "weight": self.weight,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
        }

    def to_legacy_dict(self) -> dict:
        """Convert to legacy format compatible with OpenAI version."""
        dims = self.dimensions
        volume = f"{dims['length']}x{dims['width']}x{dims['height']}"
        return {
            "volume": volume,
            "packed_volume": volume,
            "weight": self.weight,
            "reason": self.reasoning,
        }


def estimate_weight_volume(
    product_name: str,
    category: str,
    image_url: Optional[str] = None,
) -> WeightVolumeResult:
    """
    Estimate weight and volume for a product using Gemini.

    Args:
        product_name: Name/title of the product
        category: Product category
        image_url: Optional image URL for visual analysis

    Returns:
        WeightVolumeResult with estimation data
    """
    client = get_gemini_client()

    # Build prompt
    user_text = f"{SYSTEM_PROMPT}\n\nProduct: {product_name}\nCategory: {category}"

    # Build content parts
    content_parts = [types.Part.from_text(text=user_text)]

    # Add image if provided
    if image_url:
        image_data = download_image(image_url)
        if image_data:
            data, mime_type = image_data
            content_parts.append(
                types.Part.from_bytes(data=data, mime_type=mime_type)
            )

    # Call Gemini API
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[types.Content(role="user", parts=content_parts)],
        config=types.GenerateContentConfig(
            temperature=GEMINI_TEMPERATURE,
            max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
            response_mime_type="application/json",
        ),
    )

    # Parse response
    response_text = response.text
    if not response_text:
        raise ValueError("No response from Gemini")

    result = parse_gemini_response(response_text)
    return result


def parse_gemini_response(text: str) -> WeightVolumeResult:
    """Parse Gemini response JSON into WeightVolumeResult."""
    try:
        estimation = json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON from text
        json_start = text.find('{')
        json_end = text.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            json_str = text[json_start:json_end]
            estimation = json.loads(json_str)
        else:
            raise ValueError("No valid JSON found in response")

    # Validate required fields
    if not estimation.get("dimensions") or not estimation.get("weight") or not estimation.get("confidence"):
        raise ValueError("Missing required fields in response")

    return WeightVolumeResult(
        dimensions={
            "length": float(estimation["dimensions"]["length"]),
            "width": float(estimation["dimensions"]["width"]),
            "height": float(estimation["dimensions"]["height"]),
        },
        weight=float(estimation["weight"]["value"]),
        confidence={
            "dimension_confidence": estimation["confidence"]["dimension_confidence"],
            "weight_confidence": estimation["confidence"]["weight_confidence"],
        },
        reasoning=estimation.get("reasoning", ""),
    )


def process_single_item(
    product_name: str,
    category: str,
    image_url: Optional[str],
    output_format: str,
    legacy_format: bool = False,
) -> bool:
    """Process a single item and print result. Returns True on success."""
    try:
        result = estimate_weight_volume(product_name, category, image_url)

        if output_format == "json":
            output = result.to_legacy_dict() if legacy_format else result.to_dict()
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            print(f"Product: {product_name}")
            print(f"Category: {category}")
            dims = result.dimensions
            print(f"Dimensions: {dims['length']}x{dims['width']}x{dims['height']} cm")
            print(f"Weight: {result.weight} kg")
            print(f"Confidence: dimension={result.confidence['dimension_confidence']}, weight={result.confidence['weight_confidence']}")
            print(f"Reasoning: {result.reasoning}")
        return True
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False


def create_output_dir(dataset_count: int) -> Path:
    """Create output directory with timestamp and dataset count."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_dir = get_project_root() / ".local" / f"gemini-{timestamp}-{dataset_count}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def setup_logging() -> None:
    """Setup logging to combined log file at .local/weight-volume-gemini-run.log."""
    log_dir = get_project_root() / ".local"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "weight-volume-gemini-run.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.FileHandler(log_path, encoding="utf-8")],
    )


def write_description(
    output_dir: Path,
    file_path: str,
    limit: Optional[int],
    processed_count: int,
    success_count: int,
) -> None:
    """Write description.md with run metadata."""
    desc_path = output_dir / "description.md"

    limit_str = str(limit) if limit else "None (all)"
    limit_cmd = f" --limit {limit}" if limit else ""

    content = f"""# Weight/Volume Estimation Run (Gemini)

## Input
- Dataset: `{file_path}`
- Limit: {limit_str}
- Model: {GEMINI_MODEL}

## Command
```bash
uv run python scripts/weight_volume_gemini.py --file {file_path}{limit_cmd} --store
```

## Results
- Processed: {processed_count}
- Succeeded: {success_count}
- Failed: {processed_count - success_count}

## Output
- `result.jsonl`: Estimation results
"""
    desc_path.write_text(content, encoding="utf-8")


def process_batch(
    file_path: str,
    limit: Optional[int],
    output_format: str,
    store: bool = False,
    legacy_format: bool = False,
) -> int:
    """
    Process items from a JSONL file.

    Args:
        file_path: Path to JSONL file
        limit: Maximum number of items to process (None = all)
        output_format: Output format (json or text)
        store: Whether to store results to .local/ directory
        legacy_format: Whether to use legacy output format

    Returns:
        Number of successfully processed items
    """
    success_count = 0
    processed_count = 0
    results = []
    errors = []

    # Count total items in file
    with open(file_path, "r", encoding="utf-8") as f:
        total_items = sum(1 for line in f if line.strip())

    # Determine dataset count (limit or total)
    dataset_count = limit if limit is not None else total_items

    output_dir = create_output_dir(dataset_count) if store else None
    setup_logging()

    logger.info(f"Starting batch processing (Gemini): {file_path}")
    logger.info(f"Model: {GEMINI_MODEL}")
    logger.info(f"Limit: {limit if limit else 'None (all)'}")
    logger.info(f"Store: {store}")
    if output_dir:
        logger.info(f"Output directory: {output_dir}")

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
                error_msg = f"Line {line_num}: JSON parse error: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                processed_count += 1
                continue

            item_id = data.get("id", "")
            product_name = data.get("productName", "")
            category = data.get("category", "")
            image_url = data.get("imageUrl")

            name_preview = product_name[:30] if product_name else ""
            logger.info(f"Processing item {processed_count + 1}: id={item_id}, name={name_preview}...")

            if output_format == "text":
                print(f"\n--- Item {line_num} ---")

            try:
                result = estimate_weight_volume(product_name, category, image_url)
                result_dict = result.to_legacy_dict() if legacy_format else result.to_dict()
                result_dict["id"] = item_id
                result_dict["productName"] = product_name
                result_dict["category"] = category

                if store:
                    results.append(result_dict)

                if output_format == "json":
                    print(json.dumps(result_dict, ensure_ascii=False, indent=2))
                else:
                    dims = result.dimensions
                    print(f"Product: {product_name}")
                    print(f"Category: {category}")
                    print(f"Dimensions: {dims['length']}x{dims['width']}x{dims['height']} cm")
                    print(f"Weight: {result.weight} kg")
                    print(f"Confidence: dimension={result.confidence['dimension_confidence']}, weight={result.confidence['weight_confidence']}")
                    print(f"Reasoning: {result.reasoning}")

                logger.info(f"  -> Success: dims={result.dimensions}, weight={result.weight}kg")
                success_count += 1
            except Exception as e:
                error_msg = f"Error processing item {line_num} (id={item_id}): {e}"
                logger.error(error_msg)
                errors.append(error_msg)

            processed_count += 1

    logger.info(f"Batch processing complete: {success_count}/{processed_count} succeeded")

    if store and output_dir:
        # Write results
        result_path = output_dir / "result.jsonl"
        with open(result_path, "w", encoding="utf-8") as f:
            for r in results:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

        # Write description
        write_description(output_dir, file_path, limit, processed_count, success_count)

        logger.info(f"Results stored in: {output_dir}")

    if output_format == "text":
        print(f"\n=== Processed {processed_count} items, {success_count} succeeded ===")

    return success_count


def main():
    parser = argparse.ArgumentParser(
        description="Estimate product weight and volume using Google Gemini"
    )
    # Single item arguments
    parser.add_argument("--name", "-n", help="Product name/title")
    parser.add_argument("--category", "-c", help="Product category")
    parser.add_argument("--image", "-i", help="Image URL (optional)")
    parser.add_argument("--json", "-j", help="JSON input with productName, category, imageUrl")

    # Batch mode arguments
    parser.add_argument("--file", "-f", help="JSONL file path for batch processing")
    parser.add_argument("--limit", "-l", type=int, help="Maximum number of items to process")
    parser.add_argument("--store", "-s", action="store_true", help="Store results to .local/ directory")

    # Output format
    parser.add_argument("--output", "-o", choices=["json", "text"], default="json", help="Output format")
    parser.add_argument("--legacy", action="store_true", help="Use legacy output format (compatible with OpenAI version)")

    args = parser.parse_args()

    # Batch mode
    if args.file:
        success_count = process_batch(args.file, args.limit, args.output, args.store, args.legacy)
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

    success = process_single_item(product_name, category, image_url, args.output, args.legacy)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
