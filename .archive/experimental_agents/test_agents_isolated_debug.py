#!/usr/bin/env python3
"""
Isolated Agent Testing Script with Detailed Debugging
"""

import base64
from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool
from google.adk.models.google_llm import Gemini
from google.adk.agents import Agent
from google.genai import types
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

if not GOOGLE_API_KEY:
    print("❌ GOOGLE_API_KEY not found!")
    sys.exit(1)

DATA_DIR = PROJECT_ROOT / "data" / "processed" / "runs"
scenario_path = DATA_DIR / "sim_run_test"


def get_scenario_data(scenario_path: str) -> dict:
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
            return {"status": "error", "error_message": f"Unknown image type: {image_type}"}

        file_path = scenario_path / filename
        if not file_path.exists():
            return {"status": "error", "error_message": f"Image not found: {filename}"}

        with open(file_path, 'rb') as f:
            image_bytes = f.read()

        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        return {
            "status": "success",
            "image_base64": image_base64,
            "mime_type": "image/png",
            "size_kb": len(image_bytes) / 1024,
            "format": ".png",
            "encoding": "base64"
        }
    except Exception as e:
        return {"status": "error", "error_message": f"Failed: {str(e)}"}


def scenario_data_wrapper() -> dict:
    return get_scenario_data(str(scenario_path))


def image_wrapper(window_id: str, image_type: str) -> dict:
    return get_window_image_raw(window_id, image_type, str(scenario_path))


scenario_data_tool = FunctionTool(func=scenario_data_wrapper)
get_image_tool = FunctionTool(func=image_wrapper)

print(f"✓ Using model: {GEMINI_MODEL}")
print("✓ Tools ready")

# ============================================================================
# HELPER: Detailed Event Analysis
# ============================================================================


def analyze_events(events, agent_name):
    """Print detailed event analysis."""
    print(f"\n  📊 DETAILED EVENT ANALYSIS for {agent_name}:")
    print(f"  Total events: {len(events)}")

    for i, event in enumerate(events):
        author = getattr(event, 'author', None)
        content = getattr(event, 'content', None)

        print(f"\n  Event {i}:")
        print(f"    Author: '{author}'")
        print(f"    Content type: {type(content).__name__}")
        print(f"    Content is None: {content is None}")

        if author == agent_name and content is not None:
            if hasattr(content, '__iter__'):
                try:
                    parts_list = list(content)
                    print(f"    ✓ Parts count: {len(parts_list)}")

                    for j, part in enumerate(parts_list):
                        print(f"      Part {j}:")
                        print(f"        Type: {type(part).__name__}")

                        if isinstance(part, tuple) and len(part) >= 2:
                            part_type = part[0]
                            part_value = part[1]
                            value_len = len(str(part_value))

                            print(f"        Kind: {part_type}")
                            print(f"        Value length: {value_len} chars")

                            if part_type == "text":
                                text_preview = str(part_value)[:400]
                                print(f"        Preview: {text_preview}")

                                # Try to parse JSON
                                if '```json' in str(part_value):
                                    print(f"        ✓ Contains JSON block")
                                elif '{' in str(part_value):
                                    print(f"        ✓ Contains JSON object")
                        else:
                            print(f"        Raw value: {str(part)[:100]}")
                except Exception as e:
                    print(f"    ⚠️  Error iterating parts: {e}")
            else:
                print(f"    Content not iterable: {str(content)[:200]}")


# ============================================================================
# TESTS
# ============================================================================

async def test_motion_agent():
    """Test Motion Analyzer in isolation."""
    print("\n" + "=" * 80)
    print("TEST 1: MOTION ANALYZER")
    print("=" * 80)

    motion_agent = Agent(
        name="Motion_Analyzer",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[scenario_data_tool],
        instruction="Analyze motion for all windows. Call get_scenario_data() first. Return JSON only.",
        output_key="motion_features"
    )

    runner = InMemoryRunner(agent=motion_agent)
    events = await runner.run_debug(user_messages="Analyze motion for all windows")

    analyze_events(events, "Motion_Analyzer")
    return events


async def test_vision_agent():
    """Test Vision Analyzer in isolation."""
    print("\n" + "=" * 80)
    print("TEST 2: VISION ANALYZER")
    print("=" * 80)

    vision_agent = Agent(
        name="Vision_Analyzer",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[scenario_data_tool, get_image_tool],
        instruction="Analyze vision for all windows. Call get_scenario_data() first. Then get_window_image('camera'). Return JSON only.",
        output_key="vision_features"
    )

    runner = InMemoryRunner(agent=vision_agent)
    events = await runner.run_debug(user_messages="Analyze vision for all windows")

    analyze_events(events, "Vision_Analyzer")
    return events


async def test_terrain_agent():
    """Test Terrain Analyzer in isolation."""
    print("\n" + "=" * 80)
    print("TEST 3: TERRAIN ANALYZER")
    print("=" * 80)

    terrain_agent = Agent(
        name="Terrain_Analyzer",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[scenario_data_tool, get_image_tool],
        instruction="Analyze terrain for all windows. Call get_scenario_data() first. Then get_window_image() for bev images. Return JSON only.",
        output_key="terrain_features"
    )

    runner = InMemoryRunner(agent=terrain_agent)
    events = await runner.run_debug(user_messages="Analyze terrain for all windows")

    analyze_events(events, "Terrain_Analyzer")
    return events


async def test_collision_agent():
    """Test Collision Detector in isolation."""
    print("\n" + "=" * 80)
    print("TEST 4: COLLISION DETECTOR")
    print("=" * 80)

    collision_agent = Agent(
        name="Collision_Detector",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[scenario_data_tool, get_image_tool],
        instruction="Detect collisions for all windows. Call get_scenario_data() first. Then get_window_image(). Return JSON only.",
        output_key="collision_features"
    )

    runner = InMemoryRunner(agent=collision_agent)
    events = await runner.run_debug(user_messages="Analyze collisions for all windows")

    analyze_events(events, "Collision_Detector")
    return events


async def main():
    print("\n" + "=" * 80)
    print("ISOLATED AGENT TEST - DETAILED DEBUGGING")
    print("=" * 80)
    print(f"Dataset: {scenario_path}")
    print(f"Model: {GEMINI_MODEL}\n")

    await test_motion_agent()
    await test_vision_agent()
    await test_terrain_agent()
    await test_collision_agent()

    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
