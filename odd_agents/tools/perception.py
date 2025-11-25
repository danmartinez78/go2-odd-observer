"""
Perception analysis tools.
Factory functions that create tools with specific configuration.
"""

from pathlib import Path
from typing import Any, Dict, List, Union
from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from google import genai

from ..utils import build_image_path, ensure_image_bytes, extract_json_block
from .common import list_available_windows, get_window_file_paths


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

    async def analyze_window_perception_tool(window_id: str, tool_context: ToolContext) -> Dict[str, Any]:
        """Tool: run a direct multimodal Gemini call for one window (camera + 4 BEV channels)."""
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

            IMPORTANT: Refer to the ODD specification's robot physical specifications (ego vehicle)
            to understand the robot's footprint when assessing traversability and passable gaps.

            **CRITICAL DISTINCTIONS:**
            
            1. **terrain_roughness_class**: Use BEV Height (C) and Roughness (E) channels!
               Describes GROUND SURFACE elevation variations, NOT surface texture or objects.
               - smooth: Flat floor with minimal height variation (use Height channel to verify)
               - moderate: Small bumps, gentle slopes (visible in Height channel)
               - rough: Significant elevation changes, stairs, ramps (clear in Height/Roughness)
               - very_rough: Extreme terrain (large height variations, high roughness values)
               NOTE: A rug on flat floor is "smooth" (Height channel shows flat). Surface texture ≠ terrain roughness.
            
            2. **occupancy_ratio**: Use BEV Occupancy (B) channel!
               Fraction of grid cells occupied by obstacles ABOVE ground level.
               - Bright pixels in Occupancy = obstacles, dark = free space
               - Estimate bright pixel fraction in forward navigable area
            
            3. **obstacle_density**: Use BEV Occupancy (B) channel!
               Concentration/number of distinct obstacles in forward path.
               - 0.0 = clear path, no obstacles
               - 0.5 = moderate clutter (a few objects)
               - 1.0 = densely packed obstacles
            
            4. **traversability_score**: Combine ALL channels (B, C, D, E)!
               - Occupancy (B): Are there obstacles blocking the path?
               - Height (C) + Roughness (E): Is the terrain passable?
               - Density (D): Is sensor coverage good enough to trust?
               Result: 0.0 = impassable, 0.5 = difficult, 1.0 = clear and easy

            Provide a JSON object with this EXACT schema:
            {{
              "window_id": "{window_id}",
              "camera_summary": "concise natural-language observation of what the camera sees",
              "bev_summary": "concise description of obstacles visible in the LiDAR occupancy map",
              "lighting_class": "bright|dim|dark",
              "visibility_score": 0.0-1.0,
              "terrain_roughness_class": "smooth|moderate|rough|very_rough",
              "occupancy_ratio": 0.0-1.0,
              "obstacle_density": 0.0-1.0,
              "traversability_score": 0.0-1.0,
              "humans_detected": true|false,
              "environmental_constraints": ["list", "of", "observed", "constraints"]
            }}

            No explanations, just the JSON.
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
