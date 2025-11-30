#!/usr/bin/env python3
"""MANUAL TESTING: Perception Agent interactive test.

This script is for MANUAL TESTING and inspection of the PerceptionAgent.
Run it directly to see the agent's output and verify behavior.

For AUTOMATED EVALUATION, see:
- tests/test_adk_evaluation.py::test_perception_*
- tests/evaluation/perception/README.md

Usage:
    python tests/test_perception_agent.py
    python tests/test_perception_agent.py --scenario data/test/sim_2win
    python tests/test_perception_agent.py --model gemini-2.0-flash-exp
    
Expected: JSON output with per-window perception analysis.
"""

from odd_agents.agents.perception import create_perception_agent
from odd_agents import extract_json_block
import argparse
import asyncio
import json
import os
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional

from google.adk.runners import InMemoryRunner
from google.genai import Client
from dotenv import load_dotenv

# Suppress SSL and asyncio warnings that clutter output
warnings.filterwarnings(
    'ignore', category=ResourceWarning, message='.*unclosed.*')
warnings.filterwarnings('ignore', message='.*SSL.*')
warnings.filterwarnings('ignore', message='.*Event loop is closed.*')

# Load environment variables from .env file
load_dotenv()


def _extract_result(events: List[Any], agent_name: str = "PerceptionAgent") -> Optional[Dict[str, Any]]:
    """Extract final result from perception agent."""
    for event in events:
        if event.author == agent_name and event.content:
            for part in event.content.parts:
                if part.text:
                    try:
                        return extract_json_block(part.text)
                    except Exception:
                        continue
    return None


async def test_perception_agent(
    scenario_path: str = "data/test/sim_2win",
    model: str = "gemini-2.0-flash-exp",
    api_key: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Run perception agent test with specified parameters."""

    # Use provided API key or get from environment
    if api_key is None:
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            print("❌ GOOGLE_API_KEY environment variable not set")
            raise SystemExit(1)

    print("\n" + "=" * 80)
    print("PERCEPTION AGENT TEST (Camera + LiDAR BEV)")
    print("=" * 80)
    print(f"Scenario: {Path(scenario_path).name}")
    print(f"Model: {model}")
    print("=" * 80)

    # Create client and agent
    genai_client = Client(api_key=api_key)
    scenario_path_obj = Path(scenario_path).absolute()

    perception_agent = create_perception_agent(
        scenario_path_obj, genai_client, model, api_key)

    runner = InMemoryRunner(agent=perception_agent,
                            app_name="PerceptionAgentApp")
    events = await runner.run_debug("Analyze perception for all available windows")

    result = _extract_result(events)
    if result:
        print("\n✅ Final JSON output:\n")
        print(json.dumps(result, indent=2))
    else:
        print("\n❌ No valid JSON output produced")

    # Clean up to prevent SSL errors
    await genai_client.aio.aclose()

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Perception Agent")
    parser.add_argument(
        "--scenario",
        type=str,
        default="data/test/sim_2win",
        help="Path to scenario directory"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gemini-2.5-flash",
        help="Model to use for testing"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Google API key (defaults to GOOGLE_API_KEY env var)"
    )

    args = parser.parse_args()

    try:
        summary = asyncio.run(test_perception_agent(
            scenario_path=args.scenario,
            model=args.model,
            api_key=args.api_key
        ))
        if summary is None:
            raise SystemExit(1)
        print("\n" + "=" * 80)
        print("✅ PERCEPTION AGENT TEST COMPLETED")
        print("=" * 80)
    except Exception as exc:
        print(f"\n❌ Fatal error: {exc}")
        raise
    finally:
        # Suppress aiohttp cleanup warnings on exit
        import sys
        sys.stderr = open(os.devnull, 'w')
