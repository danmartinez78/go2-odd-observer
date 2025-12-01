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
PERCEPTION_TOOL_VERSION = "10.2.0"

# Hardcoded robot and sensor knowledge - this is constant across all analyses
ROBOT_SENSOR_KNOWLEDGE = """
## ROBOT PLATFORM: Unitree Go2 Quadruped
- Camera height: ~35cm off ground (LOW angle perspective)
- Camera FOV: ~120° horizontal
- Footprint: 0.65m length × 0.31m width

## SENSOR INTERPRETATION

### Camera Image (Image A)
- LOW ANGLE VIEW: This dramatically affects how you perceive humans and animals
  - Humans CLOSE: You see ONLY feet/lower legs filling the bottom of frame
  - Humans MEDIUM: Legs up to waist visible, person looms over camera
  - Humans FAR: Full body visible head to toe (requires 6m+ distance)
  - Animals (dogs/cats): At similar height to camera, eye-level when close
- Use for: Semantic understanding, ACTOR DETECTION (humans/animals), surface type, lighting
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
- Use for: traversability assessment

## TRAVERSABILITY CALIBRATION (CRITICAL)

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

## CRITICAL: ACTOR PROXIMITY vs OBSTACLE DISTANCE

⚠️ ACTORS (humans/animals) are assessed ONLY from CAMERA image:
- Look at what body parts are visible and how much they fill the frame
- Use proximity bands: none/far/medium/close/immediate
- Read the ODD spec description for human_proximity_band/animal_proximity_band for guidance

⚠️ OBSTACLES are assessed from BEV occupancy:
- "min_obstacle_distance_m" from BEV metrics is to ANY obstacle (furniture, walls, etc.)
- This is NOT actor proximity - do not confuse them
- A chair 0.5m away is NOT a human proximity violation

⚠️ DO NOT report fake precision like "human at 0.76m" - camera cannot measure distance
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

Analyze all four sensor images and provide measurements for EACH AXIS defined in the ODD specification above.

WORKFLOW:
1. Read each axis in the ODD spec (categorical, numeric, boolean)
2. Use the axis "description" field for guidance on HOW to assess it
3. Output a measurement for that axis using the EXACT axis name from the spec

For categorical axes: output one of the allowed values (or your best match)
For numeric axes: output a number within the specified range
For boolean axes: output 0 or 1

OUTPUT FORMAT (JSON only, no markdown):
{{
  "window_id": "{window_id}",
  "observations": {{
    "scene_description": "Overall description of what you see",
    "lighting": "Describe lighting conditions",
    "terrain": "Describe floor/ground surface",
    "obstacles": "Describe obstacles visible",
    "actors": "Describe humans/animals - body parts visible, apparent proximity. Say 'None visible' if none."
  }},
  "odd_measurements": {{
    "<axis_name_from_spec>": "<measured_value>",
    "... one entry per axis in the ODD spec ...": "..."
  }},
  "reasoning": {{
    "<axis_name>": "Brief reasoning for this measurement",
    "...": "..."
  }},
  "odd_concerns": ["List any potential ODD violations"],
  "confidence": 0.0-1.0
}}

IMPORTANT:
- Use EXACT axis names from the ODD spec in odd_measurements
- Read the description field for each axis - it tells you HOW to assess it
- For actor proximity axes: assess from CAMERA only (not BEV obstacle distance)
- BEV obstacle distance ({bev_metrics.get('min_obstacle_distance_m', 'N/A')}m) is to furniture/walls, NOT humans/animals"""

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
