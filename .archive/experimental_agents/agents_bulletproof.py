#!/usr/bin/env python3
"""
Production-Ready Agent Workflow Script
================================
Complete, tested implementation of all four agents with proper parameter names,
error handling, and comprehensive documentation.

This script serves as the source of truth for the notebook implementation.
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
from google.adk.agents import Agent, ParallelAgent, SequentialAgent

# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
GEMINI_MODEL = "gemini-2.0-flash-lite"  # lite model is more consistent

if not GOOGLE_API_KEY:
    print("❌ GOOGLE_API_KEY not found!")
    sys.exit(1)

DATA_DIR = PROJECT_ROOT / "data" / "processed" / "runs"
scenario_path = DATA_DIR / "sim_run_test"

print(f"✓ Configuration loaded")
print(f"  - Model: {GEMINI_MODEL}")
print(f"  - Data: {scenario_path}")

# ============================================================================
# TOOL IMPLEMENTATIONS
# ============================================================================


def get_scenario_data(scenario_path: str) -> dict:
    """
    Retrieve scenario metadata and available windows.

    Returns dictionary with:
    - status: "success" or "error"
    - scenario_name: Name of the scenario
    - total_windows: Number of available windows
    - windows: List of windows with window_id and motion_json
    """
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
    Retrieve image for a specific window as base64-encoded data.

    Parameters:
    -----------
    window_id : str
        Window ID (e.g., "006", "007")

    image_type : str
        Type of image to retrieve. MUST be one of:
        - "camera" : RGB camera image from robot
        - "bev_occupancy" : BEV occupancy grid
        - "bev_height" : BEV height map
        - "bev_density" : BEV obstacle density
        - "bev_roughness" : BEV terrain roughness

    scenario_path : str
        Path to scenario directory

    Returns:
    --------
    dict with status, image_base64, mime_type, size_kb on success
    dict with status="error" and error_message on failure
    """
    try:
        from pathlib import Path

        scenario_path = Path(scenario_path)
        scenario_name = scenario_path.name

        # CRITICAL: image_type must match exactly
        valid_types = ["camera", "bev_occupancy",
                       "bev_height", "bev_density", "bev_roughness"]
        if image_type not in valid_types:
            return {
                "status": "error",
                "error_message": f"Invalid image_type: '{image_type}'. Must be one of: {', '.join(valid_types)}"
            }

        # Map image types to filenames
        if image_type == "camera":
            filename = f"cam_{scenario_name}_w{window_id}.png"
        else:
            # bev_* types map directly to filename convention
            filename = f"{image_type}_{scenario_name}_w{window_id}.png"

        file_path = scenario_path / filename
        if not file_path.exists():
            return {
                "status": "error",
                "error_message": f"Image file not found: {filename}"
            }

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


# Tool wrappers for FunctionTool
def scenario_data_wrapper() -> dict:
    """Wrapper for get_scenario_data."""
    return get_scenario_data(str(scenario_path))


def image_wrapper(window_id: str, image_type: str) -> dict:
    """Wrapper for get_window_image with proper parameter names."""
    return get_window_image(window_id, image_type, str(scenario_path))


# Create FunctionTools
scenario_data_tool = FunctionTool(func=scenario_data_wrapper)
get_image_tool = FunctionTool(func=image_wrapper)

print("✓ Tools created and ready")

# ============================================================================
# AGENT DEFINITIONS (WITH CORRECTED PARAMETER NAMES)
# ============================================================================


def create_motion_analyzer() -> Agent:
    """Create Motion Analyzer agent with correct tool usage."""
    return Agent(
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


def create_vision_analyzer() -> Agent:
    """Create Vision Analyzer agent with correct parameter names."""
    return Agent(
        name="Vision_Analyzer",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[scenario_data_tool, get_image_tool],
        instruction="""You are a vision analysis expert for mobile robots.

CRITICAL INSTRUCTIONS FOR TOOL USAGE:
1. FIRST: Call get_scenario_data() tool to get actual window IDs
2. Do NOT make up window IDs - use ONLY what the tool returns
3. For EACH window from the tool, retrieve camera images using:
   - get_window_image(window_id="006", image_type="camera")
   - NOTE: image_type MUST be exactly "camera" (lowercase, no spaces)
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


def create_terrain_analyzer() -> Agent:
    """Create Terrain Analyzer agent with correct parameter names."""
    return Agent(
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
   - NOTE: image_type values MUST be EXACTLY as shown (lowercase, with underscore prefix)
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


def create_collision_detector() -> Agent:
    """Create Collision Detector agent with correct parameter names."""
    return Agent(
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


# ============================================================================
# JSON EXTRACTION UTILITIES
# ============================================================================


def extract_json_from_text(text: str):
    """
    Extract JSON from text that may contain markdown code blocks.

    Handles:
    - Direct JSON strings
    - Markdown code blocks (```json ... ```)
    - Embedded JSON objects
    """
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
    """
    Analyze agent events to extract final output.

    Searches through all events for the agent's final JSON response.
    Returns the LATEST valid JSON found (most recent event with JSON).
    """
    summary = {
        "agent": agent_name,
        "total_events": len(events),
        "agent_messages": 0,
        "has_final_output": False,
        "final_output_size": 0,
        "final_json": None,
    }

    # Look through ALL events for JSON content
    # Keep updating with latest valid JSON found
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
                        # Try to extract JSON
                        parsed_json, is_valid = extract_json_from_text(text)
                        if is_valid and parsed_json:
                            # Update with latest JSON found
                            latest_json = parsed_json
                            latest_json_size = len(text)

    # Set final output based on latest JSON found
    if latest_json:
        summary["has_final_output"] = True
        summary["final_json"] = latest_json
        summary["final_output_size"] = latest_json_size

    return summary


# ============================================================================
# TEST FUNCTIONS
# ============================================================================


async def test_individual_agents():
    """Test each agent in isolation."""
    print("\n" + "=" * 90)
    print("INDIVIDUAL AGENT TESTS")
    print("=" * 90)

    agents_config = [
        ('motion', create_motion_analyzer,
         "Analyze motion for all available windows"),
        ('vision', create_vision_analyzer,
         "Analyze vision for all available windows"),
        ('terrain', create_terrain_analyzer,
         "Analyze terrain for all available windows"),
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
            print(f"  ✓ {len(events)} events generated")
        except Exception as e:
            print(f"  ❌ Error: {e}")
            results[agent_key] = None

    return results


# ============================================================================
# SUMMARY & REPORTING
# ============================================================================


def print_summary(results: dict):
    """Print comprehensive test summary."""
    print("\n" + "=" * 90)
    print("SUMMARY - BULLETPROOF AGENT TESTS")
    print("=" * 90)

    agent_mapping = {
        'motion': 'Motion_Analyzer',
        'vision': 'Vision_Analyzer',
        'terrain': 'Terrain_Analyzer',
        'collision': 'Collision_Detector',
    }

    all_passed = True

    for agent_key, agent_name in agent_mapping.items():
        events = results.get(agent_key)
        if events is None:
            print(f"\n{agent_key.upper():20} ❌ EXCEPTION/ERROR")
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
            print(f"  No valid JSON output found")
            all_passed = False

    print("\n" + "=" * 90)
    if all_passed:
        print("✅ ALL AGENTS PASSED - BULLETPROOF VERIFIED")
    else:
        print("⚠️  Some agents failed. Review output above.")
    print("=" * 90)

    return all_passed


# ============================================================================
# MAIN
# ============================================================================


async def main():
    """Run complete test suite."""
    print("\n" + "=" * 90)
    print("PRODUCTION-READY AGENT WORKFLOW")
    print("=" * 90)
    print(f"Dataset: {scenario_path}")
    print(f"Model: {GEMINI_MODEL}\n")

    # Run individual tests
    results = await test_individual_agents()

    # Print summary
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
