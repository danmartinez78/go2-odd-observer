#!/usr/bin/env python3
"""Motion Agent test using shared odd_agents module."""

import asyncio
import json
from typing import Any, Dict, List, Optional

from google.adk.agents import SequentialAgent
from google.adk.runners import InMemoryRunner

# Import from shared module
from odd_agents import set_scenario, extract_json_block
from odd_agents.agents import motion_loop_agent, motion_summary_agent

# Set test scenario
set_scenario("sim_run_test")


# Create workflow using shared agents
motion_workflow = SequentialAgent(
    name="MotionWorkflow",
    sub_agents=[motion_loop_agent, motion_summary_agent],
)


def _extract_result(events: List[Any]) -> Optional[Dict[str, Any]]:
    """Extract final result from motion summary agent."""
    for event in events:
        if event.author == motion_summary_agent.name and event.content:
            for part in event.content.parts:
                if part.text:
                    try:
                        return extract_json_block(part.text)
                    except Exception:
                        continue
    return None


async def test_motion_agent() -> Optional[Dict[str, Any]]:
    print("\n" + "=" * 80)
    print("MOTION WORKFLOW TEST (IMU Sensor Analysis)")
    print("=" * 80)

    runner = InMemoryRunner(agent=motion_workflow, app_name="MotionWorkflowApp")
    events = await runner.run_debug("Analyze motion for all available windows")

    result = _extract_result(events)
    if result:
        print("\n✅ Final JSON output:\n")
        print(json.dumps(result, indent=2))
    else:
        print("\n❌ No valid JSON output produced")

    return result


if __name__ == "__main__":
    try:
        summary = asyncio.run(test_motion_agent())
        if summary is None:
            raise SystemExit(1)
        print("\n" + "=" * 80)
        print("✅ MOTION AGENT TEST COMPLETED")
        print("=" * 80)
    except Exception as exc:
        print(f"\n❌ Fatal error: {exc}")
        raise
