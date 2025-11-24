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
        """Tool: run a direct multimodal Gemini call to analyze collision risk from motion metrics + camera + 4 BEV channels."""
        try:
            # Load camera image
            cam_path = build_image_path(scenario_path, "cam", window_id)
            cam_bytes = ensure_image_bytes(cam_path)

            # Load all 4 BEV channels (pre-cropped during data generation)
            bev_occupancy_path = build_image_path(
                scenario_path, "bev_occupancy", window_id)
            bev_height_path = build_image_path(
                scenario_path, "bev_height", window_id)
            bev_density_path = build_image_path(
                scenario_path, "bev_density", window_id)
            bev_roughness_path = build_image_path(
                scenario_path, "bev_roughness", window_id)

            bev_occupancy_bytes = ensure_image_bytes(bev_occupancy_path)
            bev_height_bytes = ensure_image_bytes(bev_height_path)
            bev_density_bytes = ensure_image_bytes(bev_density_path)
            bev_roughness_bytes = ensure_image_bytes(bev_roughness_path)

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
1. Camera feed (egocentric view from robot)
2. BEV LiDAR Occupancy (obstacles only)
3. BEV LiDAR Height (elevation map)
4. BEV LiDAR Density (point cloud density)
5. BEV LiDAR Roughness (terrain surface variation)

ALL BEV IMAGES (2-5):
- Auto-cropped to remove empty borders (50-75% size reduction)
- Robot is at CENTER of map, facing upward (top = forward direction)
- SCALE: 0.05 meters per pixel (20 pixels = 1 meter)
- Coverage: ~20m x 20m area centered on robot (varies after crop)
- Upper half = forward path, lower half = behind, sides = lateral areas

BEV CHANNEL DETAILS:
- **Occupancy (2)**: Binary obstacle map. Bright = obstacles ABOVE ground (>10cm), dark = free space.
  NOTE: Robot's own body may appear at center - ignore pixels within ~10-pixel radius.
- **Height (3)**: Elevation data. Grayscale intensity = height above ground plane.
  Use to assess terrain hazards (stairs, ramps, drop-offs).
- **Density (4)**: Point cloud density. Brighter = more LiDAR points.
  Low density may indicate occlusion or max range - affects obstacle confidence.
- **Roughness (5)**: Terrain surface variation. Brighter = more uneven.
  High roughness may indicate unstable terrain or collision risk areas.

IMPORTANT: Refer to the ODD specification's robot physical specifications (ego vehicle)
to understand the robot's size when estimating collision risk and safe distances.

TASK: Analyze collision risk by fusing motion + camera + all 4 BEV channels.

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
                        mime_type="image/png", data=bev_occupancy_bytes)),
                    types.Part(inline_data=types.Blob(
                        mime_type="image/png", data=bev_height_bytes)),
                    types.Part(inline_data=types.Blob(
                        mime_type="image/png", data=bev_density_bytes)),
                    types.Part(inline_data=types.Blob(
                        mime_type="image/png", data=bev_roughness_bytes)),
                ],
            )

            data = extract_json_block(response.text or "")
            data["window_id"] = window_id
            return data

        except Exception as err:
            return {"status": "error", "window_id": window_id, "message": str(err)}

    # Return FunctionTool wrapper
    return FunctionTool(func=analyze_collision_risk_tool)
