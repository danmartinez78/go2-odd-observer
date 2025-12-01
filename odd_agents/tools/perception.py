"""
Perception analysis tools.
Factory functions that create tools with specific configuration.

v10.0.0: Observation-first architecture - hardcoded robot knowledge + reasoned assessments
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Union
from google.adk.tools import FunctionTool
from google.genai import types
from google import genai

from ..utils import build_image_path, ensure_image_bytes, extract_json_block, compute_bev_metrics
from .common import list_available_windows, get_window_file_paths


# Tool version
# v7.2.0: Compressed prompts (~50% reduction) while preserving accuracy
# v8.0.0: Single-call batch - analyze_all_perception_tool processes all windows, auto-saves artifact
# v9.0.0: Actor proximity bands (humans/animals separate, qualitative not metric)
# v10.0.0: Observation-first architecture - hardcoded robot/sensor knowledge, reasoned assessments
# v10.1.0: Reinforced actor proximity guidance - camera-only assessment, read ODD spec descriptions
# v10.2.0: Traversability calibration - indoor clutter is navigable, not impassable
# v10.3.0: Camera artifact guidance - ignore JPEG compression, blur, distortion as debris
# v11.0.0: Sensor fusion reasoning, image quality pre-check, terrain type clarification, confidence calibration
PERCEPTION_TOOL_VERSION = "11.0.0"

# Hardcoded robot and sensor knowledge - this is constant across all analyses
ROBOT_SENSOR_KNOWLEDGE = """
## ROBOT PLATFORM: Unitree Go2 Quadruped
- Camera height: ~35cm off ground (LOW angle perspective)
- Camera FOV: ~120° horizontal
- Footprint: 0.65m length × 0.31m width

## STEP 0: IMAGE QUALITY ASSESSMENT (DO THIS FIRST)

Before analyzing content, assess camera image (Image A) quality:

**Check for these artifacts:**
- JPEG compression: Blocky patterns, color banding, mosquito noise around edges
- Motion blur: Smeared edges, ghosting
- Lens distortion: Warped straight lines at image edges
- Exposure issues: Blown highlights, crushed shadows, too dark/bright overall
- Focus issues: Soft edges, lack of fine detail

**Record your assessment:**
- image_quality: "good" | "moderate" | "degraded"
- If degraded: note which artifacts are present
- This DIRECTLY affects your confidence score (degraded images → lower confidence)

**CRITICAL: Do NOT misinterpret artifacts as scene content:**
- Blocky compression patterns are NOT debris or texture
- Color banding is NOT surface variation
- Soft focus is NOT fog or smoke

## SENSOR INTERPRETATION

### Camera Image (Image A)
- LOW ANGLE VIEW: This dramatically affects how you perceive humans and animals
  - Humans CLOSE: You see ONLY feet/lower legs filling the bottom of frame
  - Humans MEDIUM: Legs up to waist visible, person looms over camera
  - Humans FAR: Full body visible head to toe (requires 6m+ distance)
  - Animals (dogs/cats): At similar height to camera, eye-level when close
- Use for: Semantic understanding, ACTOR DETECTION (humans/animals), floor MATERIAL type, lighting
- CANNOT measure exact distances - reason from visual cues only

### BEV Occupancy (Image B)
- Robot at CENTER, facing UP (forward = top of image)
- Resolution: 0.05m per pixel (20 pixels = 1 meter)
- White = obstacles, Black = free space
- IGNORE 15px radius at center (robot's own body - self-hit)
- Shows OBSTACLES ONLY (ground filtered out)
- CANNOT identify WHAT obstacles are - could be furniture, walls, or even humans
- Use for: obstacle density, clear path detection, navigation safety

### BEV Height (Image C)
- Full terrain elevation including ground
- Brighter = higher elevation
- Use to detect: stairs (multi-step pattern), ramps, elevation changes

### BEV Roughness (Image D)
- Terrain height variance per pixel
- Brighter = rougher/more uneven surface
- Use for: traversability assessment, validating camera observations

## SENSOR FUSION: CROSS-REFERENCE ALL DATA

You have FOUR sensor views - use them TOGETHER to disambiguate ambiguous observations:

**Camera vs BEV Roughness (resolve texture ambiguity):**
- Camera shows unusual texture BUT BEV roughness is LOW (dark) → Likely camera artifact, visual pattern, or patterned rug - NOT actual rough terrain
- Camera shows smooth floor BUT BEV roughness is HIGH (bright) → Actual terrain variation camera didn't capture

**Camera vs BEV Occupancy (resolve obstacle ambiguity):**
- Camera shows something on floor BUT BEV occupancy shows FREE space → Flat object, shadow, or camera artifact
- Camera shows clear path BUT BEV occupancy shows obstacle → Low object camera didn't see

**Camera vs BEV Height (resolve elevation ambiguity):**
- Camera suggests terrain change BUT BEV height is FLAT → Visual illusion, pattern, or artifact
- Camera shows flat floor BUT BEV height varies → Actual elevation change

**When sensors disagree:**
- Trust BEV for GEOMETRY (height, obstacles, roughness) - it's from LiDAR, immune to visual artifacts
- Trust camera for SEMANTICS (what things are) - but only if image quality is good
- If camera quality is degraded, weight BEV interpretation more heavily
- Note disagreements in sensor_fusion_notes

## TERRAIN TYPE IS FLOOR MATERIAL (NOT OBJECTS)

terrain_type refers to the UNDERLYING FLOOR MATERIAL the robot stands/moves on.
You MUST output one of the allowed values from the ODD specification.

**Terrain type IS:**
- The floor surface material: tile, hardwood, carpet, laminate, vinyl, concrete, area rug
- What the robot's feet physically contact

**Terrain type IS NOT:**
- Objects ON the floor (toys, papers, cables, debris)
- Visual patterns or textures in the material
- Things that could be moved or cleaned up

**Examples:**
- Patterned rug with complex design → terrain_type: "area_rug" (it's the material, ignore the pattern)
- Hardwood floor with papers scattered → terrain_type: "hardwood" (ignore papers)
- Carpet with toys on it → terrain_type: "low-pile carpet" (ignore toys)
- Floor with unusual visual texture but flat BEV → probably a patterned surface, use best material match

**DO NOT invent terrain types:**
- "shredded paper", "debris", "clutter" are NOT terrain types - they're objects
- Always output one of the allowed values from the ODD spec
- If uncertain, cross-reference with BEV roughness and pick best material match

## TRAVERSABILITY CALIBRATION

traversability_score measures PATH NAVIGABILITY for a quadruped robot, NOT tidiness:
- 0.9-1.0: Clear open path (empty hallway, open floor)
- 0.7-0.9: Minor obstacles easily navigated (some furniture to go around)
- 0.5-0.7: Moderate clutter, navigable with care (typical lived-in room, cables, toys)
- 0.3-0.5: Significant obstacles but passable (crowded space, narrow gaps)
- 0.1-0.3: Barely passable, very tight gaps
- 0.0-0.1: Truly impassable (doorway blocked, cliff edge, dense boulder field)

⚠️ INDOOR CLUTTER IS NOT IMPASSABLE:
- Rugs, toys, cables on floor = 0.5-0.7 (the robot can walk over/around them)
- A "messy room" is NOT "rocky outcropping" - calibrate accordingly
- Only use 0.0-0.2 for genuinely blocked paths (robot physically cannot pass)

## ACTOR DETECTION (BINARY)

⚠️ ACTORS (humans/animals) are assessed ONLY from CAMERA image:
- human_present: 1 if ANY human visible, 0 otherwise
- animal_present: 1 if ANY animal visible, 0 otherwise
- Do NOT estimate distances - just presence/absence

⚠️ OBSTACLES in BEV are NOT actors:
- "min_obstacle_distance_m" from BEV is to furniture/walls, NOT humans
- A chair 0.5m away is NOT a human proximity violation

## CONFIDENCE CALIBRATION

Your confidence score reflects BOTH certainty in observations AND data quality:

**Base on image quality:**
- Good quality + clear observations → 0.85-0.95
- Good quality + some ambiguity → 0.70-0.85
- Moderate quality (minor artifacts) → 0.60-0.75
- Degraded quality (significant artifacts) → 0.40-0.60

**Adjust for sensor agreement:**
- All sensors agree → +0.05 to +0.10
- Sensors partially disagree → no adjustment
- Sensors strongly disagree → -0.10 to -0.15

**Never claim high confidence (>0.85) if:**
- Image quality is degraded
- Sensors disagree significantly
- You're uncertain about terrain type or actor presence
"""


def create_perception_tools(scenario_path: Union[str, Path], genai_client: genai.Client, model: str, api_key: str = None):
    """
    Create perception analysis tools for a specific scenario.

    Args:
        scenario_path: Path to scenario directory
        genai_client: Configured Gemini client
        model: Model name for perception analysis
        api_key: API key (unused, kept for interface compatibility)

    Returns:
        Tuple of (analyze_all_perception_tool,) - single tool handles everything
    """
    scenario_path = Path(scenario_path) if isinstance(
        scenario_path, str) else scenario_path

    async def _analyze_single_window(window_id: str, odd_context: dict) -> dict:
        """Internal: Analyze one window (called by batch tool)."""
        import cv2

        try:
            file_paths = get_window_file_paths(scenario_path, window_id)
            camera_bytes = ensure_image_bytes(file_paths["camera"])
            bev_occupancy_bytes = ensure_image_bytes(
                file_paths["bev_occupancy"])
            bev_height_bytes = ensure_image_bytes(file_paths["bev_height"])
            bev_roughness_bytes = ensure_image_bytes(
                file_paths["bev_roughness"])

            # Pre-compute BEV metrics
            bev_occupancy_path = file_paths["bev_occupancy"]
            bev_img = cv2.imread(str(bev_occupancy_path), cv2.IMREAD_GRAYSCALE)
            bev_metrics = compute_bev_metrics(
                bev_img, resolution_m_per_px=0.05, self_hit_radius_px=15)

            bev_metrics_str = f"""
## PRE-COMPUTED BEV METRICS (from occupancy map)
- Obstacle density: {bev_metrics.get('obstacle_density_pct', 0):.1f}%
- Obstacle clusters: {bev_metrics.get('obstacle_cluster_count', 0)}
- Min distance to obstacle: {bev_metrics.get('min_obstacle_distance_m', 'N/A')}m (NOTE: this is to ANY obstacle, not actors)
- Mean distance to obstacles: {bev_metrics.get('mean_obstacle_distance_m', 'N/A')}m
- Forward path blocked (<2m): {bev_metrics.get('forward_path_blocked', False)}
"""

            # Build the VLA prompt combining hardcoded knowledge + ODD context
            prompt = f"""You are a perception expert analyzing robot sensor data for ODD (Operational Design Domain) compliance.

{ROBOT_SENSOR_KNOWLEDGE}

{bev_metrics_str}

## ODD SPECIFICATION TO ASSESS AGAINST
{json.dumps(odd_context, indent=2) if odd_context else "No specific ODD context provided - use general indoor navigation criteria"}

## YOUR TASK FOR WINDOW {window_id}

Analyze all four sensor images using this workflow:

### STEP 1: Assess Image Quality (Camera Image A)
Before analyzing content, check for artifacts (JPEG compression, blur, distortion, exposure issues).
Record image_quality as "good", "moderate", or "degraded".

### STEP 2: Cross-Reference Sensors
Look at ALL FOUR images together. Note where they agree or disagree:
- Does camera texture match BEV roughness?
- Do camera obstacles match BEV occupancy?
- Are there visual artifacts the BEV doesn't show?

### STEP 3: Make ODD Measurements
For each axis in the ODD spec:
- Read the axis "description" for HOW to assess it
- Use sensor fusion to resolve ambiguities
- Output using EXACT axis name from spec

For categorical axes (like terrain_type): output one of the ALLOWED values only
For numeric axes: output a number
For boolean axes: output 0 or 1

### STEP 4: Calibrate Confidence
Adjust confidence based on image quality and sensor agreement (see guidance above).

OUTPUT FORMAT (JSON only, no markdown):
{{
  "window_id": "{window_id}",
  "image_quality": {{
    "camera_quality": "good|moderate|degraded",
    "artifacts_observed": ["list any artifacts found"],
    "quality_notes": "brief note on image quality"
  }},
  "observations": {{
    "scene_description": "Overall description of what you see",
    "lighting": "Describe lighting conditions",
    "terrain": "Describe floor MATERIAL (not objects on floor)",
    "obstacles": "Describe obstacles visible",
    "actors": "Describe humans/animals visible. Say 'None visible' if none."
  }},
  "odd_measurements": {{
    "<axis_name_from_spec>": "<measured_value>",
    "... one entry per axis in the ODD spec ...": "..."
  }},
  "reasoning": {{
    "<axis_name>": "Brief reasoning for this measurement",
    "...": "..."
  }},
  "sensor_fusion_notes": [
    "Note any cross-sensor observations, e.g. 'Camera shows texture but BEV roughness is low - patterned rug'"
  ],
  "odd_concerns": ["List any potential ODD violations - only real concerns, not artifacts"],
  "confidence": 0.0-1.0
}}

CRITICAL REMINDERS:
- terrain_type is FLOOR MATERIAL (tile, hardwood, carpet, etc.) - NOT objects on floor
- DO NOT invent terrain types like "shredded paper" or "debris"
- If image quality is degraded, trust BEV more than camera for geometry
- BEV obstacle distance ({bev_metrics.get('min_obstacle_distance_m', 'N/A')}m) is to furniture/walls, NOT actors"""

            response = genai_client.models.generate_content(
                model=model,
                contents=[
                    types.Part(text=prompt.strip()),
                    types.Part(text="A) Camera Image:"),
                    types.Part.from_bytes(
                        data=camera_bytes, mime_type="image/png"),
                    types.Part(text="B) BEV Occupancy (white=obstacles):"),
                    types.Part.from_bytes(
                        data=bev_occupancy_bytes, mime_type="image/png"),
                    types.Part(text="C) BEV Height (brighter=higher):"),
                    types.Part.from_bytes(
                        data=bev_height_bytes, mime_type="image/png"),
                    types.Part(text="D) BEV Roughness (brighter=rougher):"),
                    types.Part.from_bytes(
                        data=bev_roughness_bytes, mime_type="image/png"),
                ],
            )

            data = extract_json_block(response.text or "")
            data["window_id"] = window_id
            return data

        except Exception as err:
            return {"status": "error", "window_id": window_id, "message": str(err)}

    async def analyze_all_perception_tool(odd_context: dict, tool_context) -> dict:
        """Analyze ALL windows for perception and auto-save artifact.

        Args:
            odd_context: ODD specification from parent agent (structured JSON)
            tool_context: ADK tool context for artifact saving

        Returns full per_window results with observations and assessments. Artifact is auto-saved.
        """
        print("\n" + "="*60)
        print("🔵 [PERCEPTION TOOL v10] ENTRY POINT")
        print(
            f"🔵 [PERCEPTION TOOL] odd_context keys: {list(odd_context.keys()) if odd_context else 'None'}")
        print("="*60)

        import google.genai.types as gtypes

        # Get all available windows
        windows = list_available_windows(scenario_path, require_motion=True)
        print(
            f"\n🔵 [PERCEPTION] Analyzing {len(windows)} windows with observation-first approach...")

        # Process each window
        per_window = []
        for window_id in windows:
            print(f"🔵 [PERCEPTION] Processing window {window_id}...")
            result = await _analyze_single_window(window_id, odd_context)
            per_window.append(result)

        # Auto-save artifact
        output_data = {
            "per_window": per_window,
            "windows_analyzed": len(per_window),
            "tool_version": PERCEPTION_TOOL_VERSION,
        }

        try:
            json_bytes = json.dumps(output_data, indent=2).encode('utf-8')
            artifact = gtypes.Part.from_bytes(
                data=json_bytes, mime_type="application/json")
            version = await tool_context.save_artifact(filename="perception_output.json", artifact=artifact)
            print(f"🔵 [PERCEPTION] Auto-saved artifact v{version}")
        except Exception as e:
            print(f"🔵 [PERCEPTION] Artifact save failed: {e}")

        return {
            "status": "success",
            "per_window": per_window,
            "windows_analyzed": len(per_window),
        }

    return (FunctionTool(func=analyze_all_perception_tool),)
