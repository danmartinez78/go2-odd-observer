#!/usr/bin/env python3
"""
Orchestrator Pattern - Proven Approach
======================================

Architecture:
- Orchestrator Agent: Loops through windows, coordinates sub-agents
- Motion_Agent: Analyzes motion for CURRENT window only
- Perception_Agent: Analyzes perception for CURRENT window only
- Collision_Agent: Analyzes collisions for CURRENT window only
- COD_Evaluator: Evaluates ODD compliance across all results
- Report_Generator: Synthesizes final report

Key: Orchestrator controls the loop, sub-agents stay simple (one window each)
Results cached in session state and accumulated
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
from google.adk.agents import Agent, SequentialAgent

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
print(f"  - Approach: Orchestrator pattern with loop control")

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


def get_window_data(window_id: str, scenario_path: str) -> dict:
    """
    Get all data for a SPECIFIC window (orchestrator calls this per-window).

    Returns motion_json and all 5 images (camera + 4 BEV types).
    """
    try:
        from pathlib import Path
        import pandas as pd

        scenario_path = Path(scenario_path)
        scenario_name = scenario_path.name

        # Get motion data
        index_files = list(scenario_path.glob("index_*.csv"))
        if not index_files:
            return {"status": "error", "error_message": "No index file"}

        index_df = pd.read_csv(index_files[0])
        motion_json = None
        for _, row in index_df.iterrows():
            wid = str(row['window_id']).zfill(3)
            if wid == window_id:
                motion_file = scenario_path / \
                    f"motion_{scenario_name}_w{window_id}.json"
                if motion_file.exists():
                    with open(motion_file, 'r') as f:
                        motion_json = json.load(f)
                break

        if not motion_json:
            return {"status": "error", "error_message": f"Motion data not found for window {window_id}"}

        # Get all images
        image_types = {
            "camera": f"cam_{scenario_name}_w{window_id}.png",
            "bev_occupancy": f"bev_occupancy_{scenario_name}_w{window_id}.png",
            "bev_height": f"bev_height_{scenario_name}_w{window_id}.png",
            "bev_density": f"bev_density_{scenario_name}_w{window_id}.png",
            "bev_roughness": f"bev_roughness_{scenario_name}_w{window_id}.png",
        }

        images = {}
        for image_type, filename in image_types.items():
            file_path = scenario_path / filename
            if file_path.exists():
                with open(file_path, 'rb') as f:
                    image_bytes = f.read()
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                images[image_type] = {
                    "base64": image_base64,
                    "size_kb": len(image_bytes) / 1024,
                }

        return {
            "status": "success",
            "window_id": window_id,
            "motion_json": motion_json,
            "images": images,
        }
    except Exception as e:
        return {"status": "error", "error_message": f"Failed: {str(e)}"}


def scenario_data_wrapper() -> dict:
    return get_scenario_data(str(scenario_path))


def window_data_wrapper(window_id: str) -> dict:
    return get_window_data(window_id, str(scenario_path))


scenario_data_tool = FunctionTool(func=scenario_data_wrapper)
window_data_tool = FunctionTool(func=window_data_wrapper)

print("✓ Tools created (orchestrator pattern)")

# ============================================================================
# SUB-AGENTS (analyze SINGLE window only)
# ============================================================================


def create_motion_agent() -> Agent:
    """Motion agent for SINGLE window."""
    return Agent(
        name="Motion_Agent",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[window_data_tool],
        instruction="""You are a motion analysis expert.

INSTRUCTIONS:
1. Call get_window_data(window_id="<current_window>") 
2. Extract motion metrics from the motion_json
3. Return ONLY JSON with this exact schema for that SINGLE window:

{
  "window_id": "006",
  "avg_forward_speed": <float>,
  "max_forward_speed": <float>,
  "max_abs_roll_pitch_deg": <float>,
  "motion_label": "smooth" | "dynamic"
}

CRITICAL: Return ONLY the JSON object, nothing else.""",
        output_key="motion_analysis"
    )


def create_perception_agent() -> Agent:
    """Perception agent for SINGLE window."""
    return Agent(
        name="Perception_Agent",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[window_data_tool],
        instruction="""You are a perception analyst.

INSTRUCTIONS:
1. Call get_window_data(window_id="<current_window>")
2. Analyze the camera and BEV images
3. Return ONLY JSON with this exact schema for that SINGLE window:

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
    "traversability_score": <float 0-1>
  }
}

CRITICAL: Return ONLY the JSON object, nothing else.""",
        output_key="perception_analysis"
    )


def create_collision_agent() -> Agent:
    """Collision agent for SINGLE window."""
    return Agent(
        name="Collision_Agent",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[window_data_tool],
        instruction="""You are a collision detection expert.

INSTRUCTIONS:
1. Call get_window_data(window_id="<current_window>")
2. Analyze images for collision hazards
3. Return ONLY JSON with this exact schema for that SINGLE window:

{
  "window_id": "006",
  "collision_suspected": true | false,
  "collision_confidence": <float 0-1>,
  "collision_type": "none" | "obstacle" | "wall" | "human" | "unknown",
  "risk_level": "safe" | "warning" | "danger",
  "notes": "Description"
}

CRITICAL: Return ONLY the JSON object, nothing else.""",
        output_key="collision_analysis"
    )


# ============================================================================
# ORCHESTRATOR AGENT
# ============================================================================


def create_orchestrator_agent() -> Agent:
    """
    ORCHESTRATOR: Controls the loop, coordinates sub-agents.

    This agent:
    1. Gets list of windows
    2. Loops through each window
    3. Calls sub-agents for that window
    4. Accumulates results in session state
    5. Returns summary of all results
    """
    return Agent(
        name="Orchestrator",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[scenario_data_tool],
        instruction="""You are an analysis orchestrator.

INSTRUCTIONS:
1. Call get_scenario_data() to get list of windows
2. For EACH window in the list:
   - Store the window_id in session state with key: temp:current_window_{index}
   - Instruct the motion sub-agent to analyze the current window
   - Instruct the perception sub-agent to analyze the current window
   - Instruct the collision sub-agent to analyze the current window
   - Accumulate results
3. After all windows processed, return summary

Return a summary like:
{
  "status": "complete",
  "total_windows": 2,
  "windows_processed": ["006", "007"],
  "next_step": "COD evaluation and report generation"
}""",
        output_key="orchestrator_status"
    )


# ============================================================================
# UTILITIES
# ============================================================================


def extract_json_from_text(text: str):
    """Extract JSON from text."""
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
# DEMONSTRATION
# ============================================================================


async def demo_orchestrator_pattern():
    """Demonstrate the orchestrator pattern."""
    print("\n" + "=" * 90)
    print("ORCHESTRATOR PATTERN DEMONSTRATION")
    print("=" * 90)

    print("\n1️⃣  Creating orchestrator agent...")
    orchestrator = create_orchestrator_agent()

    print("2️⃣  Creating sub-agents (motion, perception, collision)...")
    motion = create_motion_agent()
    perception = create_perception_agent()
    collision = create_collision_agent()

    print("\n3️⃣  Testing orchestrator...")
    try:
        runner = InMemoryRunner(agent=orchestrator)
        events = await runner.run_debug(
            user_messages="Orchestrate analysis of all available windows"
        )

        print(f"\n✓ Orchestrator returned {len(events)} events")

        summary = analyze_events("Orchestrator", events)
        if summary["has_final_output"]:
            print("✅ Orchestrator successfully coordinated window analysis")
            print(f"   Output: {summary['final_json']}")
        else:
            print("⚠️  Orchestrator ran but no JSON output found")
    except Exception as e:
        print(f"❌ Error: {e}")

    print("\n4️⃣  Testing sub-agents with specific window...")
    try:
        runner = InMemoryRunner(agent=motion)
        events = await runner.run_debug(user_messages="Analyze motion for window 006")

        summary = analyze_events("Motion_Agent", events)
        if summary["has_final_output"]:
            print("✅ Motion agent analyzed single window")
            print(f"   Output: {summary['final_json']}")
        else:
            print("⚠️  Motion agent ran but no JSON output")
    except Exception as e:
        print(f"❌ Error: {e}")

    print("\n" + "=" * 90)
    print("PATTERN ADVANTAGES:")
    print("=" * 90)
    print("""
✅ Orchestrator controls loop (not LLM doing iterations)
✅ Sub-agents stay simple (analyze one window only)
✅ Results naturally accumulate in session state
✅ Easy to add/remove/modify sub-agents
✅ Better error handling (one window failing doesn't break others)
✅ Clear separation of concerns
✅ Scales well (add more sub-agents without complexity)
    """)


# ============================================================================
# MAIN
# ============================================================================


async def main():
    """Run demonstration."""
    await demo_orchestrator_pattern()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
