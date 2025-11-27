"""
Utility functions for ODD Agents.
Pure utility functions with no dependencies on config or global state.
"""

import json
from pathlib import Path
from typing import Any, Dict

import cv2
import numpy as np


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

    Also handles thinking model output that may have JSON in reasoning.

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

    # Try to find JSON object by attempting to parse from different starting positions
    # This handles thinking models that may output reasoning with JSON before the final answer
    start_positions = []
    pos = 0
    while True:
        pos = cleaned.find("{", pos)
        if pos == -1:
            break
        start_positions.append(pos)
        pos += 1

    if not start_positions:
        raise ValueError(f"No JSON object found in response: {text}")

    # Try from each { position, preferring later ones (more likely to be final answer)
    # Reverse so we try the last { first
    errors = []
    for start in reversed(start_positions):
        # Find matching }
        end = cleaned.rfind("}")
        if end <= start:
            continue

        json_text = cleaned[start:end + 1]

        # Replace Python boolean literals with JSON boolean literals
        json_text = json_text.replace(": True", ": true")
        json_text = json_text.replace(": False", ": false")
        json_text = json_text.replace(":True", ":true")
        json_text = json_text.replace(":False", ":false")

        try:
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            errors.append(f"Position {start}: {e}")
            continue

    # If we got here, try the original simple approach as fallback
    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start == -1 or end == -1:
        raise ValueError(f"No JSON object found in response: {text}")

    json_text = cleaned[start:end + 1]
    json_text = json_text.replace(": True", ": true")
    json_text = json_text.replace(": False", ": false")
    json_text = json_text.replace(":True", ":true")
    json_text = json_text.replace(":False", ":false")

    # Parse and return
    return json.loads(json_text)


def auto_crop_bev(bev_image: np.ndarray, margin_percent: float = 0.1) -> np.ndarray:
    """
    Crop BEV image to occupied region plus margin.

    Removes empty black borders from bird's-eye-view images while preserving
    occupied regions with a configurable margin. Maintains square aspect ratio.

    Args:
        bev_image: Input BEV image (grayscale or RGB, cv2.imread compatible)
        margin_percent: Margin as fraction of occupied region size (default 0.1 = 10%)

    Returns:
        Cropped BEV image with margin, maintaining square aspect ratio

    Edge cases:
        - Empty BEV (all background): Return original
        - Full BEV (no empty space): Return original
        - Single-pixel occupied: Return reasonable minimum size

    Examples:
        Basic usage:
            >>> cropped = auto_crop_bev(bev_image)

        Custom margin:
            >>> cropped = auto_crop_bev(bev_image, margin_percent=0.15)

    Note:
        Typically reduces 400x400 BEV to ~150-250px square.
    """
    if bev_image is None:
        return bev_image
    if bev_image.size == 0 or bev_image.shape[0] == 0 or bev_image.shape[1] == 0:
        return bev_image

    # Convert to grayscale for background detection
    if len(bev_image.shape) == 3:
        gray = cv2.cvtColor(bev_image, cv2.COLOR_BGR2GRAY)
    else:
        gray = bev_image

    # Background detection: pixels with value < 5 (black or near-black)
    non_background_mask = gray >= 5
    coords = np.argwhere(non_background_mask)

    # Edge case: empty BEV (all background)
    if coords.size == 0:
        return bev_image

    # Find bounding box of non-background pixels
    y0, x0 = coords.min(axis=0)
    y1, x1 = coords.max(axis=0)

    # Calculate region size
    region_height = y1 - y0 + 1
    region_width = x1 - x0 + 1

    # Edge case: full BEV (no empty space to crop)
    img_height, img_width = bev_image.shape[:2]
    if region_height >= img_height and region_width >= img_width:
        return bev_image

    # CRITICAL: Robot is always at center of original BEV (looking up)
    # We must preserve this spatial relationship!
    center_y = img_height // 2  # Robot's Y position (center of image)
    center_x = img_width // 2   # Robot's X position (center of image)

    # Calculate maximum distance from robot to any occupied pixel
    # This ensures we don't crop out distant obstacles
    dy_max = max(abs(y0 - center_y), abs(y1 - center_y))
    dx_max = max(abs(x0 - center_x), abs(x1 - center_x))
    max_distance = max(dy_max, dx_max)

    # Add margin as percentage of the maximum distance
    margin = int(max_distance * margin_percent)
    margin = max(margin, 1)  # Minimum 1 pixel margin

    # Calculate crop boundaries with margin (centered on ROBOT)
    half_size = max_distance + margin
    crop_y0 = max(0, center_y - half_size)
    crop_y1 = min(img_height, center_y + half_size)
    crop_x0 = max(0, center_x - half_size)
    crop_x1 = min(img_width, center_x + half_size)

    # Adjust to maintain square aspect ratio after clamping to image bounds
    crop_height = crop_y1 - crop_y0
    crop_width = crop_x1 - crop_x0

    if crop_height != crop_width:
        # Expand the smaller dimension if possible
        target_size = max(crop_height, crop_width)

        if crop_height < target_size:
            diff = target_size - crop_height
            expand_top = diff // 2
            expand_bottom = diff - expand_top
            if crop_y0 >= expand_top:
                crop_y0 -= expand_top
                crop_y1 += expand_bottom
            else:
                crop_y1 = min(img_height, crop_y0 + target_size)
                crop_y0 = max(0, crop_y1 - target_size)

        if crop_width < target_size:
            diff = target_size - crop_width
            expand_left = diff // 2
            expand_right = diff - expand_left
            if crop_x0 >= expand_left:
                crop_x0 -= expand_left
                crop_x1 += expand_right
            else:
                crop_x1 = min(img_width, crop_x0 + target_size)
                crop_x0 = max(0, crop_x1 - target_size)

    # Extract cropped region
    cropped = bev_image[crop_y0:crop_y1, crop_x0:crop_x1]

    # Safety check: return original if cropped area is not smaller
    cropped_area = cropped.shape[0] * cropped.shape[1]
    original_area = img_height * img_width
    if cropped_area >= original_area:
        return bev_image

    return cropped
