#!/usr/bin/env python3
"""ODD Specification Agent test using shared odd_agents module."""

import asyncio
import json
from typing import Any, Optional

from google.adk.runners import InMemoryRunner

# Import from shared module
from odd_agents import extract_json_block
from odd_agents.agents import create_odd_spec_agent


async def test_odd_spec_agent() -> Optional[dict[str, Any]]:
    print("\n" + "=" * 80)
    print("ODD SPECIFICATION AGENT TEST")
    print("=" * 80)

    # Test natural language ODD description
    nl_odd_description = (
        "A quadruped robot designed for indoor office environments. "
        "Operates on smooth, flat floors with adequate lighting (bright or dim). "
        "Maximum speed 1.5 m/s. Designed for environments with moderate obstacle "
        "density and good traversability. Requires low collision risk conditions. "
        "Not designed for: outdoor environments, stairs, rough terrain, "
        "dark/low-light areas, or high-density obstacle fields."
    )

    # Create agent instance
    odd_spec_agent = create_odd_spec_agent()
    runner = InMemoryRunner(agent=odd_spec_agent, app_name="OddSpecAgentApp")
    events = await runner.run_debug(nl_odd_description)

    # Extract result
    result = None
    for event in events:
        if event.author == odd_spec_agent.name and event.content:
            for part in event.content.parts:
                if part.text:
                    try:
                        result = extract_json_block(part.text)
                        break
                    except Exception:
                        continue

    if result:
        print("\n✅ ODD Specification Generated:\n")
        print(json.dumps(result, indent=2))
    else:
        print("\n❌ No valid JSON output produced")

    return result


if __name__ == "__main__":
    try:
        spec = asyncio.run(test_odd_spec_agent())
        if spec is None:
            raise SystemExit(1)
        print("\n" + "=" * 80)
        print("✅ ODD SPECIFICATION AGENT TEST COMPLETED")
        print("=" * 80)
    except Exception as exc:
        print(f"\n❌ Fatal error: {exc}")
        raise
