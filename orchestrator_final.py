#!/usr/bin/env python3
"""
FINAL PRODUCTION READY: LoopAgent Orchestrator for Notebook
===========================================================

This module contains the complete agents and orchestration for the notebook.
Simply import and run!

Architecture:
- SetupAgent: Initialize windows list
- LoopAgent with Analyzer + Validator: Process windows iteratively
- COD_Evaluator: Evaluate ODD across all results
- ReportGenerator: Synthesize final report

Key: LoopAgent naturally handles iteration without overwrites
"""

import base64
import asyncio
import json
from pathlib import Path
from dotenv import load_dotenv
import os

from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool
from google.adk.models.google_llm import Gemini
from google.adk.agents import Agent, SequentialAgent, LoopAgent, ParallelAgent

# ============================================================================
# CONFIG
# ============================================================================

load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
GEMINI_MODEL = "gemini-2.0-flash-lite"

PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "runs"
scenario_path = DATA_DIR / "sim_run_test"

# ============================================================================
# TOOLS
# ============================================================================


def get_scenario_data_impl() -> dict:
    """Get available windows."""
    try:
        import pandas as pd

        if not scenario_path.exists():
            return {"status": "error", "error_message": f"Path not found"}

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
            "total_windows": len(windows),
            "windows": windows
        }
    except Exception as e:
        return {"status": "error", "error_message": f"Failed: {str(e)}"}


def get_window_data_impl(window_id: str) -> dict:
    """Get all data for one window."""
    try:
        import pandas as pd

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
            return {"status": "error", "error_message": f"Motion data not found"}

        # Get all images as base64
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
                images[image_type] = {
                    "base64": base64.b64encode(image_bytes).decode('utf-8'),
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


def exit_loop_impl():
    """Signal to exit the analysis loop."""
    return {"status": "approved", "message": "Analysis complete"}


# Wrap in tools
get_scenario_data_tool = FunctionTool(func=get_scenario_data_impl)
get_window_data_tool = FunctionTool(func=get_window_data_impl)
exit_loop_tool = FunctionTool(func=exit_loop_impl)

# ============================================================================
# AGENTS
# ============================================================================


def create_setup_agent() -> Agent:
    return Agent(
        name="SetupAgent",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[get_scenario_data_tool],
        instruction="""Initialize the analysis pipeline.

TASK: Get the list of windows to analyze.

INSTRUCTIONS:
1. Call get_scenario_data to retrieve windows
2. Store in session: windows_list and loop_index=0
3. Return:
{
  "status": "ready",
  "windows_count": <number>,
  "message": "Pipeline initialized"
}""",
        output_key="setup_status"
    )


def create_analyzer_agent() -> Agent:
    return Agent(
        name="WindowAnalyzer",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[get_window_data_tool],
        instruction="""Analyze the current window comprehensively.

Current Window: {current_window}
Loop Index: {loop_index}

TASK: Analyze motion, perception, and collision for THIS window.

INSTRUCTIONS:
1. Call get_window_data(window_id="{current_window}")
2. Extract and analyze all three dimensions
3. Store in session: temp:analysis_{current_window}
4. Return ONLY JSON:

{
  "window_id": "{current_window}",
  "motion": {
    "speed_avg": <float>,
    "speed_max": <float>,
    "stability": "stable" | "unstable",
    "motion_label": "smooth" | "dynamic"
  },
  "perception": {
    "lighting": "bright" | "dim" | "dark",
    "humans": true | false,
    "obstacles": true | false,
    "terrain_roughness": "smooth" | "moderate" | "rough",
    "traversability": <float 0-1>
  },
  "collision": {
    "suspected": true | false,
    "confidence": <float 0-1>,
    "risk": "safe" | "warning" | "danger"
  }
}""",
        output_key="window_analysis"
    )


def create_validator_agent() -> Agent:
    return Agent(
        name="LoopValidator",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[exit_loop_tool],
        instruction="""Control loop iteration and exit.

Current Window: {current_window}
Loop Index: {loop_index}
Max Windows: {max_windows}
Analysis: {window_analysis}

TASK: Validate analysis and decide loop continuation.

INSTRUCTIONS:
1. Verify window analysis is complete
2. Check: loop_index >= (max_windows - 1)?
3. Decision:
   - IF YES: Call exit_loop() and ONLY that
   - IF NO: Return JSON with "CONTINUE"
4. Return:

{
  "validation": "complete",
  "decision": "CONTINUE" | "EXIT",
  "index": {loop_index},
  "total": {max_windows}
}

CRITICAL: Call exit_loop() only when loop_index >= (max_windows - 1)""",
        output_key="loop_decision"
    )


def create_cod_evaluator() -> Agent:
    return Agent(
        name="COD_Evaluator",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[],
        instruction="""Evaluate ODD across all window analyses.

TASK: Review accumulated analyses and identify ODD patterns.

INSTRUCTIONS:
1. Access all analysis_* results from session state
2. Identify anomalies and ODD factors across windows
3. Return:

{
  "cod_detected": true | false,
  "severity": "low" | "medium" | "high",
  "odd_factors": [],
  "summary": "ODD assessment summary"
}""",
        output_key="cod_eval"
    )


def create_report_generator() -> Agent:
    return Agent(
        name="ReportGenerator",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[],
        instruction="""Generate final comprehensive report.

TASK: Synthesize all analyses into final report.

INSTRUCTIONS:
1. Review all accumulated analyses and COD evaluation
2. Synthesize findings
3. Return:

{
  "title": "Analysis Report",
  "windows": <count>,
  "motion": "Summary",
  "perception": "Summary",
  "collision": "Summary",
  "odd": "Summary",
  "status": "SAFE" | "CAUTION" | "ALERT",
  "confidence": <float 0-1>
}""",
        output_key="final_report"
    )


# ============================================================================
# ORCHESTRATION
# ============================================================================


def create_orchestrator() -> SequentialAgent:
    """Create the complete analysis pipeline."""

    # Agents
    setup = create_setup_agent()
    analyzer = create_analyzer_agent()
    validator = create_validator_agent()
    cod = create_cod_evaluator()
    report = create_report_generator()

    # Loop: Analyzer + Validator repeated
    analysis_loop = LoopAgent(
        name="AnalysisLoop",
        sub_agents=[analyzer, validator],
        max_iterations=10  # Enough for any scenario
    )

    # Root: Setup → Loop → COD → Report
    root = SequentialAgent(
        name="AnalysisPipeline",
        sub_agents=[setup, analysis_loop, cod, report]
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


def get_agent_output(agent_name: str, events: list):
    """Extract JSON output from agent events."""
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
# EXECUTION
# ============================================================================


async def run_analysis():
    """Execute the complete analysis pipeline."""
    print("\n" + "=" * 90)
    print("LOOPAGENT ANALYSIS PIPELINE")
    print("=" * 90)

    orchestrator = create_orchestrator()
    runner = InMemoryRunner(agent=orchestrator)

    try:
        print("\n▶️  Starting analysis...")
        events = await runner.run_debug("Analyze all windows")

        print("\n" + "=" * 90)
        print("RESULTS")
        print("=" * 90)

        # Extract key results
        setup = get_agent_output("SetupAgent", events)
        if setup:
            print(f"\n✅ Setup: {setup}")

        cod = get_agent_output("COD_Evaluator", events)
        if cod:
            print(f"\n✅ COD: {cod}")

        report = get_agent_output("ReportGenerator", events)
        if report:
            print(f"\n✅ Report: {json.dumps(report, indent=2)}")

        return {"events": events, "setup": setup, "cod": cod, "report": report}

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


# ============================================================================
# MAIN
# ============================================================================


if __name__ == "__main__":
    try:
        result = asyncio.run(run_analysis())
        print("\n✅ Analysis complete!")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
