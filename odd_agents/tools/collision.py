"""
Collision risk analysis tools.
Factory functions that create tools with specific configuration.
"""

from pathlib import Path
from typing import Any, Dict, Union
from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from google import genai

from ..utils import build_image_path, ensure_image_bytes, extract_json_block


def create_collision_tools(scenario_path: Union[str, Path], genai_client: genai.Client, model: str):
    """
    Create collision analysis tools for a specific scenario.

    Args:
        scenario_path: Path to scenario directory (string or Path object)
        genai_client: Configured Gemini client
        model: Model name to use for collision analysis

    Returns:
        FunctionTool for collision risk analysis
    """
    # Ensure scenario_path is a Path object
    scenario_path = Path(scenario_path) if isinstance(
        scenario_path, str) else scenario_path

    async def analyze_collision_risk_tool(
        window_id: str,
        motion_metrics: Dict[str, Any],
        tool_context: ToolContext
    ) -> Dict[str, Any]:
        """Tool: run a direct multimodal Gemini call to analyze collision risk from motion metrics + camera + BEV."""
        try:
            # Build paths
            cam_path = build_image_path(scenario_path, "cam", window_id)
            bev_path = build_image_path(
                scenario_path, "bev_occupancy", window_id)

            # Load images
            cam_bytes = ensure_image_bytes(cam_path)
            bev_bytes = ensure_image_bytes(bev_path)

            # Build multimodal prompt
            motion_status = "MOTION DETECTED" if motion_metrics.get(
                "motion_detected") else "STATIONARY"
            motion_type = motion_metrics.get("motion_type", "unknown")
            peak_accel = motion_metrics.get("peak_horizontal_accel_mps2", 0.0)
            peak_gyro = motion_metrics.get("peak_angular_velocity_radps", 0.0)

            prompt = f"""You are a robot safety analyst for window {window_id}.

MOTION CONTEXT:
- Status: {motion_status}
- Type: {motion_type}
- Peak horizontal accel: {peak_accel:.4f} m/s²
- Peak angular velocity: {peak_gyro:.4f} rad/s

IMAGES PROVIDED:
1. Camera feed (egocentric view)
2. BEV LiDAR map (top-down obstacle map)

TASK: Analyze collision risk by fusing motion + camera + BEV data.

Provide a JSON object with this EXACT schema:
{{
  "window_id": "{window_id}",
  "collision_risk_level": "none|low|medium|high|critical",
  "risk_confidence": 0.0-1.0,
  "closest_obstacle_meters": <float or null>,
  "obstacle_direction": "front|left|right|rear|multiple|none",
  "motion_contributes_to_risk": true|false,
  "camera_hazards": ["list of hazards from camera"],
  "bev_hazards": ["list of hazards from BEV"],
  "recommended_action": "continue|slow_down|stop|change_direction",
  "evidence": "brief explanation of multimodal fusion analysis"
}}

No explanations outside the JSON."""

            response = genai_client.models.generate_content(
                model=model,
                contents=[
                    types.Part(text=prompt.strip()),
                    types.Part(inline_data=types.Blob(
                        mime_type="image/png", data=cam_bytes)),
                    types.Part(inline_data=types.Blob(
                        mime_type="image/png", data=bev_bytes)),
                ],
            )

            data = extract_json_block(response.text or "")
            data["window_id"] = window_id
            return data

        except Exception as err:
            return {"status": "error", "window_id": window_id, "message": str(err)}

    # Return FunctionTool wrapper
    return FunctionTool(func=analyze_collision_risk_tool)
