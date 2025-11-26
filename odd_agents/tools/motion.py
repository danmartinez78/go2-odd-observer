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
from .common import get_window_file_paths


# Tool agent version
MOTION_TOOL_AGENT_VERSION = "3.0.0"


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

    async def analyze_motion_tool(window_id: str, odd_context: dict, tool_context: ToolContext) -> Dict[str, Any]:
        """
        Tool: Analyze robot motion using IMU sensor data and optional camera visual odometry.

        Args:
            window_id: Window identifier
            odd_context: Filtered ODD specification from loop agent (relevant ego dimensions)
            tool_context: ADK tool context

        NOTE: Odometry data from wheel encoders is unreliable/unavailable. This analysis
        relies solely on IMU (accelerometer + gyroscope) and camera-based velocity estimation.
        """
        try:
            # Get file paths from CSV index
            file_paths = get_window_file_paths(scenario_path, window_id)
            motion_file = file_paths["motion"]
            cam_file = file_paths["camera"]

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

**ODD CONTEXT**:
The loop agent has provided relevant ODD dimensions (typically ego vehicle capabilities):
{json.dumps(odd_context, indent=2) if odd_context else "No ODD context provided"}

Use these to guide what motion characteristics to observe, but report any motion-related observations.

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

**MOTION REASONING FRAMEWORK**:
Determine if the robot is actually moving by considering ALL evidence holistically.

1. IMU Accelerometer Context:
   - Small constant acceleration (<1.0 m/s²) combined with platform tilt often indicates gravity leakage, NOT motion
   - Reference: 1° of tilt contributes approximately 0.17 m/s² to horizontal acceleration
   - True translational motion typically shows VARYING acceleration patterns, not constant values
   - Stationary robots on tilted platforms will show steady horizontal acceleration from gravity

2. Camera Visual Evidence (PRIMARY MOTION INDICATOR):
   - Sharp textures, clear edges, no motion blur → Robot is stationary or moving very slowly
   - Blurred edges, motion streaks, smeared textures → Robot is moving at significant speed
   - Visible optical flow or scene shift between frames → Active translation
   - Stable, static scene → Robot is stationary
   - Camera evidence OVERRIDES IMU when they conflict

3. IMU Gyroscope Analysis:
   - Very small gyro values (<0.05 rad/s) are typically sensor noise or drift, not actual rotation
   - Sustained angular velocity with varying magnitude indicates genuine rotation
   - Constant low gyro values suggest stationary robot with sensor bias

4. Platform Tilt Consideration:
   - Check current roll/pitch angles - tilt causes horizontal gravity components
   - Example: pitch=1.25° and roll=-0.74° could contribute ~0.21 m/s² horizontal acceleration
   - If acceleration magnitude matches expected gravity component from tilt → likely stationary

5. Temporal Pattern Analysis:
   - Genuine motion: acceleration varies over time (starts, stops, changes)
   - IMU artifacts: constant or slowly drifting values throughout window
   - High jerk (>10 m/s³) suggests actual dynamic maneuvers

**DECISION PRIORITY** (in order of reliability):
1. Camera visual evidence (most reliable for determining actual motion)
2. Temporal patterns in IMU (varying = motion, constant = artifact)
3. Gyroscope for rotation detection
4. Accelerometer magnitude (only after accounting for gravity/tilt)

**CRITICAL REASONING RULE**:
If camera shows sharp, clear images BUT IMU shows acceleration:
→ Check if acceleration is constant and small (<1.0 m/s²)
→ Check if platform has tilt that explains the acceleration
→ If yes to both: Classify as STATIONARY (IMU artifact from gravity leakage)

3. Platform Stability Assessment:
   - Roll/pitch > 15°: Unstable (climbing, descending, or on incline)
   - Roll/pitch < 15°: Stable (on flat or gently sloped terrain)
   
4. Motion Type Classification Guidelines:
   - "stationary": No visual motion in camera AND (low varying accel OR constant accel matching tilt)
   - "rotation": Sustained gyro activity with camera showing scene rotation but no translation
   - "translation": Camera shows optical flow/blur AND varying acceleration pattern
   - "complex": Camera shows both rotation and translation with corresponding IMU patterns

**OUTPUT FORMAT**: Provide ONLY a valid JSON object (no markdown, no explanation):

REQUIRED STRUCTURE:
{{
  "window_id": "{window_id}",
  "motion_summary": "string - motion state and characteristics",
  "observations": [
    "string - motion detection with confidence",
    "string - motion type with reasoning",
    "string - acceleration patterns (peak: {peak_horiz_accel:.3f} m/s²)",
    "string - angular velocity (peak: {peak_gyro_z:.3f} rad/s)",
    "string - platform stability (roll: {max_roll:.1f}°, pitch: {max_pitch:.1f}°)",
    "string - speed estimation if observable",
    "string - motion smoothness (jerk: {peak_jerk:.1f} m/s³)",
    "string - IMU-camera correlation",
    "string - data quality assessment",
    "string - safety notes if any"
  ],
  "metrics": {{
    "peak_horizontal_accel_mps2": {peak_horiz_accel:.3f},
    "peak_angular_velocity_radps": {peak_gyro_z:.3f},
    "max_roll_deg": {max_roll:.1f},
    "max_pitch_deg": {max_pitch:.1f},
    "peak_jerk_mps3": {peak_jerk:.1f}
  }}
}}

CRITICAL RULES:
1. Output ONLY the JSON object - no ```json markers, no explanations
2. Each observation must be a complete descriptive sentence
3. Use double quotes for all strings
4. Ensure valid JSON syntax (commas, brackets, braces)
5. All observations are strings in the array
""")]

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
