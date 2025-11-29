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
# v6.0.0: Bulletproof prompt - full BEV interpretation, threshold comparison, decision logic
# v6.1.0: BEV-first collision detection, cropping awareness, sim/real voxel map detection, LiDAR 180° FOV
# v6.2.0: Add advisory collision risk (proximity/density/motion) alongside binary collisions
# v7.0.0: FULLY ADVISORY output (no ODD effect), motion-state gating, duplicate clustering guidance
COLLISION_TOOL_AGENT_VERSION = "7.0.0"


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
        motion_state: dict = None
    ) -> Dict[str, Any]:
        """Tool: Multimodal collision detection using IMU + camera + BEV, plus advisory risk.

        IMPORTANT: Collision output is ADVISORY ONLY - does NOT affect ODD/COD verdict.
        Collisions are safety events to report, not operational domain characteristics.

        Args:
            window_id: Window identifier
            odd_context: Filtered ODD specification from loop agent (minimal context needed)
            motion_state: Optional motion agent output {is_stationary: {value, confidence, evidence}}
                          Used for motion-state gating to avoid false positives when stationary

        Analyzes collision evidence from:
        - IMU data (acceleration spikes, angular velocity anomalies)
        - Camera visual evidence (impact blur, sudden scene changes)
        - BEV occupancy (contact with obstacles, excluding robot self-hit)

        Returns: collision detected (yes/no) with detailed evidence - ADVISORY ONLY.
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
            # Include motion state if provided for motion-state gating
            motion_state_str = ""
            if motion_state and motion_state.get("is_stationary"):
                is_stat = motion_state["is_stationary"]
                motion_state_str = f"""
MOTION STATE CONTEXT (from Motion Agent):
- Is Stationary: {is_stat.get('value', 'unknown')}
- Confidence: {is_stat.get('confidence', 0.0):.2f}
- Evidence: {is_stat.get('evidence', 'Not provided')}

MOTION-STATE GATING RULE:
If motion state is STATIONARY with high confidence (>0.8):
- Require STRONG evidence for collision detection (IMU spike >10 m/s² OR visual contact)
- Downgrade ambiguous evidence to "info" not collision
- A stationary robot cannot collide unless something hits IT
"""

            prompt_parts = [types.Part(text=f"""You are a collision detection expert analyzing window {window_id}.

═══════════════════════════════════════════════════════════════════════════════
IMPORTANT: ADVISORY OUTPUT ONLY
═══════════════════════════════════════════════════════════════════════════════

Your collision analysis is ADVISORY ONLY and does NOT affect ODD/COD compliance.
- Collisions are safety events to report, not operational domain characteristics
- A robot can be IN_ODD and still experience a collision (user error, unexpected obstacle)
- Report honestly but understand this is for awareness, not verdict

═══════════════════════════════════════════════════════════════════════════════
SENSOR INPUTS
═══════════════════════════════════════════════════════════════════════════════
{motion_state_str}
PRE-COMPUTED IMU METRICS:
- Peak horizontal acceleration: {peak_accel:.4f} m/s²
- Peak angular velocity (yaw): {peak_gyro:.4f} rad/s
- Peak jerk: {peak_jerk:.4f} m/s³
- Max platform tilt: {max_tilt:.2f}°

IMAGES PROVIDED:
- Camera: RGB forward-facing view (impact blur, obstacle contact)
- BEV Occupancy: Bird's eye obstacle map (400x400px, 0.05m/pixel, robot at center)
- BEV Height: Terrain elevation map
- BEV Roughness: Surface variation map

═══════════════════════════════════════════════════════════════════════════════
BEV INTERPRETATION GUIDE
═══════════════════════════════════════════════════════════════════════════════

BEV OCCUPANCY (Obstacles):
- AUTO-CROPPED to occupied region (typically 150-250px, varies per window)
- Scale: 0.05m per pixel (20px = 1m, 40px = 2m) - SCALE IS PRESERVED after cropping
- Robot is ALWAYS at CENTER of cropped image, facing UPWARD (top = forward)
- BRIGHT pixels = OBSTACLES (objects >10cm above ground)
- DARK pixels = FREE SPACE (navigable)
- CRITICAL: Small bright cluster at center (~15px radius) = robot body/LiDAR self-hit - IGNORE THIS
- NOTE: Image size varies - use pixel distance from center × 0.05 for meters

PROXIMITY ESTIMATION FROM BEV:
- Measure pixels from center to nearest bright obstacle cluster
- Convert: distance_m = pixels × 0.05
- Example: 40 bright pixels from center = 2.0m proximity
- Use proximity + density + motion state to assign collision risk (LOW/MED/HIGH). Stationary runs with clear distance should be LOW unless strong evidence says otherwise.

═══════════════════════════════════════════════════════════════════════════════
BEV DATA SOURCE DETECTION (Infer from BEV visual characteristics)
═══════════════════════════════════════════════════════════════════════════════

LIDAR CONFIGURATION:
- 180° FORWARD-FACING FOV (both sim and real)
- Robot at CENTER of BEV, facing UPWARD (top = forward)
- Upper half = forward path (primary LiDAR coverage)
- Lower half = rear (no direct coverage, may be empty or filled from accumulation)

SIMULATED DATA (Single LiDAR Scan at timestamp):
- Sharp, thin obstacle edges
- Small self-hit zone at center (~15px radius)
- Clean, minimal noise
- Precise geometric features
- Lower half likely empty (180° FOV, no rear coverage)

REAL DATA (Accumulated Voxel Map over time):
- Thickened/blurred obstacle edges (accumulation from multiple poses)
- Larger self-hit zone at center (~20-30px) from robot motion over time
- More scattered noise, possible ghost artifacts from moved objects
- Registration drift may cause duplicated/offset features
- Lower half may have older accumulated data (filled in from prior motion)
- Thickened walls ≠ larger obstacles, it's accumulation artifact

CRITICAL FOR COLLISION DETECTION:
- Trust UPPER HALF (forward path) more than LOWER HALF (rear)
- Expect larger exclusion zone at center for real data self-hits (~20-30px vs ~15px)
- Isolated single bright pixels = likely noise, not obstacles
- Real obstacles form connected clusters of bright pixels
- Sparse rear coverage is NORMAL for 180° FOV, not sensor failure

═══════════════════════════════════════════════════════════════════════════════
COLLISION DETECTION THRESHOLDS
═══════════════════════════════════════════════════════════════════════════════

PRIMARY COLLISION INDICATORS (any one strongly suggests collision):
1. Acceleration spike: peak_accel > 10.0 m/s² (sudden impact deceleration)
2. Angular velocity anomaly: peak_gyro > 5.0 rad/s (severe spin/tip-over)
3. Jerk spike: peak_jerk > 50.0 m/s³ (sudden acceleration change)

CURRENT VALUES vs THRESHOLDS:
- Acceleration: {peak_accel:.4f} m/s² (threshold: 10.0) → {"⚠️ EXCEEDS" if peak_accel > 10.0 else "✓ Below"}
- Angular velocity: {peak_gyro:.4f} rad/s (threshold: 5.0) → {"⚠️ EXCEEDS" if peak_gyro > 5.0 else "✓ Below"}
- Jerk: {peak_jerk:.4f} m/s³ (threshold: 50.0) → {"⚠️ EXCEEDS" if peak_jerk > 50.0 else "✓ Below"}

SECONDARY INDICATORS (supporting evidence):
- BEV: Obstacle pixels penetrating robot zone (beyond 15px center exclusion)
- Camera: Impact blur, scene discontinuity, visible contact with obstacle
- Tilt: Sudden large tilt change may indicate tip-over

═══════════════════════════════════════════════════════════════════════════════
COLLISION ANALYSIS FRAMEWORK (BEV-PRIMARY WITH CONFIRMATION)
═══════════════════════════════════════════════════════════════════════════════

1. BEV-FIRST APPROACH (Primary Evidence):
   - BEV occupancy is GROUND TRUTH - LiDAR physically detected objects
   - Check BEV for obstacles in robot contact zone (20-50px from center)
   - CRITICAL: IGNORE 15px center radius (robot body / LiDAR self-hits)

2. CONFIRMATION REQUIRED (Rules Out Self-Hits):
   IF BEV shows obstacle in robot zone:
     - Camera confirms obstacle visible in that direction? → REAL OBSTACLE
     - IMU shows impact spike (accel >3-5 m/s²)? → PHYSICAL CONTACT
     - EITHER confirms → collision_detected = true
     - NEITHER confirms → likely SELF-HIT ARTIFACT → collision_detected = false

3. SELF-HIT DETECTION:
   - Small bright clusters at exact BEV center = robot legs/body
   - If BEV shows contact BUT camera shows clear path AND IMU is calm
     → This is a self-hit false positive, NOT a collision

4. EDGE CASE - IMU SPIKE WITHOUT BEV CONTACT:
   - If IMU spike >10 m/s² but no BEV obstacle → unmapped collision
   - collision_detected = true (high confidence)

5. CONFIDENCE CALIBRATION:
   - High (0.9+): BEV contact + camera confirms + IMU spike
   - Medium-High (0.7-0.9): BEV contact + camera OR IMU confirms
   - Medium (0.5-0.7): BEV contact but neither confirms (ambiguous)
   - Low (<0.5): No BEV contact, no significant IMU (no collision)

═══════════════════════════════════════════════════════════════════════════════
OUTPUT FORMAT (JSON ONLY - NO MARKDOWN)
═══════════════════════════════════════════════════════════════════════════════

{{
  "window_id": "{window_id}",
  "collision_detected": false,
  "confidence": 0.95,
  "proximity_estimate_m": 2.5,
  "collision_risk_score": 0.1,
  "collision_risk_band": "LOW",
  "collision_risk_justification": "Nearest obstacle ~2.5m; density low; robot stationary",
  "explanation": "No collision indicators. IMU values well below thresholds (accel: 0.21 m/s², gyro: 0.02 rad/s). BEV shows clear forward path with nearest obstacle ~2.5m away. Camera shows stable scene.",
  "key_insights": [
    "All IMU metrics below collision thresholds",
    "Clear forward path in BEV occupancy"
  ]
}}

═══════════════════════════════════════════════════════════════════════════════
CRITICAL RULES
═══════════════════════════════════════════════════════════════════════════════

1. collision_detected MUST be true or false (boolean) - but is ADVISORY ONLY
2. IMU thresholds are PRIMARY - if exceeded, collision is likely true
3. IGNORE bright pixels at BEV center (~15px radius) - that's robot body
4. proximity_estimate_m: Distance to nearest obstacle from BEV (20px = 1m)
5. Provide advisory collision_risk_score/band from proximity + density + motion
6. Output JSON only - no markdown code blocks

MOTION-STATE GATING:
- If motion_state shows stationary with high confidence (>0.8):
  - Require STRONGER evidence for collision (IMU >10 m/s² OR visible contact)
  - Ambiguous proximity without IMU spike when stationary → NOT a collision
  - A stationary robot only collides if something hits IT

COLLISION CLUSTERING (Avoid Duplicate Counts):
- Multiple proximity events in same window with similar evidence → ONE collision
- Ramp traversal may cause repeated light bumps → cluster as ONE ramp contact event
- Count unique collision events, not every spike that could be same impact

DECISION LOGIC:
IF (BEV shows obstacle in robot zone, beyond 15px center):
    IF (camera shows obstacle nearby OR peak_accel > 3.0):
        collision_detected = true (confirmed real obstacle)
    ELSE:
        collision_detected = false (likely self-hit artifact)
ELSE IF (peak_accel > 10.0 OR peak_gyro > 5.0 OR peak_jerk > 50.0):
    collision_detected = true (IMU spike without BEV = unmapped collision)
ELSE:
    collision_detected = false (no collision evidence)""")]

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
            collision_detected = bool(
                llm_data.get("collision_detected", False))
            risk_score = llm_data.get("collision_risk_score", 0.0) or 0.0
            risk_band = llm_data.get("collision_risk_band") or "LOW"
            risk_justification = llm_data.get(
                "collision_risk_justification") or ""

            data = {
                "window_id": window_id,
                # Keep ODD/COD measurements empty to avoid treating collisions as ODD axes
                "odd_measurements": {},
                "explanation": llm_data.get("explanation", "Collision analysis from multimodal data"),
                "key_insights": llm_data.get("key_insights", []),
                "collision_detected": collision_detected,
                "confidence": llm_data.get("confidence", 0.0),
                "proximity_estimate_m": llm_data.get("proximity_estimate_m", 0.0),
                "collision_risk_score": risk_score,
                "collision_risk_band": risk_band,
                "collision_risk_justification": risk_justification,
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
