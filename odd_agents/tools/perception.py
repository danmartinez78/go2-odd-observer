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
import cv2
import numpy as np

from ..utils import build_image_path, ensure_image_bytes, extract_json_block, auto_crop_bev


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
        import pandas as pd

        if not scenario_path.exists():
            return {"status": "error", "message": "Scenario directory not found"}

        index_files = sorted(scenario_path.glob("index_*.csv"))
        if not index_files:
            return {"status": "error", "message": "No index CSV found"}

        index_df = pd.read_csv(index_files[0])
        scenario_name = scenario_path.name
        windows: List[str] = []

        for _, row in index_df.iterrows():
            window_id = str(row["window_id"]).zfill(3)
            motion_file = scenario_path / \
                f"motion_{scenario_name}_w{window_id}.json"
            if motion_file.exists():
                windows.append(window_id)

        return {
            "status": "success",
            "windows": windows,
            "count": len(windows),
        }

    async def analyze_window_perception_tool(window_id: str, tool_context: ToolContext) -> Dict[str, Any]:
        """Tool: run a direct multimodal Gemini call for one window (camera + 4 BEV channels)."""
        try:
            # Load camera image
            camera_path = build_image_path(scenario_path, "cam", window_id)
            camera_bytes = ensure_image_bytes(camera_path)

            # Load all 4 BEV channels
            bev_occupancy_path = build_image_path(
                scenario_path, "bev_occupancy", window_id)
            bev_height_path = build_image_path(
                scenario_path, "bev_height", window_id)
            bev_density_path = build_image_path(
                scenario_path, "bev_density", window_id)
            bev_roughness_path = build_image_path(
                scenario_path, "bev_roughness", window_id)

            # Load as numpy arrays for cropping
            bev_occupancy = cv2.imread(str(bev_occupancy_path))
            bev_height = cv2.imread(str(bev_height_path))
            bev_density = cv2.imread(str(bev_density_path))
            bev_roughness = cv2.imread(str(bev_roughness_path))

            # Auto-crop all BEVs (removes empty borders, maintains square aspect)
            bev_occupancy_cropped = auto_crop_bev(bev_occupancy)
            bev_height_cropped = auto_crop_bev(bev_height)
            bev_density_cropped = auto_crop_bev(bev_density)
            bev_roughness_cropped = auto_crop_bev(bev_roughness)

            # Encode cropped BEVs as bytes
            _, bev_occupancy_bytes = cv2.imencode(
                '.png', bev_occupancy_cropped)
            _, bev_height_bytes = cv2.imencode('.png', bev_height_cropped)
            _, bev_density_bytes = cv2.imencode('.png', bev_density_cropped)
            _, bev_roughness_bytes = cv2.imencode(
                '.png', bev_roughness_cropped)

            bev_occupancy_bytes = bev_occupancy_bytes.tobytes()
            bev_height_bytes = bev_height_bytes.tobytes()
            bev_density_bytes = bev_density_bytes.tobytes()
            bev_roughness_bytes = bev_roughness_bytes.tobytes()

            prompt = f"""
            You are a perception expert analyzing synchronized robot sensors for window {window_id}.
            You will receive FIVE images:
            - Image A: RGB camera frame from the robot's forward camera
            - Image B: LiDAR BEV Occupancy (obstacles only, ground filtered out)
            - Image C: LiDAR BEV Height (elevation map)
            - Image D: LiDAR BEV Density (point cloud density)
            - Image E: LiDAR BEV Roughness (terrain surface variation)

            ALL BEV IMAGES (B-E):
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
            - **Density (D)**: Point cloud density. Brighter = more LiDAR points.
              Indicates sensor quality/coverage (low density = occlusion or max range).
            - **Roughness (E)**: Terrain surface variation. Brighter = more uneven.
              Pre-computed metric for surface irregularity.

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
                    types.Part(text="Image D (BEV Density - Point Cloud):"),
                    types.Part.from_bytes(
                        data=bev_density_bytes, mime_type="image/png"),
                    types.Part(
                        text="Image E (BEV Roughness - Surface Variation):"),
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
