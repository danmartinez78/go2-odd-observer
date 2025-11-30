"""
Perception analysis tools.
Factory functions that create tools with specific configuration.

v8.0.0: Single-call batch analysis - one tool call processes all windows and auto-saves artifact.
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
PERCEPTION_TOOL_VERSION = "8.0.0"


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
PRE-COMPUTED BEV METRICS (USE THESE):
- Obstacle density: {bev_metrics.get('obstacle_density_pct', 0):.1f}% | Clusters: {bev_metrics.get('obstacle_cluster_count', 0)}
- Min distance: {bev_metrics.get('min_obstacle_distance_m', 'N/A')}m | Mean: {bev_metrics.get('mean_obstacle_distance_m', 'N/A')}m
- Forward blocked (<2m): {bev_metrics.get('forward_path_blocked', False)}"""

            prompt = f"""Perception expert analyzing window {window_id}.

IMAGES: A) Camera B) BEV Occupancy C) BEV Height D) BEV Roughness
BEV: Robot at CENTER facing UP, 0.05m/px, ignore 15px center (self-hit)
{bev_metrics_str}

ODD CONTEXT: {json.dumps(odd_context, indent=2) if odd_context else "Default"}

OUTPUT (JSON only):
{{
  "window_id": "{window_id}",
  "odd_measurements": {{
    "environment_type": "indoor_commercial|indoor_residential|outdoor_urban|outdoor_natural|mixed",
    "lighting_conditions": "bright|moderate|dim|dark",
    "surface_type": "hardwood|tile|carpet|concrete|grass|etc",
    "terrain_roughness": "smooth|slightly_rough|rough|very_rough",
    "obstacle_density_pct": <USE_PRECOMPUTED>,
    "min_obstacle_distance_m": <USE_PRECOMPUTED>,
    "traversability_score": 0.0-1.0,
    "stairs": {{"present": bool, "direction": str, "proximity_m": float, "risk": "low|medium|high"}},
    "humans_animals": {{"detected": bool, "count": int, "proximity_m": float, "in_path": bool}}
  }},
  "data_source": {{"type": "sim|real", "confidence": 0.0-1.0}},
  "explanation": "brief",
  "key_insights": ["insight1"]
}}"""

            response = genai_client.models.generate_content(
                model=model,
                contents=[
                    types.Part(text=prompt.strip()),
                    types.Part(text="A) Camera:"),
                    types.Part.from_bytes(
                        data=camera_bytes, mime_type="image/png"),
                    types.Part(text="B) BEV Occupancy:"),
                    types.Part.from_bytes(
                        data=bev_occupancy_bytes, mime_type="image/png"),
                    types.Part(text="C) BEV Height:"),
                    types.Part.from_bytes(
                        data=bev_height_bytes, mime_type="image/png"),
                    types.Part(text="D) BEV Roughness:"),
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
            odd_context: ODD specification from parent agent
            tool_context: ADK tool context for artifact saving

        Returns full per_window results. Artifact is auto-saved.
        """
        import google.genai.types as gtypes

        # Get all available windows
        windows = list_available_windows(scenario_path, require_motion=True)
        print(f"\n🔵 [PERCEPTION] Analyzing {len(windows)} windows...")

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
