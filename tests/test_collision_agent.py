#!/usr/bin/env python3
"""Collision Agent test using shared odd_agents module."""

import asyncio
import json
from typing import Any, Dict, List, Optional

from google.adk.agents import SequentialAgent
from google.adk.runners import InMemoryRunner

# Import from shared module
from odd_agents import set_scenario, extract_json_block
from odd_agents.agents import collision_loop_agent, collision_summary_agent

# Set test scenario
set_scenario("sim_run_test")


# Create workflow using shared agents
collision_workflow = SequentialAgent(
    name="CollisionWorkflow",
    sub_agents=[collision_loop_agent, collision_summary_agent],
)


def _extract_result(events: List[Any]) -> Optional[Dict[str, Any]]:
    """Extract final result from collision summary agent."""
    for event in events:
        if event.author == collision_summary_agent.name and event.content:
            for part in event.content.parts:
                if part.text:
                    try:
                        return extract_json_block(part.text)
                    except Exception:
                        continue
    return None


async def test_collision_agent() -> Optional[Dict[str, Any]]:
    print("\n" + "=" * 80)
    print("COLLISION WORKFLOW TEST (Multimodal Risk Assessment)")
    print("=" * 80)

    runner = InMemoryRunner(agent=collision_workflow,
                            app_name="CollisionWorkflowApp")
    events = await runner.run_debug("Analyze collision risk for all available windows")

    result = _extract_result(events)
    if result:
        print("\n✅ Final JSON output:\n")
        print(json.dumps(result, indent=2))
    else:
        print("\n❌ No valid JSON output produced")

    return result


if __name__ == "__main__":
    try:
        summary = asyncio.run(test_collision_agent())
        if summary is None:
            raise SystemExit(1)
        print("\n" + "=" * 80)
        print("✅ COLLISION AGENT TEST COMPLETED")
        print("=" * 80)
    except Exception as exc:
        print(f"\n❌ Fatal error: {exc}")
        raise
