#!/usr/bin/env python3
"""Perception Agent test using shared odd_agents module."""

import asyncio
import json
from typing import Any, Dict, List, Optional

from google.adk.agents import SequentialAgent
from google.adk.runners import InMemoryRunner

# Import from shared module
from odd_agents import set_scenario, extract_json_block
from odd_agents.agents import perception_loop_agent, perception_summary_agent

# Set test scenario
set_scenario("sim_run_test")


# Create workflow using shared agents
perception_workflow = SequentialAgent(
    name="PerceptionWorkflow",
    sub_agents=[perception_loop_agent, perception_summary_agent],
)


def _extract_result(events: List[Any]) -> Optional[Dict[str, Any]]:
    """Extract final result from perception summary agent."""
    for event in events:
        if event.author == perception_summary_agent.name and event.content:
            for part in event.content.parts:
                if part.text:
                    try:
                        return extract_json_block(part.text)
                    except Exception:
                        continue
    return None


async def test_perception_agent() -> Optional[Dict[str, Any]]:
    print("\n" + "=" * 80)
    print("PERCEPTION WORKFLOW TEST (Camera + LiDAR BEV)")
    print("=" * 80)

    runner = InMemoryRunner(agent=perception_workflow,
                            app_name="PerceptionWorkflowApp")
    events = await runner.run_debug("Analyze perception for all available windows")

    result = _extract_result(events)
    if result:
        print("\n✅ Final JSON output:\n")
        print(json.dumps(result, indent=2))
    else:
        print("\n❌ No valid JSON output produced")

    return result


if __name__ == "__main__":
    try:
        summary = asyncio.run(test_perception_agent())
        if summary is None:
            raise SystemExit(1)
        print("\n" + "=" * 80)
        print("✅ PERCEPTION AGENT TEST COMPLETED")
        print("=" * 80)
    except Exception as exc:  # pragma: no cover - debug aid
        print(f"\n❌ Fatal error: {exc}")
        raise
