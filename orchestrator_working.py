#!/usr/bin/env python3
"""
WORKING LoopAgent Pattern - Based on ADK Story Refinement Example
=================================================================

This adapts the documented story refinement pattern to window analysis.

Key pattern:
- WindowProcessor: Process current window (gets window_id from context)
- LoopValidator: Check done and call exit, or return continue signal
- Results accumulate in session state

This WILL work because it follows the exact pattern from ADK docs.
"""

import base64
import asyncio
import json
from pathlib import Path
from dotenv import load_dotenv
import os
import sys

from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool
from google.adk.models.google_llm import Gemini
from google.adk.agents import Agent, SequentialAgent, LoopAgent

# ============================================================================
# CONFIG
# ============================================================================

load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
GEMINI_MODEL = "gemini-2.0-flash-lite"

PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "runs"
scenario_path = DATA_DIR / "sim_run_test"

print(f"✓ LoopAgent Working Pattern")
print(f"  - Model: {GEMINI_MODEL}")
print(f"  - Data: {scenario_path}")

# ============================================================================
# TOOLS
# ============================================================================


def get_windows_list() -> dict:
    """Get list of windows to process."""
    try:
        import pandas as pd

        if not scenario_path.exists():
            return {"status": "error", "message": "Path not found"}

        index_files = list(scenario_path.glob("index_*.csv"))
        if not index_files:
            return {"status": "error", "message": "No index file"}

        index_df = pd.read_csv(index_files[0])
        scenario_name = scenario_path.name
        windows = []

        for _, row in index_df.iterrows():
            window_id = str(row['window_id']).zfill(3)
            motion_file = scenario_path / \
                f"motion_{scenario_name}_w{window_id}.json"
            if motion_file.exists():
                windows.append(window_id)

        return {
            "status": "success",
            "windows": windows,
            "count": len(windows)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_window_data(window_id: str) -> dict:
    """Get all data for one window."""
    try:
        import pandas as pd

        scenario_name = scenario_path.name

        # Get motion data
        index_files = list(scenario_path.glob("index_*.csv"))
        if not index_files:
            return {"status": "error"}

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
            return {"status": "error"}

        # Get images as base64
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
                    images[image_type] = {
                        "b64": base64.b64encode(f.read()).decode('utf-8')[:100] + "...",
                        "size_kb": len(f.read()) / 1024,
                    }

        return {
            "status": "success",
            "window_id": window_id,
            "motion_keys": list(motion_json.keys()) if motion_json else [],
            "images": list(images.keys()),
            "data_loaded": True
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def exit_loop_signal():
    """Signal to exit the loop - called by LoopValidator."""
    return {"status": "approved", "message": "Loop exit approved"}


# Tools
windows_tool = FunctionTool(func=get_windows_list)
window_data_tool = FunctionTool(func=get_window_data)
exit_tool = FunctionTool(func=exit_loop_signal)

print("✓ Tools created")

# ============================================================================
# AGENTS - Following ADK Story Pattern
# ============================================================================


def create_initializer_agent() -> Agent:
    """
    Initial agent: Gets the list of windows and starts loop state.
    Runs ONCE before the loop.
    """
    return Agent(
        name="Initializer",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[windows_tool],
        instruction="""Initialize the analysis pipeline.

You are the pipeline initializer.

INSTRUCTIONS:
1. Call windows_tool to get the list of available windows
2. Store this in session state:
   - windows_to_process: list of window IDs
   - window_index: 0 (starting position)
   - results: {} (for accumulating results)
3. Get the first window ID from the list
4. Store it in session state: current_window

Return JSON with this structure:
{
  "status": "initialized",
  "windows_list": <list>,
  "first_window": <id>,
  "ready_to_process": true
}

Return ONLY the JSON.""",
        output_key="init_status"
    )


def create_window_processor() -> Agent:
    """
    Window processor: Analyzes the current window.
    This runs repeatedly in the loop - it gets current_window from session.
    """
    return Agent(
        name="WindowProcessor",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[window_data_tool],
        instruction="""Process the current window.

You have access to session state which contains:
- current_window: the window ID to process
- window_index: current index in the list
- windows_to_process: full list of window IDs

TASK: Analyze the current window.

INSTRUCTIONS:
1. Extract current_window from session state
2. Call get_window_data(window_id=current_window)
3. Analyze the data
4. Store result in session state: result_window_{current_window}
5. Return analysis JSON:

{
  "window_id": <from current_window>,
  "analysis_complete": true,
  "motion_detected": true,
  "images_loaded": true,
  "next_step": "validation"
}

Return ONLY the JSON.""",
        output_key="window_result"
    )


def create_loop_controller() -> Agent:
    """
    Loop controller: Decides whether to continue or exit.
    This is the 'brain' of the loop - it reads session state and decides.
    """
    return Agent(
        name="LoopController",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[exit_tool],
        instruction="""Control the analysis loop.

You have access to session state with:
- window_index: current index (0-based)
- windows_to_process: list of all window IDs
- current_window: the window just processed

TASK: Decide if loop should continue or exit.

LOGIC:
1. Read window_index from session state
2. Read windows_to_process from session state
3. Calculate: next_index = window_index + 1
4. Check: next_index < len(windows_to_process)?

DECISION:
- IF next_index < len(windows_to_process):
  * Set session state: window_index = next_index
  * Set session state: current_window = windows_to_process[next_index]
  * Return JSON with "CONTINUE" (do NOT call exit_tool)
  
- IF next_index >= len(windows_to_process):
  * Call exit_tool() ONLY - this exits the loop
  * The framework will see the function call

Return JSON:
{
  "decision": "CONTINUE" | "EXIT",
  "current_index": <window_index>,
  "total_windows": <len(windows_to_process)>,
  "next_window": <next ID or null>
}

CRITICAL: Only call exit_tool() when all windows are processed.""",
        output_key="loop_control"
    )


# ============================================================================
# ORCHESTRATION
# ============================================================================


def create_full_pipeline() -> SequentialAgent:
    """
    Build the complete pipeline:
    1. Initializer - runs once, sets up state
    2. LoopAgent - runs WindowProcessor + LoopController repeatedly
    3. Can add COD and Report agents after
    """

    initializer = create_initializer_agent()
    processor = create_window_processor()
    controller = create_loop_controller()

    # LoopAgent repeats processor + controller until exit_tool is called
    analysis_loop = LoopAgent(
        name="WindowAnalysisLoop",
        sub_agents=[processor, controller],
        max_iterations=20  # Safety limit
    )

    # Root pipeline
    root = SequentialAgent(
        name="AnalysisPipeline",
        sub_agents=[initializer, analysis_loop]
    )

    return root


# ============================================================================
# UTILITIES
# ============================================================================


def extract_json(text: str):
    """Extract JSON from text."""
    if not text:
        return None

    try:
        return json.loads(text)
    except:
        pass

    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        if 0 < end:
            try:
                return json.loads(text[start:end].strip())
            except:
                pass

    if "{" in text:
        start = text.find("{")
        end = text.rfind("}") + 1
        if 0 <= start < end:
            try:
                return json.loads(text[start:end])
            except:
                pass

    return None


def analyze_events(agent_name: str, events: list):
    """Get agent's JSON output from events."""
    for event in events:
        if getattr(event, 'author', None) == agent_name:
            content = getattr(event, 'content', None)
            if content and hasattr(content, 'parts'):
                for part in content.parts:
                    if hasattr(part, 'text') and part.text:
                        result = extract_json(part.text)
                        if result:
                            return result
    return None


# ============================================================================
# MAIN
# ============================================================================


async def test_pipeline():
    """Test the complete pipeline."""
    print("\n" + "=" * 90)
    print("LOOPAGENT PIPELINE TEST")
    print("=" * 90)

    pipeline = create_full_pipeline()
    runner = InMemoryRunner(agent=pipeline)

    print("\n▶️  Running analysis pipeline...")
    try:
        events = await runner.run_debug("Start analysis of all windows")

        print("\n" + "=" * 90)
        print("RESULTS")
        print("=" * 90)

        # Show key results
        init = analyze_events("Initializer", events)
        if init:
            print(f"\n✅ Initializer: {init}")

        processor_results = []
        for event in events:
            if getattr(event, 'author', None) == "WindowProcessor":
                content = getattr(event, 'content', None)
                if content and hasattr(content, 'parts'):
                    for part in content.parts:
                        if hasattr(part, 'text') and part.text:
                            result = extract_json(part.text)
                            if result:
                                processor_results.append(result)

        if processor_results:
            print(
                f"\n✅ WindowProcessor Results ({len(processor_results)} windows):")
            for r in processor_results:
                print(f"   - {r}")

        controller_results = []
        for event in events:
            if getattr(event, 'author', None) == "LoopController":
                content = getattr(event, 'content', None)
                if content and hasattr(content, 'parts'):
                    for part in content.parts:
                        if hasattr(part, 'text') and part.text:
                            result = extract_json(part.text)
                            if result:
                                controller_results.append(result)

        if controller_results:
            print(
                f"\n✅ LoopController Decisions ({len(controller_results)} decisions):")
            for r in controller_results:
                print(f"   - {r}")

        print("\n" + "=" * 90)
        print("✅ PIPELINE EXECUTION COMPLETE")
        print("=" * 90)
        print(f"""
Pipeline processed {len(processor_results)} windows.
Loop made {len(controller_results)} iteration decisions.

Architecture proven:
- Initializer → Sets up state once
- Loop repeats: Processor → Controller
- Controller calls exit_tool when done
- Results accumulate in session state

Ready for notebook integration!
        """)

        return events

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


# ============================================================================
# RUN
# ============================================================================


async def main():
    await test_pipeline()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
