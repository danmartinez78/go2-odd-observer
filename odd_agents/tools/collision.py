"""
Collision detection tools.
Factory functions that create tools with specific configuration.
"""

import json
import math
from pathlib import Path
from typing import Any, Dict, Union
from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from google import genai

from ..utils import extract_json_block
from .common import get_window_file_paths


# Tool agent version
COLLISION_TOOL_AGENT_VERSION = "3.0.0"


def create_collision_tools(scenario_path: Union[str, Path], genai_client: genai.Client, model: str):
    """
    Create collision detection tools for a specific scenario.

    Args:
        scenario_path: Path to scenario directory (string or Path object)
        genai_client: Configured Gemini client
        model: Model name to use for collision analysis

    Returns:
        FunctionTool for multimodal collision detection
    """
    # Ensure scenario_path is a Path object
    scenario_path = Path(scenario_path) if isinstance(
        scenario_path, str) else scenario_path

    async def analyze_collision_tool(
        window_id: str,
        odd_context: dict,
        tool_context: ToolContext
    ) -> Dict[str, Any]:
        """Tool: Multimodal collision detection using IMU + camera + BEV.

        Args:
            window_id: Window identifier
            odd_context: Filtered ODD specification from loop agent (minimal context needed)
            tool_context: ADK tool context

        Analyzes collision evidence from:
        - IMU data (acceleration spikes, angular velocity anomalies)
        - Camera visual evidence (impact blur, sudden scene changes)
        - BEV occupancy (contact with obstacles, excluding robot self-hit)

        Returns: collision detected (yes/no) with detailed evidence.
        """
        try:
            # Get file paths
            file_paths = get_window_file_paths(scenario_path, window_id)
            motion_file = file_paths["motion"]
            cam_file = file_paths["camera"]
            bev_occupancy = file_paths.get("bev_occupancy")
            bev_height = file_paths.get("bev_height")
            bev_roughness = file_paths.get("bev_roughness")

            if not motion_file.exists():
                return {"status": "error", "window_id": window_id, "message": "Motion file not found"}

            # Load IMU data
            with open(motion_file, 'r') as f:
                motion_data = json.load(f)

            # Extract raw IMU data
            accel_x = motion_data["accel_x"]
            accel_y = motion_data["accel_y"]
            gyro_x = motion_data["gyro_x"]
            gyro_y = motion_data["gyro_y"]
            gyro_z = motion_data["gyro_z"]
            roll = motion_data["roll"]
            pitch = motion_data["pitch"]
            timestamps = motion_data["timestamps"]

            # Calculate horizontal acceleration magnitude
            horiz_accel = []
            for ax, ay in zip(accel_x, accel_y):
                if abs(ax) > 1e-6 or abs(ay) > 1e-6:
                    horiz_accel.append(math.sqrt(ax**2 + ay**2))

            peak_accel = max(horiz_accel) if horiz_accel else 0.0

            # Calculate angular velocity peak
            peak_gyro = max(abs(gz) for gz in gyro_z if abs(
                gz) > 1e-6) if any(abs(gz) > 1e-6 for gz in gyro_z) else 0.0

            # Calculate platform tilt
            max_tilt = max(max(abs(r) for r in roll) if roll else 0.0, max(
                abs(p) for p in pitch) if pitch else 0.0)

            # Calculate jerk (smoothness)
            jerk_samples = []
            if len(horiz_accel) > 1 and len(timestamps) > 1:
                for i in range(1, len(horiz_accel)):
                    dt = timestamps[i] - timestamps[i-1]
                    if dt > 1e-6:
                        jerk = abs(horiz_accel[i] - horiz_accel[i-1]) / dt
                        jerk_samples.append(jerk)

            peak_jerk = max(jerk_samples) if jerk_samples else 0.0

            # Build multimodal prompt
            prompt_parts = [types.Part(text=f"""You are analyzing window {window_id} for collision detection.

**TASK**: Determine if an actual collision occurred using ALL available evidence.

**ODD CONTEXT** (if provided):
{json.dumps(odd_context, indent=2) if odd_context else "Collision detection typically requires minimal ODD context."}

Focus on detecting actual collisions using multimodal sensor evidence.

=== IMU SENSOR DATA ===
Motion metrics from IMU:
- Peak horizontal acceleration: {peak_accel:.2f} m/s²
- Peak angular velocity: {peak_gyro:.2f} rad/s
=== IMU DATA ===
Peak accel: {peak_accel:.2f} m/s², gyro: {peak_gyro:.2f} rad/s, jerk: {peak_jerk:.1f} m/s³, tilt: {max_tilt:.1f}°

COLLISION INDICATORS:
- Accel >10 m/s² OR gyro >5 rad/s OR jerk >50 m/s³ → likely collision
- BEV: Obstacle penetration into robot zone (exclude 15px center = robot body)
- Camera: Impact blur, scene discontinuity

PRIORITY: IMU spikes (primary) → BEV contact → Camera blur

OUTPUT (JSON only, no markdown, be CONCISE):
{{
  "window_id": "{window_id}",
  "collision_detected": true or false,
  "confidence": 0.0-1.0,
  "evidence": {{
    "imu_analysis": "1-line summary",
    "camera_analysis": "1-line summary",
    "bev_analysis": "1-line summary",
    "multimodal_reasoning": "1-line conclusion"
  }},
  "imu_metrics": {{
    "peak_accel_mps2": {peak_accel},
    "peak_gyro_radps": {peak_gyro},
    "peak_jerk_mps3": {peak_jerk},
    "max_tilt_deg": {max_tilt}
  }},
  "quantitative_metrics": {{
    "collision_risk_score": 0.0,
    "proximity_min_distance_m": 0.0
  }},
  "thresholds_context": {{
    "accel_threshold": 10.0,
    "gyro_threshold": 5.0,
    "jerk_threshold": 50.0
  }}
}}

QUANTITATIVE METRICS GUIDANCE:
- collision_risk_score: 0.0-1.0 (0=no risk, 1=definite collision, based on IMU+camera+BEV evidence)
- proximity_min_distance_m: Minimum distance to nearest obstacle in meters (from BEV occupancy)

CRITICAL RULES:
1. Output ONLY the JSON object - no ```json markers, no explanations
2. All string values must use double quotes
3. Boolean values: true or false (lowercase, no quotes)
4. Ensure valid JSON syntax (commas, brackets, braces)
5. Focus on ACTUAL collision evidence, not proximity risk
""")]

            # Add camera image
            if cam_file.exists():
                import base64
                with open(cam_file, 'rb') as img_f:
                    img_data = base64.b64encode(img_f.read()).decode('utf-8')
                    prompt_parts.append(types.Part(inline_data=types.Blob(
                        mime_type="image/png",
                        data=img_data
                    )))

            # Add BEV images
            for bev_file, label in [
                (bev_occupancy, "BEV Occupancy"),
                (bev_height, "BEV Height"),
                (bev_roughness, "BEV Roughness")
            ]:
                if bev_file and bev_file.exists():
                    import base64
                    with open(bev_file, 'rb') as img_f:
                        img_data = base64.b64encode(
                            img_f.read()).decode('utf-8')
                        prompt_parts.append(types.Part(
                            text=f"\n=== {label} ==="))
                        prompt_parts.append(types.Part(inline_data=types.Blob(
                            mime_type="image/png",
                            data=img_data
                        )))

            # Generate LLM analysis
            response = genai_client.models.generate_content(
                model=model,
                contents=prompt_parts,
            )

            data = extract_json_block(response.text or "")
            data["window_id"] = window_id

            return data

        except Exception as err:
            return {
                "status": "error",
                "window_id": window_id,
                "message": str(err),
                "collision_detected": False,
                "evidence": {"error": f"Error during collision detection: {err}"}
            }

    # Return FunctionTool wrapper
    return FunctionTool(func=analyze_collision_tool)
