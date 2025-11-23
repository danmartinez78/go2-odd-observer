"""
Motion analysis tools.
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


def create_motion_tools(scenario_path: Union[str, Path], genai_client: genai.Client, model: str):
    """
    Create motion analysis tools for a specific scenario.

    Args:
        scenario_path: Path to scenario directory (string or Path object)
        genai_client: Configured Gemini client
        model: Model name to use for motion analysis

    Returns:
        FunctionTool for motion analysis
    """
    # Ensure scenario_path is a Path object
    scenario_path = Path(scenario_path) if isinstance(
        scenario_path, str) else scenario_path

    async def analyze_motion_tool(window_id: str, tool_context: ToolContext) -> Dict[str, Any]:
        """
        Tool: Analyze robot motion using IMU sensor data and optional camera visual odometry.

        NOTE: Odometry data from wheel encoders is unreliable/unavailable. This analysis
        relies solely on IMU (accelerometer + gyroscope) and camera-based velocity estimation.
        """
        try:
            scenario_name = scenario_path.name
            motion_file = scenario_path / \
                f"motion_{scenario_name}_w{window_id}.json"
            cam_file = scenario_path / f"cam_{scenario_name}_w{window_id}.png"

            if not motion_file.exists():
                return {"status": "error", "window_id": window_id, "message": "Motion file not found"}

            with open(motion_file, 'r') as f:
                motion_data = json.load(f)

            # Extract IMU data
            accel_x = motion_data["accel_x"]
            accel_y = motion_data["accel_y"]
            accel_z = motion_data["accel_z"]
            gyro_x = motion_data["gyro_x"]
            gyro_y = motion_data["gyro_y"]
            gyro_z = motion_data["gyro_z"]
            roll = motion_data["roll"]
            pitch = motion_data["pitch"]
            timestamps = motion_data["timestamps"]

            # Filter out zero readings (sensor gaps)
            def filter_zeros(values):
                return [v for v in values if abs(v) > 1e-6]

            accel_x_valid = filter_zeros(accel_x)
            accel_y_valid = filter_zeros(accel_y)
            gyro_z_valid = filter_zeros(gyro_z)

            # Calculate horizontal acceleration magnitude (X-Y plane, gravity already compensated)
            horiz_accel = []
            for ax, ay in zip(accel_x, accel_y):
                if abs(ax) > 1e-6 or abs(ay) > 1e-6:  # Skip zero readings
                    horiz_accel.append(math.sqrt(ax**2 + ay**2))

            # Statistical analysis
            peak_horiz_accel = max(horiz_accel) if horiz_accel else 0.0
            avg_horiz_accel = sum(horiz_accel) / \
                len(horiz_accel) if horiz_accel else 0.0
            median_horiz_accel = sorted(horiz_accel)[len(
                horiz_accel)//2] if horiz_accel else 0.0

            # Angular velocity analysis
            peak_gyro_z = max(abs(gz)
                              for gz in gyro_z_valid) if gyro_z_valid else 0.0
            avg_gyro_z = sum(abs(gz) for gz in gyro_z_valid) / \
                len(gyro_z_valid) if gyro_z_valid else 0.0

            # Full 3D rotation analysis
            peak_gyro_x = max(abs(gx) for gx in gyro_x if abs(
                gx) > 1e-6) if any(abs(gx) > 1e-6 for gx in gyro_x) else 0.0
            peak_gyro_y = max(abs(gy) for gy in gyro_y if abs(
                gy) > 1e-6) if any(abs(gy) > 1e-6 for gy in gyro_y) else 0.0

            # Platform orientation stats
            max_roll = max(abs(r) for r in roll) if roll else 0.0
            max_pitch = max(abs(p) for p in pitch) if pitch else 0.0

            # Calculate jerk (rate of change of acceleration) for smoothness assessment
            jerk_samples = []
            if len(horiz_accel) > 1 and len(timestamps) > 1:
                for i in range(1, len(horiz_accel)):
                    dt = timestamps[i] - timestamps[i-1]
                    if dt > 1e-6:
                        jerk = abs(horiz_accel[i] - horiz_accel[i-1]) / dt
                        jerk_samples.append(jerk)

            peak_jerk = max(jerk_samples) if jerk_samples else 0.0
            avg_jerk = sum(jerk_samples) / \
                len(jerk_samples) if jerk_samples else 0.0

            # Build multimodal prompt with IMU + camera
            prompt_parts = [types.Part(text=f"""You are a robotics motion analyst for window {window_id}.

**IMPORTANT CONTEXT**: Wheel odometry is UNAVAILABLE/UNRELIABLE. Use only IMU and camera evidence.

=== IMU ACCELEROMETER DATA ===
Body-frame linear acceleration (gravity-compensated):
- Valid samples: {len(horiz_accel)} (after filtering sensor gaps)
- Peak horizontal accel: {peak_horiz_accel:.4f} m/s²
- Average horizontal accel: {avg_horiz_accel:.4f} m/s²
- Median horizontal accel: {median_horiz_accel:.4f} m/s²
- Acceleration samples (m/s²): {horiz_accel[:15]} {'...' if len(horiz_accel) > 15 else ''}

=== JERK ANALYSIS (Smoothness) ===
Rate of change of acceleration:
- Peak jerk: {peak_jerk:.2f} m/s³
- Average jerk: {avg_jerk:.2f} m/s³
- High jerk (>5 m/s³) indicates abrupt starts/stops

=== IMU GYROSCOPE DATA ===
Angular velocities in body frame:
- Yaw rate (gyro_z): peak {peak_gyro_z:.4f} rad/s, avg {avg_gyro_z:.4f} rad/s
- Roll rate (gyro_x): peak {peak_gyro_x:.4f} rad/s
- Pitch rate (gyro_y): peak {peak_gyro_y:.4f} rad/s
- Yaw samples (rad/s): {gyro_z_valid[:10]} {'...' if len(gyro_z_valid) > 10 else ''}

=== PLATFORM ORIENTATION ===
Current attitude angles:
- Max roll: {max_roll:.1f}°
- Max pitch: {max_pitch:.1f}°

=== CAMERA IMAGE ===
Front camera view (use for visual odometry estimation):
[See attached image]

**ANALYSIS GUIDELINES**:
1. Motion Detection Thresholds:
   - Horizontal accel > 0.05 m/s²: Translation detected (moving forward/sideways/backward)
   - Horizontal accel > 0.5 m/s²: Strong acceleration/deceleration
   - Angular velocity > 0.1 rad/s: Rotation detected (turning)
   
2. Visual Odometry Hints (from camera):
   - Blurred edges → high velocity
   - Sharp floor textures → low velocity or stationary
   - Optical flow direction → movement direction
   - Scene shift between frames → approximate speed
   
3. Platform Stability:
   - Roll/pitch > 15°: Unstable (climbing/descending)
   - Roll/pitch < 15°: Stable (flat terrain)
   
4. Motion Type Classification:
   - "stationary": accel < 0.05 AND gyro < 0.1
   - "rotation": gyro ≥ 0.1 AND accel < 0.5 (turning in place)
   - "translation": accel ≥ 0.05 AND gyro < 0.1 (straight motion)
   - "complex": accel ≥ 0.05 AND gyro ≥ 0.1 (turning while moving)

**OUTPUT**: JSON object with EXACT schema (no extra text):
{{
  "window_id": "{window_id}",
  "motion_detected": true|false,
  "motion_type": "stationary|rotation|translation|complex",
  "peak_horizontal_accel_mps2": <float>,
  "peak_angular_velocity_radps": <float>,
  "platform_stability": "stable|unstable",
  "max_tilt_deg": <float>,
  "motion_confidence": 0.0-1.0,
  "estimated_speed_mps": <float or null>,
  "motion_smoothness": "smooth|moderate|abrupt",
  "evidence": "Brief explanation citing IMU values and camera observations"
}}

Note: estimated_speed_mps should be your best estimate from camera blur/flow if possible, null if uncertain.""")]

            # Add camera image if available
            if cam_file.exists():
                import base64
                with open(cam_file, 'rb') as img_f:
                    img_data = base64.b64encode(img_f.read()).decode('utf-8')
                    prompt_parts.append(types.Part(inline_data=types.Blob(
                        mime_type="image/png",
                        data=img_data
                    )))

            response = genai_client.models.generate_content(
                model=model,
                contents=prompt_parts,
            )

            data = extract_json_block(response.text or "")
            data["window_id"] = window_id

            # Ensure backward compatibility
            if "estimated_speed_mps" not in data:
                data["estimated_speed_mps"] = None
            if "motion_smoothness" not in data:
                data["motion_smoothness"] = "moderate"

            return data

        except Exception as err:
            return {"status": "error", "window_id": window_id, "message": str(err)}

    # Return FunctionTool wrapper
    return FunctionTool(func=analyze_motion_tool)
