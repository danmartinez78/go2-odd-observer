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
        """Tool: run a direct multimodal Gemini call for one window (camera + BEV)."""
        try:
            camera_path = build_image_path(scenario_path, "cam", window_id)
            bev_path = build_image_path(
                scenario_path, "bev_occupancy", window_id)

            camera_bytes = ensure_image_bytes(camera_path)
            bev_bytes = ensure_image_bytes(bev_path)

            prompt = f"""
            You are a perception expert analyzing synchronized robot sensors for window {window_id}.
            You will receive two images:
            - Image A: RGB camera frame from the robot's forward camera.
            - Image B: LiDAR bird's-eye occupancy map where bright pixels indicate obstacles.

            **CRITICAL DISTINCTIONS:**
            
            1. **terrain_roughness_class**: Describes GROUND SURFACE elevation variations, NOT surface texture or objects on the ground.
               - smooth: Flat floor/ground with minimal elevation changes (includes carpets, rugs, smooth concrete)
               - moderate: Small bumps, gentle slopes, slightly uneven surfaces
               - rough: Significant elevation changes, stairs, ramps, rocky/unpaved ground
               - very_rough: Extreme terrain (large boulders, steep slopes, severely uneven surfaces)
               NOTE: A rug on a flat floor is "smooth" terrain. Surface texture (plush, high-pile) is NOT terrain roughness.
            
            2. **occupancy_ratio**: Fraction of BEV grid cells occupied by obstacles (objects ABOVE ground level).
               - Only count objects/obstacles visible in the BEV occupancy map (bright pixels)
               - Do NOT confuse ground surface texture with obstacles
            
            3. **obstacle_density**: Concentration/number of distinct obstacles in the forward path.
               - 0.0 = clear path, no obstacles
               - 0.5 = moderate clutter (a few objects)
               - 1.0 = densely packed obstacles blocking most of the area
            
            4. **traversability_score**: Combined assessment considering BOTH terrain AND obstacles.
               - 0.0 = completely blocked or impassable
               - 0.5 = partially obstructed but navigable with care
               - 1.0 = clear, easy path with no obstacles or terrain challenges

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
                    types.Part(text="Image A (camera):"),
                    types.Part.from_bytes(
                        data=camera_bytes, mime_type="image/png"),
                    types.Part(text="Image B (LiDAR BEV occupancy):"),
                    types.Part.from_bytes(
                        data=bev_bytes, mime_type="image/png"),
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
