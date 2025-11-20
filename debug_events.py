#!/usr/bin/env python3
"""Debug event structure to find author names."""

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
    """Retrieve scenario data."""
    try:
        from pathlib import Path
        import pandas as pd

        scenario_path = Path(scenario_path)
        if not scenario_path.exists():
            return {"status": "error", "error_message": f"Path not found: {scenario_path}"}

        index_files = list(scenario_path.glob("index_*.csv"))
        if not index_files:
            return {"status": "error", "error_message": f"No index file found"}

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
    except Exception as e:
        return {"status": "error", "error_message": f"Failed: {str(e)}"}


def scenario_data_wrapper() -> dict:
    return get_scenario_data(str(scenario_path))


scenario_data_tool = FunctionTool(func=scenario_data_wrapper)


async def debug_motion():
    """Debug motion agent event structure."""
    print("\n📊 DEBUGGING MOTION AGENT EVENT STRUCTURE\n")

    motion_agent = Agent(
        name="Motion_Analyzer",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[scenario_data_tool],
        instruction="Analyze motion.",
        output_key="motion_features"
    )

    runner = InMemoryRunner(agent=motion_agent)
    events = await runner.run_debug(user_messages="Analyze motion")

    print(f"Total events: {len(events)}\n")

    for i, event in enumerate(events):
        print(f"Event {i}:")
        print(f"  Type: {type(event)}")
        print(f"  Dir: {[x for x in dir(event) if not x.startswith('_')]}")

        # Check all attributes
        for attr in ['author', 'role', 'content', 'parts', 'user', 'model_response']:
            if hasattr(event, attr):
                val = getattr(event, attr)
                print(f"  .{attr}: {type(val).__name__} = {repr(val)[:100]}")

        print()


if __name__ == "__main__":
    asyncio.run(debug_motion())
