#!/usr/bin/env python3
"""Quick test to check agent author names."""

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
            return {"status": "error"}

        file_path = scenario_path / filename
        if not file_path.exists():
            return {"status": "error"}

        with open(file_path, 'rb') as f:
            image_bytes = f.read()

        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        return {
            "status": "success",
            "image_base64": image_base64,
            "mime_type": "image/png",
            "size_kb": len(image_bytes) / 1024
        }
    except:
        return {"status": "error"}


scenario_data_tool = FunctionTool(
    func=lambda: get_scenario_data(str(scenario_path)))
get_image_tool = FunctionTool(func=lambda window_id, image_type: get_window_image_raw(
    window_id, image_type, str(scenario_path)))


async def test_terrain():
    """Check author names in terrain agent."""
    terrain_agent = Agent(
        name="Terrain_Analyzer",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[scenario_data_tool, get_image_tool],
        instruction="Analyze terrain.",
        output_key="terrain_features"
    )

    runner = InMemoryRunner(agent=terrain_agent)
    events = await runner.run_debug(user_messages="Analyze terrain")

    print("Terrain Agent - All Authors:\n")
    for i, event in enumerate(events):
        author = getattr(event, 'author', 'NO_AUTHOR')
        print(f"  Event {i}: author = '{author}'")


if __name__ == "__main__":
    asyncio.run(test_terrain())
