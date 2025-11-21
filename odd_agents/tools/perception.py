"""
Perception analysis tools.
Extracted from odd_workflow_full.py (reference implementation).
"""

from typing import Any, Dict, List
from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types

from ..config import SCENARIO_PATH, GENAI_CLIENT, GEMINI_MODEL_PERCEPTION
from ..utils import build_image_path, ensure_image_bytes, extract_json_block


async def list_windows_tool() -> Dict[str, Any]:
    """Tool: list available window IDs for the scenario."""
    import pandas as pd

    if not SCENARIO_PATH.exists():
        return {"status": "error", "message": "Scenario directory not found"}

    index_files = sorted(SCENARIO_PATH.glob("index_*.csv"))
    if not index_files:
        return {"status": "error", "message": "No index CSV found"}

    index_df = pd.read_csv(index_files[0])
    scenario_name = SCENARIO_PATH.name
    windows: List[str] = []

    for _, row in index_df.iterrows():
        window_id = str(row["window_id"]).zfill(3)
        motion_file = SCENARIO_PATH / \
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
        camera_path = build_image_path("cam", window_id)
        bev_path = build_image_path("bev_occupancy", window_id)

        camera_bytes = ensure_image_bytes(camera_path)
        bev_bytes = ensure_image_bytes(bev_path)

        prompt = f"""
        You are a perception expert analyzing synchronized robot sensors for window {window_id}.
        You will receive two images:
        - Image A: RGB camera frame from the robot's forward camera.
        - Image B: LiDAR bird's-eye occupancy map where bright pixels indicate obstacles.

        Provide a JSON object with this EXACT schema:
        {{
          "window_id": "{window_id}",
          "camera_summary": "concise natural-language observation",
          "bev_summary": "concise LiDAR occupancy observation",
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

        response = GENAI_CLIENT.models.generate_content(
            model=GEMINI_MODEL_PERCEPTION,
            contents=[
                types.Part(text=prompt.strip()),
                types.Part(text="Image A (camera):"),
                types.Part.from_bytes(
                    data=camera_bytes, mime_type="image/png"),
                types.Part(text="Image B (LiDAR BEV occupancy):"),
                types.Part.from_bytes(data=bev_bytes, mime_type="image/png"),
            ],
        )

        data = extract_json_block(response.text or "")
        data["window_id"] = window_id
        return data

    except Exception as err:
        return {"status": "error", "window_id": window_id, "message": str(err)}


# FunctionTool wrappers
LIST_WINDOWS = FunctionTool(func=list_windows_tool)
ANALYZE_WINDOW_PERCEPTION = FunctionTool(func=analyze_window_perception_tool)
