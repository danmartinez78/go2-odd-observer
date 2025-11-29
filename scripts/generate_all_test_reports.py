#!/usr/bin/env python3
"""
Generate HTML reports for all test data scenarios.
Non-interactive batch processor.
"""

from odd_agents import run_odd_workflow
from odd_agents.odd_definition import DEFAULT_ODD_DESCRIPTION, ODD_DEFINITION_VERSION
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from google.genai import Client

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# Model configuration (same as run_odd_analysis.py)
MODEL_PERCEPTION = "gemini-2.5-pro"
MODEL_MOTION = "gemini-2.5-flash"
MODEL_COLLISION = "gemini-2.5-pro"
MODEL_ODD_SPEC = "gemini-2.5-pro"
MODEL_COD = "gemini-2.5-flash"
MODEL_REPORT = "gemini-2.5-flash"

# ============================================================================
# ODD DESCRIPTION (Centralized in odd_agents/odd_definition.py)
# ============================================================================
# Imported from odd_agents.odd_definition - see that file for the full definition
# Version: {ODD_DEFINITION_VERSION} - includes human/animal proximity, carpet, no collision axis


async def run_scenario(scenario_name: str, data_type: str, analysis_dir: Path, genai_client):
    """Run analysis and generate report for one scenario."""
    print("=" * 80)
    print(f"Processing: {scenario_name} ({data_type})")
    print("=" * 80)

    scenario_path = project_root / "data" / "processed" / \
        "test_data" / data_type / scenario_name
    output_dir = analysis_dir / scenario_name
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run ODD analysis
    print(f"⏳ Running ODD analysis on {scenario_name}...")
    result = await run_odd_workflow(
        scenario_path=str(scenario_path),
        genai_client=genai_client,
        api_key=os.environ.get("GOOGLE_API_KEY"),
        nl_odd_description=DEFAULT_ODD_DESCRIPTION,
        model_perception=MODEL_PERCEPTION,
        model_motion=MODEL_MOTION,
        model_collision=MODEL_COLLISION,
        model_odd_spec=MODEL_ODD_SPEC,
        model_cod=MODEL_COD,
        model_report=MODEL_REPORT,
    )

    if not result:
        print(f"❌ Analysis failed for {scenario_name}")
        return False

    # Save JSON result
    json_path = output_dir / "full_result.json"
    with open(json_path, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"✅ Saved: {json_path}")

    # Generate HTML report
    import subprocess
    subprocess.run([
        sys.executable,
        str(project_root / "scripts" / "generate_html_report.py"),
        "--input", str(json_path),
        "--scenario-dir", str(scenario_path),
        "--output", str(project_root / "docs" / "reports" /
                        f"{scenario_name}_report.html")
    ], check=True)

    print(f"✅ Completed: {scenario_name}")
    print()
    return True


async def main():
    """Main execution function."""
    load_dotenv()
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY not set")
        sys.exit(1)

    print("=" * 80)
    print("Test Scenario Report Generator")
    print("=" * 80)
    print()

    # Scenarios to process
    real_scenarios = [
        "real_01_173442",
        "real_02_173813",
        "real_03_174232",
        "real_04_174321",
        "real_05_174503",
        "real_06_174604",
        "real_07_174604",
    ]

    sim_scenarios = [
        "sim_run_test",
    ]

    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    analysis_dir = project_root / "data" / "analysis_results" / \
        "automated" / f"test_reports_{timestamp}"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    print(f"Analysis results will be saved to: {analysis_dir}")
    print()

    # Create client
    genai_client = Client(api_key=api_key)

    # Process all scenarios
    success_count = 0
    total_count = len(real_scenarios) + len(sim_scenarios)

    for scenario in real_scenarios:
        if await run_scenario(scenario, "real", analysis_dir, genai_client):
            success_count += 1

    for scenario in sim_scenarios:
        if await run_scenario(scenario, "sim", analysis_dir, genai_client):
            success_count += 1

    print("=" * 80)
    print("✅ ALL REPORTS GENERATED")
    print("=" * 80)
    print()
    print(f"Results: {success_count}/{total_count} scenarios completed")
    print(f"  - Analysis JSON: {analysis_dir}/")
    print(f"  - HTML Reports: docs/reports/")
    print()
    print("Next steps:")
    print("  1. Review reports in docs/reports/")
    print("  2. Update docs/index.html to link to all reports")
    print("  3. Commit and push to deploy to GitHub Pages")


if __name__ == "__main__":
    asyncio.run(main())
