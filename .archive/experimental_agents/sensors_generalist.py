#!/usr/bin/env python3
"""
Generalist Sensor Analyzer - Unified approach
============================================

Test alternative architecture:
- Motion_Analyzer (specialized - motion data)
- Sensor_Analyzer (generalist - ALL image types)
- Collision_Detector (specialized - collision risk)

This reduces complexity and improves performance.
"""

import base64
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

# ============================================================================
# SETUP
# ============================================================================

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

print(f"✓ Configuration loaded")
print(f"  - Model: {GEMINI_MODEL}")
print(f"  - Data: {scenario_path}")

# ============================================================================
# TOOLS
# ============================================================================


def get_scenario_data(scenario_path: str) -> dict:
    """Retrieve scenario metadata and available windows."""
    try:
        from pathlib import Path
        import pandas as pd

        scenario_path = Path(scenario_path)
        if not scenario_path.exists():
            return {"status": "error", "error_message": f"Path not found: {scenario_path}"}

        index_files = list(scenario_path.glob("index_*.csv"))
        if not index_files:
            return {"status": "error", "error_message": "No index file found"}

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


def get_window_image(window_id: str, image_type: str, scenario_path: str) -> dict:
    """
    Retrieve image for a specific window as base64.

    Supports all image types:
    - "camera" : RGB camera image
    - "bev_occupancy", "bev_height", "bev_density", "bev_roughness" : BEV maps
    """
    try:
        from pathlib import Path

        scenario_path = Path(scenario_path)
        scenario_name = scenario_path.name

        valid_types = ["camera", "bev_occupancy",
                       "bev_height", "bev_density", "bev_roughness"]
        if image_type not in valid_types:
            return {
                "status": "error",
                "error_message": f"Invalid image_type: '{image_type}'. Must be one of: {', '.join(valid_types)}"
            }

        if image_type == "camera":
            filename = f"cam_{scenario_name}_w{window_id}.png"
        else:
            filename = f"{image_type}_{scenario_name}_w{window_id}.png"

        file_path = scenario_path / filename
        if not file_path.exists():
            return {"status": "error", "error_message": f"Image file not found: {filename}"}

        with open(file_path, 'rb') as f:
            image_bytes = f.read()

        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        return {
            "status": "success",
            "image_base64": image_base64,
            "mime_type": "image/png",
            "size_kb": len(image_bytes) / 1024,
        }
    except Exception as e:
        return {"status": "error", "error_message": f"Failed: {str(e)}"}


def scenario_data_wrapper() -> dict:
    return get_scenario_data(str(scenario_path))


def image_wrapper(window_id: str, image_type: str) -> dict:
    return get_window_image(window_id, image_type, str(scenario_path))


scenario_data_tool = FunctionTool(func=scenario_data_wrapper)
get_image_tool = FunctionTool(func=image_wrapper)

print("✓ Tools created")

# ============================================================================
# AGENT DEFINITIONS - GENERALIST APPROACH
# ============================================================================


def create_motion_analyzer() -> Agent:
    """Motion analyzer - unchanged, specializes in motion data."""
    return Agent(
        name="Motion_Analyzer",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[scenario_data_tool],
        instruction="""You are a motion analysis expert for mobile robots.

INSTRUCTIONS:
1. Call get_scenario_data() to get window IDs
2. Extract motion metrics from motion_json for each window
3. Return JSON with motion features

Output schema:
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
}""",
        output_key="motion_features"
    )


def create_sensor_analyzer() -> Agent:
    """
    GENERALIST Sensor Analyzer - handles ALL image types.

    Unified approach for vision + terrain analysis.
    Analyzes both camera and BEV images with single agent.
    """
    return Agent(
        name="Sensor_Analyzer",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[scenario_data_tool, get_image_tool],
        instruction="""You are a comprehensive sensor analysis expert for mobile robots.

INSTRUCTIONS:
1. Call get_scenario_data() to get window IDs
2. For EACH window, retrieve and analyze these images:
   - get_window_image(window_id="006", image_type="camera")
   - get_window_image(window_id="006", image_type="bev_occupancy")
   - get_window_image(window_id="006", image_type="bev_height")
   - get_window_image(window_id="006", image_type="bev_density")
   - get_window_image(window_id="006", image_type="bev_roughness")
3. ANALYZE each image immediately after retrieval
4. Synthesize findings into unified sensor analysis
5. Return comprehensive results for ALL windows

CRITICAL: image_type must be EXACTLY: camera, bev_occupancy, bev_height, bev_density, bev_roughness

Output schema:
{
  "windows": [
    {
      "window_id": "006",
      "vision": {
        "lighting_class": "bright" | "dim" | "dark",
        "humans_detected": true | false,
        "humans_very_close": true | false,
        "obstacle_visible": true | false,
        "visibility_score": <float 0-1>
      },
      "terrain": {
        "terrain_roughness_class": "smooth" | "moderate" | "rough" | "very_rough",
        "occupancy_ratio": <float 0-1>,
        "obstacle_density": <float 0-1>,
        "traversability_score": <float 0-1>,
        "hazard_regions": []
      }
    }
  ]
}""",
        output_key="sensor_features"
    )


def create_collision_detector() -> Agent:
    """Collision detector - unchanged, specialized role."""
    return Agent(
        name="Collision_Detector",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[scenario_data_tool, get_image_tool],
        instruction="""You are a collision detection expert for mobile robots.

INSTRUCTIONS:
1. Call get_scenario_data() to get window IDs
2. For EACH window, retrieve images:
   - get_window_image(window_id="006", image_type="camera")
   - get_window_image(window_id="006", image_type="bev_occupancy")
   - get_window_image(window_id="006", image_type="bev_height")
3. ANALYZE each image immediately after retrieval
4. Return collision assessment for ALL windows

Output schema:
{
  "windows": [
    {
      "window_id": "006",
      "collision_suspected": true | false,
      "collision_confidence": <float 0-1>,
      "collision_type": "none" | "obstacle" | "wall" | "human" | "unknown",
      "risk_level": "safe" | "warning" | "danger",
      "notes": "Description"
    }
  ]
}""",
        output_key="collision_features"
    )


# ============================================================================
# UTILITIES
# ============================================================================


def extract_json_from_text(text: str):
    """Extract JSON from text with markdown code blocks."""
    if text is None:
        return None, False

    try:
        return json.loads(text), True
    except:
        pass

    if "```json" in text and "```" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        if start > 7 and end > start:
            json_str = text[start:end].strip()
            try:
                return json.loads(json_str), True
            except:
                pass

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
    """Analyze agent events."""
    summary = {
        "agent": agent_name,
        "total_events": len(events),
        "agent_messages": 0,
        "has_final_output": False,
        "final_output_size": 0,
        "final_json": None,
    }

    latest_json = None
    latest_json_size = 0

    for event in events:
        author = getattr(event, 'author', None)
        content = getattr(event, 'content', None)

        if author == agent_name:
            summary["agent_messages"] += 1

            if content is not None and hasattr(content, 'parts'):
                for part in content.parts:
                    if hasattr(part, 'text') and part.text is not None:
                        text = part.text
                        parsed_json, is_valid = extract_json_from_text(text)
                        if is_valid and parsed_json:
                            latest_json = parsed_json
                            latest_json_size = len(text)

    if latest_json:
        summary["has_final_output"] = True
        summary["final_json"] = latest_json
        summary["final_output_size"] = latest_json_size

    return summary


# ============================================================================
# TESTS
# ============================================================================


async def test_agents():
    """Test all agents."""
    print("\n" + "=" * 90)
    print("GENERALIST SENSOR ANALYZER - TEST")
    print("=" * 90)

    agents_config = [
        ('motion', create_motion_analyzer,
         "Analyze motion for all available windows"),
        ('sensor', create_sensor_analyzer,
         "Analyze all sensor data for all available windows"),
        ('collision', create_collision_detector,
         "Analyze collisions for all available windows"),
    ]

    results = {}

    for agent_key, agent_factory, prompt in agents_config:
        print(f"\n📊 Testing {agent_key.upper()}")
        try:
            agent = agent_factory()
            runner = InMemoryRunner(agent=agent)
            events = await runner.run_debug(user_messages=prompt)
            results[agent_key] = events
            print(f"  ✓ {len(events)} events")
        except Exception as e:
            print(f"  ❌ Error: {e}")
            results[agent_key] = None

    return results


def print_summary(results: dict):
    """Print summary."""
    print("\n" + "=" * 90)
    print("SUMMARY - GENERALIST APPROACH")
    print("=" * 90)

    agent_mapping = {
        'motion': 'Motion_Analyzer',
        'sensor': 'Sensor_Analyzer',
        'collision': 'Collision_Detector',
    }

    all_passed = True

    for agent_key, agent_name in agent_mapping.items():
        events = results.get(agent_key)
        if events is None:
            print(f"\n{agent_key.upper():20} ❌ EXCEPTION")
            all_passed = False
            continue

        summary = analyze_events(agent_name, events)

        if summary["has_final_output"]:
            status = "✅ SUCCESS"
            print(f"\n{agent_key.upper():20} {status}")
            print(f"  Events: {summary['total_events']}")
            print(f"  Output size: {summary['final_output_size']} chars")
            if summary['final_json'] and 'windows' in summary['final_json']:
                num_windows = len(summary['final_json']['windows'])
                print(f"  Windows: {num_windows}")
        else:
            status = "❌ FAILED"
            print(f"\n{agent_key.upper():20} {status}")
            print(f"  Events: {summary['total_events']}")
            all_passed = False

    print("\n" + "=" * 90)
    if all_passed:
        print("✅ GENERALIST APPROACH VERIFIED")
    else:
        print("⚠️  Some agents failed")
    print("=" * 90)

    return all_passed


# ============================================================================
# MAIN
# ============================================================================


async def main():
    """Run tests."""
    results = await test_agents()
    all_passed = print_summary(results)
    return all_passed


if __name__ == "__main__":
    try:
        passed = asyncio.run(main())
        sys.exit(0 if passed else 1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
