"""
Perception analysis tools.
Factory functions that create tools with specific configuration.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Union
from google.adk.tools import FunctionTool
from google.genai import types
from google import genai

from ..utils import build_image_path, ensure_image_bytes, extract_json_block
from .common import list_available_windows, get_window_file_paths


# Tool agent version
# v4.1.0: Added explicit example + anti-pattern to ensure flat output format
# v5.0.0: Added save_output_tool for artifact-based data handoff to Evaluator
# v5.1.0: Added data_source detection (sim vs real) as metadata field
PERCEPTION_TOOL_AGENT_VERSION = "5.1.0"


def create_perception_tools(scenario_path: Union[str, Path], genai_client: genai.Client, model: str):
    """
    Create perception analysis tools for a specific scenario.

    Args:
        scenario_path: Path to scenario directory (string or Path object)
        genai_client: Configured Gemini client
        model: Model name to use for perception analysis

    Returns:
        Tuple of (list_windows_tool, analyze_window_perception_tool)
    """
    # Ensure scenario_path is a Path object
    scenario_path = Path(scenario_path) if isinstance(
        scenario_path, str) else scenario_path

    async def list_windows_tool() -> Dict[str, Any]:
        """Tool: list available window IDs for the scenario."""
        try:
            windows = list_available_windows(
                scenario_path, require_motion=True)
            return {
                "status": "success",
                "windows": windows,
                "count": len(windows),
            }
        except FileNotFoundError as e:
            return {"status": "error", "message": str(e)}

    async def analyze_window_perception_tool(window_id: str, odd_context: dict) -> Dict[str, Any]:
        """Tool: run a direct multimodal Gemini call for one window (camera + 4 BEV channels).

        Args:
            window_id: Window identifier
            odd_context: Filtered ODD specification from loop agent (relevant dimensions only)
        """
        try:
            # Get file paths from CSV index
            file_paths = get_window_file_paths(scenario_path, window_id)
            camera_path = file_paths["camera"]
            bev_occupancy_path = file_paths["bev_occupancy"]
            bev_height_path = file_paths["bev_height"]
            bev_roughness_path = file_paths["bev_roughness"]

            # Load images
            camera_bytes = ensure_image_bytes(camera_path)
            bev_occupancy_bytes = ensure_image_bytes(bev_occupancy_path)
            bev_height_bytes = ensure_image_bytes(bev_height_path)
            bev_roughness_bytes = ensure_image_bytes(bev_roughness_path)

            prompt = f"""Analyze synchronized sensors for window {window_id}.

INPUTS:
- Image A: RGB camera (forward-facing)
- Image B: LiDAR BEV Occupancy (bright=obstacles, dark=clear, robot at center facing up)
- Image C: LiDAR BEV Height (grayscale elevation map)
- Image D: LiDAR BEV Roughness (bright=rough terrain)

BEV Scale: 0.05m/pixel (20px = 1m), ~20m x 20m coverage, robot-centered.

ODD CONTEXT (use these axis names in odd_measurements):
{json.dumps(odd_context, indent=2) if odd_context else "No ODD context - use default perception metrics"}

OUTPUT FORMAT - FLAT STRUCTURE ONLY:
{{
  "window_id": "{window_id}",
  "odd_measurements": {{
    "environment_type": "indoor_commercial",
    "lighting_conditions": "bright",
    "obstacle_density": 0.35,
    "terrain_type": "smooth",
    "traversability_score": 0.8
  }},
  "data_source": {{
    "type": "simulated",
    "confidence": 0.95,
    "indicators": ["uniform textures", "synthetic lighting"]
  }},
  "explanation": "1-2 sentence reasoning",
  "key_insights": ["observation 1", "observation 2"],
  "camera_summary": "Brief scene description",
  "bev_summary": "Brief spatial layout"
}}

CRITICAL - odd_measurements must be FLAT (axis_name: value pairs only):
✓ CORRECT: {{"obstacle_density": 0.35, "lighting_conditions": "bright"}}
✗ WRONG: {{"environment": {{"categorical": {{}}, "numeric": {{}}}}}}
✗ WRONG: {{"numeric": {{"obstacle_density": 0.35}}}}

MEASUREMENT GUIDANCE:
- lighting_conditions: "bright" | "moderate" | "dim"
- terrain_type: "smooth" | "slightly_rough" | "rough"
- obstacle_density: 0.0-1.0 (fraction of BEV with obstacles)
- traversability_score: 0.0-1.0 (ease of navigation, higher=easier)
- stairs_present: 0 or 1

DATA SOURCE DETECTION (metadata, not ODD):
Analyze visual characteristics to determine if imagery is from simulation or real-world:
- "data_source": {{"type": "simulated" or "real", "confidence": 0.0-1.0, "indicators": ["reason1", "reason2"]}}
Indicators for SIMULATED: perfect textures, uniform lighting, synthetic materials, unrealistic shadows, game-engine artifacts
Indicators for REAL: natural lighting variation, real-world imperfections, dust/wear, organic textures

Be CONCISE. Output JSON only, no markdown."""

            response = genai_client.models.generate_content(
                model=model,
                contents=[
                    types.Part(text=prompt.strip()),
                    types.Part(text="Image A (Camera):"),
                    types.Part.from_bytes(
                        data=camera_bytes, mime_type="image/png"),
                    types.Part(text="Image B (BEV Occupancy - Obstacles):"),
                    types.Part.from_bytes(
                        data=bev_occupancy_bytes, mime_type="image/png"),
                    types.Part(text="Image C (BEV Height - Elevation):"),
                    types.Part.from_bytes(
                        data=bev_height_bytes, mime_type="image/png"),
                    types.Part(
                        text="Image D (BEV Roughness - Surface Variation):"),
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
        """Save final perception output as artifact for Evaluator to load.

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
            f"\n🔵 [SAVE_PERCEPTION_OUTPUT] Called with {len(per_window)} windows")

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

    # Import ToolContext for type hint
    from google.adk.tools.tool_context import ToolContext

    # Return FunctionTool wrappers
    return (
        FunctionTool(func=list_windows_tool),
        FunctionTool(func=analyze_window_perception_tool),
        FunctionTool(func=save_perception_output_tool)
    )
