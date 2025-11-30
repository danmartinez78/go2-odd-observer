"""
Collision detection tools.
Factory functions that create tools with specific configuration.

v8.0.0: Single-call batch analysis - one tool call processes all windows and auto-saves artifact.
"""

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from google.adk.tools import FunctionTool
from google.genai import types
from google import genai

from ..utils import extract_json_block, compute_bev_metrics
from .common import list_available_windows, get_window_file_paths


# Tool version
# v7.3.0: Removed BEV images - uses camera + IMU + pre-computed metrics only
# v8.0.0: Single-call batch - analyze_all_collision_tool processes all windows, auto-saves artifact
COLLISION_TOOL_AGENT_VERSION = "8.0.0"


def create_collision_tools(scenario_path: Union[str, Path], genai_client: genai.Client, model: str):
    """
    Create collision detection tools for a specific scenario.

    Args:
        scenario_path: Path to scenario directory (string or Path object)
        genai_client: Configured Gemini client
        model: Model name to use for collision analysis

    Returns:
        Tuple of (analyze_all_collision_tool,) - single tool handles everything
    """
    scenario_path = Path(scenario_path) if isinstance(
        scenario_path, str) else scenario_path

    async def _analyze_single_window(window_id: str, odd_context: dict, motion_state: Optional[dict] = None) -> dict:
        """Internal: Analyze one window for collision (called by batch tool)."""
        import cv2
        import base64

        try:
            file_paths = get_window_file_paths(scenario_path, window_id)
            motion_file = file_paths["motion"]
            cam_file = file_paths["camera"]
            bev_occupancy = file_paths.get("bev_occupancy")

            if not motion_file.exists():
                return {"status": "error", "window_id": window_id, "message": "Motion file not found"}

            # Load IMU data
            with open(motion_file, 'r') as f:
                motion_data = json.load(f)

            accel_x, accel_y = motion_data["accel_x"], motion_data["accel_y"]
            gyro_z = motion_data["gyro_z"]
            roll, pitch = motion_data["roll"], motion_data["pitch"]
            timestamps = motion_data["timestamps"]

            # Calculate metrics
            horiz_accel = [math.sqrt(
                ax**2 + ay**2) for ax, ay in zip(accel_x, accel_y) if abs(ax) > 1e-6 or abs(ay) > 1e-6]
            peak_accel = max(horiz_accel) if horiz_accel else 0.0
            peak_gyro = max(abs(gz) for gz in gyro_z if abs(
                gz) > 1e-6) if any(abs(gz) > 1e-6 for gz in gyro_z) else 0.0
            max_tilt = max(max(abs(r) for r in roll) if roll else 0.0, max(
                abs(p) for p in pitch) if pitch else 0.0)

            jerk_samples = []
            if len(horiz_accel) > 1 and len(timestamps) > 1:
                for i in range(1, len(horiz_accel)):
                    dt = timestamps[i] - timestamps[i-1]
                    if dt > 1e-6:
                        jerk_samples.append(
                            abs(horiz_accel[i] - horiz_accel[i-1]) / dt)
            peak_jerk = max(jerk_samples) if jerk_samples else 0.0

            # Pre-compute BEV metrics
            bev_metrics = {"computed": False}
            if bev_occupancy and bev_occupancy.exists():
                bev_img = cv2.imread(str(bev_occupancy), cv2.IMREAD_GRAYSCALE)
                bev_metrics = compute_bev_metrics(
                    bev_img, resolution_m_per_px=0.05, self_hit_radius_px=15)

            min_dist = bev_metrics.get('min_obstacle_distance_m', 2.5) or 2.5

            # Motion state gating
            motion_str = ""
            if motion_state and motion_state.get("is_stationary", {}).get("value"):
                motion_str = "STATIONARY - require strong collision evidence"

            prompt = f"""Collision detection for window {window_id}. ADVISORY ONLY.
{motion_str}
IMU: accel={peak_accel:.3f} m/s² (>10=collision), gyro={peak_gyro:.3f} rad/s (>5=collision), jerk={peak_jerk:.3f}
BEV: min_dist={min_dist}m (<0.3m + IMU spike = collision)

OUTPUT (JSON only):
{{
  "collision_detected": bool,
  "confidence": 0.0-1.0,
  "proximity_estimate_m": {min_dist},
  "collision_risk_band": "LOW|MED|HIGH",
  "explanation": "brief"
}}"""

            prompt_parts = [types.Part(text=prompt)]

            # Add camera image
            if cam_file.exists():
                with open(cam_file, 'rb') as img_f:
                    img_data = base64.b64encode(img_f.read()).decode('utf-8')
                    prompt_parts.append(types.Part(inline_data=types.Blob(
                        mime_type="image/png", data=img_data)))

            response = genai_client.models.generate_content(
                model=model, contents=prompt_parts)
            llm_data = extract_json_block(response.text or "")

            return {
                "window_id": window_id,
                "odd_measurements": {},
                "collision_detected": bool(llm_data.get("collision_detected", False)),
                "confidence": llm_data.get("confidence", 0.0),
                "proximity_estimate_m": llm_data.get("proximity_estimate_m", min_dist),
                "collision_risk_band": llm_data.get("collision_risk_band", "LOW"),
                "explanation": llm_data.get("explanation", "Collision analysis"),
                "key_insights": llm_data.get("key_insights", []),
            }

        except Exception as err:
            return {"status": "error", "window_id": window_id, "message": str(err), "collision_detected": False}

    async def analyze_all_collision_tool(odd_context: dict, motion_results: Optional[dict] = None, tool_context=None) -> dict:
        """Analyze ALL windows for collision and auto-save artifact.

        Args:
            odd_context: ODD specification from parent agent
            motion_results: Optional motion analysis results for motion-state gating
            tool_context: ADK tool context for artifact saving

        Returns full per_window results. Artifact is auto-saved.
        """
        import google.genai.types as gtypes

        windows = list_available_windows(scenario_path, require_motion=True)
        print(f"\n🟠 [COLLISION] Analyzing {len(windows)} windows...")

        # Build motion state lookup from motion results
        motion_lookup = {}
        if motion_results and "per_window" in motion_results:
            for mw in motion_results["per_window"]:
                wid = mw.get("window_id")
                if wid:
                    motion_lookup[wid] = mw

        per_window = []
        collisions_detected = 0
        for window_id in windows:
            print(f"🟠 [COLLISION] Processing window {window_id}...")
            motion_state = motion_lookup.get(window_id)
            result = await _analyze_single_window(window_id, odd_context, motion_state)
            per_window.append(result)
            if result.get("collision_detected"):
                collisions_detected += 1

        # Auto-save artifact (always, not conditional)
        output_data = {
            "per_window": per_window,
            "windows_analyzed": len(per_window),
            "collision_stats": {"total_windows": len(per_window), "collisions_detected": collisions_detected}
        }

        try:
            json_bytes = json.dumps(output_data, indent=2).encode('utf-8')
            artifact = gtypes.Part.from_bytes(
                data=json_bytes, mime_type="application/json")
            version = await tool_context.save_artifact(filename="collision_output.json", artifact=artifact)
            print(f"🟠 [COLLISION] Auto-saved artifact v{version}")
        except Exception as e:
            print(f"🟠 [COLLISION] Artifact save failed: {e}")

        return {"status": "success", "per_window": per_window, "windows_analyzed": len(per_window), "collisions_detected": collisions_detected}

    return (FunctionTool(func=analyze_all_collision_tool),)
