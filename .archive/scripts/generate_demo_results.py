#!/usr/bin/env python3
"""
Generate demonstration results for the ODD analysis system.
Runs analysis on sim_run_new and saves comprehensive outputs.
"""

from odd_agents import run_odd_workflow
import asyncio
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from google.genai import Client

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# Load environment
load_dotenv()
API_KEY = os.environ.get("GOOGLE_API_KEY")
if not API_KEY:
    print("❌ GOOGLE_API_KEY environment variable not set")
    sys.exit(1)

# Configuration
SCENARIO_NAME = "sim_run_new"
SCENARIO_PATH = project_root / "data" / "processed" / "runs" / SCENARIO_NAME
DEMO_OUTPUT_DIR = project_root / "data" / "examples"

# Natural language ODD (conversational!)
NL_ODD = """
The Unitree Go2 is a quadruped robot designed for indoor office navigation. 

It's meant to operate in typical office buildings - think conference rooms, hallways, 
and open workspaces. The floors should be smooth (tile, hardwood, or low-pile carpet), 
and there needs to be adequate lighting so the cameras can see clearly. Bright office 
lighting is ideal, but it can handle dimmer areas too. No pitch-black rooms though.

The robot moves at a walking pace - nothing crazy fast. Think leisurely stroll, not 
a sprint. It's designed to navigate around typical office obstacles like chairs, 
desk legs, and the occasional box, but it's not meant for super cluttered spaces 
where there's barely room to move.

The robot expects relatively flat, stable ground. No stairs, no steep ramps, and 
definitely not designed for outdoor terrain like gravel or grass. It needs space 
to maneuver safely without constantly being on the verge of hitting things.

DEFINITELY NOT designed for:
- Outdoor environments (weather, uneven ground, GPS reliance)
- Staircases or steep slopes
- Dark rooms where vision sensors can't work
- Extremely crowded spaces where collision is almost guaranteed
- Rough terrain, gravel, sand, or anything unstable
"""

# Model configuration - using Pro for complex tasks
MODELS = {
    "perception": "gemini-2.5-pro",       # Complex vision analysis
    "motion": "gemini-2.0-flash-lite",    # Straightforward IMU analysis
    "collision": "gemini-2.5-pro",        # Complex risk reasoning
    "odd_spec": "gemini-2.5-pro",         # Complex NLP parsing
    "cod": "gemini-2.0-flash-lite",       # Classification task
    "report": "gemini-2.0-flash-lite",    # Report generation
}


async def main():
    print("\n" + "=" * 80)
    print("GENERATING DEMONSTRATION RESULTS")
    print("=" * 80)
    print(f"\nScenario: {SCENARIO_NAME}")
    print(f"Path: {SCENARIO_PATH}")
    print(f"Output: {DEMO_OUTPUT_DIR}")
    print(f"\nModel Configuration:")
    for agent, model in MODELS.items():
        print(f"  {agent:12s}: {model}")
    print("\n" + "=" * 80)

    if not SCENARIO_PATH.exists():
        print(f"❌ Scenario not found: {SCENARIO_PATH}")
        sys.exit(1)

    # Create output directory
    DEMO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Create client
    client = Client(api_key=API_KEY)

    print("\n🚀 Running ODD analysis workflow...")
    print("⏳ This will take 3-5 minutes with 13 windows...\n")

    # Run workflow
    result = await run_odd_workflow(
        scenario_path=str(SCENARIO_PATH),
        genai_client=client,
        api_key=API_KEY,
        nl_odd_description=NL_ODD,
        model_perception=MODELS["perception"],
        model_motion=MODELS["motion"],
        model_collision=MODELS["collision"],
        model_odd_spec=MODELS["odd_spec"],
        model_cod=MODELS["cod"],
        model_report=MODELS["report"],
    )

    if not result:
        print("❌ Workflow failed")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("✅ ANALYSIS COMPLETE!")
    print("=" * 80)

    # Extract key results
    report = result.get('report', {})
    metadata = report.get('scenario_metadata', {})
    compliance = result.get('full_analysis', {}).get('odd_compliance', {})

    print(f"\n📊 Quick Summary:")
    print(f"  • Windows analyzed: {metadata.get('total_windows_analyzed')}")
    print(
        f"  • Data source: {metadata.get('data_source')} (confidence: {metadata.get('data_source_confidence')})")
    print(f"  • ODD compliance: {compliance.get('overall_compliance')}")
    print(f"  • Violations: {len(compliance.get('violations', []))}")
    print(f"  • Warnings: {len(compliance.get('warnings', []))}")

    # Save comprehensive results
    demo_report_path = DEMO_OUTPUT_DIR / "demo_analysis_report.json"
    with open(demo_report_path, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"\n✅ Full report saved: {demo_report_path}")
    print(f"   Size: {demo_report_path.stat().st_size / 1024:.1f} KB")

    # Save executive summary separately (easier to read)
    summary_path = DEMO_OUTPUT_DIR / "demo_executive_summary.json"
    summary = {
        "scenario": SCENARIO_NAME,
        "executive_summary": report.get('executive_summary'),
        "key_findings": report.get('key_findings'),
        "recommendations": report.get('recommendations'),
        "metadata": metadata,
        "compliance": {
            "overall_compliance": compliance.get('overall_compliance'),
            "violations": compliance.get('violations', []),
            "warnings": compliance.get('warnings', []),
            "categorical_compliance": compliance.get('categorical_compliance', {}),
            "numeric_compliance": compliance.get('numeric_compliance', {}),
        }
    }

    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"✅ Executive summary saved: {summary_path}")
    print(f"   Size: {summary_path.stat().st_size / 1024:.1f} KB")

    print("\n" + "=" * 80)
    print("DEMONSTRATION RESULTS READY FOR COMMIT")
    print("=" * 80)
    print("\nNext steps:")
    print("  1. Review outputs in data/examples/")
    print("  2. Update README with findings")
    print("  3. Commit demo artifacts")
    print()


if __name__ == "__main__":
    asyncio.run(main())
