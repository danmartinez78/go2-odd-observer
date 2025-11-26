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

            prompt = f"""
            You are a perception expert analyzing synchronized robot sensors for window {window_id}.
            You will receive FOUR images:
            - Image A: RGB camera frame from the robot's forward camera
            - Image B: LiDAR BEV Occupancy (obstacles only, ground filtered out)
            - Image C: LiDAR BEV Height (elevation map)
            - Image D: LiDAR BEV Roughness (terrain surface variation)

            ALL BEV IMAGES (B-D):
            - Auto-cropped to remove empty borders (50-75% size reduction)
            - Robot is at CENTER of map, facing upward (top = forward direction)
            - SCALE: 0.05 meters per pixel (20 pixels = 1 meter)
            - Coverage: ~20m x 20m area centered on robot (varies after crop)
            - Upper half = forward path, lower half = behind, sides = lateral areas

            BEV CHANNEL DETAILS:
            - **Occupancy (B)**: Binary obstacle map. Bright = obstacles ABOVE ground (>10cm), dark = free space.
              NOTE: Robot's own body may appear at center - ignore when assessing obstacles.
            - **Height (C)**: Elevation data. Grayscale intensity = height above ground plane.
              CRITICAL FOR terrain_roughness_class - shows elevation variations of the ground surface.
            - **Roughness (D)**: Terrain surface variation. Brighter = more uneven.
              Pre-computed metric for surface irregularity. Combines height variation and surface normals.

            **ODD CONTEXT**:
            The loop agent has provided relevant ODD dimensions to guide your analysis:
            {json.dumps(odd_context, indent=2) if odd_context else "No ODD context provided"}
            
            Use these dimensions as guidance for what to observe, but you are NOT limited to only these.
            Report any observations relevant to safety, reliability, and operational effectiveness.

            **MEASUREMENT GUIDANCE**:
            
            - **Terrain Analysis**: Use BEV Height (C) and Roughness (D) channels.
              Terrain roughness describes GROUND SURFACE elevation variations, NOT surface texture.
              (Smooth = flat floor, Moderate = bumps/slopes, Rough = stairs/ramps, Very rough = extreme terrain)
            
            - **Obstacle Analysis**: Use BEV Occupancy (B) channel.
              Occupancy = fraction of space with obstacles ABOVE ground (exclude robot body at center).
              Density = concentration/count of distinct obstacles in forward path.
            
            - **Traversability**: Combine all channels - obstacles blocking path + terrain passability.
            
            - **Lighting & Visibility**: Camera image quality, clarity, exposure.
            
            - **Actors**: Humans, animals, other dynamic entities visible in camera or BEV.

            **OUTPUT FORMAT**: Provide ONLY a valid JSON object (no markdown, no explanation):
            
            REQUIRED STRUCTURE:
            {{
              "window_id": "{window_id}",
              "camera_summary": "string - what the camera sees",
              "bev_summary": "string - spatial environment from BEV",
              "observations": [
                "string - lighting conditions",
                "string - visibility and clarity",
                "string - terrain characteristics",
                "string - obstacles present",
                "string - traversability assessment",
                "string - actors detected (if any)",
                "string - environment type",
                "string - data quality notes",
                "string - safety concerns (if any)"
              ]
            }}
            
            CRITICAL RULES:
            1. Output ONLY the JSON object - no ```json markers, no explanations
            2. Each observation must be a complete descriptive sentence
            3. Use double quotes for all strings
            4. Ensure valid JSON syntax (commas, brackets, braces)
            5. All observations are strings in the array
            
            Focus on grounded observations from sensor data. The summary agent will map to ODD dimensions.
            """

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
