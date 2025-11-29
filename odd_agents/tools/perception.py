"""
Perception analysis tools.
Factory functions that create tools with specific configuration.

v6.0.0: Bulletproof FunctionTool prompts (reverted from AgentTool brittleness)
- Self-contained prompts with full BEV/camera interpretation guidance
- No dependency on knowledge base (tools don't have access)
- Explicit schema, examples, and anti-patterns
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Union
from google.adk.tools import FunctionTool
from google.genai import types
from google import genai

from ..utils import build_image_path, ensure_image_bytes, extract_json_block
from .common import list_available_windows, get_window_file_paths


# Tool version
# v5.1.0: Added data_source detection (sim vs real)
# v6.0.0: Bulletproof FunctionTool - verbose prompts, no KB dependency
# v6.1.0: BEV cropping awareness, sim/real voxel map detection, image artifact guidance, LiDAR 180° FOV
PERCEPTION_TOOL_VERSION = "6.1.0"


def create_perception_tools(scenario_path: Union[str, Path], genai_client: genai.Client, model: str, api_key: str = None):
    """
    Create perception analysis tools for a specific scenario.

    Args:
        scenario_path: Path to scenario directory
        genai_client: Configured Gemini client
        model: Model name for perception analysis
        api_key: API key (unused in FunctionTool, kept for interface compatibility)

    Returns:
        Tuple of (list_windows_tool, analyze_window_perception_tool, save_perception_output_tool)
    """
    scenario_path = Path(scenario_path) if isinstance(
        scenario_path, str) else scenario_path

    async def list_windows_tool() -> Dict[str, Any]:
        """List available window IDs for this scenario."""
        try:
            windows = list_available_windows(
                scenario_path, require_motion=True)
            return {"status": "success", "windows": windows, "count": len(windows)}
        except FileNotFoundError as e:
            return {"status": "error", "message": str(e)}

    async def analyze_window_perception_tool(window_id: str, odd_context: dict) -> Dict[str, Any]:
        """Analyze camera + LiDAR BEV for one window.

        Args:
            window_id: Window identifier (e.g., "010")
            odd_context: ODD specification from parent agent (used to select relevant axes)
        """
        try:
            file_paths = get_window_file_paths(scenario_path, window_id)
            camera_bytes = ensure_image_bytes(file_paths["camera"])
            bev_occupancy_bytes = ensure_image_bytes(
                file_paths["bev_occupancy"])
            bev_height_bytes = ensure_image_bytes(file_paths["bev_height"])
            bev_roughness_bytes = ensure_image_bytes(
                file_paths["bev_roughness"])

            # Build comprehensive prompt with all guidance embedded
            prompt = f"""You are a perception expert analyzing synchronized robot sensors for window {window_id}.

═══════════════════════════════════════════════════════════════════════════════
IMAGE INPUTS (4 images provided)
═══════════════════════════════════════════════════════════════════════════════

IMAGE A - RGB CAMERA (Forward-facing):
- Shows the robot's forward view from an onboard camera
- Use for: environment type, lighting, humans, obstacles, terrain texture

IMAGE ARTIFACT AWARENESS (Real Camera Data):
- JPEG compression: Blocky artifacts, ringing around high-contrast edges - NOT real features
- Sensor noise: Grainy/speckled appearance, especially in low light - NOT texture detail
- Lens distortion: Curved lines at image edges, barrel/pincushion effect
- Overexposure: Washed out bright areas (windows, lights) - lost detail, reduce confidence
- Underexposure: Dark areas with no visible detail - cannot assess those regions
- Motion blur: Smeared edges - may affect obstacle detection, indicates robot was moving
- Color artifacts: Banding, false colors in gradients - NOT real surface colors

ARTIFACT HANDLING:
- If camera shows significant artifacts → rely MORE on BEV (LiDAR unaffected)
- Reduce confidence in camera-only observations when image quality is poor
- Note "degraded image quality" in explanation if artifacts affect analysis
- BEV is ground truth for obstacle positions; camera confirms/adds context

IMAGE B - LiDAR BEV OCCUPANCY (Bird's Eye View - OBSTACLES ONLY):
- AUTO-CROPPED to occupied region (typically 150-250px, varies per window)
- Scale: 0.05m per pixel (20px = 1m) - SCALE IS PRESERVED after cropping
- Robot is ALWAYS at CENTER of cropped image, facing UPWARD (top = forward)
- BRIGHT pixels = OBSTACLES (objects >10cm above ground)
- DARK pixels = FREE SPACE (navigable)
- CRITICAL: Ground is filtered out - only elevated objects appear
- Small bright cluster at center may be robot body (LiDAR self-hit) - IGNORE
- Upper half = forward path, Lower half = behind robot
- NOTE: Image size varies - use pixel distance from center × 0.05 for meters

IMAGE C - LiDAR BEV HEIGHT (Elevation Map - FULL TERRAIN):
- Same scale/orientation/cropping as occupancy (robot at center)
- Shows ALL points including ground (not filtered)
- Grayscale: brighter = higher elevation
- Use for: detecting slopes, stairs, curbs, terrain elevation changes
- NOTE: This includes ground, unlike occupancy

IMAGE D - LiDAR BEV ROUGHNESS (Surface Variation):
- Same scale/orientation/cropping as occupancy (robot at center)
- Shows height variance per pixel (terrain bumpiness)
- Brighter = rougher/more variable surface
- Use for: terrain traversability assessment
- NOTE: This includes ground, unlike occupancy

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

CRITICAL FOR PERCEPTION:
- Trust UPPER HALF (forward path) more than LOWER HALF (rear)
- Expect larger exclusion zone at center for real data self-hits
- Isolated single bright pixels = likely noise, not obstacles
- Real obstacles form connected clusters of bright pixels
- Sparse rear coverage is NORMAL for 180° FOV, not sensor failure

═══════════════════════════════════════════════════════════════════════════════
ODD CONTEXT (Axes to evaluate)
═══════════════════════════════════════════════════════════════════════════════
{json.dumps(odd_context, indent=2) if odd_context else "No ODD context provided - use default perception metrics"}

═══════════════════════════════════════════════════════════════════════════════
MEASUREMENT GUIDANCE
═══════════════════════════════════════════════════════════════════════════════

ENVIRONMENT TYPE (from camera):
- "indoor_commercial": Office, warehouse, retail (flat floors, artificial light)
- "indoor_residential": Home environment (furniture, carpets, narrow passages)
- "outdoor_urban": Sidewalks, parking lots, paved surfaces
- "outdoor_natural": Parks, trails, unpaved terrain
- "mixed": Transition zones (e.g., building entrance)

LIGHTING CONDITIONS (from camera):
- "bright": Well-lit, clear visibility, no shadows affecting perception
- "moderate": Adequate lighting, some shadows but navigable
- "dim": Low light, reduced visibility, may affect camera quality
- "dark": Very low light, camera severely degraded

TERRAIN ASSESSMENT (primarily from BEV height/roughness):
- terrain_type: "smooth" | "slightly_rough" | "rough" | "very_rough"
- smooth: Flat floor, minimal elevation change (carpets count as smooth!)
- slightly_rough: Small bumps, gentle transitions
- rough: Significant elevation changes, uneven surfaces
- very_rough: Stairs, large obstacles, severe terrain
- CRITICAL: Texture (carpet pile, tile pattern) is NOT roughness - use elevation!

OBSTACLE METRICS (from BEV occupancy):
- obstacle_density: 0.0-1.0 (fraction of forward path with obstacles)
  - 0.0-0.2: Clear path, minimal obstacles
  - 0.2-0.5: Light clutter, easy navigation
  - 0.5-0.8: Moderate obstacles, careful navigation needed
  - 0.8-1.0: Dense obstacles, path may be blocked
- Count BRIGHT pixels in upper half of BEV occupancy (forward path)
- IGNORE center ~15px radius (robot body)

TRAVERSABILITY SCORE (combined assessment):
- 0.0-0.3: Difficult/blocked (dense obstacles OR rough terrain OR stairs)
- 0.3-0.6: Challenging but navigable with care
- 0.6-0.8: Good traversability, minor obstacles
- 0.8-1.0: Excellent, clear path with smooth terrain

STAIRS DETECTION:
- stairs_present: 0 or 1
- Look for: regular step patterns in height BEV, handrails in camera
- Stairs are a HARD constraint for most robots

HUMAN DETECTION (from camera):
- humans_detected: 0 or 1
- Look for: people, legs, faces, human silhouettes
- Important for safety compliance

═══════════════════════════════════════════════════════════════════════════════
DATA SOURCE DETECTION (Metadata - not ODD)
═══════════════════════════════════════════════════════════════════════════════

Analyze visual characteristics to determine if imagery is SIMULATED or REAL:

SIMULATED indicators:
- Perfect/uniform textures, synthetic materials
- Unrealistic shadows, game-engine lighting artifacts
- Too-clean surfaces, no dust/wear/imperfections
- Geometric precision in objects
- Uniform noise patterns

REAL indicators:
- Natural lighting variation, real shadows
- Surface imperfections, dust, wear marks
- Organic textures, realistic materials
- Motion blur, sensor noise patterns
- Environmental weathering

═══════════════════════════════════════════════════════════════════════════════
OUTPUT FORMAT (JSON ONLY - NO MARKDOWN)
═══════════════════════════════════════════════════════════════════════════════

{{
  "window_id": "{window_id}",
  "odd_measurements": {{
    "environment_type": "indoor_commercial",
    "lighting_conditions": "bright",
    "terrain_type": "smooth",
    "obstacle_density": 0.15,
    "traversability_score": 0.85,
    "stairs_present": 0,
    "humans_detected": 0
  }},
  "data_source": {{
    "type": "simulated",
    "confidence": 0.90,
    "indicators": ["uniform textures", "perfect lighting"]
  }},
  "camera_summary": "Indoor commercial space with tiled floor, fluorescent lighting, clear forward path",
  "bev_summary": "Minimal obstacles in forward path, flat terrain, ~2m clearance ahead",
  "explanation": "Environment is well-lit indoor commercial with smooth floor and clear navigation path",
  "key_insights": [
    "Clear forward path with >3m visibility",
    "No humans or dynamic obstacles detected"
  ]
}}

═══════════════════════════════════════════════════════════════════════════════
CRITICAL RULES
═══════════════════════════════════════════════════════════════════════════════

1. odd_measurements MUST be FLAT (axis: value pairs only)
   ✓ CORRECT: {{"obstacle_density": 0.35, "lighting_conditions": "bright"}}
   ✗ WRONG: {{"environment": {{"categorical": {{}}, "numeric": {{}}}}}}
   ✗ WRONG: {{"numeric": {{"obstacle_density": 0.35}}}}

2. Use BEV OCCUPANCY for obstacles, BEV HEIGHT/ROUGHNESS for terrain

3. Ignore small bright cluster at BEV center (robot body self-hit)

4. Terrain roughness = elevation changes, NOT surface texture

5. Output JSON only - no markdown code blocks, no extra text

Be CONCISE but COMPLETE. Ground all observations in the images."""

            response = genai_client.models.generate_content(
                model=model,
                contents=[
                    types.Part(text=prompt.strip()),
                    types.Part(text="IMAGE A (Camera - Forward View):"),
                    types.Part.from_bytes(
                        data=camera_bytes, mime_type="image/png"),
                    types.Part(
                        text="IMAGE B (BEV Occupancy - Obstacles Only):"),
                    types.Part.from_bytes(
                        data=bev_occupancy_bytes, mime_type="image/png"),
                    types.Part(
                        text="IMAGE C (BEV Height - Full Terrain Elevation):"),
                    types.Part.from_bytes(
                        data=bev_height_bytes, mime_type="image/png"),
                    types.Part(
                        text="IMAGE D (BEV Roughness - Surface Variation):"),
                    types.Part.from_bytes(
                        data=bev_roughness_bytes, mime_type="image/png"),
                ],
            )

            data = extract_json_block(response.text or "")
            data["window_id"] = window_id
            return data

        except Exception as err:
            return {"status": "error", "window_id": window_id, "message": str(err)}

    async def save_perception_output_tool(
        per_window: List[Dict[str, Any]],
        temporal_analysis: Dict[str, Any],
        summary_insights: List[str],
        tool_context
    ) -> Dict[str, Any]:
        """Save final perception output as artifact for Evaluator.

        Args:
            per_window: List of window results [{window_id, measurements}, ...]
            temporal_analysis: {odd_trends, anomalies, concerns}
            summary_insights: List of key insight strings
            tool_context: ADK tool context with artifact service

        MUST be called after processing all windows.
        """
        import google.genai.types as gtypes

        print(
            f"\n🔵 [SAVE_PERCEPTION_OUTPUT] Called with {len(per_window)} windows")

        try:
            output_data = {
                "per_window": per_window,
                "temporal_analysis": temporal_analysis,
                "summary_insights": summary_insights
            }

            json_bytes = json.dumps(output_data, indent=2).encode('utf-8')
            artifact = gtypes.Part.from_bytes(
                data=json_bytes, mime_type="application/json")

            version = await tool_context.save_artifact(
                filename="perception_output.json",
                artifact=artifact
            )

            print(f"🔵 [SAVE_PERCEPTION_OUTPUT] Saved artifact v{version}")

            return {
                "status": "saved",
                "artifact": "perception_output.json",
                "version": version,
                "windows_saved": len(per_window)
            }
        except Exception as e:
            print(f"🔵 [SAVE_PERCEPTION_OUTPUT] Error: {e}")
            return {"status": "error", "message": str(e)}

    return (
        FunctionTool(func=list_windows_tool),
        FunctionTool(func=analyze_window_perception_tool),
        FunctionTool(func=save_perception_output_tool)
    )
