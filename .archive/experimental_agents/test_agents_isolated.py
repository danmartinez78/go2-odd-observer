#!/usr/bin/env python3
"""
Isolated Agent Testing Script
Tests each agent individually to identify failures in parallel execution.
"""

import base64
from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool
from google.adk.models.google_llm import Gemini
from google.adk.agents import Agent, SequentialAgent, ParallelAgent
from google.genai import types
import asyncio
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Setup paths
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# LOAD CONFIG
# ============================================================================
load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
GEMINI_MODEL = "gemini-2.0-flash-lite"

if not GOOGLE_API_KEY:
    print("❌ GOOGLE_API_KEY not found!")
    sys.exit(1)

print(f"✓ Using model: {GEMINI_MODEL}")

# ============================================================================
# DATA ACCESS TOOLS
# ============================================================================

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


def get_window_image_raw(window_id: str, image_type: str, scenario_path: str) -> dict:
    """Retrieve image as base64."""
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


# Create tool wrappers
def scenario_data_wrapper() -> dict:
    return get_scenario_data(str(scenario_path))


def image_wrapper(window_id: str, image_type: str) -> dict:
    return get_window_image_raw(window_id, image_type, str(scenario_path))


scenario_data_tool = FunctionTool(func=scenario_data_wrapper)
get_image_tool = FunctionTool(func=image_wrapper)

print("✓ Tools defined and ready")

# ============================================================================
# ODD SPEC (Used by all agents)
# ============================================================================
odd_spec_json = {
    "version": "1.0",
    "description": "Unitree Go2 indoor office navigation",
    "axes": {
        "speed": {
            "type": "numeric",
            "feature": "avg_forward_speed",
            "units": "m/s",
            "in_odd": [0, 1.5],
            "near_boundary": [1.5, 1.8],
            "hard_limit": [0, 2.5]
        },
        "roll_pitch": {
            "type": "numeric",
            "feature": "max_abs_roll_pitch_deg",
            "units": "degrees",
            "in_odd": [0, 15],
            "near_boundary": [15, 20],
            "hard_limit": [0, 30]
        },
        "terrain": {
            "type": "categorical",
            "feature": "terrain_roughness_class",
            "allowed_in_odd": ["smooth", "moderate"],
            "allowed_all": ["smooth", "moderate", "rough", "very_rough"]
        },
        "lighting": {
            "type": "categorical",
            "feature": "lighting_class",
            "allowed_in_odd": ["bright", "dim"],
            "allowed_all": ["bright", "dim", "dark"]
        },
        "humans_close": {
            "type": "categorical",
            "feature": "humans_very_close",
            "allowed_in_odd": [False],
            "allowed_all": [True, False]
        },
        "collision": {
            "type": "categorical",
            "feature": "collision_suspected",
            "allowed_in_odd": [False],
            "allowed_all": [True, False]
        }
    },
    "importance": {
        "speed": 1.0,
        "roll_pitch": 1.2,
        "terrain": 1.0,
        "lighting": 0.8,
        "humans_close": 1.5,
        "collision": 2.0
    }
}

# ============================================================================
# TEST FUNCTIONS
# ============================================================================


async def test_motion_agent():
    """Test Motion Analyzer in isolation."""
    print("\n" + "=" * 80)
    print("TEST 1: MOTION ANALYZER (Isolated)")
    print("=" * 80)

    motion_agent = Agent(
        name="Motion_Analyzer",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[scenario_data_tool],
        instruction="""You are a motion analysis expert for mobile robots.

CRITICAL INSTRUCTIONS:
1. FIRST: Call get_scenario_data() tool to retrieve actual window IDs
2. Do NOT make up window IDs - use ONLY what the tool returns
3. For EACH window returned by the tool, extract motion features
4. Return results for ALL windows from the tool

From the shared state, you have:
- odd_spec_json: The formal ODD specification

Output valid JSON ONLY with this schema:
{
  "windows": [
    {
      "window_id": "006",
      "avg_forward_speed": <float>,
      "max_forward_speed": <float>,
      "max_abs_roll_pitch_deg": <float>,
      "motion_label": "smooth" | "dynamic"
    }
  ]
}

IMPORTANT: Process ALL windows. Extract REAL metrics. Return complete analysis.""",
        output_key="motion_features"
    )

    runner = InMemoryRunner(agent=motion_agent)
    events = await runner.run_debug(user_messages="Analyze motion for all windows")

    print(f"✓ Received {len(events)} events")

    # Detailed event analysis
    for i, event in enumerate(events):
        author = getattr(event, 'author', None)
        content = getattr(event, 'content', None)

        print(f"  Event {i}:")
        print(f"    Author: {author}")
        print(f"    Content type: {type(content)}")
        print(f"    Content is None: {content is None}")

        if author == "Motion_Analyzer":
            if content is not None and hasattr(content, '__iter__'):
                parts_list = list(content)
                print(f"    Parts count: {len(parts_list)}")
                for j, part in enumerate(parts_list):
                    print(f"      Part {j}: {type(part)}")
                    if isinstance(part, tuple) and len(part) >= 2:
                        print(
                            f"        Type: {part[0]}, Value length: {len(str(part[1]))}")
                        if part[0] == "text":
                            text_preview = str(part[1])[:300]
                            print(f"        Content: {text_preview}...")
    events = await runner.run_debug(user_messages="Analyze vision for all windows")

    print(f"✓ Received {len(events)} events")

    for i, event in enumerate(events):
        if getattr(event, 'author', None) == "Vision_Analyzer":
            content = getattr(event, 'content', None)
            has_content = content is not None
            print(f"  Event {i}: content={'✅' if has_content else '❌ EMPTY'}")

            if content and hasattr(content, '__iter__'):
                for part in content:
                    if isinstance(part, tuple) and len(part) >= 2:
                        if part[0] == "text":
                            text = str(part[1])[:200]
                            print(f"    Text preview: {text}...")

    return events


async def test_terrain_agent():
    """Test Terrain Analyzer in isolation."""
    print("\n" + "=" * 80)
    print("TEST 3: TERRAIN ANALYZER (Isolated)")
    print("=" * 80)

    terrain_agent = Agent(
        name="Terrain_Analyzer",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[scenario_data_tool, get_image_tool],
        instruction="""You are a terrain analysis expert for mobile robots.

CRITICAL INSTRUCTIONS:
1. FIRST: Call get_scenario_data() tool to get actual window IDs
2. Do NOT make up window IDs - use ONLY what the tool returns
3. For EACH window from the tool, retrieve BEV images
4. Call get_window_image() with: "bev_occupancy", "bev_height", "bev_density", "bev_roughness"
5. ANALYZE each retrieved BEV image immediately
6. DO NOT include raw image bytes in your JSON output
7. Return results for ALL windows

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

IMPORTANT: Process ALL windows. Retrieve ALL four BEV images. Analyze BEV maps. No image bytes. Complete analysis.""",
        output_key="terrain_features"
    )

    runner = InMemoryRunner(agent=terrain_agent)
    events = await runner.run_debug(user_messages="Analyze terrain for all windows")

    print(f"✓ Received {len(events)} events")

    for i, event in enumerate(events):
        if getattr(event, 'author', None) == "Terrain_Analyzer":
            content = getattr(event, 'content', None)
            has_content = content is not None
            print(f"  Event {i}: content={'✅' if has_content else '❌ EMPTY'}")

            if content and hasattr(content, '__iter__'):
                for part in content:
                    if isinstance(part, tuple) and len(part) >= 2:
                        if part[0] == "text":
                            text = str(part[1])[:200]
                            print(f"    Text preview: {text}...")

    return events


async def test_collision_agent():
    """Test Collision Detector in isolation."""
    print("\n" + "=" * 80)
    print("TEST 4: COLLISION DETECTOR (Isolated)")
    print("=" * 80)

    collision_agent = Agent(
        name="Collision_Detector",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[scenario_data_tool, get_image_tool],
        instruction="""You are a collision detection expert for mobile robots.

CRITICAL INSTRUCTIONS:
1. FIRST: Call get_scenario_data() tool to get actual window IDs
2. Do NOT make up window IDs - use ONLY what the tool returns
3. For EACH window from the tool, retrieve images
4. Call get_window_image() with: "camera", "bev_occupancy", "bev_height"
5. ANALYZE each retrieved image immediately
6. DO NOT include raw image bytes in your JSON output
7. Return results for ALL windows

Output valid JSON ONLY with this schema:
{
  "windows": [
    {
      "window_id": "006",
      "collision_suspected": true | false,
      "collision_confidence": <float 0-1>,
      "collision_type": "none" | "obstacle" | "wall" | "human" | "unknown",
      "risk_level": "safe" | "warning" | "danger",
      "notes": "Description of what collision hazard was detected"
    }
  ]
}

IMPORTANT: Process ALL windows. Retrieve MULTIPLE image types. Analyze images. No image bytes. Complete analysis.""",
        output_key="collision_features"
    )

    runner = InMemoryRunner(agent=collision_agent)
    events = await runner.run_debug(user_messages="Analyze collisions for all windows")

    print(f"✓ Received {len(events)} events")

    for i, event in enumerate(events):
        if getattr(event, 'author', None) == "Collision_Detector":
            content = getattr(event, 'content', None)
            has_content = content is not None
            print(f"  Event {i}: content={'✅' if has_content else '❌ EMPTY'}")

            if content and hasattr(content, '__iter__'):
                for part in content:
                    if isinstance(part, tuple) and len(part) >= 2:
                        if part[0] == "text":
                            text = str(part[1])[:200]
                            print(f"    Text preview: {text}...")

    return events


async def main():
    """Run all agent tests in sequence."""
    print("\n" + "=" * 80)
    print("ISOLATED AGENT TEST SUITE")
    print("=" * 80)
    print(f"Dataset: {scenario_path}")
    print(f"Model: {GEMINI_MODEL}")

    results = {}

    try:
        results['motion'] = await test_motion_agent()
    except Exception as e:
        print(f"❌ Motion Agent Error: {e}")
        results['motion'] = None

    try:
        results['vision'] = await test_vision_agent()
    except Exception as e:
        print(f"❌ Vision Agent Error: {e}")
        results['vision'] = None

    try:
        results['terrain'] = await test_terrain_agent()
    except Exception as e:
        print(f"❌ Terrain Agent Error: {e}")
        results['terrain'] = None

    try:
        results['collision'] = await test_collision_agent()
    except Exception as e:
        print(f"❌ Collision Agent Error: {e}")
        results['collision'] = None

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    for agent_name, events in results.items():
        if events:
            final_event = None
            for event in events:
                if getattr(event, 'author', None) and agent_name.capitalize() in getattr(event, 'author', ''):
                    final_event = event

            if final_event:
                has_content = getattr(final_event, 'content', None) is not None
                status = "✅ SUCCESS" if has_content else "❌ FAILED"
                print(f"{agent_name.upper():15} {status}")
            else:
                print(f"{agent_name.upper():15} ❌ NO FINAL EVENT")
        else:
            print(f"{agent_name.upper():15} ❌ EXCEPTION")


if __name__ == "__main__":
    asyncio.run(main())
