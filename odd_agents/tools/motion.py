"""
Motion analysis tools.
Factory functions that create tools with specific configuration.

v10.0.0: Simplified motion metrics:
- Speed: Always from derived_speed (position differentiation)
- Acceleration: IMU only (derived accel is too noisy)
- Angular velocity: IMU gyro preferred, fallback to derived_yaw_rate
- Reports data_availability dict for transparency
"""

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Union
from google.adk.tools import FunctionTool
from google.genai import types
from google import genai

from ..utils import extract_json_block
from .common import list_available_windows, get_window_file_paths


# Tool version
# v7.3.0: IMU-only analysis - removed camera VLM call
# v8.0.0: Single-call batch - analyze_all_motion_tool processes all windows, auto-saves artifact
# v9.0.0: Use position-derived velocity/accel when IMU data is zeros (real robot fix)
# v10.0.0: Simplified - always use derived_speed, IMU for accel/gyro when available, clear unavailable flags
# v11.0.0: Added trajectory metrics (displacement, path_length, efficiency) from position data
MOTION_TOOL_VERSION = "11.0.0"


def create_motion_tools(scenario_path: Union[str, Path], genai_client: genai.Client, model: str):
    """
    Create motion analysis tools for a specific scenario.

    Args:
        scenario_path: Path to scenario directory (string or Path object)
        genai_client: Configured Gemini client
        model: Model name to use for motion analysis

    Returns:
        Tuple of (analyze_all_motion_tool,) - single tool handles everything
    """
    scenario_path = Path(scenario_path) if isinstance(
        scenario_path, str) else scenario_path

    async def _analyze_single_window(window_id: str, odd_context: dict) -> dict:
        """Internal: Analyze one window's motion data (called by batch tool).

        Data sources:
        - Speed: ALWAYS from derived_speed (position-based, accurate)
        - Acceleration: IMU when valid, else unavailable
        - Angular velocity: IMU gyro when valid, else derived_yaw_rate
        - Roll/Pitch: Always from orientation (reliable in both sim/real)
        """
        try:
            file_paths = get_window_file_paths(scenario_path, window_id)
            motion_file = file_paths["motion"]

            if not motion_file.exists():
                return {"status": "error", "window_id": window_id, "message": "Motion file not found"}

            with open(motion_file, 'r') as f:
                motion_data = json.load(f)

            # Extract data
            accel_x = motion_data.get("accel_x", [])
            accel_y = motion_data.get("accel_y", [])
            gyro_z = motion_data.get("gyro_z", [])
            roll = motion_data.get("roll", [])
            pitch = motion_data.get("pitch", [])
            timestamps = motion_data.get("timestamps", [])

            # Derived values from position differentiation
            derived_speed = motion_data.get("derived_speed", [])
            derived_yaw_rate = motion_data.get("derived_yaw_rate", [])

            # Position data for trajectory analysis
            pos_x = motion_data.get("pos_x", [])
            pos_y = motion_data.get("pos_y", [])
            pos_z = motion_data.get("pos_z", [])

            # Check data availability
            imu_accel_valid = any(
                abs(ax) > 1e-6 for ax in accel_x) or any(abs(ay) > 1e-6 for ay in accel_y)
            imu_gyro_valid = any(abs(gz) > 1e-6 for gz in gyro_z)
            has_derived_speed = bool(derived_speed) and any(
                s > 1e-6 for s in derived_speed)
            has_derived_yaw = bool(derived_yaw_rate)
            has_position = bool(pos_x) and bool(pos_y)

            # === SPEED: Always use derived_speed (position-based, most accurate) ===
            peak_speed = 0.0
            avg_speed = 0.0
            if has_derived_speed:
                speed_valid = [s for s in derived_speed if s > 1e-6]
                peak_speed = max(speed_valid) if speed_valid else 0.0
                avg_speed = sum(derived_speed) / \
                    len(derived_speed) if derived_speed else 0.0

            # === ACCELERATION: IMU only (derived accel is too noisy) ===
            peak_accel = None  # None means unavailable
            if imu_accel_valid:
                horiz_accel = [math.sqrt(ax**2 + ay**2) for ax, ay in zip(accel_x, accel_y)
                               if abs(ax) > 1e-6 or abs(ay) > 1e-6]
                peak_accel = max(horiz_accel) if horiz_accel else 0.0

            # === ANGULAR VELOCITY: IMU gyro preferred, fallback to derived_yaw_rate ===
            peak_angular_vel = 0.0
            angular_vel_source = "unavailable"
            if imu_gyro_valid:
                gyro_valid = [abs(gz) for gz in gyro_z if abs(gz) > 1e-6]
                peak_angular_vel = max(gyro_valid) if gyro_valid else 0.0
                angular_vel_source = "imu"
            elif has_derived_yaw:
                yaw_valid = [abs(yr)
                             for yr in derived_yaw_rate if abs(yr) > 1e-6]
                peak_angular_vel = max(yaw_valid) if yaw_valid else 0.0
                angular_vel_source = "derived"

            # === ORIENTATION: Always available from odometry ===
            max_roll = max(abs(r) for r in roll) if roll else 0.0
            max_pitch = max(abs(p) for p in pitch) if pitch else 0.0

            # === STATIONARY DETECTION: Based on speed (most reliable) ===
            is_stationary = peak_speed < 0.05  # Less than 5 cm/s

            # === TRAJECTORY METRICS (from position data) ===
            displacement = 0.0
            path_length = 0.0
            # displacement / path_length (1.0 = straight line)
            trajectory_efficiency = 0.0

            if has_position and len(pos_x) > 1:
                # Net displacement (start to end)
                dx = pos_x[-1] - pos_x[0]
                dy = pos_y[-1] - pos_y[0]
                displacement = math.sqrt(dx**2 + dy**2)

                # Path length (sum of all movements)
                for i in range(1, len(pos_x)):
                    seg_dx = pos_x[i] - pos_x[i-1]
                    seg_dy = pos_y[i] - pos_y[i-1]
                    path_length += math.sqrt(seg_dx**2 + seg_dy**2)

                # Trajectory efficiency (1.0 = perfectly straight, <1.0 = wandering/turning)
                if path_length > 0.01:  # Avoid div by zero
                    trajectory_efficiency = displacement / path_length

            # Build data availability summary for LLM
            data_status = []
            if has_derived_speed:
                data_status.append("speed:OK")
            else:
                data_status.append("speed:UNAVAILABLE")
            if imu_accel_valid:
                data_status.append("accel:IMU")
            else:
                data_status.append("accel:UNAVAILABLE")
            if angular_vel_source != "unavailable":
                data_status.append(f"angular:{angular_vel_source}")
            else:
                data_status.append("angular:UNAVAILABLE")
            if has_position:
                data_status.append("position:OK")
            else:
                data_status.append("position:UNAVAILABLE")

            # LLM prompt for motion state interpretation
            accel_str = f"{peak_accel:.4f}" if peak_accel is not None else "N/A"
            trajectory_str = ""
            if has_position:
                trajectory_str = f"""
TRAJECTORY:
- Displacement: {displacement:.3f}m (net start-to-end distance)
- Path length: {path_length:.3f}m (total distance traveled)
- Efficiency: {trajectory_efficiency:.2f} (1.0=straight, <0.5=wandering/turning)"""

            prompt = f"""Motion analyst for window {window_id}.

DATA AVAILABILITY: {', '.join(data_status)}

MEASUREMENTS:
- Speed: peak={peak_speed:.4f} m/s, avg={avg_speed:.4f} m/s
- Acceleration: {accel_str} m/s² (from IMU, includes leg dynamics)
- Angular velocity: {peak_angular_vel:.4f} rad/s ({angular_vel_source})
- Orientation: roll={max_roll:.2f}°, pitch={max_pitch:.2f}°
{trajectory_str}

STATIONARY DETECTION: speed < 0.05 m/s → stationary
Current: {"STATIONARY" if is_stationary else "MOVING"} (speed={peak_speed:.4f} m/s)

NOTE: If accel/angular show "N/A" or "UNAVAILABLE", the IMU data was not recorded.
This is common for real robot data - use speed and orientation for analysis.

MOTION STATES: 
- stationary: speed < 0.05 m/s
- moving: significant speed, efficiency > 0.7 (mostly straight)
- rotating: high angular velocity or efficiency < 0.5
- complex: combination of above

OUTPUT (JSON only):
{{
  "motion_state": "stationary|moving|rotating|complex",
  "is_stationary": {{"value": {str(is_stationary).lower()}, "confidence": 0.0-1.0, "evidence": "reason"}},
  "explanation": "brief motion description",
  "key_insights": ["insight1"]
}}"""

            response = genai_client.models.generate_content(
                model=model, contents=[types.Part(text=prompt)])
            llm_data = extract_json_block(response.text or "")

            # Build ODD measurements - use None for unavailable values
            odd_measurements = {
                "max_speed_mps": round(peak_speed, 4),
                "max_angular_velocity_radps": round(peak_angular_vel, 4),
                "max_roll_deg": round(max_roll, 2),
                "max_pitch_deg": round(max_pitch, 2),
            }

            # Only include accel if available (None means unavailable)
            if peak_accel is not None:
                odd_measurements["max_accel_mps2"] = round(peak_accel, 4)
            else:
                # Explicitly unavailable
                odd_measurements["max_accel_mps2"] = None

            return {
                "window_id": window_id,
                "odd_measurements": odd_measurements,
                "data_availability": {
                    "speed": "derived" if has_derived_speed else "unavailable",
                    "acceleration": "imu" if imu_accel_valid else "unavailable",
                    "angular_velocity": angular_vel_source,
                    "orientation": "available",
                    "position": "available" if has_position else "unavailable",
                },
                "trajectory_metrics": {
                    "displacement_m": round(displacement, 3),
                    "path_length_m": round(path_length, 3),
                    "efficiency": round(trajectory_efficiency, 2),
                },
                "speed_metrics": {
                    "peak_mps": round(peak_speed, 4),
                    "avg_mps": round(avg_speed, 4),
                },
                "is_stationary": llm_data.get("is_stationary", {"value": is_stationary, "confidence": 0.9, "evidence": f"speed={peak_speed:.4f} m/s"}),
                "motion_state": llm_data.get("motion_state", "stationary" if is_stationary else "moving"),
                "explanation": llm_data.get("explanation", "Motion analysis"),
                "key_insights": llm_data.get("key_insights", []),
            }

        except Exception as err:
            return {"status": "error", "window_id": window_id, "message": str(err), "odd_measurements": {}}

    async def analyze_all_motion_tool(odd_context: dict, tool_context) -> dict:
        """Analyze ALL windows for motion and auto-save artifact.

        Args:
            odd_context: ODD specification from parent agent
            tool_context: ADK tool context for artifact saving

        Returns full per_window results. Artifact is auto-saved.
        """
        import google.genai.types as gtypes

        windows = list_available_windows(scenario_path, require_motion=True)
        print(f"\n🟢 [MOTION] Analyzing {len(windows)} windows...")

        per_window = []
        for window_id in windows:
            print(f"🟢 [MOTION] Processing window {window_id}...")
            result = await _analyze_single_window(window_id, odd_context)
            per_window.append(result)

        # Auto-save artifact
        output_data = {"per_window": per_window,
                       "windows_analyzed": len(per_window)}

        try:
            json_bytes = json.dumps(output_data, indent=2).encode('utf-8')
            artifact = gtypes.Part.from_bytes(
                data=json_bytes, mime_type="application/json")
            version = await tool_context.save_artifact(filename="motion_output.json", artifact=artifact)
            print(f"🟢 [MOTION] Auto-saved artifact v{version}")
        except Exception as e:
            print(f"🟢 [MOTION] Artifact save failed: {e}")

        return {"status": "success", "per_window": per_window, "windows_analyzed": len(per_window)}

    return (FunctionTool(func=analyze_all_motion_tool),)
