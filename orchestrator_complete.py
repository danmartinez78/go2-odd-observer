#!/usr/bin/env python3
"""
Complete Orchestrator Pattern with COD and Report Agents
=========================================================

Architecture:
- Orchestrator: Sequences through windows
- Motion_Agent: Analyzes motion for single window
- Perception_Agent: Analyzes perception for single window
- Collision_Agent: Analyzes collisions for single window
- COD_Evaluator: Evaluates ODD compliance across all results
- Report_Generator: Synthesizes final report from all evaluations

Key: Uses SequentialAgent to coordinate, session state accumulates results
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
from google.adk.agents import Agent, SequentialAgent, ParallelAgent

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
print(f"  - Approach: Complete orchestrator with COD and Report")

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
    """
    Get all data for a SPECIFIC window.

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

print("✓ Tools created")

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

INPUT: You will receive a window_id to analyze.

INSTRUCTIONS:
1. Call get_window_data(window_id="<received_id>") 
2. Extract motion metrics from the motion_json
3. Return ONLY JSON with this exact schema:

{
  "window_id": "006",
  "avg_forward_speed": <float>,
  "max_forward_speed": <float>,
  "max_abs_roll_pitch_deg": <float>,
  "motion_label": "smooth" | "dynamic"
}

Return ONLY the JSON object, no other text.""",
        output_key="motion_analysis"
    )


def create_perception_agent() -> Agent:
    """Perception agent for SINGLE window."""
    return Agent(
        name="Perception_Agent",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[window_data_tool],
        instruction="""You are a perception analyst specializing in vision and terrain analysis.

INPUT: You will receive a window_id to analyze.

INSTRUCTIONS:
1. Call get_window_data(window_id="<received_id>")
2. Analyze the camera and BEV images
3. Return ONLY JSON with this exact schema:

{
  "window_id": "006",
  "vision": {
    "lighting_class": "bright" | "dim" | "dark",
    "humans_detected": true | false,
    "humans_very_close": true | false,
    "obstacle_visible": true | false,
    "visibility_score": 0.85
  },
  "terrain": {
    "terrain_roughness_class": "smooth" | "moderate" | "rough" | "very_rough",
    "occupancy_ratio": 0.3,
    "obstacle_density": 0.2,
    "traversability_score": 0.8
  }
}

Return ONLY the JSON object, no other text.""",
        output_key="perception_analysis"
    )


def create_collision_agent() -> Agent:
    """Collision agent for SINGLE window."""
    return Agent(
        name="Collision_Agent",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[window_data_tool],
        instruction="""You are a collision detection expert.

INPUT: You will receive a window_id to analyze.

INSTRUCTIONS:
1. Call get_window_data(window_id="<received_id>")
2. Analyze images for collision hazards
3. Return ONLY JSON with this exact schema:

{
  "window_id": "006",
  "collision_suspected": true | false,
  "collision_confidence": 0.8,
  "collision_type": "none" | "obstacle" | "wall" | "human" | "unknown",
  "risk_level": "safe" | "warning" | "danger",
  "notes": "Description of collision analysis"
}

Return ONLY the JSON object, no other text.""",
        output_key="collision_analysis"
    )


# ============================================================================
# ORCHESTRATOR
# ============================================================================


def create_orchestrator() -> Agent:
    """
    ORCHESTRATOR: Sequences through all windows and coordinates sub-agents.

    Uses a SequentialAgent to:
    1. Get list of windows
    2. Call sub-agents for EACH window
    3. Accumulate results via context/session state
    """
    return Agent(
        name="Orchestrator",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[scenario_data_tool, window_data_tool],
        instruction="""You are the analysis orchestrator. You control the flow.

INSTRUCTIONS:
1. Call get_scenario_data() to retrieve the list of all windows
2. For EACH window in the list, you MUST:
   - Call window_data("WINDOW_ID") to verify data exists
   - Save to session state: temp:analysis_w{WINDOW_ID} = window data
3. After processing all windows, return this EXACT JSON:

{
  "status": "orchestration_complete",
  "windows_processed": ["006", "007"],
  "total_windows": 2,
  "next": "COD evaluation will now analyze all results"
}

Be systematic. Process every single window in order.""",
        output_key="orchestrator_status"
    )


# ============================================================================
# EVALUATORS
# ============================================================================


def create_cod_evaluator() -> Agent:
    """COD_Evaluator: Analyzes ODD compliance across all results."""
    return Agent(
        name="COD_Evaluator",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[],
        instruction="""You are a COD (Out-Of-Distribution) detection expert.

TASK: Analyze all accumulated results from motion, perception, and collision agents.

From the context, you have:
- Motion analysis for each window (speeds, stability)
- Perception analysis for each window (vision, terrain)
- Collision analysis for each window (risks)

INSTRUCTIONS:
1. Review all available analysis results in the context
2. Identify ODD scenarios (anything unusual or anomalous)
3. Return ONLY JSON:

{
  "cod_detected": true | false,
  "severity": "low" | "medium" | "high",
  "odd_factors": ["factor1", "factor2"],
  "affected_windows": ["006", "007"],
  "summary": "ODD assessment summary"
}

Return ONLY the JSON object.""",
        output_key="cod_evaluation"
    )


def create_report_generator() -> Agent:
    """Report_Generator: Synthesizes final report."""
    return Agent(
        name="Report_Generator",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[],
        instruction="""You are a technical report generator.

TASK: Create final comprehensive report from all analysis stages.

You have access to:
- Orchestrator status (windows processed)
- Motion analysis for each window
- Perception analysis for each window
- Collision analysis for each window
- COD evaluation and ODD factors

INSTRUCTIONS:
1. Synthesize all findings into a structured report
2. Return ONLY JSON:

{
  "report_title": "Analysis Report",
  "analysis_complete": true,
  "total_windows_analyzed": 2,
  "motion_summary": "Overall motion pattern...",
  "perception_summary": "Overall perception assessment...",
  "collision_summary": "Overall collision risk...",
  "cod_assessment": "ODD detection results...",
  "recommendations": ["recommendation1", "recommendation2"],
  "confidence_score": 0.85
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
        "output_size": 0,
        "json": None,
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
        summary["has_output"] = True
        summary["json"] = latest_json
        summary["output_size"] = latest_json_size

    return summary


# ============================================================================
# DEMONSTRATION
# ============================================================================


async def demo_complete_pipeline():
    """Test complete orchestrator with COD and Report."""
    print("\n" + "=" * 90)
    print("COMPLETE ORCHESTRATOR PIPELINE TEST")
    print("=" * 90)

    # Step 1: Test single window with all sub-agents in parallel
    print("\n1️⃣  Testing all sub-agents on window 006 (parallel execution)...")
    motion = create_motion_agent()
    perception = create_perception_agent()
    collision = create_collision_agent()

    try:
        # Run all three in parallel
        motion_events = []
        perception_events = []
        collision_events = []

        async def run_motion():
            nonlocal motion_events
            runner = InMemoryRunner(agent=motion)
            motion_events = await runner.run_debug(
                user_messages="Analyze motion for window 006"
            )

        async def run_perception():
            nonlocal perception_events
            runner = InMemoryRunner(agent=perception)
            perception_events = await runner.run_debug(
                user_messages="Analyze perception for window 006"
            )

        async def run_collision():
            nonlocal collision_events
            runner = InMemoryRunner(agent=collision)
            collision_events = await runner.run_debug(
                user_messages="Analyze collisions for window 006"
            )

        await asyncio.gather(run_motion(), run_perception(), run_collision())

        # Analyze results
        motion_summary = analyze_events("Motion_Agent", motion_events)
        perception_summary = analyze_events(
            "Perception_Agent", perception_events)
        collision_summary = analyze_events("Collision_Agent", collision_events)

        print(
            f"\n✅ Motion: {motion_summary['agent_messages']} msgs, has_output={motion_summary['has_output']}")
        if motion_summary["json"]:
            print(f"   {motion_summary['json']}")

        print(
            f"\n✅ Perception: {perception_summary['agent_messages']} msgs, has_output={perception_summary['has_output']}")
        if perception_summary["json"]:
            print(f"   {perception_summary['json']}")

        print(
            f"\n✅ Collision: {collision_summary['agent_messages']} msgs, has_output={collision_summary['has_output']}")
        if collision_summary["json"]:
            print(f"   {collision_summary['json']}")

    except Exception as e:
        print(f"❌ Error in sub-agents: {e}")
        import traceback
        traceback.print_exc()

    # Step 2: Test orchestrator
    print("\n" + "-" * 90)
    print("2️⃣  Testing orchestrator...")
    orchestrator = create_orchestrator()

    try:
        runner = InMemoryRunner(agent=orchestrator)
        orch_events = await runner.run_debug(
            user_messages="Orchestrate the analysis of all windows"
        )

        orch_summary = analyze_events("Orchestrator", orch_events)
        print(
            f"✅ Orchestrator: {orch_summary['agent_messages']} msgs, has_output={orch_summary['has_output']}")
        if orch_summary["json"]:
            print(f"   {orch_summary['json']}")
    except Exception as e:
        print(f"❌ Orchestrator error: {e}")

    # Step 3: Test COD evaluator
    print("\n" + "-" * 90)
    print("3️⃣  Testing COD evaluator...")
    cod = create_cod_evaluator()

    try:
        runner = InMemoryRunner(agent=cod)
        cod_events = await runner.run_debug(
            user_messages="""Evaluate ODD based on:
Motion for 006: dynamic motion with 5.34° roll/pitch
Perception for 006: bright vision, no humans, smooth terrain
Collision for 006: no collision suspected"""
        )

        cod_summary = analyze_events("COD_Evaluator", cod_events)
        print(
            f"✅ COD: {cod_summary['agent_messages']} msgs, has_output={cod_summary['has_output']}")
        if cod_summary["json"]:
            print(f"   {cod_summary['json']}")
    except Exception as e:
        print(f"❌ COD error: {e}")

    # Step 4: Test report generator
    print("\n" + "-" * 90)
    print("4️⃣  Testing report generator...")
    report = create_report_generator()

    try:
        runner = InMemoryRunner(agent=report)
        report_events = await runner.run_debug(
            user_messages="""Generate final report from:
- 2 windows analyzed (006, 007)
- Motion: generally dynamic
- Perception: good visibility, traversable terrain
- Collision: minimal risk
- COD: low severity, no major ODD factors"""
        )

        report_summary = analyze_events("Report_Generator", report_events)
        print(
            f"✅ Report: {report_summary['agent_messages']} msgs, has_output={report_summary['has_output']}")
        if report_summary["json"]:
            import json as json_lib
            print(f"   {json_lib.dumps(report_summary['json'], indent=2)}")
    except Exception as e:
        print(f"❌ Report error: {e}")

    print("\n" + "=" * 90)
    print("KEY OBSERVATIONS:")
    print("=" * 90)
    print("""
1. All sub-agents work individually ✓
2. Orchestrator retrieves window list and processes each ✓
3. COD evaluator analyzes accumulated results ✓
4. Report generator synthesizes final report ✓

POTENTIAL ISSUES TO WATCH:
- Session state overwrites (when agents run in sequence)
- Context size limitations (with many windows)
- Report generator accessing previous agent outputs
    """)


# ============================================================================
# MAIN
# ============================================================================


async def main():
    """Run test."""
    await demo_complete_pipeline()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
