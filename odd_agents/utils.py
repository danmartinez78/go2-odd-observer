"""
Utility functions for ODD Agents.
Pure utility functions with no dependencies on config or global state.
"""

import json
from pathlib import Path
from typing import Any, Dict


def build_image_path(scenario_path: Path, prefix: str, window_id: str) -> Path:
    """
    Build path to image file for a specific window.

    Args:
        scenario_path: Path to scenario directory
        prefix: Image type prefix (e.g., "cam", "bev_occupancy")
        window_id: Window identifier (e.g., "001", "002")

    Returns:
        Path to the image file
    """
    scenario_name = scenario_path.name
    filename = f"{prefix}_{scenario_name}_w{window_id}.png"
    return scenario_path / filename


def ensure_image_bytes(path: Path) -> bytes:
    """
    Load image bytes, raising error if file is missing.

    Args:
        path: Path to image file

    Returns:
        Image file contents as bytes

    Raises:
        FileNotFoundError: If image file doesn't exist
    """
    if not path.exists():
        raise FileNotFoundError(f"Missing image: {path}")
    return path.read_bytes()


def extract_json_block(text: str) -> Dict[str, Any]:
    """
    Extract JSON object from text that may contain markdown code blocks.

    Handles responses like:
        ```json
        {"key": "value"}
        ```

    Args:
        text: Text containing JSON (possibly with markdown)

    Returns:
        Parsed JSON as dictionary

    Raises:
        ValueError: If no valid JSON object found
        json.JSONDecodeError: If JSON is malformed
    """
    cleaned = text.strip()

    # Remove markdown code fences
    if cleaned.startswith("```"):
        cleaned = "\n".join(
            line for line in cleaned.splitlines()
            if not line.strip().startswith("```")
        )

    # Find JSON object boundaries
    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start == -1 or end == -1:
        raise ValueError(f"No JSON object found in response: {text}")

    json_text = cleaned[start:end + 1]

    # Replace Python boolean literals with JSON boolean literals
    json_text = json_text.replace(": True", ": true")
    json_text = json_text.replace(": False", ": false")
    json_text = json_text.replace(":True", ":true")
    json_text = json_text.replace(":False", ":false")

    # Parse and return
    return json.loads(json_text)
