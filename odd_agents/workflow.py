"""
ODD workflow orchestration.
Extracted from odd_workflow_full.py (reference implementation).
"""

import json
import time
from pathlib import Path
from typing import Optional, Dict, Any
from google.adk.agents import SequentialAgent
from google.adk.runners import InMemoryRunner
from google.genai import Client

from .utils import extract_json_block
from .metadata import hash_text, extract_pipeline_metadata, build_agent_registry
from .agent_prompts import get_all_prompts
from .robot_specs import get_robot_specs
from .agents import (
    create_odd_spec_agent,
    create_perception_agent,
    create_motion_agent,
    create_collision_agent,
    create_evaluator_agent,
    create_report_agent,
    AGENT_VERSIONS,
)


# =============================================================================
# FULL WORKFLOW
# =============================================================================

def create_odd_workflow(
    scenario_path: str,
    genai_client: Client,
    api_key: str,
    model_perception: str = "gemini-2.0-flash-exp",
    model_motion: str = "gemini-2.0-flash-exp",
    model_collision: str = "gemini-2.0-flash-exp",
    model_odd_spec: str = "gemini-2.0-flash-exp",
    model_evaluator: str = "gemini-2.0-flash-exp",
    model_report: str = "gemini-2.0-flash-exp",
) -> SequentialAgent:
    """Create a new ODD workflow instance with Phase 1.4.4 architecture.

    Phase 1.4.4 - Type-driven COD construction:
    - ODD Spec v5.0.0: Adds type definitions (range/bool/enum)
    - Sensor agents v5.0.0: Output per-window typed measurements
    - Evaluator v1.0.0: Uses Python tools for COD construction
    - Report v4.0.0: File-reading tool for efficient data access

    Args:
        scenario_path: Path to the scenario directory
        genai_client: Google GenAI client instance
        api_key: Google API key
        model_*: Model names for each agent (defaults to gemini-2.0-flash-exp)

    Returns:
        SequentialAgent workflow instance
    """
    from pathlib import Path
    scenario = Path(scenario_path)

    return SequentialAgent(
        name="OddWorkflow",
        sub_agents=[
            create_odd_spec_agent(api_key, model_odd_spec),
            create_perception_agent(
                scenario, genai_client, model_perception, api_key),
            create_motion_agent(
                str(scenario), genai_client, model_motion, api_key),
            create_collision_agent(
                str(scenario), genai_client, model_collision, api_key),
            create_evaluator_agent(
                scenario, genai_client, model_evaluator, api_key),
            create_report_agent(scenario, api_key, model_report),
        ],
    )


def extract_final_report(events: list) -> Optional[Dict[str, Any]]:
    """Extract final report from ReportAgent output."""
    for event in events:
        if event.author == "ReportAgent" and event.content:
            for part in event.content.parts:
                if part.text:
                    try:
                        return extract_json_block(part.text)
                    except Exception:
                        continue
    return None


def extract_agent_output(events: list, agent_name: str) -> Optional[Dict[str, Any]]:
    """Extract output from a specific agent."""
    for event in events:
        if event.author == agent_name and event.content:
            for part in event.content.parts:
                if part.text:
                    try:
                        return extract_json_block(part.text)
                    except Exception:
                        continue
    return None


def save_sensor_outputs(events: list, scenario_path: Path):
    """Save sensor agent outputs to files for Evaluator/Report access."""
    import json

    # Extract and save each sensor agent output
    for agent_name in ["PerceptionAgent", "MotionAgent", "CollisionAgent"]:
        output = extract_agent_output(events, agent_name)
        if output:
            output_file = scenario_path / \
                f"{agent_name.lower().replace('agent', '')}_output.json"
            with open(output_file, 'w') as f:
                json.dump(output, f, indent=2)
            print(f"📝 Saved {agent_name} output to {output_file.name}")

    # Also save ODD spec for reference
    odd_spec = extract_agent_output(events, "OddSpecAgent")
    if odd_spec:
        output_file = scenario_path / "odd_spec.json"
        with open(output_file, 'w') as f:
            json.dump(odd_spec, f, indent=2)
        print(f"📝 Saved ODD specification to {output_file.name}")


async def run_odd_workflow(
    scenario_path: str,
    genai_client: Client,
    api_key: str,
    nl_odd_description: Optional[str] = None,
    model_perception: str = "gemini-2.0-flash-exp",
    model_motion: str = "gemini-2.0-flash-exp",
    model_collision: str = "gemini-2.0-flash-exp",
    model_odd_spec: str = "gemini-2.0-flash-exp",
    model_evaluator: str = "gemini-2.0-flash-exp",
    model_report: str = "gemini-2.0-flash-exp",
) -> Optional[Dict[str, Any]]:
    """Run the complete ODD analysis workflow with Phase 1.4.4 architecture.

    Phase 1.4.4 - Type-driven COD construction:
    - Deterministic Python tools for distance calculations (massive token savings)
    - Per-window typed measurements enable temporal violation tracking
    - File-based data handoff reduces blackboard overhead

    Args:
        scenario_path: Path to the scenario directory (e.g., "data/processed/runs/sim_run_new")
        genai_client: Google GenAI client instance
        api_key: Google API key
        nl_odd_description: Natural language ODD description. If None, uses default.
        model_*: Model names for each agent (defaults to gemini-2.0-flash-exp)

    Returns:
        Dictionary containing:
        - report: Final analysis report
        - full_analysis: Complete agent outputs
        - pipeline_metadata: Execution metadata (versions, models, tokens, timing)

        Returns None if failed.
    """
    scenario_path_obj = Path(scenario_path)
    scenario_name = scenario_path_obj.name

    if not scenario_path_obj.exists():
        print(f"❌ Scenario not found: {scenario_path}")
        return None

    # Default ODD description
    if nl_odd_description is None:
        nl_odd_description = (
            "A quadruped robot designed for indoor office environments. "
            "Operates on smooth, flat floors with adequate lighting (bright or dim). "
            "Maximum speed 1.5 m/s. Designed for environments with moderate obstacle "
            "density and good traversability. Requires low collision risk conditions. "
            "Not designed for: outdoor environments, stairs, rough terrain, "
            "dark/low-light areas, or high-density obstacle fields."
        )

    print("\n" + "=" * 80)
    print(f"ODD WORKFLOW - PHASE 1.4.4 (Type-Driven COD Construction)")
    print(f"Scenario: {scenario_name}")
    print(f"ODD Description: {nl_odd_description[:100]}...")
    print("=" * 80)

    # Get robot specs (for context, not part of ODD)
    robot_specs = get_robot_specs("go2")

    user_query = (
        f"Analyze scenario '{scenario_name}' against this ODD specification:\n\n"
        f"{nl_odd_description}\n\n"
        f"Robot Platform Specifications (for context only, NOT part of ODD):\n"
        f"{robot_specs}"
    )

    # Build agent registry for metadata tracking
    # Extract actual prompts from agent factory functions
    agent_prompts = get_all_prompts()

    agent_registry = build_agent_registry(
        agent_versions=AGENT_VERSIONS,
        agent_prompts=agent_prompts,
        model_perception=model_perception,
        model_motion=model_motion,
        model_collision=model_collision,
        model_odd_spec=model_odd_spec,
        model_evaluator=model_evaluator,
        model_report=model_report,
    )

    # Create fresh workflow instance
    odd_workflow = create_odd_workflow(
        scenario_path=scenario_path,
        genai_client=genai_client,
        api_key=api_key,
        model_perception=model_perception,
        model_motion=model_motion,
        model_collision=model_collision,
        model_odd_spec=model_odd_spec,
        model_evaluator=model_evaluator,
        model_report=model_report,
    )
    runner = InMemoryRunner(agent=odd_workflow, app_name="OddWorkflowApp")

    # Run workflow and track timing
    pipeline_start = time.time()
    events = await runner.run_debug(user_query)
    pipeline_duration = time.time() - pipeline_start

    # Extract report
    report = extract_final_report(events)

    if report:
        print("\n✅ WORKFLOW COMPLETED - Final Report:\n")
        print(json.dumps(report, indent=2))

        # Save report to file
        output_file = scenario_path_obj / "odd_analysis_report.json"
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n📄 Report saved to: {output_file}")

        # Extract pipeline metadata from events
        pipeline_metadata = extract_pipeline_metadata(
            events=events,
            agent_registry=agent_registry,
            pipeline_start_time=pipeline_start,
            pipeline_duration=pipeline_duration,
            odd_spec_hash=hash_text(nl_odd_description),
            scenario_path=scenario_path,
        )

        # Compute lightweight analysis metadata for reports
        total_tokens = sum(
            exec_data.get('token_usage', {}).get('total_tokens', 0)
            for exec_data in pipeline_metadata['agent_executions'].values()
        )

        # Gemini pricing (as of Nov 2024): ~$0.00001/token for flash, ~$0.00003/token for pro
        # Use weighted average based on model distribution
        avg_price_per_token = 0.00002  # Conservative estimate
        estimated_cost = total_tokens * avg_price_per_token

        analysis_metadata = {
            'pipeline_version': pipeline_metadata['pipeline_version'],
            'analysis_timestamp': pipeline_metadata['pipeline_start_time'],
            'analysis_duration_seconds': round(pipeline_metadata['pipeline_duration_seconds'], 2),
            'total_agents_executed': len(pipeline_metadata['agent_executions']),
            'total_tokens_used': total_tokens,
            'estimated_cost_usd': round(estimated_cost, 4),
        }

        # Extract evaluator output for full_analysis
        evaluator_output = extract_agent_output(events, "EvaluatorAgent")

        # =====================================================================
        # POST-PIPELINE REPORT GENERATION
        # =====================================================================
        # Use report_builder to generate comprehensive reports from all outputs
        from .report_builder import extract_all_agent_outputs, generate_reports

        # Extract all agent outputs for full report
        all_agent_outputs = extract_all_agent_outputs(events)

        # Generate both executive summary and full technical report
        reports = generate_reports(
            events=events,
            pipeline_metadata=pipeline_metadata,
            output_dir=scenario_path_obj,  # Save to scenario directory
        )

        # Return report + metadata
        # Phase 1.4.4: Report is flat, evaluator output goes in full_analysis
        return {
            'report': report,  # From ReportAgent (executive summary)
            'full_analysis': evaluator_output or {},  # COD + compliance
            'analysis_metadata': analysis_metadata,
            'pipeline_metadata': pipeline_metadata,
            # New: comprehensive reports from post-processing
            'reports': {
                'executive_summary': reports['executive_summary'],
                'full_technical': reports['full_report'],
            },
            # New: all raw agent outputs for debugging
            'agent_outputs': all_agent_outputs,
        }
    else:
        print("\n❌ No valid report generated")
        return None
