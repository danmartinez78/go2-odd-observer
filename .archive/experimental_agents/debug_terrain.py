#!/usr/bin/env python3
"""Debug terrain agent specifically."""

import base64
from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool
from google.adk.models.google_llm import Gemini
from google.adk.agents import Agent
import asyncio
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
GEMINI_MODEL = "gemini-2.0-flash-lite"

DATA_DIR = PROJECT_ROOT / "data" / "processed" / "runs"
scenario_path = DATA_DIR / "sim_run_test"


def get_scenario_data(scenario_path: str) -> dict:
    try:
        from pathlib import Path
        import pandas as pd

        scenario_path = Path(scenario_path)
        if not scenario_path.exists():
            return {"status": "error"}

        index_files = list(scenario_path.glob("index_*.csv"))
        if not index_files:
            return {"status": "error"}

        index_df = pd.read_csv(index_files[0])
        scenario_name = scenario_path.name
        windows = []

        for _, row in index_df.iterrows():
            window_id = str(row['window_id']).zfill(3)
            motion_file = scenario_path / \
                f"motion_{scenario_name}_w{window_id}.json"
            if motion_file.exists():
                with open(motion_file, 'r') as f:
                    motion_json = json.load(f)
                windows.append(
                    {"window_id": window_id, "motion_json": motion_json})

        return {
            "status": "success",
            "scenario_name": scenario_name,
            "total_windows": len(windows),
            "windows": windows
        }
    except:
        return {"status": "error"}


def get_window_image_raw(window_id: str, image_type: str, scenario_path: str) -> dict:
    try:
        from pathlib import Path

        scenario_path = Path(scenario_path)
        scenario_name = scenario_path.name

        if image_type == "camera":
            filename = f"cam_{scenario_name}_w{window_id}.png"
        elif image_type == "bev_occupancy":
            filename = f"bev_occupancy_{scenario_name}_w{window_id}.png"
        elif image_type == "bev_height":
            filename = f"bev_height_{scenario_name}_w{window_id}.png"
        elif image_type == "bev_density":
            filename = f"bev_density_{scenario_name}_w{window_id}.png"
        elif image_type == "bev_roughness":
            filename = f"bev_roughness_{scenario_name}_w{window_id}.png"
        else:
            return {"status": "error", "error_message": f"Unknown image_type: {image_type}"}

        file_path = scenario_path / filename
        if not file_path.exists():
            return {"status": "error", "error_message": f"File not found: {filename}"}

        with open(file_path, 'rb') as f:
            image_bytes = f.read()

        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        return {
            "status": "success",
            "image_base64": image_base64,
            "mime_type": "image/png",
            "size_kb": len(image_bytes) / 1024
        }
    except Exception as e:
        return {"status": "error", "error_message": f"Error: {str(e)}"}


def scenario_data_wrapper(): return get_scenario_data(str(scenario_path))


def image_wrapper(window_id, image_type): return get_window_image_raw(
    window_id, image_type, str(scenario_path))


scenario_data_tool = FunctionTool(func=scenario_data_wrapper)
get_image_tool = FunctionTool(func=image_wrapper)


async def test_terrain():
    """Debug terrain agent."""
    print("\n" + "=" * 80)
    print("DEBUG: TERRAIN ANALYZER")
    print("=" * 80)

    terrain_agent = Agent(
        name="Terrain_Analyzer",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[scenario_data_tool, get_image_tool],
        instruction="""You are a terrain analysis expert for mobile robots.

CRITICAL INSTRUCTIONS FOR TOOL USAGE:
1. FIRST: Call get_scenario_data() tool to get actual window IDs
2. Do NOT make up window IDs - use ONLY what the tool returns
3. For EACH window from the tool, retrieve ALL four BEV images using:
   - get_window_image(window_id="006", image_type="bev_occupancy")
   - get_window_image(window_id="006", image_type="bev_height")
   - get_window_image(window_id="006", image_type="bev_density")
   - get_window_image(window_id="006", image_type="bev_roughness")
   - NOTE: image_type values MUST be EXACTLY as shown (lowercase, with underscore)
4. ANALYZE each retrieved BEV image immediately after retrieval
5. DO NOT include raw image bytes in your JSON output
6. Return results for ALL windows

Output valid JSON ONLY with this schema:
{
  "windows": [
    {
      "window_id": "006",
      "terrain_roughness_class": "smooth" | "moderate" | "rough" | "very_rough",
      "occupancy_ratio": <float 0-1>,
      "obstacle_density": <float 0-1>,
      "traversability_score": <float 0-1>,
      "hazard_regions": []
    }
  ]
}

IMPORTANT: 
- Process ALL windows
- Retrieve ALL FOUR BEV image types with exact parameter values
- Analyze BEV maps immediately after retrieval
- No raw image bytes in output
- Return complete JSON analysis""",
        output_key="terrain_features"
    )

    runner = InMemoryRunner(agent=terrain_agent)
    events = await runner.run_debug(user_messages="Analyze terrain for all available windows")

    print(f"\n✓ Total events: {len(events)}\n")

    print("All events content:")
    for i, event in enumerate(events):
        author = getattr(event, 'author', 'Unknown')
        print(f"\nEvent {i}: {author}")

        if hasattr(event, 'content') and event.content and hasattr(event.content, 'parts'):
            for j, part in enumerate(event.content.parts):
                print(f"  Part {j}: {type(part).__name__}")
                if hasattr(part, 'text'):
                    text = part.text
                    if text:
                        preview = text[:200] if len(text) > 200 else text
                        print(f"    {preview}")
                    else:
                        print(f"    (empty/None)")


if __name__ == "__main__":
    asyncio.run(test_terrain())
