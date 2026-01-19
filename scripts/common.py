"""
Common utilities for OpenAI API scripts.
"""

from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Union
from openai import OpenAI


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def get_openai_client() -> OpenAI:
    """
    Initialize and return OpenAI client.
    Requires OPENAI_API_KEY environment variable.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    return OpenAI(api_key=api_key)


def load_prompt_template(filename: str) -> str:
    """
    Load a prompt template from the prompts/ directory.
    
    Args:
        filename: Name of the prompt file (e.g., 'weight-volume.system.txt')
    
    Returns:
        Content of the prompt file
    """
    prompt_path = get_project_root() / "prompts" / filename
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt template not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def build_user_content(text: str, image_url: Optional[str] = None) -> List[Dict]:
    """
    Build user message content array for OpenAI API.
    Supports multimodal input (text + image).
    
    Args:
        text: The text content of the message
        image_url: Optional image URL for vision analysis
    
    Returns:
        Content array for OpenAI messages
    """
    content = [{"type": "text", "text": text}]
    
    if image_url and image_url.strip():
        content.append({
            "type": "image_url",
            "image_url": {"url": image_url}
        })
    
    return content


def call_openai_json(
    client: OpenAI,
    system_prompt: str,
    user_content: Union[List[Dict], str],
    model: str = "gpt-4o-mini",
    temperature: float = 0.01,
) -> Dict:
    """
    Call OpenAI API and return JSON response.
    
    Args:
        client: OpenAI client instance
        system_prompt: System prompt text
        user_content: User message content (string or multimodal array)
        model: Model to use
        temperature: Temperature for response generation
    
    Returns:
        Parsed JSON response from OpenAI
    """
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
        temperature=temperature,
    )
    
    response_text = completion.choices[0].message.content
    if not response_text:
        raise ValueError("No response from OpenAI")
    
    return json.loads(response_text)
