"""
Collision detection tools.
Factory functions that create tools with specific configuration.

v10.0.0: Multi-modal collision detection with convergent evidence:
- Requires BOTH motion anomaly AND visual/BEV proximity for collision
- Sudden stop alone is NOT sufficient - must see close obstacle
- Enhanced VLM prompt with explicit decision logic
- New evidence_summary in output for transparency

v9.0.0: Enhanced collision detection:
- Uses derived_speed for motion state detection (works for real robot)
- Position-based collision signatures (sudden stops, trajectory anomalies)
- Reports data_availability dict for transparency
- IMU still used for impact detection when available
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
# v9.0.0: Use derived_speed for motion state, add position-based collision detection, data_availability
# v10.0.0: Multi-modal reasoning - require convergent evidence (motion + visual) for collision detection
COLLISION_TOOL_AGENT_VERSION = "10.0.0"


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
        """Internal: Analyze one window for collision (called by batch tool).

        Data sources:
        - Speed: derived_speed (position-based, always available)
        - Impact detection: IMU accel when valid, else speed changes
        - Angular: IMU gyro when valid, else derived_yaw_rate
        - Proximity: BEV occupancy min_obstacle_distance
        """
        import cv2
        import base64

        try:
            file_paths = get_window_file_paths(scenario_path, window_id)
            motion_file = file_paths["motion"]
            cam_file = file_paths["camera"]
            bev_occupancy = file_paths.get("bev_occupancy")

            if not motion_file.exists():
                return {"status": "error", "window_id": window_id, "message": "Motion file not found"}

            # Load motion data
            with open(motion_file, 'r') as f:
                motion_data = json.load(f)

            # IMU data
            accel_x = motion_data.get("accel_x", [])
            accel_y = motion_data.get("accel_y", [])
            gyro_z = motion_data.get("gyro_z", [])
            roll = motion_data.get("roll", [])
            pitch = motion_data.get("pitch", [])
            timestamps = motion_data.get("timestamps", [])

            # Derived motion data (position-based)
            derived_speed = motion_data.get("derived_speed", [])
            derived_yaw_rate = motion_data.get("derived_yaw_rate", [])
            pos_x = motion_data.get("pos_x", [])
            pos_y = motion_data.get("pos_y", [])

            # Check data availability
            imu_accel_valid = any(
                abs(ax) > 1e-6 for ax in accel_x) or any(abs(ay) > 1e-6 for ay in accel_y)
            imu_gyro_valid = any(abs(gz) > 1e-6 for gz in gyro_z)
            has_derived_speed = bool(derived_speed) and any(
                s > 1e-6 for s in derived_speed)
            has_position = bool(pos_x) and bool(pos_y)

            # === MOTION STATE: Use derived_speed (most reliable) ===
            peak_speed = max(derived_speed) if has_derived_speed else 0.0
            avg_speed = sum(derived_speed) / \
                len(derived_speed) if derived_speed else 0.0
            is_stationary = peak_speed < 0.05  # <5 cm/s

            # === IMU METRICS (when available) ===
            peak_accel = None
            peak_gyro = None
            peak_jerk = None
            max_tilt = 0.0

            if imu_accel_valid:
                horiz_accel = [math.sqrt(ax**2 + ay**2) for ax, ay in zip(accel_x, accel_y)
                               if abs(ax) > 1e-6 or abs(ay) > 1e-6]
                peak_accel = max(horiz_accel) if horiz_accel else 0.0

                # Jerk from acceleration changes
                if len(horiz_accel) > 1 and len(timestamps) > 1:
                    jerk_samples = []
                    for i in range(1, min(len(horiz_accel), len(timestamps))):
                        dt = timestamps[i] - timestamps[i-1]
                        if dt > 0.01:  # MIN_DT_THRESHOLD
                            jerk_samples.append(
                                abs(horiz_accel[i] - horiz_accel[i-1]) / dt)
                    peak_jerk = max(jerk_samples) if jerk_samples else 0.0

            if imu_gyro_valid:
                gyro_valid = [abs(gz) for gz in gyro_z if abs(gz) > 1e-6]
                peak_gyro = max(gyro_valid) if gyro_valid else 0.0

            if roll and pitch:
                max_tilt = max(max(abs(r) for r in roll),
                               max(abs(p) for p in pitch))

            # === POSITION-BASED COLLISION SIGNATURES ===
            sudden_stop_detected = False
            speed_drop = 0.0
            if has_derived_speed and len(derived_speed) > 2:
                # Check for sudden speed drops (collision signature)
                for i in range(1, len(derived_speed)):
                    drop = derived_speed[i-1] - derived_speed[i]
                    if drop > 0.3:  # >0.3 m/s sudden drop
                        sudden_stop_detected = True
                        speed_drop = max(speed_drop, drop)

            # Displacement analysis
            total_displacement = 0.0
            if has_position and len(pos_x) > 1:
                dx = pos_x[-1] - pos_x[0]
                dy = pos_y[-1] - pos_y[0]
                total_displacement = math.sqrt(dx**2 + dy**2)

            # === BEV PROXIMITY ===
            bev_metrics = {"computed": False}
            if bev_occupancy and bev_occupancy.exists():
                bev_img = cv2.imread(str(bev_occupancy), cv2.IMREAD_GRAYSCALE)
                bev_metrics = compute_bev_metrics(
                    bev_img, resolution_m_per_px=0.05, self_hit_radius_px=15)

            min_dist = bev_metrics.get('min_obstacle_distance_m', 2.5) or 2.5

            # === BUILD DATA AVAILABILITY ===
            data_availability = {
                "speed": "derived" if has_derived_speed else "unavailable",
                "acceleration": "imu" if imu_accel_valid else "unavailable",
                "angular_velocity": "imu" if imu_gyro_valid else ("derived" if derived_yaw_rate else "unavailable"),
                "position": "available" if has_position else "unavailable",
                "bev_proximity": "computed" if bev_metrics.get("computed") else "unavailable",
            }

            # Build metrics string based on availability
            accel_str = f"{peak_accel:.3f}" if peak_accel is not None else "N/A"
            gyro_str = f"{peak_gyro:.3f}" if peak_gyro is not None else "N/A"
            jerk_str = f"{peak_jerk:.3f}" if peak_jerk is not None else "N/A"

            prompt = f"""COLLISION DETECTION for window {window_id}. ADVISORY ONLY.

You have MULTIPLE data sources. Analyze ALL of them before deciding.

═══════════════════════════════════════════════════════════════════════════════
DATA SOURCES AVAILABLE
═══════════════════════════════════════════════════════════════════════════════
{', '.join(f'{k}: {v}' for k,v in data_availability.items())}

MOTION DATA:
- Speed: peak={peak_speed:.3f} m/s, avg={avg_speed:.3f} m/s (position-derived)
- Sudden stop detected: {sudden_stop_detected} (speed drop: {speed_drop:.2f} m/s)
- Displacement: {total_displacement:.2f}m
- Is stationary: {is_stationary}

IMU DATA (if available):
- Peak acceleration: {accel_str} m/s²
- Peak angular velocity: {gyro_str} rad/s  
- Peak jerk: {jerk_str} m/s³

BEV PROXIMITY:
- Minimum obstacle distance: {min_dist:.2f}m (from occupancy map)

═══════════════════════════════════════════════════════════════════════════════
COLLISION DECISION LOGIC - MULTI-MODAL EVIDENCE REQUIRED
═══════════════════════════════════════════════════════════════════════════════

A collision requires CONVERGENT EVIDENCE from multiple sources:

✅ COLLISION LIKELY (confidence >0.7) - requires BOTH:
   1. Motion anomaly: sudden stop (>0.5 m/s drop) OR high impact accel (>15 m/s²)
   2. Visual confirmation: obstacle <0.3m in BEV OR camera shows contact/very close object

✅ COLLISION POSSIBLE (confidence 0.4-0.7) - requires BOTH:
   1. Motion anomaly: sudden stop OR unusual deceleration
   2. Proximity evidence: obstacle <0.5m in BEV OR camera shows close obstacle

❌ NOT A COLLISION - any of these:
   - Sudden stop but NO close obstacles visible (<0.5m) → commanded stop
   - Close obstacle but NO motion anomaly → normal navigation
   - Robot stationary with no impact signature
   - Motion changes are gradual, not sudden

⚠️ CRITICAL: A sudden stop ALONE is NOT collision evidence!
   Robots frequently stop quickly due to commands or path planning.
   You MUST see something close (<0.5m) in camera or BEV to confirm collision.

═══════════════════════════════════════════════════════════════════════════════
IMAGE ANALYSIS REQUIREMENTS  
═══════════════════════════════════════════════════════════════════════════════

CAMERA IMAGE - Examine carefully for:
- Objects very close to camera (large in frame, near bottom edge)
- Signs of contact (blur, object touching/filling frame)
- Context: tight space vs open area?

BEV OCCUPANCY - Look for:
- Occupied pixels within 0.3m of center = collision zone
- Occupied pixels 0.3-0.5m = close proximity zone
- Note: Small clusters at robot center may be self-hits (ignore)

SIMULATION NOTE: Large uniform gray areas are sim boundaries, NOT obstacles.

═══════════════════════════════════════════════════════════════════════════════
OUTPUT (JSON only)
═══════════════════════════════════════════════════════════════════════════════
{{
  "collision_detected": <true ONLY if motion anomaly AND visual proximity both present>,
  "confidence": <0.0-1.0>,
  "evidence_summary": {{
    "motion_anomaly_present": <true if sudden stop or high accel>,
    "visual_proximity_confirmed": <true if obstacle <0.5m in camera/BEV>,
    "closest_obstacle_m": <your estimate from BEV/camera>
  }},
  "proximity_estimate_m": {min_dist:.2f},
  "collision_risk_band": "LOW|MED|HIGH",
  "explanation": "<state what motion AND visual evidence you found, or why evidence was insufficient>"
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

            # Extract evidence summary from LLM response (with defaults)
            evidence_summary = llm_data.get("evidence_summary", {})
            if not evidence_summary:
                # Fallback if LLM didn't provide evidence_summary
                evidence_summary = {
                    "motion_anomaly_present": sudden_stop_detected or (peak_accel is not None and peak_accel > 10),
                    "visual_proximity_confirmed": min_dist < 0.5,
                    "closest_obstacle_m": min_dist
                }

            return {
                "window_id": window_id,
                "odd_measurements": {},
                "data_availability": data_availability,
                "collision_detected": bool(llm_data.get("collision_detected", False)),
                "confidence": llm_data.get("confidence", 0.0),
                "proximity_estimate_m": llm_data.get("proximity_estimate_m", min_dist),
                "collision_risk_band": llm_data.get("collision_risk_band", "LOW"),
                "evidence_summary": evidence_summary,
                "collision_signatures": {
                    "sudden_stop": sudden_stop_detected,
                    "speed_drop_mps": round(speed_drop, 3),
                    "peak_accel_mps2": round(peak_accel, 3) if peak_accel is not None else None,
                    "peak_jerk_mps3": round(peak_jerk, 3) if peak_jerk is not None else None,
                },
                "motion_metrics": {
                    "peak_speed_mps": round(peak_speed, 3),
                    "is_stationary": is_stationary,
                    "displacement_m": round(total_displacement, 3),
                },
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
