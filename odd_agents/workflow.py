"""
ODD workflow orchestration.
Extracted from odd_workflow_full.py (reference implementation).
"""

import json
from typing import Optional, Dict, Any
from google.adk.agents import SequentialAgent
from google.adk.runners import InMemoryRunner

from .config import DATA_DIR, set_scenario
from .utils import extract_json_block
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
)


# =============================================================================
# FULL WORKFLOW
# =============================================================================

def create_odd_workflow() -> SequentialAgent:
    """Create a new ODD workflow instance with fresh agent instances."""
    return SequentialAgent(
        name="OddWorkflow",
        sub_agents=[
            create_odd_spec_agent(),            # 1. Define ODD specification from NL
            create_perception_loop_agent(),     # 2. Analyze perception (current conditions)
            create_perception_summary_agent(),
            create_motion_loop_agent(),         # 3. Analyze motion (current conditions)
            create_motion_summary_agent(),
            create_collision_loop_agent(),      # 4. Analyze collision (current conditions)
            create_collision_summary_agent(),
            create_cod_classifier_agent(),      # 5. Classify current operating domain (COD)
            create_odd_compliance_agent(),      # 6. Compare COD vs ODD (violations)
            create_report_agent(),              # 7. Generate final report
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
    scenario_name: str = "sim_run_new",
    nl_odd_description: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Run the complete ODD analysis workflow.

    Args:
        scenario_name: Name of the scenario to analyze
        nl_odd_description: Natural language ODD description. If None, uses default.

    Returns:
        Dictionary containing the final analysis report, or None if failed.
    """
    # Set the scenario path (updates global config)
    scenario_path = set_scenario(scenario_name)

    if not scenario_path.exists():
        print(f"❌ Scenario not found: {scenario_name}")
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
    print(f"ODD WORKFLOW - FULL PIPELINE")
    print(f"Scenario: {scenario_name}")
    print(f"ODD Description: {nl_odd_description[:100]}...")
    print("=" * 80)

    user_query = (
        f"Analyze scenario '{scenario_name}' against this ODD specification:\n\n"
        f"{nl_odd_description}"
    )

    # Create fresh workflow instance
    odd_workflow = create_odd_workflow()
    runner = InMemoryRunner(agent=odd_workflow, app_name="OddWorkflowApp")
    events = await runner.run_debug(user_query)

    report = extract_final_report(events)

    if report:
        print("\n✅ WORKFLOW COMPLETED - Final Report:\n")
        print(json.dumps(report, indent=2))

        # Save report to file
        output_file = scenario_path / "odd_analysis_report.json"
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n📄 Report saved to: {output_file}")
    else:
        print("\n❌ No valid report generated")

    return report
