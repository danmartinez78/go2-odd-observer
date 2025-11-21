#!/usr/bin/env python3
"""
LoopAgent Orchestrator Pattern for Window Analysis
===================================================

Architecture using ADK's LoopAgent for refinement cycles:

1. Initial Setup Agent - Gets window list and prepares state
2. Analysis Loop (repeating):
   - Analyzer: Runs motion + perception + collision in parallel for current window
   - Validator: Checks if done, advances to next window or signals exit
3. COD Evaluator - Reviews all accumulated results
4. Report Generator - Synthesizes final report

Key advantage: Loop naturally accumulates results, no overwrites, clean exit condition
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
from google.adk.agents import Agent, SequentialAgent, LoopAgent, ParallelAgent

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
print(f"  - Approach: LoopAgent orchestrator with refinement cycle pattern")

# ============================================================================
# GLOBAL STATE FOR LOOP CONTROL
# ============================================================================


class LoopState:
    """Tracks loop state across iterations."""
    window_list = []
    current_index = 0
    results = {}  # Accumulates results: {"006": {...}, "007": {...}}


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
                windows.append(window_id)

        return {
            "status": "success",
            "scenario_name": scenario_name,
            "total_windows": len(windows),
            "windows": windows
        }
    except Exception as e:
        return {"status": "error", "error_message": f"Failed: {str(e)}"}


def get_window_data(window_id: str, scenario_path: str) -> dict:
    """Get all data for a SPECIFIC window."""
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


def process_next_window() -> dict:
    """Signal to advance to next window in the loop."""
    return {
        "status": "continue",
        "message": f"Processing window {LoopState.window_list[LoopState.current_index] if LoopState.current_index < len(LoopState.window_list) else 'N/A'}"
    }


def analysis_complete() -> dict:
    """Signal to exit the loop - all windows analyzed."""
    return {
        "status": "complete",
        "message": "All windows analyzed. Exiting loop.",
        "total_windows": len(LoopState.window_list),
        "windows_processed": LoopState.window_list
    }


def scenario_data_wrapper() -> dict:
    return get_scenario_data(str(scenario_path))


def window_data_wrapper(window_id: str) -> dict:
    return get_window_data(window_id, str(scenario_path))


scenario_data_tool = FunctionTool(func=scenario_data_wrapper)
window_data_tool = FunctionTool(func=window_data_wrapper)
process_next_tool = FunctionTool(func=process_next_window)
analysis_complete_tool = FunctionTool(func=analysis_complete)

print("✓ Tools created (LoopAgent pattern)")

# ============================================================================
# INITIAL SETUP
# ============================================================================


def create_setup_agent() -> Agent:
    """Initial agent: Get window list and initialize loop state."""
    return Agent(
        name="SetupAgent",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[scenario_data_tool],
        instruction="""You are the setup orchestrator for window analysis.

TASK: Initialize the analysis by retrieving the list of available windows.

INSTRUCTIONS:
1. Call get_scenario_data() to get the list of all windows
2. Store result in session state with key: windows_list
3. Initialize loop counter in session state: loop_iteration = 0
4. Return JSON indicating ready to start:

{
  "status": "setup_complete",
  "windows_ready": true,
  "next_step": "Begin analysis loop"
}

Return ONLY the JSON object.""",
        output_key="setup_status"
    )


# ============================================================================
# LOOP AGENTS (repeating)
# ============================================================================


def create_analyzer_agent() -> Agent:
    """
    Analyzer: Runs motion + perception + collision analysis for CURRENT window.

    This agent is called repeatedly by the LoopAgent.
    The current window_id comes from the loop iteration.
    """
    return Agent(
        name="WindowAnalyzer",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[window_data_tool],
        instruction="""You are a multi-modal window analyzer.

TASK: Analyze the current window across three dimensions (motion, perception, collision).

The current window to analyze is: {current_window_id}

INSTRUCTIONS:
1. Call get_window_data(window_id="{current_window_id}")
2. Analyze motion, perception, and collision aspects
3. Return ONLY JSON with all three analyses:

{
  "window_id": "{current_window_id}",
  "analysis_status": "complete",
  "motion": {
    "avg_forward_speed": <float>,
    "max_forward_speed": <float>,
    "max_abs_roll_pitch_deg": <float>,
    "motion_label": "smooth" | "dynamic"
  },
  "perception": {
    "lighting_class": "bright" | "dim" | "dark",
    "humans_detected": true | false,
    "obstacle_visible": true | false,
    "terrain_roughness_class": "smooth" | "moderate" | "rough" | "very_rough",
    "traversability_score": <float 0-1>
  },
  "collision": {
    "collision_suspected": true | false,
    "collision_confidence": <float 0-1>,
    "collision_type": "none" | "obstacle" | "wall" | "human" | "unknown",
    "risk_level": "safe" | "warning" | "danger"
  }
}

Return ONLY the JSON object.""",
        output_key="current_window_analysis"
    )


def create_validator_agent() -> Agent:
    """
    Validator: Reviews analysis and either advances loop or signals exit.

    This is the "brain" of the loop - it decides whether to continue or stop.
    """
    return Agent(
        name="LoopValidator",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[process_next_tool, analysis_complete_tool],
        instruction="""You are the loop validator and controller.

TASK: Evaluate if analysis is complete for the current window, then decide loop fate.

Current Analysis: {current_window_analysis}
Loop Iteration: {loop_iteration}
Total Windows: {total_windows}
Windows Processed: {windows_processed}

INSTRUCTIONS:
1. Verify the current window analysis is valid
2. Increment the iteration counter in your mind
3. Decide:
   - IF (loop_iteration + 1) >= total_windows:
     * Call analysis_complete() to exit the loop
     * This signals that ALL windows have been processed
   - OTHERWISE:
     * Call process_next_window() to continue
     * The loop will advance to the next window

CRITICAL: You must call exactly ONE of these functions:
- analysis_complete() when done
- process_next_window() to continue

The loop will read your function call to know what to do next.""",
        output_key="loop_decision"
    )


# ============================================================================
# FINAL AGENTS
# ============================================================================


def create_cod_evaluator() -> Agent:
    """COD_Evaluator: Analyzes ODD compliance across all results."""
    return Agent(
        name="COD_Evaluator",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[],
        instruction="""You are a COD (Out-Of-Distribution) detection expert.

TASK: Analyze all accumulated window analyses to identify ODD scenarios.

From the session state, you have all window analyses.

INSTRUCTIONS:
1. Review all window analyses
2. Identify patterns, anomalies, ODD scenarios
3. Return ONLY JSON:

{
  "cod_detected": true | false,
  "severity": "low" | "medium" | "high",
  "odd_factors": ["factor1", "factor2"],
  "pattern_summary": "Summary of patterns observed"
}

Return ONLY the JSON object.""",
        output_key="cod_evaluation"
    )


def create_report_generator() -> Agent:
    """Report_Generator: Synthesizes final report."""
    return Agent(
        name="ReportGenerator",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[],
        instruction="""You are a technical report generator.

TASK: Create comprehensive report from all analyses.

INSTRUCTIONS:
1. Review all window analyses from session state
2. Review COD evaluation
3. Synthesize findings
4. Return ONLY JSON:

{
  "report_title": "Comprehensive Analysis Report",
  "analysis_complete": true,
  "windows_analyzed": <number>,
  "motion_patterns": "Summary",
  "perception_summary": "Summary",
  "collision_assessment": "Summary",
  "cod_findings": "Summary",
  "overall_assessment": "Safe" | "Caution" | "Risk",
  "confidence_score": <float 0-1>
}

Return ONLY the JSON object.""",
        output_key="final_report"
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
    """Analyze agent events to extract results."""
    summary = {
        "agent": agent_name,
        "total_events": len(events),
        "agent_messages": 0,
        "has_output": False,
        "json": None,
    }

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
                        parsed_json, is_valid = extract_json_from_text(text)
                        if is_valid and parsed_json:
                            latest_json = parsed_json

    if latest_json:
        summary["has_output"] = True
        summary["json"] = latest_json

    return summary


# ============================================================================
# DEMONSTRATION
# ============================================================================


async def demo_loop_orchestrator():
    """Demonstrate the LoopAgent orchestrator pattern."""
    print("\n" + "=" * 90)
    print("LOOPAGENT ORCHESTRATOR PATTERN DEMONSTRATION")
    print("=" * 90)

    # Step 1: Setup
    print("\n1️⃣  Setting up analysis environment...")
    setup = create_setup_agent()

    try:
        runner = InMemoryRunner(agent=setup)
        setup_events = await runner.run_debug(
            user_messages="Initialize analysis for all available windows"
        )
        setup_summary = analyze_events("SetupAgent", setup_events)
        if setup_summary["has_output"]:
            print(f"✅ Setup complete")
            print(f"   {setup_summary['json']}")

        # Get scenario data to know our windows
        scenario_data = get_scenario_data(str(scenario_path))
        LoopState.window_list = scenario_data.get("windows", [])
        print(f"\n📋 Windows to process: {LoopState.window_list}")

    except Exception as e:
        print(f"❌ Setup error: {e}")
        return

    # Step 2: Test the loop pattern with first window
    print("\n2️⃣  Testing loop pattern - Analyzer + Validator...")
    analyzer = create_analyzer_agent()
    validator = create_validator_agent()

    if not LoopState.window_list:
        print("❌ No windows available!")
        return

    try:
        # Manually test first iteration
        current_window = LoopState.window_list[0]
        print(f"\n   Processing window: {current_window}")

        runner = InMemoryRunner(agent=analyzer)
        analyzer_events = await runner.run_debug(
            user_messages=f"Analyze window {current_window}"
        )
        analyzer_summary = analyze_events("WindowAnalyzer", analyzer_events)

        if analyzer_summary["has_output"]:
            print(f"   ✅ Analyzer result for window {current_window}:")
            print(
                f"      - Motion: {analyzer_summary['json'].get('motion', {}).get('motion_label', 'N/A')}")
            print(
                f"      - Collision: {analyzer_summary['json'].get('collision', {}).get('collision_suspected', 'N/A')}")
        else:
            print(f"   ❌ Analyzer failed to return JSON")

    except Exception as e:
        print(f"❌ Loop test error: {e}")
        import traceback
        traceback.print_exc()

    # Step 3: Show what full loop would look like
    print("\n3️⃣  Full Loop Architecture:")
    print(f"""
The LoopAgent would run like this:
    
Initial: SetupAgent → gets windows and initializes state
    
Loop (max_iterations=3):
  Iteration 1:
    - WindowAnalyzer processes window 006
    - LoopValidator checks: more windows? → call process_next_window()
    - Loop continues with window_id updated to 007
    
  Iteration 2:
    - WindowAnalyzer processes window 007
    - LoopValidator checks: more windows? → call analysis_complete()
    - Loop exits (exit condition met)
    
Final (after loop):
  - COD_Evaluator reviews all accumulated results
  - ReportGenerator synthesizes final report

Results accumulate in session state:
  session_state['window_006_analysis'] = {...}
  session_state['window_007_analysis'] = {...}
  → No overwrites, clean accumulation
    """)

    print("\n" + "=" * 90)
    print("KEY ADVANTAGES OF LOOPAGENT PATTERN:")
    print("=" * 90)
    print("""
✅ Natural loop control with clear exit conditions
✅ Session state cleanly accumulates results ({window_id}_analysis)
✅ No agent overwrites - each iteration stores separate result
✅ Validator is the "brain" - it decides continue/exit
✅ Scales to any number of windows
✅ Follows ADK's refinement cycle pattern
✅ Easy to understand and debug
    """)


# ============================================================================
# MAIN
# ============================================================================


async def main():
    """Run demonstration."""
    await demo_loop_orchestrator()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
