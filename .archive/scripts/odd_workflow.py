#!/usr/bin/env python3
"""
ODD Workflow - Production Script
=================================

Main entry point for running ODD analysis using the shared odd_agents module.
This replaces the monolithic odd_workflow_full.py with a clean import-based approach.

Usage:
    python scripts/odd_workflow.py
"""

import asyncio
import os
import sys
from pathlib import Path
from google.genai import Client
from dotenv import load_dotenv
from odd_agents import run_odd_workflow

# Load environment variables from .env file
load_dotenv()


async def main():
    """Run the ODD analysis workflow."""
    try:
        # Configuration
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            print("❌ GOOGLE_API_KEY environment variable not set")
            return 1

        genai_client = Client(api_key=api_key)
        scenario_path = str(
            Path("data/processed/runs/sim_run_test").absolute())

        # Test with small 2-window dataset
        result = await run_odd_workflow(
            scenario_path=scenario_path,
            genai_client=genai_client,
            api_key=api_key,
        )

        if result is None:
            print("\n❌ WORKFLOW FAILED")
            return 1

        print("\n" + "=" * 80)
        print("✅ ODD WORKFLOW COMPLETED SUCCESSFULLY")
        print("=" * 80)
        return 0

    except Exception as exc:
        print(f"\n❌ Fatal error: {exc}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
