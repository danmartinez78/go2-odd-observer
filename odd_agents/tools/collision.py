"""
Collision detection tools.
Factory functions that create tools with specific configuration.
"""

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Union
from google.adk.tools import FunctionTool
from google.genai import types
from google import genai

from ..utils import extract_json_block
from .common import get_window_file_paths


# Tool agent version
# v4.0.0: Outputs odd_measurements (strict), explanation, key_insights (flexible)
# v5.0.0: Added save_output_tool for artifact-based data handoff to Evaluator
COLLISION_TOOL_AGENT_VERSION = "5.0.0"


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
        odd_context: dict
    ) -> Dict[str, Any]:
        """Tool: Multimodal collision detection using IMU + camera + BEV.

        Args:
            window_id: Window identifier
            odd_context: Filtered ODD specification from loop agent (minimal context needed)

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

=== PRE-COMPUTED IMU METRICS ===
- peak_accel: {peak_accel:.4f} m/s²
- peak_gyro: {peak_gyro:.4f} rad/s
- peak_jerk: {peak_jerk:.4f} m/s³
- max_tilt: {max_tilt:.2f}°

COLLISION THRESHOLDS:
- Accel >10 m/s² OR gyro >5 rad/s OR jerk >50 m/s³ → likely collision
- BEV: Obstacle penetration into robot zone (exclude 15px center = robot body)
- Camera: Impact blur, scene discontinuity

OUTPUT (JSON only, no markdown):
{{
  "window_id": "{window_id}",
  "collision_detected": true or false,
  "confidence": 0.0-1.0,
  "explanation": "1-2 sentence collision assessment",
  "key_insights": [
    "Notable collision evidence or safety concern (if any)"
  ],
  "proximity_estimate_m": 0.0
}}

ANALYSIS RULES:
1. IMU spikes are primary collision indicator
2. BEV shows obstacle contact (ignore 15px robot center)
3. Camera blur/discontinuity supports collision hypothesis
4. proximity_estimate_m: Nearest obstacle distance from BEV (estimate)

Be CONCISE. Focus on collision YES/NO with reasoning.""")]

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

            llm_data = extract_json_block(response.text or "")

            # === DETERMINISTIC ODD-ALIGNED MEASUREMENTS ===
            # collision_detected is bool (0/1 for COD)
            collision_detected = llm_data.get("collision_detected", False)

            data = {
                "window_id": window_id,
                "odd_measurements": {
                    "collision_detected": 1 if collision_detected else 0,
                    "min_proximity_m": llm_data.get("proximity_estimate_m", 0.0),
                },
                "explanation": llm_data.get("explanation", "Collision analysis from multimodal data"),
                "key_insights": llm_data.get("key_insights", []),
                "collision_detected": collision_detected,
                "confidence": llm_data.get("confidence", 0.0),
            }

            return data

        except Exception as err:
            return {
                "status": "error",
                "window_id": window_id,
                "message": str(err),
                "odd_measurements": {"collision_detected": 0, "min_proximity_m": 0.0},
                "explanation": f"Error: {err}",
                "key_insights": [],
                "collision_detected": False,
                "confidence": 0.0,
            }

    async def save_collision_output_tool(
        per_window: List[Dict[str, Any]],
        temporal_analysis: Dict[str, Any],
        summary_insights: List[str],
        collision_stats: Dict[str, Any],
        tool_context
    ) -> Dict[str, Any]:
        """Save final collision output as artifact for Evaluator to load.

        Args:
            per_window: List of window results, each with {window_id: str, measurements: dict}
                        measurements should contain odd_measurements from analyze tool
            temporal_analysis: Dict with {odd_trends: str, anomalies: list, concerns: list}
            summary_insights: List of key insight strings
            collision_stats: Dict with {total_windows: int, collisions_detected: int}
            tool_context: ADK tool context with artifact service access

        Call this AFTER processing all windows to persist your combined output.
        """
        import google.genai.types as gtypes

        print(
            f"\n🟠 [SAVE_COLLISION_OUTPUT] Called with {len(per_window)} windows")

        try:
            # Build structured output from explicit parameters
            output_data = {
                "per_window": per_window,
                "temporal_analysis": temporal_analysis,
                "summary_insights": summary_insights,
                "collision_stats": collision_stats
            }

            # Serialize output to JSON bytes
            json_bytes = json.dumps(output_data, indent=2).encode('utf-8')
            artifact = gtypes.Part.from_bytes(
                data=json_bytes, mime_type="application/json")

            # Save as artifact
            version = await tool_context.save_artifact(
                filename="collision_output.json",
                artifact=artifact
            )

            print(f"🟠 [SAVE_COLLISION_OUTPUT] Saved artifact v{version}")

            return {
                "status": "saved",
                "artifact": "collision_output.json",
                "version": version,
                "windows_saved": len(per_window)
            }
        except Exception as e:
            print(f"🟠 [SAVE_COLLISION_OUTPUT] Error: {e}")
            return {"status": "error", "message": str(e)}

    # Return FunctionTool wrappers (analyze + save)
    return (
        FunctionTool(func=analyze_collision_tool),
        FunctionTool(func=save_collision_output_tool)
    )
