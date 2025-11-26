#!/usr/bin/env python3
"""
Manual ODD Analysis Runner (Phase 1.4.3)

Interactive script to run complete ODD analysis workflow on a single scenario.
Uses consolidated 7-agent pipeline with flash-exp models for cost optimization.

Usage:
    python scripts/run_odd_analysis.py

Output:
    data/archive/analysis_results/manual/<timestamp>/<scenario>/
        - full_result.json
        - executive_summary.json
"""

from odd_agents import run_odd_workflow
import argparse
import asyncio
import json
import os
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from dotenv import load_dotenv
from google.genai import Client

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# Suppress noisy warnings
warnings.filterwarnings(
    'ignore', category=ResourceWarning, message='.*unclosed.*')
warnings.filterwarnings('ignore', message='.*SSL.*')
warnings.filterwarnings('ignore', message='.*Event loop is closed.*')

# ============================================================================
# MODEL CONFIGURATION (Phase 1.4.3 Optimizations)
# ============================================================================
# Using gemini-2.0-flash-exp for 100x cost reduction vs pro models
# Flash-exp is sufficient for most tasks with massive token savings
# Options: "gemini-2.0-flash-exp", "gemini-2.5-flash", "gemini-2.5-pro"

# All agents use flash-exp for maximum cost efficiency
# Phase 1.4.4 - Type-driven COD construction
MODEL_PERCEPTION = "gemini-2.0-flash-exp"   # Perception agent (v5.0.0)
MODEL_MOTION = "gemini-2.0-flash-exp"       # Motion agent (v5.0.0)
MODEL_COLLISION = "gemini-2.0-flash-exp"    # Collision agent (v5.0.0)
MODEL_ODD_SPEC = "gemini-2.0-flash-exp"     # ODD spec parsing (v5.0.0)
MODEL_EVALUATOR = "gemini-2.0-flash-exp"    # Evaluator agent (v1.0.0)
MODEL_REPORT = "gemini-2.0-flash-exp"       # Final report generation (v4.0.0)

# ============================================================================
# ODD DESCRIPTION (Default from notebook)
# ============================================================================
DEFAULT_ODD_DESCRIPTION = """
The Unitree Go2 is a quadruped robot designed for general indoor navigation in 
residential and commercial spaces.

ROBOT PHYSICAL SPECIFICATIONS (EGO VEHICLE):
- Footprint: 0.65m length × 0.31m width (standing posture)
- Height: 0.40m (standing), 0.25m (crouching)
- Minimum passable gap: 0.4m width for straight corridors
- Comfortable clearance: 0.5m+ width for maneuvering around obstacles
- Turning radius: ~0.3m (can rotate in place)

ENVIRONMENT:
The robot operates in typical indoor environments including homes, offices, hallways, 
conference rooms, living rooms, and workspaces. It handles smooth floors (tile, 
hardwood, low-pile carpet) and requires adequate lighting for camera-based perception. 
Bright to moderate lighting is ideal; very dim areas are acceptable but pitch-black 
rooms are outside operational limits.

OBSTACLE HANDLING:
Designed for furniture-dense residential spaces with moderate to high obstacle density. 
The robot can navigate around sofas, coffee tables, dining chairs, desk legs, and 
typical household items. Close proximity to furniture is expected and normal during 
navigation. The robot is NOT designed for extreme clutter where clear navigation paths 
are blocked, doorways are obstructed, or the floor is covered with scattered objects.

MOTION CHARACTERISTICS:
The robot uses dynamic motion control appropriate for agile quadruped navigation:
- Smooth motion during open navigation in hallways and clear spaces
- Quick reactive maneuvers when avoiding obstacles (acceleration up to 10 m/s²)
- Brief "abrupt" motion is normal and expected during:
  * Obstacle avoidance reactions
  * Direction changes around furniture
  * Emergency stops when unexpected obstacles appear
  
The robot is NOT designed for:
- Aggressive high-speed racing or sustained high acceleration
- Violent or erratic motion when operating in open, obstacle-free spaces

TERRAIN:
Designed for flat, stable indoor surfaces. Can handle:
- Gentle transitions between rooms (door thresholds, slight elevation changes)
- Minor surface variations (rug edges, mat transitions)

NOT designed for:
- Staircases (multi-step elevation changes)
- Steep ramps (>15 degree incline)
- Outdoor terrain (gravel, grass, dirt, uneven ground)
- Unstable surfaces (sand, loose materials)

DEFINITELY NOT DESIGNED FOR:
- Outdoor environments (weather exposure, GPS reliance, rough terrain)
- Dark rooms where camera sensors cannot function
- Industrial environments with heavy machinery or hazardous materials
- Extreme clutter where navigation paths are completely blocked
- Environments requiring climbing (stairs, steep slopes >15°)
- High-speed applications or aggressive maneuvering
"""


def find_scenarios():
    """Find all available scenarios (production + test datasets)."""
    scenarios = []
    data_dir = project_root / "data"

    # Search production/ and test/ subdirectories
    search_dirs = [
        ("production", data_dir / "production"),
        ("test", data_dir / "test"),
    ]

    for category, search_dir in search_dirs:
        if not search_dir.exists():
            continue

        for scenario_dir in sorted(search_dir.iterdir()):
            if not scenario_dir.is_dir():
                continue
            if scenario_dir.name.startswith('.'):
                continue

            # Check for index file
            index_files = list(scenario_dir.glob("index_*.csv"))
            if not index_files:
                continue

            # Count windows
            with open(index_files[0]) as f:
                window_count = len(f.readlines()) - 1  # Subtract header

            scenarios.append({
                'name': scenario_dir.name,
                'path': scenario_dir,
                'category': category,
                'windows': window_count
            })

    return scenarios


def select_scenario(scenarios):
    """Prompt user to select a scenario."""
    print("\n" + "=" * 80)
    print("AVAILABLE SCENARIOS")
    print("=" * 80)
    print()

    # Group by category
    categories = {}
    for scenario in scenarios:
        cat = scenario['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(scenario)

    idx = 1
    scenario_map = {}
    for cat in sorted(categories.keys()):
        print(f"\n{cat}:")
        print("-" * 80)
        for scenario in categories[cat]:
            print(
                f"  {idx:2d}. {scenario['name']:40s} ({scenario['windows']:3d} windows)")
            scenario_map[idx] = scenario
            idx += 1

    print()
    try:
        choice = input("Select scenario number (or 'q' to quit): ").strip()
        if choice.lower() == 'q':
            return None

        idx = int(choice)
        if idx in scenario_map:
            return scenario_map[idx]
        else:
            print("❌ Invalid selection")
            return None
    except (ValueError, KeyboardInterrupt):
        return None


def get_compliance_data(result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract compliance data from evaluator output (Phase 1.4.4)."""
    # Phase 1.4.4: evaluator output contains compliance_verdict
    evaluator = result['full_analysis'].get('evaluator', {})
    if 'compliance_verdict' in evaluator:
        return evaluator['compliance_verdict']
    # Fallback for old structure
    if 'odd_compliance' in result['full_analysis']:
        compliance = result['full_analysis']['odd_compliance']
        if 'odd_compliance' in compliance:
            return compliance['odd_compliance']
        return compliance
    return {}


def save_results(result: Dict[str, Any], scenario_name: str, timestamp: str, source_path: str = None) -> Path:
    """Save results to timestamped directory."""
    # Create output directory
    output_base = project_root / "data" / "analysis_results" / \
        "manual" / timestamp / scenario_name
    output_base.mkdir(parents=True, exist_ok=True)

    # Add source path to result if provided
    if source_path:
        result['source_scenario_path'] = source_path

    # Save full result
    full_result_path = output_base / "full_result.json"
    with open(full_result_path, 'w') as f:
        json.dump(result, f, indent=2)

    # Save executive summary separately
    summary_path = output_base / "executive_summary.json"
    compliance_data = get_compliance_data(result)

    # Extract compliance summary (Phase 1.4.4 compatible)
    overall_compliance = compliance_data.get('overall', 'UNKNOWN')
    violations = []  # Phase 1.4.4: critical_axes become violations
    if compliance_data.get('critical_axes'):
        violations = [
            f"Critical axis: {axis}" for axis in compliance_data['critical_axes']]

    summary_data = {
        'executive_summary': result['report'].get('executive_summary', ''),
        'key_findings': result['report'].get('key_findings', []),
        'recommendations': result['report'].get('recommendations', []),
        'scenario_metadata': result['report'].get('scenario_metadata', {}),
        'overall_compliance': overall_compliance,
        'violations': violations,
        'rationale': compliance_data.get('rationale', '')
    }
    with open(summary_path, 'w') as f:
        json.dump(summary_data, f, indent=2)

    return output_base


def display_summary(result: Dict[str, Any]):
    """Display executive summary and compliance status."""
    report = result['report']
    # Handle potential double nesting in compliance data
    compliance_data = get_compliance_data(result)
    metadata = report.get('scenario_metadata', {})
    analysis_meta = result.get('analysis_metadata', {})

    print("\n" + "=" * 80)
    print("EXECUTIVE SUMMARY")
    print("=" * 80)
    print()
    print(report.get('executive_summary', 'N/A'))
    print()

    print("=" * 80)
    print("KEY FINDINGS")
    print("=" * 80)
    for i, finding in enumerate(report.get('key_findings', []), 1):
        print(f"\n{i}. {finding}")

    print()
    print("=" * 80)
    print("SCENARIO METADATA")
    print("=" * 80)
    print(
        f"  • Windows analyzed: {metadata.get('total_windows_analyzed', 'N/A')}")
    print(
        f"  • Data source: {metadata.get('data_source', 'N/A')} (confidence: {metadata.get('data_source_confidence', 'N/A')})")
    print(f"  • Environment: {metadata.get('environment_class', 'N/A')}")

    # Display analysis metadata if available
    if analysis_meta:
        print()
        print("=" * 80)
        print("ANALYSIS METADATA")
        print("=" * 80)
        print(
            f"  • Pipeline version: {analysis_meta.get('pipeline_version', 'N/A')}")
        print(
            f"  • Duration: {analysis_meta.get('analysis_duration_seconds', 'N/A')} seconds")
        print(
            f"  • Agents executed: {analysis_meta.get('total_agents_executed', 'N/A')}")
        print(
            f"  • Total tokens: {analysis_meta.get('total_tokens_used', 'N/A'):,}")
        print(
            f"  • Estimated cost: ${analysis_meta.get('estimated_cost_usd', 0):.4f} USD")

    print()
    print("=" * 80)
    print("ODD COMPLIANCE")
    print("=" * 80)
    overall = compliance_data.get('overall', 'UNKNOWN')
    rationale = compliance_data.get('rationale', 'N/A')
    critical_axes = compliance_data.get('critical_axes', [])
    temporal_stability = compliance_data.get('temporal_stability', 'N/A')
    
    print(f"  • Overall: {overall}")
    print(f"  • Temporal Stability: {temporal_stability}")
    print(f"  • Critical Axes: {len(critical_axes)}")
    print(f"  • Rationale: {rationale}")

    if critical_axes:
        print()
        print("⚠️  CRITICAL AXES (Violations):")
        for axis in critical_axes:
            print(f"    • {axis}")

    print()
    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    for i, rec in enumerate(report.get('recommendations', []), 1):
        print(f"\n{i}. {rec}")


async def main():
    """Main execution function."""
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Run ODD analysis on a scenario"
    )
    parser.add_argument(
        "--scenario",
        type=str,
        help="Scenario name or path to run analysis on (skips interactive selection)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="Output directory for results (default: data/archive/analysis_results/manual/<timestamp>)"
    )
    args = parser.parse_args()

    # Load environment
    load_dotenv()
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY not set in environment")
        print("Please create a .env file with: GOOGLE_API_KEY=your-key")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("ODD ANALYSIS - MANUAL RUNNER")
    print("=" * 80)
    print()
    print("🔧 Model Configuration (Phase 1.4.4 - Type-Driven COD):")
    print(f"   Perception:  {MODEL_PERCEPTION}")
    print(f"   Motion:      {MODEL_MOTION}")
    print(f"   Collision:   {MODEL_COLLISION}")
    print(f"   ODD Spec:    {MODEL_ODD_SPEC}")
    print(f"   Evaluator:   {MODEL_EVALUATOR}")
    print(f"   Report:      {MODEL_REPORT}")

    # Find scenarios
    print()
    print("🔍 Scanning for scenarios...")
    scenarios = find_scenarios()

    if not scenarios:
        print("❌ No scenarios found in data/production/ or data/test/")
        print("Please run extract_windows.py to create data")
        sys.exit(1)

    print(f"✅ Found {len(scenarios)} scenarios")

    # Select scenario (either from args or interactively)
    if args.scenario:
        # Find matching scenario by name
        scenario = None
        for s in scenarios:
            if s['name'] == args.scenario or str(s['path']) == args.scenario:
                scenario = s
                break

        if scenario is None:
            print(f"❌ Scenario '{args.scenario}' not found")
            print(
                f"Available scenarios: {', '.join(s['name'] for s in scenarios)}")
            sys.exit(1)

        print(f"\n✅ Using scenario: {scenario['name']}")
    else:
        # Interactive selection
        scenario = select_scenario(scenarios)
        if scenario is None:
            print("\n👋 Cancelled")
            return

    scenario_path = str(scenario['path'].absolute())
    scenario_name = scenario['name']

    print()
    print("=" * 80)
    print("STARTING ANALYSIS")
    print("=" * 80)
    print(f"  • Scenario: {scenario_name}")
    print(f"  • Windows: {scenario['windows']}")
    print(f"  • Category: {scenario['category']}")
    print(f"  • Path: {scenario_path}")
    print()
    print("⏳ This may take 2-3 minutes...")
    print()

    # Create timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create client
    genai_client = Client(api_key=api_key)

    try:
        # Run workflow
        result = await run_odd_workflow(
            scenario_path=scenario_path,
            genai_client=genai_client,
            api_key=api_key,
            nl_odd_description=DEFAULT_ODD_DESCRIPTION,
            model_perception=MODEL_PERCEPTION,
            model_motion=MODEL_MOTION,
            model_collision=MODEL_COLLISION,
            model_odd_spec=MODEL_ODD_SPEC,
            model_evaluator=MODEL_EVALUATOR,
            model_report=MODEL_REPORT,
        )

        if result:
            # Save results
            if args.output_dir:
                # Use specified output directory
                output_base = Path(args.output_dir)
                output_dir = output_base / scenario_name
            else:
                # Use default timestamp-based directory
                output_base = project_root / "data" / "archive" / \
                    "analysis_results" / "manual" / timestamp
                output_dir = output_base / scenario_name

            output_dir.mkdir(parents=True, exist_ok=True)

            # Save full results
            full_result_path = output_dir / "full_result.json"
            with open(full_result_path, 'w') as f:
                json.dump(result, f, indent=2)

            # Save executive summary
            summary_path = output_dir / "executive_summary.json"
            with open(summary_path, 'w') as f:
                json.dump({
                    'report': result.get('report', {}),
                    'scenario_metadata': result.get('report', {}).get('scenario_metadata', {}),
                }, f, indent=2)

            # Display summary
            display_summary(result)

            print()
            print("=" * 80)
            print("✅ ANALYSIS COMPLETE")
            print("=" * 80)
            print()
            print(f"📁 Results saved to:")
            print(f"   {output_dir}")
            print()
            print(f"   • full_result.json         - Complete analysis data")
            print(f"   • executive_summary.json   - Key findings and recommendations")

        else:
            print()
            print("❌ Workflow failed - no results generated")
            sys.exit(1)

    except Exception as e:
        print()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Clean up client
        await genai_client.aio.aclose()
        # Suppress cleanup warnings
        sys.stderr = open(os.devnull, 'w')


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Cancelled by user")
        sys.exit(0)
