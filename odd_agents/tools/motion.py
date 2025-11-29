"""
Motion analysis tools.
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
# v6.0.0: Bulletproof prompt - gravity vs motion reasoning, camera priority, temporal patterns
# v6.1.0: Image artifact awareness (compression, blur, noise vs motion detection)
# v7.0.0: Added is_stationary with confidence, clearer roll/pitch reporting with max+windows+rationale
MOTION_TOOL_AGENT_VERSION = "7.0.0"


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

    async def analyze_motion_tool(window_id: str, odd_context: dict) -> Dict[str, Any]:
        """
        Tool: Analyze robot motion using IMU sensor data and optional camera visual odometry.

        Args:
            window_id: Window identifier
            odd_context: Filtered ODD specification from loop agent (relevant ego dimensions)

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

═══════════════════════════════════════════════════════════════════════════════
SENSOR INPUTS
═══════════════════════════════════════════════════════════════════════════════

**IMPORTANT**: Wheel odometry is UNAVAILABLE/UNRELIABLE. Use only IMU and camera.

IMAGE: RGB camera frame (forward-facing) - use for visual motion evidence

PRE-COMPUTED IMU METRICS:
- Peak horizontal acceleration: {peak_horiz_accel:.4f} m/s²
- Average horizontal acceleration: {avg_horiz_accel:.4f} m/s²
- Peak yaw rate (gyro_z): {peak_gyro_z:.4f} rad/s
- Peak roll rate (gyro_x): {peak_gyro_x:.4f} rad/s
- Peak pitch rate (gyro_y): {peak_gyro_y:.4f} rad/s
- Max roll angle: {max_roll:.2f}°
- Max pitch angle: {max_pitch:.2f}°
- Peak jerk: {peak_jerk:.4f} m/s³
- Average jerk: {avg_jerk:.4f} m/s³

═══════════════════════════════════════════════════════════════════════════════
ODD CONTEXT (Axes to evaluate)
═══════════════════════════════════════════════════════════════════════════════
{json.dumps(odd_context, indent=2) if odd_context else "No ODD context provided - use default motion metrics"}

═══════════════════════════════════════════════════════════════════════════════
MOTION REASONING FRAMEWORK (CRITICAL - READ CAREFULLY)
═══════════════════════════════════════════════════════════════════════════════

1. IMU ACCELEROMETER INTERPRETATION:
   - Small constant acceleration (<1.0 m/s²) + platform tilt = GRAVITY LEAKAGE, not motion
   - Reference: 1° of tilt contributes ~0.17 m/s² to horizontal acceleration
   - True translation shows VARYING acceleration patterns, not constant values
   - Stationary robot on tilted platform shows steady horizontal accel from gravity
   - Example: pitch=1.25° and roll=-0.74° → ~0.21 m/s² horizontal (NOT motion!)

2. CAMERA VISUAL EVIDENCE (PRIMARY MOTION INDICATOR):
   - Sharp textures, clear edges, no blur → STATIONARY or very slow
   - Blurred edges, motion streaks → MOVING at significant speed
   - Visible optical flow, scene shift → Active translation
   - Stable static scene → STATIONARY
   - CRITICAL: Camera evidence OVERRIDES IMU when they conflict!

   IMAGE ARTIFACT WARNING (Real Camera Data):
   - JPEG compression artifacts: Blocky patterns, ringing around edges - NOT motion
   - Lens blur/defocus: Uniform soft focus across image - NOT motion blur
   - Rolling shutter: Diagonal distortion of vertical lines - may indicate motion OR artifact
   - Sensor noise: Grainy/speckled appearance, especially in low light - NOT motion
   - Exposure issues: Over/underexposed areas, washed out regions - NOT motion evidence
   
   MOTION BLUR vs ARTIFACTS:
   - True motion blur: Directional streaking along motion vector, sharp→blurred transition
   - Compression artifact: Block-shaped, affects entire image uniformly
   - Defocus blur: Circular/uniform blur, no directional component
   - If blur is UNIFORM across frame → likely artifact, not motion
   - If blur is DIRECTIONAL with clear motion vector → likely real motion

3. GYROSCOPE ANALYSIS:
   - Very small values (<0.05 rad/s) = sensor noise/drift, NOT rotation
   - Sustained varying angular velocity = genuine rotation
   - Constant low values = stationary with sensor bias

4. JERK ANALYSIS (Smoothness):
   - Low jerk (<5 m/s³): Smooth motion or stationary
   - High jerk (>10 m/s³): Abrupt starts/stops, actual dynamic maneuvers
   - Very high jerk (>50 m/s³): Possible collision or impact

5. PLATFORM STABILITY:
   - Roll/pitch < 5°: Stable, flat surface
   - Roll/pitch 5-15°: Mild incline or uneven terrain
   - Roll/pitch > 15°: Unstable, climbing, or on significant slope

═══════════════════════════════════════════════════════════════════════════════
DECISION PRIORITY (in order of reliability)
═══════════════════════════════════════════════════════════════════════════════

1. Camera visual evidence (most reliable for motion detection)
2. Temporal patterns in IMU (varying = motion, constant = artifact)
3. Gyroscope for rotation detection
4. Accelerometer magnitude (only after gravity/tilt compensation)

CRITICAL RULE:
If camera shows SHARP, CLEAR images BUT IMU shows acceleration:
→ Check if acceleration is constant and small (<1.0 m/s²)
→ Check if platform tilt explains the acceleration
→ If yes to both: Classify as STATIONARY (gravity leakage artifact)

═══════════════════════════════════════════════════════════════════════════════
MOTION STATE CLASSIFICATION
═══════════════════════════════════════════════════════════════════════════════

- "stationary": No visual motion AND (low varying accel OR constant accel matching tilt)
- "moving": Camera shows optical flow/blur AND varying acceleration pattern
- "rotating": Sustained gyro activity with scene rotation but no translation
- "complex": Both rotation and translation with corresponding IMU patterns

═══════════════════════════════════════════════════════════════════════════════
STATIONARITY OUTPUT (Required for cross-agent consistency)
═══════════════════════════════════════════════════════════════════════════════

"is_stationary": {{
  "value": true/false,
  "confidence": 0.0-1.0,
  "evidence": "Brief description of why stationary/not"
}}

Use high confidence (>0.9) when camera and IMU agree.
Use lower confidence (0.5-0.8) when evidence is mixed.
This output is CRITICAL for collision agent to use for motion-state gating.

═══════════════════════════════════════════════════════════════════════════════
ROLL/PITCH REPORTING (Detailed)
═══════════════════════════════════════════════════════════════════════════════

"roll_pitch_analysis": {{
  "max_roll_deg": <float>,
  "max_pitch_deg": <float>,
  "roll_concern": "none" | "mild" | "moderate" | "severe",
  "pitch_concern": "none" | "mild" | "moderate" | "severe",
  "rationale": "Why this concern level (e.g., 'Within normal indoor operation', 'Indicates ramp traversal')"
}}

Concern levels:
- none: <5° - Normal indoor operation
- mild: 5-10° - Minor incline or terrain variation
- moderate: 10-15° - Significant slope, near ODD boundary
- severe: >15° - Likely out of ODD, steep terrain or instability

═══════════════════════════════════════════════════════════════════════════════
OUTPUT FORMAT (JSON ONLY - NO MARKDOWN)
═══════════════════════════════════════════════════════════════════════════════

{{
  "window_id": "{window_id}",
  "motion_state": "stationary",
  "is_stationary": {{
    "value": true,
    "confidence": 0.95,
    "evidence": "Sharp camera image with no blur, constant IMU values match platform tilt"
  }},
  "roll_pitch_analysis": {{
    "max_roll_deg": 0.74,
    "max_pitch_deg": 1.25,
    "roll_concern": "none",
    "pitch_concern": "none",
    "rationale": "Both well within normal indoor operation (<5°)"
  }},
  "explanation": "Camera shows sharp, static indoor scene. IMU acceleration of 0.21 m/s² is explained by 1.2° platform tilt (gravity leakage). No evidence of actual motion.",
  "key_insights": [
    "Sharp camera image confirms stationary state",
    "Small IMU acceleration attributed to platform tilt, not motion"
  ]
}}

RULES:
1. Camera evidence OVERRIDES IMU when they conflict
2. Account for gravity leakage before concluding motion from accelerometer
3. ALWAYS output is_stationary with confidence - collision agent depends on this
4. ALWAYS output roll_pitch_analysis with concern level and rationale
5. Explain your reasoning, especially when camera and IMU appear to conflict
6. Output JSON only - no markdown code blocks""")]

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

            llm_data = extract_json_block(response.text or "")

            # === DETERMINISTIC ODD-ALIGNED MEASUREMENTS ===
            # These are computed directly from sensor data, not LLM output
            # Maps raw metrics to ODD axis names for COD construction
            data = {
                "window_id": window_id,
                "odd_measurements": {
                    "max_accel_mps2": round(peak_horiz_accel, 4),
                    "max_speed_mps": 0.0,  # Cannot estimate from IMU alone
                    "max_angular_velocity_radps": round(peak_gyro_z, 4),
                    "max_roll_deg": round(max_roll, 2),
                    "max_pitch_deg": round(max_pitch, 2),
                    "peak_jerk_mps3": round(peak_jerk, 4),
                },
                "is_stationary": llm_data.get("is_stationary", {
                    "value": False,
                    "confidence": 0.5,
                    "evidence": "Not determined"
                }),
                "roll_pitch_analysis": llm_data.get("roll_pitch_analysis", {
                    "max_roll_deg": round(max_roll, 2),
                    "max_pitch_deg": round(max_pitch, 2),
                    "roll_concern": "none" if max_roll < 5 else "mild" if max_roll < 10 else "moderate" if max_roll < 15 else "severe",
                    "pitch_concern": "none" if max_pitch < 5 else "mild" if max_pitch < 10 else "moderate" if max_pitch < 15 else "severe",
                    "rationale": "Computed from max values"
                }),
                "explanation": llm_data.get("explanation", "Motion analysis from IMU data"),
                "key_insights": llm_data.get("key_insights", []),
                "motion_state": llm_data.get("motion_state", "unknown"),
            }

            return data

        except Exception as err:
            return {
                "status": "error",
                "window_id": window_id,
                "message": str(err),
                "odd_measurements": {},
                "explanation": f"Error: {err}",
                "key_insights": [],
                "motion_state": "error",
            }

    async def save_motion_output_tool(
        per_window: List[Dict[str, Any]],
        temporal_analysis: Dict[str, Any],
        summary_insights: List[str],
        tool_context
    ) -> Dict[str, Any]:
        """Save final motion output as artifact for Evaluator to load.

        Args:
            per_window: List of window results, each with {window_id: str, measurements: dict}
                        measurements should contain odd_measurements from analyze tool
            temporal_analysis: Dict with {odd_trends: str, anomalies: list, concerns: list}
            summary_insights: List of key insight strings
            tool_context: ADK tool context with artifact service access

        Call this AFTER processing all windows to persist your combined output.
        """
        import google.genai.types as gtypes

        print(
            f"\n🟢 [SAVE_MOTION_OUTPUT] Called with {len(per_window)} windows")

        try:
            # Build structured output from explicit parameters
            output_data = {
                "per_window": per_window,
                "temporal_analysis": temporal_analysis,
                "summary_insights": summary_insights
            }

            # Serialize output to JSON bytes
            json_bytes = json.dumps(output_data, indent=2).encode('utf-8')
            artifact = gtypes.Part.from_bytes(
                data=json_bytes, mime_type="application/json")

            # Save as artifact
            version = await tool_context.save_artifact(
                filename="motion_output.json",
                artifact=artifact
            )

            print(f"🟢 [SAVE_MOTION_OUTPUT] Saved artifact v{version}")

            return {
                "status": "saved",
                "artifact": "motion_output.json",
                "version": version,
                "windows_saved": len(per_window)
            }
        except Exception as e:
            print(f"🟢 [SAVE_MOTION_OUTPUT] Error: {e}")
            return {"status": "error", "message": str(e)}

    # Return FunctionTool wrappers (analyze + save)
    return (
        FunctionTool(func=analyze_motion_tool),
        FunctionTool(func=save_motion_output_tool)
    )
