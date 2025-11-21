#!/usr/bin/env python3
"""
STANDALONE TEST: Collision Agent
Test multi-modal collision detection (motion + camera + LiDAR) in isolation
"""

import asyncio
import base64
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool
from google.adk.models.google_llm import Gemini
from google.adk.agents import Agent

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
GEMINI_MODEL = "gemini-2.0-flash-lite"

DATA_DIR = PROJECT_ROOT / "data" / "processed" / "runs"
scenario_path = DATA_DIR / "sim_run_test"


def get_motion_json(window_id: str) -> dict:
    """Get motion data for a window."""
    try:
        scenario_name = scenario_path.name
        file_path = scenario_path / f"motion_{scenario_name}_w{window_id}.json"

        if not file_path.exists():
            return {"status": "error"}

        with open(file_path) as f:
            data = json.load(f)

        return {
            "status": "success",
            "window_id": window_id,
            "motion_data": data,
        }
    except Exception as e:
        return {"status": "error"}


def get_window_image(window_id: str, image_type: str) -> dict:
    """Get a specific image for a window (camera or BEV)."""
    try:
        scenario_name = scenario_path.name
        filename_map = {
            "camera": f"cam_{scenario_name}_w{window_id}.png",
            "bev_occupancy": f"bev_occupancy_{scenario_name}_w{window_id}.png",
            "bev_height": f"bev_height_{scenario_name}_w{window_id}.png",
            "bev_density": f"bev_density_{scenario_name}_w{window_id}.png",
            "bev_roughness": f"bev_roughness_{scenario_name}_w{window_id}.png",
        }

        if image_type not in filename_map:
            return {"status": "error", "message": "Invalid image_type"}

        file_path = scenario_path / filename_map[image_type]
        if not file_path.exists():
            return {"status": "error", "message": "File not found"}

        with open(file_path, 'rb') as f:
            image_base64 = base64.b64encode(f.read()).decode('utf-8')

        return {
            "status": "success",
            "window_id": window_id,
            "image_type": image_type,
            "base64": image_base64,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_scenario_windows() -> dict:
    """Get list of all available windows in scenario."""
    try:
        import pandas as pd

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
                windows.append(window_id)

        return {"status": "success", "windows": windows, "count": len(windows)}
    except Exception as e:
        return {"status": "error"}


# Tools
get_motion_tool = FunctionTool(func=get_motion_json)
get_image_tool = FunctionTool(func=get_window_image)
get_windows_tool = FunctionTool(func=get_scenario_windows)


def create_collision_agent() -> Agent:
    """Analyze collision risks using multi-modal fusion (motion + camera + LiDAR)."""
    return Agent(
        name="Collision_Agent",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[get_windows_tool, get_motion_tool, get_image_tool],
        instruction="""You are a multi-modal collision detection specialist using motion, camera, and LiDAR.

TASK: Analyze ACTUAL collision risks for ALL windows using multi-modal fusion of real data.

STEP-BY-STEP:
1. Call get_scenario_windows() to get actual window IDs from data
2. For EACH window ID returned, perform REAL multi-modal fusion:
   a) Call get_motion_json(window_id) to retrieve actual kinematic data
      - Analyze: forward_speed, angular_velocity, roll, pitch from actual data
      - Assess actual motion dynamics
   b) Call get_image_tool(window_id, "camera") to analyze actual camera image for collision threats
   c) Call get_image_tool(window_id, "bev_occupancy") to analyze actual obstacle proximity
3. Fuse ACTUAL modalities to assess collision risk:
   - Motion-based risk: Analyze actual speed, turning, stability
   - Camera-based risk: Identify actual obstacles in path, visibility conditions
   - LiDAR-based risk: Analyze actual obstacle distances in occupancy grid
4. Classify per window based on ACTUAL fused data:
   - risk_level: "safe" | "caution" | "alert"
   - collision_likelihood_score: 0.0-1.0
5. Return ONLY valid JSON with this structure:

{
  "windows_analyzed": [<list of actual window IDs>],
  "collision_events": [
    {
      "window_id": <actual_id>,
      "risk_level": <based on actual data>,
      "collision_likelihood_score": <calculated from fusion>,
      "motion_risk_factors": [<actual factors observed>],
      "vision_risk_factors": [<actual observations>],
      "lidar_risk_factors": [<actual observations>],
      "fusion_evidence": "<actual analysis>"
    }
  ]
}""",
    )


async def test_collision_agent():
    """Test collision agent in isolation."""
    print("\n" + "=" * 80)
    print("COLLISION AGENT - ISOLATED TEST (Motion + Camera + LiDAR)")
    print("=" * 80)

    agent = create_collision_agent()
    runner = InMemoryRunner(agent=agent)

    try:
        events = await runner.run_debug("Analyze collision risks for all windows using motion + image fusion")

        # Extract JSON from agent output
        for event in events:
            author = getattr(event, 'author', None)
            content = getattr(event, 'content', None)

            if author == "Collision_Agent" and content:
                if hasattr(content, 'parts'):
                    for part in content.parts:
                        if hasattr(part, 'text') and part.text:
                            text = part.text
                            print(
                                f"\n[DEBUG] Collision Agent raw output:\n{text}\n")
                            # Try to extract JSON
                            if "{" in text and "}" in text:
                                start = text.find("{")
                                end = text.rfind("}") + 1
                                json_str = text[start:end]
                                try:
                                    result = json.loads(json_str)
                                    print("\n✅ Collision Agent Output:")
                                    print(json.dumps(result, indent=2))
                                    return result
                                except Exception as je:
                                    print(f"[DEBUG] JSON parse error: {je}")
                                    pass

        print("❌ No valid JSON output from Collision Agent")
        return None

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    try:
        result = asyncio.run(test_collision_agent())
        if result:
            print("\n" + "=" * 80)
            print("✅ COLLISION AGENT TEST PASSED")
            print("=" * 80)
        else:
            print("\n" + "=" * 80)
            print("❌ COLLISION AGENT TEST FAILED")
            print("=" * 80)
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
