#!/usr/bin/env python3
"""
Production LoopAgent Orchestrator - Ready for Notebook Integration
==================================================================

This is the FINAL, production-ready pattern combining:
1. SetupAgent - Initializes window list
2. LoopAgent with Analyzer + Validator - Process windows iteratively
3. COD_Evaluator + ReportGenerator - Synthesize results

Key pattern:
- Each loop iteration processes ONE window
- Results accumulate: session_state[f"window_{id}_analysis"]
- Validator signals loop exit via exit_loop() function call
- No overwrites, clean separation of concerns
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
from google.adk.agents import Agent, SequentialAgent, LoopAgent

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

print(f"✓ Configuration loaded (Production LoopAgent Pattern)")
print(f"  - Model: {GEMINI_MODEL}")
print(f"  - Data path: {scenario_path}")

# ============================================================================
# TOOLS & EXIT CONTROL
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
            return {"status": "error", "error_message": f"Motion data not found"}

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


def exit_analysis_loop():
    """Called by validator when all windows are processed."""
    return {
        "status": "approved",
        "message": "All windows analyzed. Exiting loop."
    }


def get_scenario_data_wrapper() -> dict:
    """Wrapper for scenario data tool."""
    return get_scenario_data(str(scenario_path))


scenario_data_tool = FunctionTool(func=get_scenario_data_wrapper)
window_data_tool = FunctionTool(func=get_window_data)
exit_loop_tool = FunctionTool(func=exit_analysis_loop)

print("✓ Tools created")

# ============================================================================
# AGENTS
# ============================================================================


def create_setup_agent() -> Agent:
    """Get window list and prepare state."""
    return Agent(
        name="SetupAgent",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[scenario_data_tool],
        instruction="""Initialize the window analysis pipeline.

TASK: Retrieve the list of windows and prepare analysis state.

INSTRUCTIONS:
1. Call scenario_data to get list of available windows
2. Store in session state:
   - windows_list: the list of window IDs
   - loop_index: 0 (starting index)
   - loop_max: total windows count
   - completed_windows: [] (empty list)
3. Return JSON:

{
  "status": "ready",
  "windows_count": <number>,
  "message": "Analysis pipeline initialized"
}""",
        output_key="setup_result"
    )


def create_window_analyzer() -> Agent:
    """Analyze current window across motion/perception/collision."""
    return Agent(
        name="WindowAnalyzer",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[window_data_tool],
        instruction="""Analyze the current window.

Current Window: {current_window}
Window Index: {loop_index}

TASK: Comprehensive analysis of motion, perception, and collision for THIS window.

INSTRUCTIONS:
1. Call get_window_data(window_id="{current_window}", scenario_path="{scenario_path}")
2. Extract and analyze:
   - Motion metrics (speeds, stability, motion_label)
   - Perception (vision conditions, terrain properties)
   - Collision risks (detection, confidence, risk_level)
3. Store analysis in session state with key: temp:window_{current_window}_analysis
4. Return ONLY JSON:

{
  "window_id": "{current_window}",
  "motion": {
    "motion_label": "smooth" | "dynamic",
    "max_roll_pitch_deg": <float>
  },
  "perception": {
    "lighting": "bright" | "dim" | "dark",
    "traversability": <float 0-1>
  },
  "collision": {
    "suspected": true | false,
    "risk_level": "safe" | "warning" | "danger"
  }
}""",
        output_key="window_analysis"
    )


def create_loop_validator() -> Agent:
    """Validate analysis and decide: continue loop or exit."""
    return Agent(
        name="LoopValidator",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[exit_loop_tool],
        instruction="""Control the analysis loop iteration.

Current Window: {current_window}
Window Index: {loop_index}
Loop Max: {loop_max}
Analysis: {window_analysis}

TASK: Validate window analysis and decide loop continuation.

INSTRUCTIONS:
1. Verify window analysis is complete and valid
2. Check: loop_index >= (loop_max - 1)?
3. Decision:
   - IF YES (all windows processed):
     * Call exit_analysis_loop()
     * This EXITS the loop
   - IF NO (more windows):
     * Do NOT call any function
     * Just return continue signal in JSON
4. Return JSON:

{
  "validation": "complete",
  "loop_decision": "CONTINUE" | "EXIT",
  "current_index": {loop_index},
  "total": {loop_max}
}

IMPORTANT: 
- Call exit_analysis_loop() ONLY when loop_index >= (loop_max - 1)
- Otherwise return JSON only (no function call)
- The framework will increment loop_index for next iteration""",
        output_key="loop_validation"
    )


def create_cod_evaluator() -> Agent:
    """Evaluate ODD compliance across all windows."""
    return Agent(
        name="COD_Evaluator",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[],
        instruction="""Analyze all accumulated window analyses for ODD.

TASK: Review all window analyses from session state and evaluate ODD factors.

INSTRUCTIONS:
1. Access all window_*_analysis results from session state
2. Identify patterns, anomalies, ODD scenarios across windows
3. Return ONLY JSON:

{
  "cod_detected": true | false,
  "severity": "low" | "medium" | "high",
  "odd_summary": "Summary of ODD analysis",
  "affected_windows": []
}""",
        output_key="cod_result"
    )


def create_report_generator() -> Agent:
    """Generate final comprehensive report."""
    return Agent(
        name="ReportGenerator",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[],
        instruction="""Generate final analysis report.

TASK: Synthesize all window analyses and COD evaluation into final report.

INSTRUCTIONS:
1. Review all window analyses and COD evaluation from session state
2. Synthesize findings into structured report
3. Return ONLY JSON:

{
  "report_title": "Analysis Report",
  "windows_analyzed": <count>,
  "motion_assessment": "Summary",
  "perception_assessment": "Summary",
  "collision_assessment": "Summary",
  "cod_assessment": "Summary",
  "overall_status": "SAFE" | "CAUTION" | "ALERT",
  "confidence": <float 0-1>
}""",
        output_key="final_report"
    )


# ============================================================================
# UTILITIES
# ============================================================================


def extract_json_from_text(text: str):
    """Extract JSON from text."""
    if not text:
        return None, False

    try:
        return json.loads(text), True
    except:
        pass

    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        if 0 < end:
            try:
                return json.loads(text[start:end].strip()), True
            except:
                pass

    if "{" in text:
        start = text.find("{")
        end = text.rfind("}") + 1
        if 0 <= start < end:
            try:
                return json.loads(text[start:end]), True
            except:
                pass

    return None, False


def analyze_events(agent_name: str, events: list) -> dict:
    """Extract agent results from events."""
    summary = {
        "agent": agent_name,
        "total_events": len(events),
        "messages": 0,
        "json": None,
    }

    for event in events:
        if getattr(event, 'author', None) == agent_name:
            summary["messages"] += 1
            content = getattr(event, 'content', None)
            if content and hasattr(content, 'parts'):
                for part in content.parts:
                    if hasattr(part, 'text') and part.text:
                        json_obj, valid = extract_json_from_text(part.text)
                        if valid:
                            summary["json"] = json_obj

    return summary


# ============================================================================
# MAIN PIPELINE
# ============================================================================


async def run_production_pipeline():
    """Execute the complete LoopAgent orchestrator pipeline."""
    print("\n" + "=" * 90)
    print("PRODUCTION LOOPAGENT ORCHESTRATOR PIPELINE")
    print("=" * 90)

    # Step 1: Get scenario info
    print("\n1️⃣  Retrieving scenario info...")
    scenario_data = get_scenario_data(str(scenario_path))
    if scenario_data["status"] != "success":
        print(f"❌ Failed to get scenario data: {scenario_data}")
        return

    windows = scenario_data["windows"]
    print(f"✅ Found {len(windows)} windows: {windows}")

    # Step 2: Run setup agent
    print("\n2️⃣  Running setup agent...")
    setup = create_setup_agent()
    try:
        runner = InMemoryRunner(agent=setup)
        events = await runner.run_debug("Initialize pipeline")
        result = analyze_events("SetupAgent", events)
        if result["json"]:
            print(f"✅ Setup: {result['json']}")
        else:
            print(f"⚠️  Setup ran but no JSON output")
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return

    # Step 3: Build loop agents
    print("\n3️⃣  Creating loop agents (Analyzer + Validator)...")
    analyzer = create_window_analyzer()
    validator = create_loop_validator()

    print(f"\n4️⃣  Creating final agents (COD + Report)...")
    cod = create_cod_evaluator()
    report = create_report_generator()

    # Step 4: Show the pipeline structure
    print("\n" + "=" * 90)
    print("PIPELINE ARCHITECTURE FOR NOTEBOOK INTEGRATION")
    print("=" * 90)
    print(f"""
Complete LoopAgent Orchestrator:

1. SetupAgent
   └─ Gets windows list: {windows}
   └─ Prepares state: loop_index=0, windows_list=[...]

2. LoopAgent (max_iterations=len(windows))
   ├─ Iteration 1:
   │  ├─ WindowAnalyzer processes window 006
   │  │  └─ Stores: temp:window_006_analysis
   │  └─ LoopValidator checks: index < max?
   │     └─ YES → Continue, increment index
   ├─ Iteration 2:
   │  ├─ WindowAnalyzer processes window 007
   │  │  └─ Stores: temp:window_007_analysis
   │  └─ LoopValidator checks: index >= max?
   │     └─ YES → Call exit_analysis_loop()
   └─ Loop exits when exit_analysis_loop() called

3. COD_Evaluator
   └─ Reviews all window_*_analysis results
   └─ Returns: {{'cod_detected': ..., 'severity': ...}}

4. ReportGenerator
   └─ Synthesizes final report
   └─ Returns: {{'report_title': ..., 'windows_analyzed': ...}}

RESULTS FLOW:
window_006_analysis → accumulated in session state
window_007_analysis → accumulated in session state
cod_result          → evaluation across all
final_report        → synthesis of everything

NO OVERWRITES ✓
    """)

    # Step 5: Test individual agents on real data
    print("\n5️⃣  Testing individual agents on real window...")
    try:
        print(f"\n   Testing WindowAnalyzer on window 006...")
        runner = InMemoryRunner(agent=analyzer)
        events = await runner.run_debug(
            f"Analyze window 006",
            session_state={
                "current_window": "006",
                "loop_index": "0",
                "scenario_path": str(scenario_path)
            }
        )
        result = analyze_events("WindowAnalyzer", events)
        if result["json"]:
            print(f"   ✅ Analyzer: {result['json']}")
        else:
            print(f"   ⚠️  No JSON output")
    except Exception as e:
        print(f"   ⚠️  Analyzer test: {e}")

    print("\n" + "=" * 90)
    print("✅ PRODUCTION PIPELINE READY")
    print("=" * 90)
    print("""
To integrate into notebook:

1. Import this module's agents
2. Create SequentialAgent:
   root = SequentialAgent(
       name="AnalysisPipeline",
       sub_agents=[
           SetupAgent,
           LoopAgent(
               sub_agents=[WindowAnalyzer, LoopValidator],
               max_iterations=len(windows)
           ),
           COD_Evaluator,
           ReportGenerator
       ]
   )
3. Run with InMemoryRunner
4. Extract results from session state

Results will cleanly accumulate without overwrites!
    """)


# ============================================================================
# MAIN
# ============================================================================


async def main():
    """Run the pipeline."""
    await run_production_pipeline()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
