"""
Motion analysis tools.
Extracted from odd_workflow_full.py (reference implementation).
"""

import json
import math
from typing import Any, Dict
from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types

from ..config import SCENARIO_PATH, GENAI_CLIENT, GEMINI_MODEL_MOTION
from ..utils import extract_json_block


async def analyze_motion_tool(window_id: str, tool_context: ToolContext) -> Dict[str, Any]:
    """Tool: run a direct Gemini call to analyze raw IMU motion sensor data."""
    try:
        scenario_name = SCENARIO_PATH.name
        motion_file = SCENARIO_PATH / \
            f"motion_{scenario_name}_w{window_id}.json"

        if not motion_file.exists():
            return {"status": "error", "window_id": window_id, "message": "Motion file not found"}

        with open(motion_file, 'r') as f:
            motion_data = json.load(f)

        # Calculate summary statistics for the prompt
        accel_x = motion_data["accel_x"]
        accel_y = motion_data["accel_y"]
        gyro_z = motion_data["gyro_z"]
        roll = motion_data["roll"]
        pitch = motion_data["pitch"]

        # Calculate horizontal acceleration magnitude
        horiz_accel = [math.sqrt(ax**2 + ay**2)
                       for ax, ay in zip(accel_x, accel_y)]
        peak_horiz_accel = max(horiz_accel) if horiz_accel else 0.0
        avg_horiz_accel = sum(horiz_accel) / \
            len(horiz_accel) if horiz_accel else 0.0

        # Calculate angular velocity stats
        peak_gyro_z = max(abs(gz) for gz in gyro_z) if gyro_z else 0.0
        avg_gyro_z = sum(abs(gz) for gz in gyro_z) / \
            len(gyro_z) if gyro_z else 0.0

        # Platform tilt stats
        max_roll = max(abs(r) for r in roll) if roll else 0.0
        max_pitch = max(abs(p) for p in pitch) if pitch else 0.0

        prompt = f"""You are a robotics motion analyst for window {window_id}.

IMU ACCELEROMETER DATA (gravity-compensated, body frame):
- Horizontal acceleration samples (sqrt(accel_x² + accel_y²)): {len(horiz_accel)} samples
- Peak horizontal accel: {peak_horiz_accel:.4f} m/s²
- Average horizontal accel: {avg_horiz_accel:.4f} m/s²
- Sample values: {horiz_accel[:10]} (first 10 of {len(horiz_accel)})

IMU GYROSCOPE DATA:
- Peak angular velocity (|gyro_z|): {peak_gyro_z:.4f} rad/s
- Average angular velocity: {avg_gyro_z:.4f} rad/s
- Sample values: {gyro_z[:10]} (first 10 of {len(gyro_z)})

PLATFORM ORIENTATION:
- Max roll: {max_roll:.1f}°
- Max pitch: {max_pitch:.1f}°

MOTION DETECTION GUIDANCE:
- Horizontal accel > 0.05 m/s² indicates translation (robot moving forward/sideways)
- Horizontal accel > 0.5 m/s² indicates strong acceleration/deceleration
- Angular velocity > 0.1 rad/s indicates rotation (turning)
- Roll/pitch > 15° indicates platform instability

TASK: Analyze this sensor data and provide a JSON object with this EXACT schema:
{{
  "window_id": "{window_id}",
  "motion_detected": true|false,
  "motion_type": "stationary|rotation|translation|complex",
  "peak_horizontal_accel_mps2": <float>,
  "peak_angular_velocity_radps": <float>,
  "platform_stability": "stable|unstable",
  "max_tilt_deg": <float>,
  "motion_confidence": 0.0-1.0,
  "evidence": "brief explanation of your analysis"
}}

No explanations outside the JSON."""

        response = GENAI_CLIENT.models.generate_content(
            model=GEMINI_MODEL_MOTION,
            contents=[types.Part(text=prompt.strip())],
        )

        data = extract_json_block(response.text or "")
        data["window_id"] = window_id
        return data

    except Exception as err:
        return {"status": "error", "window_id": window_id, "message": str(err)}


# FunctionTool wrapper
ANALYZE_MOTION = FunctionTool(func=analyze_motion_tool)
