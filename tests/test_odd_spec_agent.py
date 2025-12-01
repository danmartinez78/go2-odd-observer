#!/usr/bin/env python3
"""MANUAL TESTING: ODD Specification Agent interactive test.

This script is for MANUAL TESTING and inspection of the ODD Spec Agent.
Run it directly to see the agent's output and verify behavior.

For AUTOMATED EVALUATION (when available), see:
- tests/test_adk_evaluation.py::test_odd_spec_*
- tests/evaluation/odd_spec/README.md

Usage:
    python tests/test_odd_spec_agent.py
    python tests/test_odd_spec_agent.py --model gemini-1.5-flash
    
Expected: Structured ODD specification parsed from natural language.
"""

from odd_agents.agents import create_odd_spec_agent
from odd_agents import extract_json_block
import argparse
import asyncio
import json
import os
import warnings
from typing import Any, Optional

from google.adk.runners import InMemoryRunner
from dotenv import load_dotenv

# Suppress SSL and asyncio warnings that clutter output
warnings.filterwarnings(
    'ignore', category=ResourceWarning, message='.*unclosed.*')
warnings.filterwarnings('ignore', message='.*SSL.*')
warnings.filterwarnings('ignore', message='.*Event loop is closed.*')

# Load environment variables from .env file
load_dotenv()


async def test_odd_spec_agent(
    model: str = "gemini-2.5-flash",
    api_key: Optional[str] = None,
    nl_odd_description: Optional[str] = None
) -> Optional[dict[str, Any]]:
    """Run ODD spec agent test with specified parameters."""

    # Use provided API key or get from environment
    if api_key is None:
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            print("❌ GOOGLE_API_KEY environment variable not set")
            raise SystemExit(1)

    print("\n" + "=" * 80)
    print("ODD SPECIFICATION AGENT TEST")
    print("=" * 80)
    print(f"Model: {model}")
    print("=" * 80)

    # Use default ODD description if none provided
    if nl_odd_description is None:
        nl_odd_description = (
            "A quadruped robot designed for indoor office environments. "
            "Operates on smooth, flat floors with adequate lighting (bright or dim). "
            "Maximum speed 2.5 m/s. Designed for environments with moderate obstacle "
            "density and good clearance for navigation. Requires low collision risk conditions. "
            "Not designed for: outdoor environments, stairs, rough terrain, "
            "dark/low-light areas, or high-density obstacle fields."
        )

    # Create agent instance
    odd_spec_agent = create_odd_spec_agent(api_key, model)
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
    parser = argparse.ArgumentParser(
        description="Test ODD Specification Agent")
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
    parser.add_argument(
        "--odd-description",
        type=str,
        default=None,
        help="Natural language ODD description (uses default if not provided)"
    )

    args = parser.parse_args()

    try:
        spec = asyncio.run(test_odd_spec_agent(
            model=args.model,
            api_key=args.api_key,
            nl_odd_description=args.odd_description
        ))
        if spec is None:
            raise SystemExit(1)
        print("\n" + "=" * 80)
        print("✅ ODD SPECIFICATION AGENT TEST COMPLETED")
        print("=" * 80)
    except Exception as exc:
        print(f"\n❌ Fatal error: {exc}")
        raise
    finally:
        # Suppress aiohttp cleanup warnings on exit
        import sys
        sys.stderr = open(os.devnull, 'w')
