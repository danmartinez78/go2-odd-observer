"""
Perception analysis tools.
Factory functions that create tools with specific configuration.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Union
from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from google import genai

from ..utils import build_image_path, ensure_image_bytes, extract_json_block
from .common import list_available_windows, get_window_file_paths


# Tool agent version
PERCEPTION_TOOL_AGENT_VERSION = "3.0.0"


def create_perception_tools(scenario_path: Union[str, Path], genai_client: genai.Client, model: str):
    """
    Create perception analysis tools for a specific scenario.

    Args:
        scenario_path: Path to scenario directory (string or Path object)
        genai_client: Configured Gemini client
        model: Model name to use for perception analysis

    Returns:
        Tuple of (list_windows_tool, analyze_window_perception_tool)
    """
    # Ensure scenario_path is a Path object
    scenario_path = Path(scenario_path) if isinstance(
        scenario_path, str) else scenario_path

    async def list_windows_tool() -> Dict[str, Any]:
        """Tool: list available window IDs for the scenario."""
        try:
            windows = list_available_windows(
                scenario_path, require_motion=True)
            return {
                "status": "success",
                "windows": windows,
                "count": len(windows),
            }
        except FileNotFoundError as e:
            return {"status": "error", "message": str(e)}

    async def analyze_window_perception_tool(window_id: str, odd_context: dict, tool_context: ToolContext) -> Dict[str, Any]:
        """Tool: run a direct multimodal Gemini call for one window (camera + 4 BEV channels).

        Args:
            window_id: Window identifier
            odd_context: Filtered ODD specification from loop agent (relevant dimensions only)
            tool_context: ADK tool context
        """
        try:
            # Get file paths from CSV index
            file_paths = get_window_file_paths(scenario_path, window_id)
            camera_path = file_paths["camera"]
            bev_occupancy_path = file_paths["bev_occupancy"]
            bev_height_path = file_paths["bev_height"]
            bev_roughness_path = file_paths["bev_roughness"]

            # Load images
            camera_bytes = ensure_image_bytes(camera_path)
            bev_occupancy_bytes = ensure_image_bytes(bev_occupancy_path)
            bev_height_bytes = ensure_image_bytes(bev_height_path)
            bev_roughness_bytes = ensure_image_bytes(bev_roughness_path)

            prompt = f"""Analyze synchronized sensors for window {window_id}. Be CONCISE (1-2 sentences per observation).

INPUTS:
- Image A: RGB camera (forward-facing)
- Image B: LiDAR BEV Occupancy (bright=obstacles, dark=clear, robot at center facing up)
- Image C: LiDAR BEV Height (grayscale elevation map)
- Image D: LiDAR BEV Roughness (bright=rough terrain)

BEV Scale: 0.05m/pixel (20px = 1m), ~20m x 20m coverage, robot-centered.

ODD Context (guidance only): {json.dumps(odd_context) if odd_context else "None"}

OUTPUT (JSON only, no markdown):
{{
  "window_id": "{window_id}",
  "camera_summary": "brief scene description",
  "bev_summary": "brief spatial layout",
  "observations": [
    "lighting: <concise>",
    "terrain: <concise>",
    "obstacles: <concise>",
    "traversability: <concise>",
    "actors: <concise if present>",
    "safety: <concise if issues>"
  ],
  "quantitative_metrics": {{
    "obstacle_density_ratio": 0.0,
    "traversability_score": 0.0,
    "lighting_adequacy_score": 0.0,
    "terrain_roughness_score": 0.0
  }}
}}

Metrics: 0.0-1.0 floats. Observations: Max 2 sentences each, essential info only."""

            response = genai_client.models.generate_content(
                model=model,
                contents=[
                    types.Part(text=prompt.strip()),
                    types.Part(text="Image A (Camera):"),
                    types.Part.from_bytes(
                        data=camera_bytes, mime_type="image/png"),
                    types.Part(text="Image B (BEV Occupancy - Obstacles):"),
                    types.Part.from_bytes(
                        data=bev_occupancy_bytes, mime_type="image/png"),
                    types.Part(text="Image C (BEV Height - Elevation):"),
                    types.Part.from_bytes(
                        data=bev_height_bytes, mime_type="image/png"),
                    types.Part(
                        text="Image D (BEV Roughness - Surface Variation):"),
                    types.Part.from_bytes(
                        data=bev_roughness_bytes, mime_type="image/png"),
                ],
            )

            data = extract_json_block(response.text or "")
            data["window_id"] = window_id
            return data

        except Exception as err:
            return {"status": "error", "window_id": window_id, "message": str(err)}

    # Return FunctionTool wrappers
    return (
        FunctionTool(func=list_windows_tool),
        FunctionTool(func=analyze_window_perception_tool)
    )
