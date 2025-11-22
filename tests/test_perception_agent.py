#!/usr/bin/env python3
"""Perception Agent test using shared odd_agents module."""

from odd_agents.agents.perception import create_perception_loop_agent, create_perception_summary_agent
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
MODEL = "gemini-2.5-pro"
SCENARIO_PATH = str(Path("data/processed/runs/sim_run_test").absolute())


def _extract_result(events: List[Any], agent_name: str = "PerceptionSummaryAgent") -> Optional[Dict[str, Any]]:
    """Extract final result from perception summary agent."""
    for event in events:
        if event.author == agent_name and event.content:
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

    # Create workflow using factory functions (creates new instances)
    perception_workflow = SequentialAgent(
        name="PerceptionWorkflow",
        sub_agents=[
            create_perception_loop_agent(
                SCENARIO_PATH, GENAI_CLIENT, MODEL, API_KEY),
            create_perception_summary_agent(API_KEY, MODEL),
        ],
    )

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
