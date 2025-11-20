#!/usr/bin/env python3
"""Extract exact output content from Event 2"""

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
                    windows.append(
                        {"window_id": window_id, "motion_json": json.load(f)})
        return {"status": "success", "windows": windows}
    except:
        return {"status": "error"}


def get_window_image_raw(window_id: str, image_type: str, scenario_path: str) -> dict:
    try:
        from pathlib import Path
        scenario_path = Path(scenario_path)
        scenario_name = scenario_path.name
        if image_type == "camera":
            filename = f"cam_{scenario_name}_w{window_id}.png"
        elif image_type.startswith("bev_"):
            channel = image_type.replace("bev_", "")
            filename = f"bev_{channel}_{scenario_name}_w{window_id}.png"
        else:
            return {"status": "error"}
        file_path = scenario_path / filename
        if not file_path.exists():
            return {"status": "error"}
        with open(file_path, 'rb') as f:
            image_bytes = f.read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        return {"status": "success", "image_base64": image_base64, "size_kb": len(image_bytes) / 1024}
    except:
        return {"status": "error"}


def scenario_data_wrapper() -> dict:
    return get_scenario_data(str(scenario_path))


def image_wrapper(window_id: str, image_type: str) -> dict:
    return get_window_image_raw(window_id, image_type, str(scenario_path))


scenario_data_tool = FunctionTool(func=scenario_data_wrapper)
get_image_tool = FunctionTool(func=image_wrapper)


async def test_terrain():
    print("=" * 80)
    print("TERRAIN ANALYZER - DETAILED OUTPUT INSPECTION")
    print("=" * 80)

    terrain_agent = Agent(
        name="Terrain_Analyzer",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[scenario_data_tool, get_image_tool],
        instruction="Analyze terrain. Call get_scenario_data(), then get_window_image() for BEV images. Return JSON.",
        output_key="terrain_features"
    )

    runner = InMemoryRunner(agent=terrain_agent)
    events = await runner.run_debug(user_messages="Analyze terrain")

    print(f"\nTotal events: {len(events)}\n")

    for i, event in enumerate(events):
        author = getattr(event, 'author', None)
        content = getattr(event, 'content', None)

        if author == "Terrain_Analyzer":
            print(f"Event {i} - Terrain_Analyzer:")

            if content is None:
                print("  ⚠️  Content is NONE!")
            else:
                try:
                    parts_list = list(content)
                    print(f"  Parts: {len(parts_list)}")

                    for j, part in enumerate(parts_list):
                        if isinstance(part, tuple) and len(part) >= 2:
                            part_type = part[0]
                            part_value = part[1]

                            if part_type == "text":
                                print(f"\n  ✓ Part {j} - TEXT:")
                                print(
                                    f"    Length: {len(str(part_value))} chars")
                                print(f"    Content:\n{part_value}\n")
                            elif part_type == "parts":
                                print(f"\n  Part {j} - PARTS:")
                                print(f"    Value: {part_value}")
                except Exception as e:
                    print(f"  Error: {e}")

            print()

asyncio.run(test_terrain())
