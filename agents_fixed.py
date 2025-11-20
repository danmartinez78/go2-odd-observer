#!/usr/bin/env python3
"""
Fixed Agent Script - All Agents with Corrected Parameter Names
Tests each agent with the correct parameter names discovered during debugging.
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
    """
    Retrieve image as base64.

    Parameters:
    - window_id: str (e.g., "006", "007")
    - image_type: str - must be one of:
        * "camera" - RGB camera image
        * "bev_occupancy" - BEV occupancy map
        * "bev_height" - BEV height map
        * "bev_density" - BEV obstacle density
        * "bev_roughness" - BEV terrain roughness
    """
    try:
        from pathlib import Path

        scenario_path = Path(scenario_path)
        scenario_name = scenario_path.name

        # Map image types to filenames
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
            return {
                "status": "error",
                "error_message": f"Invalid image_type: {image_type}. Must be one of: camera, bev_occupancy, bev_height, bev_density, bev_roughness"
            }

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
# AGENT DEFINITIONS (WITH FIXED PARAMETER NAMES)
# ============================================================================


async def test_motion_agent():
    """Test Motion Analyzer with correct tool usage."""
    print("\n" + "=" * 80)
    print("TEST 1: MOTION ANALYZER")
    print("=" * 80)

    motion_agent = Agent(
        name="Motion_Analyzer",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[scenario_data_tool],
        instruction="""You are a motion analysis expert for mobile robots.

CRITICAL INSTRUCTIONS FOR TOOL USAGE:
1. FIRST: Call get_scenario_data() tool to retrieve actual window IDs
2. Do NOT make up window IDs - use ONLY what the tool returns
3. For EACH window returned by the tool, extract motion features
4. Return results for ALL windows from the tool

Output valid JSON ONLY with this schema:
{
  "windows": [
    {
      "window_id": "006",
      "avg_forward_speed": <float m/s>,
      "max_forward_speed": <float m/s>,
      "max_abs_roll_pitch_deg": <float degrees>,
      "motion_label": "smooth" | "dynamic"
    }
  ]
}

IMPORTANT: 
- Process ALL windows
- Extract REAL metrics from motion_json
- Return complete JSON analysis
- Do NOT include tool responses or raw data in final output""",
        output_key="motion_features"
    )

    runner = InMemoryRunner(agent=motion_agent)
    events = await runner.run_debug(user_messages="Analyze motion for all available windows")

    print(f"✓ Received {len(events)} events")
    return events


async def test_vision_agent():
    """Test Vision Analyzer with correct tool usage."""
    print("\n" + "=" * 80)
    print("TEST 2: VISION ANALYZER")
    print("=" * 80)

    vision_agent = Agent(
        name="Vision_Analyzer",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[scenario_data_tool, get_image_tool],
        instruction="""You are a vision analysis expert for mobile robots.

CRITICAL INSTRUCTIONS FOR TOOL USAGE:
1. FIRST: Call get_scenario_data() tool to get actual window IDs
2. Do NOT make up window IDs - use ONLY what the tool returns
3. For EACH window from the tool, retrieve camera images using:
   - get_window_image(window_id="006", image_type="camera")
   - NOTE: image_type MUST be exactly "camera" (lowercase)
4. ANALYZE each retrieved camera image immediately after retrieval
5. DO NOT include raw image bytes in your JSON output
6. Return results for ALL windows

Output valid JSON ONLY with this schema:
{
  "windows": [
    {
      "window_id": "006",
      "lighting_class": "bright" | "dim" | "dark",
      "humans_detected": true | false,
      "humans_very_close": true | false,
      "obstacle_visible": true | false,
      "visibility_score": <float 0-1>,
      "notes": "Brief description"
    }
  ]
}

IMPORTANT: 
- Process ALL windows
- Retrieve images with exact parameter values: window_id and image_type="camera"
- Analyze images immediately after retrieval
- No raw image bytes in output
- Return complete JSON analysis""",
        output_key="vision_features"
    )

    runner = InMemoryRunner(agent=vision_agent)
    events = await runner.run_debug(user_messages="Analyze vision for all available windows")

    print(f"✓ Received {len(events)} events")
    return events


async def test_terrain_agent():
    """Test Terrain Analyzer with correct tool usage."""
    print("\n" + "=" * 80)
    print("TEST 3: TERRAIN ANALYZER")
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

    print(f"✓ Received {len(events)} events")
    return events


async def test_collision_agent():
    """Test Collision Detector with correct tool usage."""
    print("\n" + "=" * 80)
    print("TEST 4: COLLISION DETECTOR")
    print("=" * 80)

    collision_agent = Agent(
        name="Collision_Detector",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[scenario_data_tool, get_image_tool],
        instruction="""You are a collision detection expert for mobile robots.

CRITICAL INSTRUCTIONS FOR TOOL USAGE:
1. FIRST: Call get_scenario_data() tool to get actual window IDs
2. Do NOT make up window IDs - use ONLY what the tool returns
3. For EACH window from the tool, retrieve images using:
   - get_window_image(window_id="006", image_type="camera")
   - get_window_image(window_id="006", image_type="bev_occupancy")
   - get_window_image(window_id="006", image_type="bev_height")
   - NOTE: image_type values MUST be EXACTLY as shown (lowercase, with underscores)
4. ANALYZE each retrieved image immediately after retrieval
5. DO NOT include raw image bytes in your JSON output
6. Return results for ALL windows

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

IMPORTANT: 
- Process ALL windows
- Retrieve MULTIPLE image types with exact parameter values
- Analyze images immediately after retrieval
- No raw image bytes in output
- Return complete JSON analysis""",
        output_key="collision_features"
    )

    runner = InMemoryRunner(agent=collision_agent)
    events = await runner.run_debug(user_messages="Analyze collisions for all available windows")

    print(f"✓ Received {len(events)} events")
    return events


# ============================================================================
# SUMMARY & ANALYSIS
# ============================================================================

def extract_json_from_text(text: str):
    """Extract JSON from text that may contain markdown code blocks."""
    if text is None:
        return None, False

    # Try direct JSON parse first
    try:
        return json.loads(text), True
    except:
        pass

    # Try to extract from markdown code block
    if "```json" in text and "```" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        if start > 7 and end > start:
            json_str = text[start:end].strip()
            try:
                return json.loads(json_str), True
            except:
                pass

    # Try to extract any JSON block
    if "{" in text and "}" in text:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            json_str = text[start:end]
            try:
                return json.loads(json_str), True
            except:
                pass

    return None, False


def analyze_events(agent_name: str, events: list) -> dict:
    """Analyze agent events to extract final output."""
    summary = {
        "agent": agent_name,
        "total_events": len(events),
        "agent_messages": 0,
        "has_final_output": False,
        "final_output_size": 0,
        "final_json": None,
        "error": None
    }

    # Look through ALL events, not just the last one
    latest_text = None
    latest_json = None

    for event in events:
        author = getattr(event, 'author', None)
        content = getattr(event, 'content', None)

        if author == agent_name:
            summary["agent_messages"] += 1

            if content is not None and hasattr(content, 'parts'):
                for part in content.parts:
                    if hasattr(part, 'text') and part.text is not None:
                        text = part.text
                        summary["final_output_size"] = len(text)
                        latest_text = text
                        # Try to extract JSON
                        parsed_json, is_valid = extract_json_from_text(text)
                        if is_valid and parsed_json:
                            latest_json = parsed_json

    # Set final output based on latest JSON found
    if latest_json:
        summary["has_final_output"] = True
        summary["final_json"] = latest_json

    return summary


async def main():
    """Run all agent tests."""
    print("\n" + "=" * 90)
    print("FIXED AGENT TEST SUITE - All agents with corrected parameter names")
    print("=" * 90)
    print(f"Dataset: {scenario_path}")
    print(f"Model: {GEMINI_MODEL}")
    print()

    results = {}
    agents = {
        'motion': test_motion_agent,
        'vision': test_vision_agent,
        'terrain': test_terrain_agent,
        'collision': test_collision_agent,
    }

    for agent_name, test_func in agents.items():
        try:
            events = await test_func()
            results[agent_name] = events
        except Exception as e:
            print(f"❌ {agent_name.upper()} Error: {e}")
            import traceback
            traceback.print_exc()
            results[agent_name] = None

    # Summary
    print("\n" + "=" * 90)
    print("SUMMARY - Agent Performance")
    print("=" * 90)

    all_passed = True
    agent_mapping = {
        'motion': 'Motion_Analyzer',
        'vision': 'Vision_Analyzer',
        'terrain': 'Terrain_Analyzer',
        'collision': 'Collision_Detector',
    }

    for agent_key, agent_name in agent_mapping.items():
        events = results.get(agent_key)
        if events is None:
            print(f"{agent_key.upper():20} ❌ EXCEPTION")
            all_passed = False
            continue

        summary = analyze_events(agent_name, events)

        if summary["has_final_output"]:
            status = "✅ SUCCESS"
            print(f"{agent_key.upper():20} {status}")
            print(f"  - Total events: {summary['total_events']}")
            print(f"  - Agent messages: {summary['agent_messages']}")
            print(f"  - Output size: {summary['final_output_size']} chars")
            if summary['final_json'] and 'windows' in summary['final_json']:
                print(
                    f"  - Windows analyzed: {len(summary['final_json']['windows'])}")
        else:
            status = "❌ FAILED"
            print(f"{agent_key.upper():20} {status}")
            print(f"  - Total events: {summary['total_events']}")
            print(f"  - Agent messages: {summary['agent_messages']}")
            print(f"  - Has valid JSON output: {summary['has_final_output']}")
            all_passed = False

    print("\n" + "=" * 90)
    if all_passed:
        print("✅ ALL AGENTS PASSED!")
    else:
        print("⚠️  Some agents failed. Check output above.")
    print("=" * 90)


if __name__ == "__main__":
    asyncio.run(main())
