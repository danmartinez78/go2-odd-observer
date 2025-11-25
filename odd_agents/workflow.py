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
from .agents import (
    create_odd_spec_agent,
    create_perception_loop_agent,
    create_perception_summary_agent,
    create_motion_loop_agent,
    create_motion_summary_agent,
    create_collision_loop_agent,
    create_collision_summary_agent,
    create_cod_classifier_agent,
    create_odd_compliance_agent,
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
    model_perception: str = "gemini-2.5-pro",
    model_motion: str = "gemini-2.0-flash-lite",
    model_collision: str = "gemini-2.0-flash-lite",
    model_odd_spec: str = "gemini-2.0-flash-lite",
    model_cod: str = "gemini-2.0-flash-lite",
    model_report: str = "gemini-2.0-flash-lite",
) -> SequentialAgent:
    """Create a new ODD workflow instance with fresh agent instances.

    Args:
        scenario_path: Path to the scenario directory
        genai_client: Google GenAI client instance
        api_key: Google API key
        model_*: Model names for each agent (defaults to gemini-2.0-flash-exp)

    Returns:
        SequentialAgent workflow instance
    """
    return SequentialAgent(
        name="OddWorkflow",
        sub_agents=[
            create_odd_spec_agent(api_key, model_odd_spec),
            create_perception_loop_agent(
                scenario_path, genai_client, model_perception, api_key),
            create_perception_summary_agent(api_key, model_perception),
            create_motion_loop_agent(
                scenario_path, genai_client, model_motion, api_key),
            create_motion_summary_agent(api_key, model_motion),
            create_collision_loop_agent(
                scenario_path, genai_client, model_collision, api_key),
            create_collision_summary_agent(api_key, model_collision),
            create_cod_classifier_agent(api_key, model_cod),
            create_odd_compliance_agent(api_key, model_cod),
            create_report_agent(api_key, model_report),
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


async def run_odd_workflow(
    scenario_path: str,
    genai_client: Client,
    api_key: str,
    nl_odd_description: Optional[str] = None,
    model_perception: str = "gemini-2.0-flash-lite",
    model_motion: str = "gemini-2.0-flash-lite",
    model_collision: str = "gemini-2.0-flash-lite",
    model_odd_spec: str = "gemini-2.0-flash-lite",
    model_cod: str = "gemini-2.0-flash-lite",
    model_report: str = "gemini-2.0-flash-lite",
) -> Optional[Dict[str, Any]]:
    """Run the complete ODD analysis workflow with metadata tracking.

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
    print(f"ODD WORKFLOW - FULL PIPELINE (v2.0.0 with metadata tracking)")
    print(f"Scenario: {scenario_name}")
    print(f"ODD Description: {nl_odd_description[:100]}...")
    print("=" * 80)

    user_query = (
        f"Analyze scenario '{scenario_name}' against this ODD specification:\n\n"
        f"{nl_odd_description}"
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
        model_cod=model_cod,
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
        model_cod=model_cod,
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

        # Return report + metadata
        return {
            'report': report.get('report', {}),
            'full_analysis': report.get('full_analysis', {}),
            'analysis_metadata': analysis_metadata,
            'pipeline_metadata': pipeline_metadata,
        }
    else:
        print("\n❌ No valid report generated")
        return None
