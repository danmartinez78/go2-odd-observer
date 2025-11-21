#!/usr/bin/env python3
"""
STANDALONE TEST: Motion Agent
Test motion analysis in isolation
"""

import asyncio
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
        import pandas as pd

        index_files = list(scenario_path.glob("index_*.csv"))
        if not index_files:
            return {"status": "error"}

        index_df = pd.read_csv(index_files[0])
        scenario_name = scenario_path.name

        for _, row in index_df.iterrows():
            wid = str(row['window_id']).zfill(3)
            if wid == window_id:
                motion_file = scenario_path / \
                    f"motion_{scenario_name}_w{window_id}.json"
                if motion_file.exists():
                    with open(motion_file, 'r') as f:
                        motion_data = json.load(f)
                    return {"status": "success", "window_id": window_id, "data": motion_data}

        return {"status": "error", "message": "Motion data not found"}
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
get_windows_tool = FunctionTool(func=get_scenario_windows)


def create_motion_agent() -> Agent:
    """Analyze motion metrics per window."""
    return Agent(
        name="Motion_Agent",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[get_windows_tool, get_motion_tool],
        instruction="""You are a motion analysis specialist.

TASK: Analyze motion for ALL windows in the scenario.

INSTRUCTIONS:
1. Call get_scenario_windows() to get list of window IDs
2. For each window, call get_motion_json(window_id)
3. Extract metrics: avg_forward_speed, max_forward_speed, max_abs_roll_pitch_deg
4. Classify each window's motion as "smooth" or "dynamic"
5. Return ONLY JSON with per-window analysis for ALL windows:

{
  "windows_analyzed": ["<id>", "<id>", ...],
  "per_window_motion": [
    {
      "window_id": "<id>",
      "avg_forward_speed": <float>,
      "max_forward_speed": <float>,
      "max_abs_roll_pitch_deg": <float>,
      "motion_label": "smooth|dynamic"
    }
  ]
}""",
    )


async def test_motion_agent():
    """Test motion agent in isolation."""
    print("\n" + "=" * 80)
    print("MOTION AGENT - ISOLATED TEST")
    print("=" * 80)

    agent = create_motion_agent()
    runner = InMemoryRunner(agent=agent)

    try:
        events = await runner.run_debug("Analyze motion for all windows")

        # Extract JSON from agent output
        for event in events:
            author = getattr(event, 'author', None)
            content = getattr(event, 'content', None)

            if author == "Motion_Agent" and content:
                if hasattr(content, 'parts'):
                    for part in content.parts:
                        if hasattr(part, 'text') and part.text:
                            text = part.text
                            # Try to extract JSON
                            if "{" in text and "}" in text:
                                start = text.find("{")
                                end = text.rfind("}") + 1
                                json_str = text[start:end]
                                try:
                                    result = json.loads(json_str)
                                    print("\n✅ Motion Agent Output:")
                                    print(json.dumps(result, indent=2))
                                    return result
                                except:
                                    pass

        print("❌ No valid JSON output from Motion Agent")
        return None

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    try:
        result = asyncio.run(test_motion_agent())
        if result:
            print("\n" + "=" * 80)
            print("✅ MOTION AGENT TEST PASSED")
            print("=" * 80)
        else:
            print("\n" + "=" * 80)
            print("❌ MOTION AGENT TEST FAILED")
            print("=" * 80)
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
