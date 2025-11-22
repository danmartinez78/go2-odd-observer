#!/usr/bin/env python3
"""MANUAL TESTING: Motion Agent interactive test.

This script is for MANUAL TESTING and inspection of the MotionLoopAgent.
Run it directly to see the agent's output and verify behavior.

For AUTOMATED EVALUATION, see:
- tests/test_adk_evaluation.py::test_motion_*
- tests/evaluation/motion/README.md

Usage:
    python tests/test_motion_agent.py
    
Expected: JSON output with motion statistics from IMU data (sim_run_test).
"""

from odd_agents.agents import create_motion_loop_agent, create_motion_summary_agent
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
motion_loop_agent = create_motion_loop_agent(
    SCENARIO_PATH, GENAI_CLIENT, MODEL, API_KEY)
motion_summary_agent = create_motion_summary_agent(API_KEY, MODEL)
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

    runner = InMemoryRunner(agent=motion_workflow,
                            app_name="MotionWorkflowApp")
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
