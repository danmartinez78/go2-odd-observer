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
# v7.0.0: BEV+camera terrain fusion, numeric density %, structured stairs output, human/animal proximity
PERCEPTION_TOOL_VERSION = "7.0.0"


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

TERRAIN ASSESSMENT (BEV + CAMERA FUSION):
Surface type (from camera): hardwood, tile, laminate, low_pile_carpet, high_pile_carpet, concrete, outdoor
Roughness (from BEV height/roughness): elevation variance, NOT texture
- terrain_type: "smooth" | "slightly_rough" | "rough" | "very_rough"
- smooth: Flat floor (hardwood, tile, low_pile_carpet all = smooth)
- slightly_rough: Small bumps, gentle transitions, rug edges
- rough: Significant elevation changes, thresholds, uneven surfaces
- very_rough: Stairs, large obstacles, severe terrain

CRITICAL TERRAIN FUSION:
- Camera shows SURFACE TYPE (carpet, tile, wood) - for ODD surface compatibility
- BEV height/roughness shows ELEVATION CHANGES - for traversability
- Carpet with flat BEV = smooth terrain, traversable
- Tile with bumpy BEV = rough terrain (damaged floor, debris)
- Report BOTH: surface_type (camera) + terrain_roughness (BEV)
- Cross-check: If they conflict, note in explanation

OBSTACLE METRICS (from BEV occupancy - QUANTITATIVE):
- Count bright pixels in UPPER HALF of BEV occupancy (forward path)
- IGNORE center ~15-20px radius (robot body self-hit)
- Report as obstacle_density_pct (0-100%)
  - <20%: Clear path, minimal obstacles
  - 20-50%: Light obstacles, easy navigation
  - 50-80%: Moderate obstacles, careful navigation needed
  - >80%: Dense obstacles, path may be blocked
- Also report top_obstacle_clusters: count of distinct bright regions

TRAVERSABILITY SCORE (combined assessment):
- 0.0-0.3: Difficult/blocked (dense obstacles OR rough terrain OR stairs)
- 0.3-0.6: Challenging but navigable with care
- 0.6-0.8: Good traversability, minor obstacles
- 0.8-1.0: Excellent, clear path with smooth terrain
- traversability_justification: One sentence explaining the score

STAIRS DETECTION (Structured Output):
- stairs: {{
    "present": true/false,
    "direction": "up" | "down" | "unknown",
    "proximity_m": <float>,  # Distance from robot
    "risk": "low" | "medium" | "high",
    "justification": "why this risk level"
  }}
- Low risk: Stairs visible but distant (>3m), not intersecting path
- Medium risk: Stairs moderately close (1.5-3m), may need avoidance
- High risk: Stairs close (<1.5m), downward stairs, or intersecting path
- Look for: regular step patterns in height BEV, handrails in camera

HUMAN/ANIMAL DETECTION (from camera - Safety Critical):
- humans_animals: {{
    "detected": true/false,
    "type": "human" | "animal" | "both" | "none",
    "count": <int>,
    "proximity_m": <float>,  # Estimated closest distance
    "in_path": true/false,   # Are they in forward travel path?
    "justification": "description of detection"
  }}
- Look for: people, faces, legs, silhouettes, pets, animals
- CRITICAL: Close proximity (<1m) to humans/animals = major safety concern

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
    "environment_type": "indoor_residential",
    "lighting_conditions": "bright",
    "surface_type": "low_pile_carpet",
    "terrain_roughness": "smooth",
    "obstacle_density_pct": 25,
    "top_obstacle_clusters": 3,
    "traversability_score": 0.75,
    "traversability_justification": "Moderate furniture density but clear path exists",
    "stairs": {{
      "present": false,
      "direction": null,
      "proximity_m": null,
      "risk": "low",
      "justification": "No stairs visible in camera or BEV"
    }},
    "humans_animals": {{
      "detected": true,
      "type": "human",
      "count": 1,
      "proximity_m": 2.5,
      "in_path": false,
      "justification": "Person visible on left side of frame, not in travel path"
    }}
  }},
  "data_source": {{
    "type": "real",
    "confidence": 0.85,
    "indicators": ["natural lighting", "carpet texture", "thickened BEV edges"]
  }},
  "camera_summary": "Living room with carpet floor, sofa on left, clear path ahead, person standing to the side",
  "bev_summary": "25% forward path occupied, furniture clusters at 1-2m, clear corridor down center",
  "explanation": "Residential environment with moderate obstacle density but navigable central path. One human detected but not obstructing.",
  "key_insights": [
    "Carpet surface but terrain is smooth (flat BEV)",
    "Clear 0.8m corridor through furniture",
    "Human present at 2.5m, not in path"
  ]
}}

═══════════════════════════════════════════════════════════════════════════════
CRITICAL RULES
═══════════════════════════════════════════════════════════════════════════════

1. odd_measurements MUST be FLAT (axis: value pairs only, except structured stairs/humans_animals)
   ✓ CORRECT: {{"obstacle_density_pct": 35, "lighting_conditions": "bright"}}
   ✗ WRONG: {{"environment": {{"categorical": {{}}, "numeric": {{}}}}}}

2. TERRAIN FUSION: Surface type from camera, roughness from BEV height/roughness
   - Carpet + flat BEV = "smooth" terrain (traversable)
   - Any surface + bumpy BEV = roughness reflects BEV

3. QUANTITATIVE DENSITY: Report obstacle_density_pct (0-100), not just categories

4. Ignore small bright cluster at BEV center (robot body self-hit)

5. STAIRS: Output structured {{present, direction, proximity_m, risk, justification}}

6. HUMANS/ANIMALS: Output structured {{detected, type, count, proximity_m, in_path, justification}}

7. Output JSON only - no markdown code blocks, no extra text

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
