#!/usr/bin/env python3
"""Collision Agent test using shared odd_agents module."""

from odd_agents.agents import create_collision_loop_agent, create_collision_summary_agent
from odd_agents import extract_json_block
import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from google.adk.agents import SequentialAgent
from google.adk.runners import InMemoryRunner
from google.genai import Client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import from shared module

# Configuration
API_KEY = os.environ.get("GOOGLE_API_KEY")
if not API_KEY:
    print("❌ GOOGLE_API_KEY environment variable not set")
    raise SystemExit(1)

GENAI_CLIENT = Client(api_key=API_KEY)
MODEL = "gemini-2.0-flash-lite"
SCENARIO_PATH = str(Path("data/processed/runs/sim_run_test").absolute())

# Create workflow using factory functions
collision_loop_agent = create_collision_loop_agent(
    SCENARIO_PATH, GENAI_CLIENT, MODEL, API_KEY)
collision_summary_agent = create_collision_summary_agent(API_KEY, MODEL)
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
