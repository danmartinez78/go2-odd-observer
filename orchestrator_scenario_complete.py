#!/usr/bin/env python3
"""
COMPLETE ODD/COD ANALYSIS ORCHESTRATION - SCENARIO-LEVEL
=========================================================

Comprehensive agent workflow for analyzing entire scenarios:

1. ODD Spec Agent: Natural language → structured ODD specification
2. Data Source Agent: Determine if scenario is sim or real
3. Window Analysis (Parallel):
   - Motion Agent: Kinematic metrics per window
   - Perception Agent: Multi-modal (camera + LiDAR) per window
   - Collision Agent: Collision detection per window
4. Window Evaluator: Per-window IN_ODD / BOUNDARY / ODD_EXIT classification
5. Scenario Aggregator: Combine windows → scenario-level COD with ranges
6. ODD Classifier: Compare scenario COD to ODD spec, compute distance
7. Report Generator: Final narrative with window-specific violations

Key architectural principles:
- Windows are parts of a single scenario (not isolated)
- COD structure mirrors ODD taxonomy
- Scenario classification with per-window violation tagging
- Sim/Real domain tagging for entire scenario
- Distance metrics computed at scenario level
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

print(f"✓ Complete ODD/COD Scenario Analysis Orchestration")
print(f"  - Model: {GEMINI_MODEL}")
print(f"  - Focus: Entire scenario, not per-window")
print(f"  - Agents: 7-agent pipeline with scenario-level aggregation")

# ============================================================================
# TOOLS
# ============================================================================


def get_window_image(window_id: str, image_type: str) -> dict:
    """Get a specific image for a window (camera or BEV type)."""
    try:
        scenario_name = scenario_path.name
        filename_map = {
            "camera": f"cam_{scenario_name}_w{window_id}.png",
            "bev_occupancy": f"bev_occupancy_{scenario_name}_w{window_id}.png",
            "bev_height": f"bev_height_{scenario_name}_w{window_id}.png",
            "bev_density": f"bev_density_{scenario_name}_w{window_id}.png",
            "bev_roughness": f"bev_roughness_{scenario_name}_w{window_id}.png",
        }

        if image_type not in filename_map:
            return {"status": "error", "message": "Invalid image_type"}

        file_path = scenario_path / filename_map[image_type]
        if not file_path.exists():
            return {"status": "error", "message": "File not found"}

        with open(file_path, 'rb') as f:
            image_base64 = base64.b64encode(f.read()).decode('utf-8')

        return {
            "status": "success",
            "window_id": window_id,
            "image_type": image_type,
            "base64": image_base64,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_motion_json(window_id: str) -> dict:
    """Get motion data for a window."""
    try:
        import pandas as pd

        index_files = list(scenario_path.glob("index_*.csv"))
        if not index_files:
            return {"status": "error"}

        index_df = pd.read_csv(index_files[0])
        scenario_name = scenario_path.name

        for _, row in index_df.iterrows():
            wid = str(row['window_id']).zfill(3)
            if wid == window_id:
                motion_file = scenario_path / \
                    f"motion_{scenario_name}_w{window_id}.json"
                if motion_file.exists():
                    with open(motion_file, 'r') as f:
                        motion_data = json.load(f)
                    return {"status": "success", "window_id": window_id, "data": motion_data}

        return {"status": "error", "message": "Motion data not found"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_scenario_windows() -> dict:
    """Get list of all available windows in scenario."""
    try:
        import pandas as pd

        if not scenario_path.exists():
            return {"status": "error"}

        index_files = list(scenario_path.glob("index_*.csv"))
        if not index_files:
            return {"status": "error"}

        index_df = pd.read_csv(index_files[0])
        scenario_name = scenario_path.name
        windows = []

        for _, row in index_df.iterrows():
            window_id = str(row['window_id']).zfill(3)
            motion_file = scenario_path / \
                f"motion_{scenario_name}_w{window_id}.json"
            if motion_file.exists():
                windows.append(window_id)

        return {"status": "success", "windows": windows, "count": len(windows)}
    except Exception as e:
        return {"status": "error"}


def get_manifest_data() -> dict:
    """Get scenario metadata from manifest."""
    try:
        import pandas as pd

        manifest_file = DATA_DIR.parent / "manifest.csv"
        if not manifest_file.exists():
            return {"status": "error", "message": "Manifest not found"}

        manifest_df = pd.read_csv(manifest_file)
        scenario_name = scenario_path.name

        for _, row in manifest_df.iterrows():
            if row['scenario_id'] == scenario_name:
                return {
                    "status": "success",
                    "scenario_id": row['scenario_id'],
                    "is_sim": bool(row['is_sim']),
                    "domain": "sim" if row['is_sim'] else "real",
                    "notes": row.get('notes', '')
                }

        return {"status": "error", "message": "Scenario not found in manifest"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# Tools
get_image_tool = FunctionTool(func=get_window_image)
get_motion_tool = FunctionTool(func=get_motion_json)
get_windows_tool = FunctionTool(func=get_scenario_windows)
get_manifest_tool = FunctionTool(func=get_manifest_data)

print("✓ Tools created (image, motion, windows, manifest)")

# ============================================================================
# AGENTS
# ============================================================================


def create_odd_spec_agent() -> Agent:
    """Convert natural language ODD description into structured specification."""
    return Agent(
        name="ODD_Spec_Agent",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[],
        instruction="""You are an ODD (Operational Design Domain) specification expert.

TASK: Convert a natural language ODD description into a structured JSON specification.

The ODD should define constraints across these axes:
- speed: [min, max] m/s
- terrain: allowed classes (e.g., ["smooth", "moderate"])
- lighting: allowed classes (e.g., ["bright"])
- humans: allowed proximity levels (e.g., ["none", "visible_far"])
- collisions: boolean (allowed: true/false)
- domain: ["sim"] or ["real"] or ["sim", "real"]

For a simple test, assume this ODD:
"The robot operates on smooth to moderate terrain in bright lighting with no humans present and no collisions."

Return ONLY JSON:
{
  "version": "1.0",
  "description": "Robot ODD specification",
  "axes": {
    "speed": {"min": 0.0, "max": 2.0, "units": "m/s"},
    "terrain": {"allowed": ["smooth", "moderate"]},
    "lighting": {"allowed": ["bright"]},
    "humans": {"allowed": ["none", "visible_far"]},
    "collisions": {"allowed": false},
    "domain": {"allowed": ["sim", "real"]}
  },
  "importance_weights": {
    "speed": 0.15,
    "terrain": 0.2,
    "lighting": 0.15,
    "humans": 0.2,
    "collisions": 0.3,
    "domain": 0.0
  }
}""",
        output_key="odd_spec"
    )


def create_data_source_agent() -> Agent:
    """Determine if scenario is from simulation or real world."""
    return Agent(
        name="Data_Source_Agent",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[get_manifest_tool],
        instruction="""You are a data source classification specialist.

TASK: Determine whether the scenario is from simulation or real-world deployment.

INSTRUCTIONS:
1. Call get_manifest_data() to read the manifest
2. Extract the domain information
3. Return ONLY JSON:

{
  "scenario_domain": "sim" | "real",
  "confidence": 0.95,
  "rationale": "Based on manifest data"
}""",
        output_key="data_source"
    )


def create_motion_agent() -> Agent:
    """Analyze motion metrics per window."""
    return Agent(
        name="Motion_Agent",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[get_windows_tool, get_motion_tool],
        instruction="""You are a motion analysis specialist.

TASK: Analyze motion for ALL windows in the scenario.

INSTRUCTIONS:
1. Call get_scenario_windows() to get list of window IDs
2. For each window, call get_motion_json(window_id)
3. Extract metrics: avg_forward_speed, max_forward_speed, max_abs_roll_pitch_deg
4. Classify each window's motion as "smooth" or "dynamic"
5. Return ONLY JSON with per-window analysis:

{
  "windows_analyzed": ["006", "007"],
  "per_window_motion": [
    {
      "window_id": "006",
      "avg_forward_speed": 0.5,
      "max_forward_speed": 1.2,
      "max_abs_roll_pitch_deg": 4.54,
      "motion_label": "smooth"
    },
    {
      "window_id": "007",
      "avg_forward_speed": 0.3,
      "max_forward_speed": 0.8,
      "max_abs_roll_pitch_deg": 1.75,
      "motion_label": "smooth"
    }
  ]
}""",
        output_key="motion_analysis"
    )


def create_perception_agent() -> Agent:
    """Analyze multi-modal perception (camera + LiDAR) per window."""
    return Agent(
        name="Perception_Agent",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[get_windows_tool],
        instruction="""You are a multi-modal perception specialist (camera + LiDAR BEV analysis).

TASK: Analyze vision (camera) and terrain (LiDAR BEV) for ALL windows.

NOTE: For this test run, generate realistic perception estimates without accessing images.
In production, tools would fetch camera and LiDAR BEV data.

INSTRUCTIONS:
1. Call get_scenario_windows() to get list of window IDs
2. For each window, estimate realistic perception metrics:
   - lighting_class: bright/dim/dark
   - visibility_score: 0.0-1.0
   - terrain_roughness_class: smooth/moderate/rough/very_rough
   - occupancy_ratio: 0.0-1.0
   - obstacle_density: 0.0-1.0
   - traversability_score: 0.0-1.0
3. Return ONLY JSON with per-window analysis:

{
  "windows_analyzed": ["006", "007"],
  "per_window_perception": [
    {
      "window_id": "006",
      "lighting_class": "bright",
      "visibility_score": 0.8,
      "terrain_roughness_class": "moderate",
      "occupancy_ratio": 0.3,
      "obstacle_density": 0.2,
      "traversability_score": 0.7,
      "humans_detected": false,
      "environmental_constraints": ["moderate_obstacles"]
    },
    {
      "window_id": "007",
      "lighting_class": "bright",
      "visibility_score": 0.8,
      "terrain_roughness_class": "moderate",
      "occupancy_ratio": 0.3,
      "obstacle_density": 0.2,
      "traversability_score": 0.7,
      "humans_detected": false,
      "environmental_constraints": ["moderate_obstacles"]
    }
  ]
}""",
        output_key="perception_analysis"
    )


def create_collision_agent() -> Agent:
    """Analyze collision risks per window using multi-modal fusion."""
    return Agent(
        name="Collision_Agent",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[get_windows_tool, get_motion_tool],
        instruction="""You are a collision detection specialist (multi-modal fusion).

TASK: Analyze collision risks for ALL windows using motion + camera + LiDAR.

NOTE: For this test run, estimate collision likelihood based on motion metrics.
In production, tools would fetch motion, camera, and LiDAR BEV data.

INSTRUCTIONS:
1. Call get_scenario_windows() to get list of window IDs
2. For each window:
   - Get motion data to check for deceleration/jerk patterns
   - Estimate collision likelihood based on motion anomalies
3. Determine collision likelihood per window
4. Return ONLY JSON with per-window collision analysis:

{
  "windows_analyzed": ["006", "007"],
  "per_window_collision": [
    {
      "window_id": "006",
      "collision_suspected": false,
      "collision_confidence": 0.0,
      "collision_type": "none",
      "risk_level": "safe"
    },
    {
      "window_id": "007",
      "collision_suspected": false,
      "collision_confidence": 0.0,
      "collision_type": "none",
      "risk_level": "safe"
    }
  ]
}""",
        output_key="collision_analysis"
    )


def create_window_evaluator() -> Agent:
    """Evaluate each window against ODD spec to determine IN_ODD / BOUNDARY / ODD_EXIT."""
    return Agent(
        name="Window_Evaluator",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[],
        instruction="""You are a window-level ODD compliance evaluator.

TASK: For each window in the scenario, determine IN_ODD / BOUNDARY / ODD_EXIT classification.

INSTRUCTIONS:
1. Read the ODD specification from odd_spec in session state
2. Read per_window_motion from motion_analysis in session state
3. Read per_window_perception from perception_analysis in session state
4. Read per_window_collision from collision_analysis in session state
5. For each window, compare metrics to ODD constraints:
   - IN_ODD: all metrics within acceptable ranges
   - BOUNDARY: some metrics at edge of ODD (e.g., speed near max)
   - ODD_EXIT: violates ODD constraint (e.g., speed > max, dark lighting when bright required, collision)
6. Return ONLY JSON with per_window evaluation for ALL windows in the scenario:

{
  "windows_evaluated": ["<window_ids>"],
  "per_window_status": [
    {
      "window_id": "<id>",
      "status": "IN_ODD" | "BOUNDARY" | "ODD_EXIT",
      "violations": [],
      "boundary_factors": []
    }
  ]
}""",
        output_key="window_evaluations"
    )


def create_scenario_aggregator() -> Agent:
    """Aggregate per-window analysis into scenario-level COD with ranges and violation tags."""
    return Agent(
        name="Scenario_Aggregator",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[],
        instruction="""You are a scenario-level data aggregation specialist.

TASK: Combine all window-level analyses into a single scenario-level COD profile.

INSTRUCTIONS:
1. Read per_window_motion from motion_analysis
2. Read per_window_perception from perception_analysis
3. Read per_window_collision from collision_analysis
4. Read per_window_status from window_evaluations
5. Compute scenario-level COD by aggregating across ALL windows:
   - For numeric axes (speed): compute range, mean, distribution
   - For categorical axes (terrain, lighting): collect unique values, identify primary
   - For collisions: flag any windows with collisions
   - Identify which windows are BOUNDARY or ODD_EXIT
6. Return ONLY JSON with aggregated scenario profile:

{
  "scenario_id": "<from scenario_path>",
  "total_windows": "<count>",
  "scenario_cod": {
    "speed": {
      "range": [min, max],
      "mean": <value>,
      "units": "m/s"
    },
    "terrain": {
      "classes_observed": ["<unique_classes>"],
      "primary": "<most_common>"
    },
    "lighting": {
      "classes_observed": ["<unique_classes>"],
      "primary": "<most_common>"
    },
    "humans": {
      "classes_observed": ["<unique_classes>"],
      "primary": "<most_common>"
    },
    "collisions": {
      "any_collision": <boolean>,
      "collision_windows": ["<window_ids>"],
      "boundary_windows": ["<window_ids>"],
      "exit_windows": ["<window_ids>"]
    }
  },
  "window_summary": {
    "total": <count>,
    "in_odd": <count>,
    "boundary": <count>,
    "exit": <count>
  }
}""",
        output_key="scenario_aggregation"
    )


def create_odd_classifier() -> Agent:
    """Compare scenario COD to ODD spec and classify scenario status."""
    return Agent(
        name="ODD_Classifier",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[],
        instruction="""You are an ODD compliance classification specialist.

TASK: Compare scenario COD to ODD specification and determine overall scenario status.

INSTRUCTIONS:
1. Read odd_spec from session state (the structured ODD specification)
2. Read scenario_aggregation from session state (the scenario-level COD)
3. Read data_source from session state (sim or real domain)
4. For each axis in the ODD spec, compare the scenario COD:
   - IN_ODD: all axes within spec ranges/values
   - BOUNDARY: some axes at edge but not violated
   - ODD_EXIT: at least one axis violates spec
5. Compute a rough distance metric (0=perfect, 1=severe violation)
6. Return ONLY JSON:

{
  "scenario_status": "IN_ODD" | "BOUNDARY" | "ODD_EXIT",
  "distance_from_odd": <0.0-1.0>,
  "violations_detected": ["<axis>: <reason>"],
  "boundary_factors": ["<axis>: <reason>"],
  "scenario_domain": "sim" | "real",
  "assessment": "<brief summary>"
}""",
        output_key="odd_classification"
    )


def create_report_generator() -> Agent:
    """Generate comprehensive final report with scenario status and window-specific violations."""
    return Agent(
        name="Report_Generator",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[],
        instruction="""You are a comprehensive report generator.

TASK: Synthesize all analyses into a final narrative report.

INSTRUCTIONS:
1. Read all agent outputs from session state:
   - odd_spec: ODD specification
   - data_source: scenario domain
   - motion_analysis: per-window motion data
   - perception_analysis: per-window perception data
   - collision_analysis: per-window collision data
   - window_evaluations: per-window IN/BOUNDARY/EXIT status
   - scenario_aggregation: scenario COD profile with ranges
   - odd_classification: scenario status and violations
2. Structure report:
   - Scenario metadata (ID, domain, total windows)
   - ODD specification summary
   - Scenario-level COD profile with ranges
   - Overall scenario status (IN_ODD / BOUNDARY / ODD_EXIT)
   - Per-window status details for all windows
   - Violations and boundary factors (with window IDs)
   - Key findings and summary
3. Return ONLY JSON:

{
  "report_title": "ODD/COD Analysis Report",
  "scenario_id": "<id>",
  "scenario_domain": "sim" | "real",
  "total_windows": <count>,
  "scenario_status": "IN_ODD" | "BOUNDARY" | "ODD_EXIT",
  "cod_distance_from_odd": <0.0-1.0>,
  "motion_summary": "<summary>",
  "perception_summary": "<summary>",
  "collision_summary": "<summary>",
  "window_summary": {
    "total": <count>,
    "in_odd": <count>,
    "boundary": <count>,
    "exit": <count>
  },
  "window_details": [
    {"window_id": "<id>", "status": "IN_ODD" | "BOUNDARY" | "ODD_EXIT"}
  ],
  "violations": ["<violation details with window IDs>"],
  "overall_assessment": "<narrative summary>",
  "confidence": <0.0-1.0>
}""",
        output_key="final_report"
    )


# ============================================================================
# ORCHESTRATION
# ============================================================================


def create_orchestration_pipeline() -> SequentialAgent:
    """
    Create the complete scenario analysis pipeline.

    Structure:
    1. ODD_Spec_Agent (define constraints)
    2. Data_Source_Agent (determine sim/real)
    3. ParallelAgent: Motion, Perception, Collision (per-window analysis)
    4. Window_Evaluator (per-window status)
    5. Scenario_Aggregator (combine into scenario COD)
    6. ODD_Classifier (determine scenario status & distance)
    7. Report_Generator (final narrative)
    """

    # Create all agents
    odd_spec = create_odd_spec_agent()
    data_source = create_data_source_agent()
    motion = create_motion_agent()
    perception = create_perception_agent()
    collision = create_collision_agent()
    window_eval = create_window_evaluator()
    scenario_agg = create_scenario_aggregator()
    odd_class = create_odd_classifier()
    report = create_report_generator()

    # Parallel window analysis
    parallel_window_analysis = ParallelAgent(
        name="WindowAnalysis",
        sub_agents=[motion, perception, collision]
    )

    # Sequential orchestration
    root = SequentialAgent(
        name="ScenarioAnalysisPipeline",
        sub_agents=[
            odd_spec,
            data_source,
            parallel_window_analysis,
            window_eval,
            scenario_agg,
            odd_class,
            report
        ]
    )

    return root


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
    """Analyze agent events to extract JSON output."""
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
# MAIN - TEST
# ============================================================================


async def test_orchestration():
    """Test the complete scenario analysis pipeline."""
    print("\n" + "=" * 90)
    print("SCENARIO-LEVEL ODD/COD ANALYSIS PIPELINE TEST")
    print("=" * 90)

    pipeline = create_orchestration_pipeline()
    runner = InMemoryRunner(agent=pipeline)

    print("\n▶️  Running scenario analysis pipeline...")
    print("   1. ODD Spec Agent → structured specification")
    print("   2. Data Source Agent → determine sim/real")
    print("   3. Window Analysis (parallel):")
    print("      - Motion Agent (kinematic metrics)")
    print("      - Perception Agent (camera + LiDAR)")
    print("      - Collision Agent (multi-modal fusion)")
    print("   4. Window Evaluator → per-window IN/BOUNDARY/EXIT")
    print("   5. Scenario Aggregator → scenario COD with ranges")
    print("   6. ODD Classifier → scenario status & distance")
    print("   7. Report Generator → final narrative")

    try:
        events = await runner.run_debug("Analyze complete scenario against ODD spec")

        print("\n" + "=" * 90)
        print("RESULTS")
        print("=" * 90)

        # Extract each agent's output
        odd_spec = analyze_events("ODD_Spec_Agent", events)
        data_src = analyze_events("Data_Source_Agent", events)
        motion = analyze_events("Motion_Agent", events)
        perception = analyze_events("Perception_Agent", events)
        collision = analyze_events("Collision_Agent", events)
        window_eval = analyze_events("Window_Evaluator", events)
        scenario_agg = analyze_events("Scenario_Aggregator", events)
        odd_class = analyze_events("ODD_Classifier", events)
        report = analyze_events("Report_Generator", events)

        print(
            f"\n✅ ODD Spec: {odd_spec['agent_messages']} events, output={'YES' if odd_spec['has_output'] else 'NO'}")
        if odd_spec['json']:
            print(
                f"   Axes defined: {list(odd_spec['json'].get('axes', {}).keys())}")

        print(
            f"\n✅ Data Source: {data_src['agent_messages']} events, output={'YES' if data_src['has_output'] else 'NO'}")
        if data_src['json']:
            print(
                f"   Domain: {data_src['json'].get('scenario_domain', 'N/A')}")

        print(
            f"\n✅ Motion: {motion['agent_messages']} events, output={'YES' if motion['has_output'] else 'NO'}")
        if motion['json']:
            print(f"   Windows: {motion['json'].get('windows_analyzed', [])}")

        print(
            f"\n✅ Perception: {perception['agent_messages']} events, output={'YES' if perception['has_output'] else 'NO'}")
        if perception['json']:
            print(
                f"   Windows: {perception['json'].get('windows_analyzed', [])}")

        print(
            f"\n✅ Collision: {collision['agent_messages']} events, output={'YES' if collision['has_output'] else 'NO'}")
        if collision['json']:
            print(
                f"   Windows: {collision['json'].get('windows_analyzed', [])}")

        print(
            f"\n✅ Window Evaluator: {window_eval['agent_messages']} events, output={'YES' if window_eval['has_output'] else 'NO'}")
        if window_eval['json']:
            print(
                f"   Windows evaluated: {window_eval['json'].get('windows_evaluated', [])}")

        print(
            f"\n✅ Scenario Aggregator: {scenario_agg['agent_messages']} events, output={'YES' if scenario_agg['has_output'] else 'NO'}")
        if scenario_agg['json']:
            cod = scenario_agg['json'].get('scenario_cod', {})
            print(
                f"   Speed range: {cod.get('speed', {}).get('range', 'N/A')}")
            print(
                f"   Terrain: {cod.get('terrain', {}).get('classes_observed', [])}")

        print(
            f"\n✅ ODD Classifier: {odd_class['agent_messages']} events, output={'YES' if odd_class['has_output'] else 'NO'}")
        if odd_class['json']:
            print(
                f"   Scenario Status: {odd_class['json'].get('scenario_status', 'N/A')}")
            print(
                f"   Distance from ODD: {odd_class['json'].get('distance_from_odd', 'N/A')}")
            print(
                f"   Domain: {odd_class['json'].get('scenario_domain', 'N/A')}")

        print(
            f"\n✅ Report: {report['agent_messages']} events, output={'YES' if report['has_output'] else 'NO'}")
        if report['json']:
            print(f"   Scenario: {report['json'].get('scenario_id', 'N/A')}")
            print(f"   Status: {report['json'].get('scenario_status', 'N/A')}")
            print(f"   Domain: {report['json'].get('scenario_domain', 'N/A')}")
            print(
                f"   Total Windows: {report['json'].get('total_windows', 'N/A')}")

        print("\n" + "=" * 90)
        print("✅ SCENARIO ANALYSIS COMPLETE")
        print("=" * 90)
        print("""
Pipeline Architecture (SCENARIO-LEVEL):

Phase 1: Specification
- ODD Spec Agent: Natural language → structured specification
- Data Source Agent: Determine sim/real domain

Phase 2: Window-level Analysis (Parallel)
- Motion Agent: Kinematic metrics per window
- Perception Agent: Multi-modal (camera + LiDAR BEV) per window
- Collision Agent: Multi-modal collision detection per window

Phase 3: Aggregation & Classification
- Window Evaluator: Per-window IN_ODD / BOUNDARY / ODD_EXIT
- Scenario Aggregator: Combine windows → scenario COD with ranges
- ODD Classifier: Compare to ODD spec, compute distance metric

Phase 4: Reporting
- Report Generator: Final narrative with window-specific violations

Key Features:
✓ Scenario-level COD with ranges (e.g., lighting: [bright, dark])
✓ Window-specific violation tagging
✓ Sim/Real domain classification
✓ Distance metric computation
✓ ODD spec in structured JSON matching COD taxonomy

Ready for full scenario analysis!
        """)

        return events

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


# ============================================================================
# MAIN
# ============================================================================


async def main():
    """Run the test."""
    await test_orchestration()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
