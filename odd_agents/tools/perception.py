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
# v11.1.0: Robot size in BEV pixels, BEV-based traversability assessment, quadruped capabilities
# v12.0.0: Rename traversability_score → clearance_index for semantic clarity
# v12.1.0: Added rotate-in-place capability, "BLOCKED FORWARD ≠ TRAPPED" guidance
# v12.2.0: Lighting vs dark objects guidance - distinguish dim room from dark furniture in view
PERCEPTION_TOOL_VERSION = "12.2.0"

# Hardcoded robot and sensor knowledge - this is constant across all analyses
ROBOT_SENSOR_KNOWLEDGE = """
## ROBOT PLATFORM: Unitree Go2 Quadruped
- Camera height: ~35cm off ground (LOW angle perspective)
- Camera FOV: ~120° horizontal
- Physical footprint: 0.65m length × 0.31m width
- **In BEV images: ~13 pixels long × 6 pixels wide** (at 0.05m/pixel resolution)
- Robot is at CENTER of BEV, facing UP (top of image = forward)
- Quadruped can step over small obstacles (<15cm height) and navigate tight spaces

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

## LIGHTING vs DARK OBJECTS (DO NOT CONFUSE!)

**Dim lighting** means the ROOM/ENVIRONMENT has insufficient illumination.
**Dark objects** are furniture/walls with dark colors (couches, cabinets, dark paint).

How to distinguish:
- DIM ROOM: Everything is dark, including floor and walls visible in frame. Shadows are indistinct.
- DARK OBJECT IN VIEW: The dark area has distinct edges/boundaries. Floor or other areas AROUND it are properly lit.
- LARGE DARK FURNITURE: If a couch, cabinet, or furniture piece fills most of the frame but you can see the floor/edges are lit → lighting is FINE, just a dark object in view

**Example:**
- Robot camera looks at a dark brown couch that fills 70% of frame → lighting is FINE (assess from the visible floor/walls)
- Robot in hallway where ceiling lights are off → lighting is DIM (everything uniformly dark)
- Dark furniture + good lighting → lighting_conditions = "moderate" or "bright" (based on visible lit areas)

**When assessing lighting_conditions:**
- Look at the FLOOR and VISIBLE ROOM AREAS, not the dominant object color
- If floor is well-lit but large dark furniture fills frame → lighting is adequate
- If unable to see floor texture/detail due to darkness → lighting may be dim

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
- Use for: clearance_index validation, cross-referencing camera observations

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

## CLEARANCE INDEX ASSESSMENT (USE BEV OCCUPANCY!)

clearance_index measures PATH NAVIGABILITY for this quadruped robot.
**Use BEV Occupancy (Image B) as your PRIMARY source** - it shows actual obstacle geometry.

### CRITICAL: USE OBSTACLE_DENSITY AS SANITY CHECK
Before scoring clearance_index, check the pre-computed obstacle_density:
- If obstacle_density < 10% → Most of BEV is FREE → clearance_index should be ≥0.5
- If obstacle_density < 5% → BEV is VERY open → clearance_index should be ≥0.7
- ONLY give clearance_index < 0.3 if obstacle_density > 50% or ALL paths truly blocked

Example sanity check:
- obstacle_density = 3.2% means 96.8% of BEV is FREE SPACE
- Even if ONE direction is blocked, there MUST be navigable paths elsewhere
- 3.2% density with clearance_index=0.1 is INCONSISTENT → re-evaluate!

### FOCUS ON THE FORWARD REGION (TOP HALF OF BEV)
- Robot is at CENTER, facing UP (top = forward direction of travel)
- **Assess clearance in the FORWARD CONE** - the top half/upper portion of the BEV
- Behind the robot (bottom of BEV) is where it came from - less relevant
- Sides matter for maneuvering room, but forward path is PRIMARY

### How to assess from BEV Occupancy:
1. Robot is at CENTER (ignore 15px radius self-hit zone)
2. Robot footprint is ~13×6 pixels - look for gaps WIDER than this
3. **FOCUS ON TOP HALF**: Is there a navigable path AHEAD of the robot?
4. **ALSO CHECK SIDES**: If forward blocked, can robot turn and go another way?
5. Look for BLACK (free) space - ANY viable path counts!

### "BLOCKED FORWARD" ≠ "NO PATH"
A large obstacle directly ahead does NOT mean clearance_index = 0.1!
- Can robot turn left? Check LEFT side of BEV for gaps
- Can robot turn right? Check RIGHT side of BEV for gaps
- Can robot reverse slightly and re-route? Check surrounding space
- ONLY score <0.3 if ALL directions are blocked with no viable path

### Clearance Index Scale (based on BEV gap analysis):
- 0.9-1.0: Wide open space, >70% of BEV is free (black), clear paths in all directions
- 0.7-0.9: Mostly open, obstacles clustered at edges, clear forward path (>20px wide gaps)
- 0.5-0.7: Forward may have obstacles BUT alternative paths exist, typical furnished room
- 0.3-0.5: Tight but passable, gaps 6-10px (~0.3-0.5m), robot can squeeze through
- 0.1-0.3: Very constrained, gaps barely wider than robot (6px), requires precise navigation
- 0.0-0.1: TRUE BLOCKAGE: No viable path in ANY direction, walls on all sides

### Quadruped Capabilities (be generous!):
- Can step OVER small obstacles (<15cm) - don't count low clutter as blocking
- Can navigate AROUND furniture - look for ANY viable path, not just straight ahead
- Can ROTATE IN PLACE (360°) - robot can turn to face any direction without moving
- Can TURN and re-route - blocked forward doesn't mean stuck
- Can handle uneven surfaces - BEV roughness ≠ impassable
- Rugs, toys, cables = easily traversed (0.6-0.8 range)

### COMMON SCORING MISTAKE - AVOID THIS:
❌ WRONG: "Forward blocked by couch → clearance_index = 0.1"
✅ RIGHT: "Forward blocked by couch, but sides are clear → clearance_index = 0.5"

The robot can ROTATE IN PLACE and go a different direction. 
clearance_index < 0.3 means the robot is TRAPPED, not just facing an obstacle.

### Cross-reference Camera + BEV:
- Camera tells you WHAT obstacles are (semantic understanding)
- BEV tells you WHERE they are and if there's SPACE to navigate
- If BEV shows open space but camera looks cluttered → trust BEV geometry
- Indoor "messy room" with scattered items but clear BEV paths = 0.6-0.8, NOT 0.3

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
