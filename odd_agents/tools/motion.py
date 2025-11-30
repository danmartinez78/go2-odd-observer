"""
Motion analysis tools.
Factory functions that create tools with specific configuration.

v8.0.0: Single-call batch analysis - one tool call processes all windows and auto-saves artifact.
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
MOTION_TOOL_AGENT_VERSION = "8.0.0"


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
        """Internal: Analyze one window's IMU data (called by batch tool)."""
        try:
            file_paths = get_window_file_paths(scenario_path, window_id)
            motion_file = file_paths["motion"]

            if not motion_file.exists():
                return {"status": "error", "window_id": window_id, "message": "Motion file not found"}

            with open(motion_file, 'r') as f:
                motion_data = json.load(f)

            # Extract IMU data
            accel_x = motion_data["accel_x"]
            accel_y = motion_data["accel_y"]
            gyro_x = motion_data["gyro_x"]
            gyro_y = motion_data["gyro_y"]
            gyro_z = motion_data["gyro_z"]
            roll = motion_data["roll"]
            pitch = motion_data["pitch"]
            timestamps = motion_data["timestamps"]

            # Calculate horizontal acceleration magnitude
            horiz_accel = [math.sqrt(ax**2 + ay**2) for ax, ay in zip(accel_x, accel_y)
                           if abs(ax) > 1e-6 or abs(ay) > 1e-6]

            peak_horiz_accel = max(horiz_accel) if horiz_accel else 0.0
            avg_horiz_accel = sum(horiz_accel) / \
                len(horiz_accel) if horiz_accel else 0.0

            # Angular velocity analysis
            gyro_z_valid = [gz for gz in gyro_z if abs(gz) > 1e-6]
            peak_gyro_z = max(abs(gz)
                              for gz in gyro_z_valid) if gyro_z_valid else 0.0
            peak_gyro_x = max(abs(gx) for gx in gyro_x if abs(
                gx) > 1e-6) if any(abs(gx) > 1e-6 for gx in gyro_x) else 0.0
            peak_gyro_y = max(abs(gy) for gy in gyro_y if abs(
                gy) > 1e-6) if any(abs(gy) > 1e-6 for gy in gyro_y) else 0.0

            # Platform orientation
            max_roll = max(abs(r) for r in roll) if roll else 0.0
            max_pitch = max(abs(p) for p in pitch) if pitch else 0.0

            # Calculate jerk
            jerk_samples = []
            if len(horiz_accel) > 1 and len(timestamps) > 1:
                for i in range(1, len(horiz_accel)):
                    dt = timestamps[i] - timestamps[i-1]
                    if dt > 1e-6:
                        jerk_samples.append(
                            abs(horiz_accel[i] - horiz_accel[i-1]) / dt)
            peak_jerk = max(jerk_samples) if jerk_samples else 0.0

            # LLM prompt for motion state interpretation
            prompt = f"""Motion analyst for window {window_id}. IMU-ONLY.

IMU: Peak accel={peak_horiz_accel:.4f} m/s², Avg={avg_horiz_accel:.4f}, Peak gyro_z={peak_gyro_z:.4f} rad/s
Angles: roll={max_roll:.2f}°, pitch={max_pitch:.2f}°, Jerk={peak_jerk:.4f} m/s³

STATIONARY HEURISTIC: avg_accel<0.5 AND peak_gyro<0.1 AND peak_jerk<5 → likely stationary
MOTION STATES: stationary | moving | rotating | complex

OUTPUT (JSON only):
{{
  "motion_state": "stationary|moving|rotating|complex",
  "is_stationary": {{"value": bool, "confidence": 0.0-1.0, "evidence": "reason"}},
  "explanation": "brief",
  "key_insights": ["insight1"]
}}"""

            response = genai_client.models.generate_content(
                model=model, contents=[types.Part(text=prompt)])
            llm_data = extract_json_block(response.text or "")

            # Deterministic ODD measurements from sensor data
            return {
                "window_id": window_id,
                "odd_measurements": {
                    "max_accel_mps2": round(peak_horiz_accel, 4),
                    "max_speed_mps": 0.0,
                    "max_angular_velocity_radps": round(peak_gyro_z, 4),
                    "max_roll_deg": round(max_roll, 2),
                    "max_pitch_deg": round(max_pitch, 2),
                    "peak_jerk_mps3": round(peak_jerk, 4),
                },
                "is_stationary": llm_data.get("is_stationary", {"value": False, "confidence": 0.5, "evidence": "Not determined"}),
                "motion_state": llm_data.get("motion_state", "unknown"),
                "explanation": llm_data.get("explanation", "Motion analysis from IMU"),
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
