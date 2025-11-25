#!/usr/bin/env python3
"""
Automated Batch ODD Analysis Runner

Processes all production scenarios and generates aggregate report.
Follows the notebook workflow pattern with model configuration at top.

Usage:
    python scripts/run_odd_batch_analysis.py

Output:
    data/analysis_results/automated/<timestamp>/
        <scenario_1>/
            - full_result.json
            - executive_summary.json
        <scenario_2>/
            ...
        aggregate_report.json
"""

from odd_agents import run_odd_workflow
import asyncio
import json
import os
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv
from google.genai import Client

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# Suppress noisy warnings
warnings.filterwarnings(
    'ignore', category=ResourceWarning, message='.*unclosed.*')
warnings.filterwarnings('ignore', message='.*SSL.*')
warnings.filterwarnings('ignore', message='.*Event loop is closed.*')

# ============================================================================
# MODEL CONFIGURATION
# ============================================================================
# Customize which models to use for each agent
# Options: "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro",
#          "gemini-3-pro", "gemini-robotics-er-1.5-preview"

# Camera + LiDAR analysis (complex vision)
MODEL_PERCEPTION = "gemini-2.5-pro"
# IMU motion detection (straightforward)
MODEL_MOTION = "gemini-2.5-flash"
# Collision risk assessment (complex reasoning)
MODEL_COLLISION = "gemini-2.5-pro"
# ODD specification parsing (complex NLP)
MODEL_ODD_SPEC = "gemini-2.5-pro"
MODEL_COD = "gemini-2.5-flash"             # COD classification + compliance
MODEL_REPORT = "gemini-2.5-flash"          # Final report generation

# ============================================================================
# ODD DESCRIPTION (Default from notebook)
# ============================================================================
DEFAULT_ODD_DESCRIPTION = """
The Unitree Go2 is a quadruped robot designed for general indoor navigation.

It's meant to operate in typical indoor environments - think homes, offices, hallways, 
conference rooms, living rooms, and open workspaces. The floors should be smooth (tile, 
hardwood, or low-pile carpet), and there needs to be adequate lighting so the cameras 
can see clearly. Bright lighting is ideal, but it can handle dimmer areas too. 
No pitch-black rooms though.

The robot moves with smooth to moderate acceleration - controlled movements during 
normal navigation. It can handle quick starts and stops when needed (like avoiding 
obstacles), but it's not meant for aggressive racing-style maneuvers or abrupt jerky 
motions. Think responsive and agile, not violent or chaotic. The motion should feel 
controlled and deliberate, even when reacting to obstacles. It's designed to 
navigate around typical indoor obstacles like furniture, chairs, desk legs, and the 
occasional box, but it's not meant for super cluttered spaces where there's barely 
room to move.

The robot expects relatively flat, stable ground. No stairs, no steep ramps, and 
definitely not designed for outdoor terrain like gravel or grass. It needs space 
to maneuver safely without constantly being on the verge of hitting things.

DEFINITELY NOT designed for:
- Outdoor environments (weather, uneven ground, GPS reliance)
- Staircases or steep slopes
- Dark rooms where vision sensors can't work
- Extremely crowded spaces where collision is almost guaranteed
- Rough terrain, gravel, sand, or anything unstable
- Industrial environments with heavy machinery or hazardous materials
- Extremely crowded spaces where collision is almost guaranteed
- Rough terrain, gravel, sand, or anything unstable
- Industrial environments with heavy machinery or hazardous materials
"""


def find_production_scenarios():
    """Find all production scenarios."""
    scenarios = []
    production_dir = project_root / "data" / "processed" / "production"

    if not production_dir.exists():
        return scenarios

    for scenario_dir in sorted(production_dir.iterdir()):
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
            'windows': window_count
        })

    return scenarios


def save_scenario_results(result: Dict[str, Any], scenario_name: str, output_base: Path, source_path: str = None) -> Path:
    """Save individual scenario results."""
    scenario_dir = output_base / scenario_name
    scenario_dir.mkdir(parents=True, exist_ok=True)

    # Add source path to result if provided
    if source_path:
        result['source_scenario_path'] = source_path

    # Save full result
    full_result_path = scenario_dir / "full_result.json"
    with open(full_result_path, 'w') as f:
        json.dump(result, f, indent=2)

    # Save executive summary
    summary_path = scenario_dir / "executive_summary.json"
    compliance_data = get_compliance_data(result)
    summary_data = {
        'executive_summary': result['report'].get('executive_summary', ''),
        'key_findings': result['report'].get('key_findings', []),
        'recommendations': result['report'].get('recommendations', []),
        'scenario_metadata': result['report'].get('scenario_metadata', {}),
        'overall_compliance': compliance_data.get('overall_compliance', ''),
        'violations': compliance_data.get('violations', []),
        'warnings': compliance_data.get('warnings', [])
    }
    with open(summary_path, 'w') as f:
        json.dump(summary_data, f, indent=2)

    return scenario_dir


def get_compliance_data(result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract compliance data, handling potential double nesting."""
    compliance = result['full_analysis']['odd_compliance']
    # Handle double nesting if present
    if 'odd_compliance' in compliance:
        return compliance['odd_compliance']
    return compliance


def generate_aggregate_report(results: List[Dict[str, Any]], timestamp: str) -> Dict[str, Any]:
    """Generate aggregate report from all scenario results."""
    aggregate = {
        'batch_metadata': {
            'timestamp': timestamp,
            'total_scenarios': len(results),
            'successful_scenarios': len([r for r in results if r['success']]),
            'failed_scenarios': len([r for r in results if not r['success']]),
            'total_windows_analyzed': sum(r.get('window_count', 0) for r in results if r['success']),
        },
        'scenario_summaries': [],
        'aggregate_statistics': {
            'compliance_distribution': {},
            'violation_types': {},
            'environment_distribution': {},
            'data_source_distribution': {},
        },
        'overall_findings': []
    }

    # Compliance distribution
    compliance_counts = {}
    violation_types = {}
    env_counts = {}
    source_counts = {}

    for result in results:
        if not result['success']:
            continue

        scenario_name = result['scenario_name']
        data = result['data']

        # Extract compliance data (handle double nesting)
        compliance_data = get_compliance_data(data)
        compliance = compliance_data.get('overall_compliance', 'UNKNOWN')
        violations = compliance_data.get('violations', [])
        warnings_list = compliance_data.get('warnings', [])

        metadata = data['report'].get('scenario_metadata', {})
        environment = metadata.get('environment_class', 'UNKNOWN')
        data_source = metadata.get('data_source', 'UNKNOWN')

        # Count compliance
        compliance_counts[compliance] = compliance_counts.get(
            compliance, 0) + 1

        # Count violation types
        for v in violations:
            violation_types[v] = violation_types.get(v, 0) + 1

        # Count environments
        env_counts[environment] = env_counts.get(environment, 0) + 1

        # Count data sources
        source_counts[data_source] = source_counts.get(data_source, 0) + 1

        # Add to summaries
        aggregate['scenario_summaries'].append({
            'scenario_name': scenario_name,
            'windows': result['window_count'],
            'compliance': compliance,
            'violations_count': len(violations),
            'warnings_count': len(warnings_list),
            'environment': environment,
            'data_source': data_source,
        })

    aggregate['aggregate_statistics']['compliance_distribution'] = compliance_counts
    aggregate['aggregate_statistics']['violation_types'] = violation_types
    aggregate['aggregate_statistics']['environment_distribution'] = env_counts
    aggregate['aggregate_statistics']['data_source_distribution'] = source_counts

    # Generate overall findings
    total_success = aggregate['batch_metadata']['successful_scenarios']
    total_scenarios = aggregate['batch_metadata']['total_scenarios']

    if total_success > 0:
        in_odd_count = compliance_counts.get('IN_ODD', 0)
        violation_count = compliance_counts.get('VIOLATION', 0)
        boundary_count = compliance_counts.get('ODD_BOUNDARY', 0)

        aggregate['overall_findings'] = [
            f"Analyzed {total_success}/{total_scenarios} scenarios successfully",
            f"ODD Compliance: {in_odd_count} in ODD, {boundary_count} at boundary, {violation_count} violations",
            f"Most common environment: {max(env_counts.items(), key=lambda x: x[1])[0] if env_counts else 'N/A'}",
            f"Data sources: {', '.join(f'{k} ({v})' for k, v in source_counts.items())}",
        ]

        if violation_types:
            top_violation = max(violation_types.items(), key=lambda x: x[1])
            aggregate['overall_findings'].append(
                f"Most common violation: {top_violation[0]} ({top_violation[1]} occurrences)")

    return aggregate


async def process_scenario(scenario: Dict[str, Any], genai_client: Client, api_key: str) -> Dict[str, Any]:
    """Process a single scenario."""
    scenario_name = scenario['name']
    scenario_path = str(scenario['path'].absolute())

    try:
        result = await run_odd_workflow(
            scenario_path=scenario_path,
            genai_client=genai_client,
            api_key=api_key,
            nl_odd_description=DEFAULT_ODD_DESCRIPTION,
            model_perception=MODEL_PERCEPTION,
            model_motion=MODEL_MOTION,
            model_collision=MODEL_COLLISION,
            model_odd_spec=MODEL_ODD_SPEC,
            model_cod=MODEL_COD,
            model_report=MODEL_REPORT,
        )

        if result:
            return {
                'success': True,
                'scenario_name': scenario_name,
                'window_count': scenario['windows'],
                'source_path': scenario_path,
                'data': result
            }
        else:
            return {
                'success': False,
                'scenario_name': scenario_name,
                'error': 'Workflow returned no results'
            }

    except Exception as e:
        return {
            'success': False,
            'scenario_name': scenario_name,
            'error': str(e)
        }


async def main():
    """Main execution function."""
    # Load environment
    load_dotenv()
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY not set in environment")
        print("Please create a .env file with: GOOGLE_API_KEY=your-key")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("ODD ANALYSIS - AUTOMATED BATCH RUNNER")
    print("=" * 80)
    print()
    print("🔧 Model Configuration:")
    print(f"   Perception:  {MODEL_PERCEPTION}")
    print(f"   Motion:      {MODEL_MOTION}")
    print(f"   Collision:   {MODEL_COLLISION}")
    print(f"   ODD Spec:    {MODEL_ODD_SPEC}")
    print(f"   COD/Comply:  {MODEL_COD}")
    print(f"   Report:      {MODEL_REPORT}")

    # Find scenarios
    print()
    print("🔍 Scanning for production scenarios...")
    scenarios = find_production_scenarios()

    if not scenarios:
        print("❌ No production scenarios found in data/production/")
        print("Please run extract_windows.py to create data")
        sys.exit(1)

    total_windows = sum(s['windows'] for s in scenarios)
    print(
        f"✅ Found {len(scenarios)} scenarios ({total_windows} total windows)")
    print()
    for scenario in scenarios:
        print(f"  • {scenario['name']:40s} ({scenario['windows']:3d} windows)")

    # Create timestamp and output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_base = project_root / "data" / \
        "analysis_results" / "automated" / timestamp
    output_base.mkdir(parents=True, exist_ok=True)

    print()
    print("=" * 80)
    print("STARTING BATCH ANALYSIS")
    print("=" * 80)
    print(f"  • Scenarios: {len(scenarios)}")
    print(f"  • Total windows: {total_windows}")
    print(f"  • Output: {output_base}")
    print()
    print("⚠️  Will exit on first error to save time and cost")
    print()

    # Create client
    genai_client = Client(api_key=api_key)

    results = []

    try:
        # Process scenarios with progress bar
        if HAS_TQDM:
            scenario_iterator = tqdm(
                scenarios, desc="Processing scenarios", unit="scenario")
        else:
            scenario_iterator = scenarios
            print("⏳ Processing scenarios...")

        for i, scenario in enumerate(scenario_iterator, 1):
            if not HAS_TQDM:
                print(
                    f"\n[{i}/{len(scenarios)}] Processing: {scenario['name']} ({scenario['windows']} windows)...")

            result = await process_scenario(scenario, genai_client, api_key)
            results.append(result)

            if result['success']:
                # Save individual results
                save_scenario_results(
                    result['data'], result['scenario_name'], output_base, result.get('source_path'))
                if not HAS_TQDM:
                    print(f"  ✅ Completed: {result['scenario_name']}")
            else:
                print()
                print(f"❌ FAILED: {result['scenario_name']}")
                print(f"   Error: {result['error']}")
                print()
                print("Exiting on first error (as configured)")
                break

        # Generate aggregate report
        print()
        print("=" * 80)
        print("GENERATING AGGREGATE REPORT")
        print("=" * 80)

        aggregate = generate_aggregate_report(results, timestamp)

        # Save aggregate report
        aggregate_path = output_base / "aggregate_report.json"
        with open(aggregate_path, 'w') as f:
            json.dump(aggregate, f, indent=2)

        # Display summary
        print()
        print("📊 BATCH SUMMARY:")
        print("-" * 80)
        print(
            f"  • Total scenarios: {aggregate['batch_metadata']['total_scenarios']}")
        print(
            f"  • Successful: {aggregate['batch_metadata']['successful_scenarios']}")
        print(f"  • Failed: {aggregate['batch_metadata']['failed_scenarios']}")
        print(
            f"  • Total windows: {aggregate['batch_metadata']['total_windows_analyzed']}")
        print()
        print("📈 COMPLIANCE DISTRIBUTION:")
        print("-" * 80)
        for status, count in aggregate['aggregate_statistics']['compliance_distribution'].items():
            print(f"  • {status:20s}: {count}")
        print()
        print("🌍 ENVIRONMENT DISTRIBUTION:")
        print("-" * 80)
        for env, count in aggregate['aggregate_statistics']['environment_distribution'].items():
            print(f"  • {env:20s}: {count}")
        print()
        print("💡 OVERALL FINDINGS:")
        print("-" * 80)
        for finding in aggregate['overall_findings']:
            print(f"  • {finding}")

        print()
        print("=" * 80)
        print("✅ BATCH ANALYSIS COMPLETE")
        print("=" * 80)
        print()
        print(f"📁 Results saved to:")
        print(f"   {output_base}")
        print()
        print(f"   • <scenario>/full_result.json        - Individual scenario results")
        print(f"   • <scenario>/executive_summary.json  - Individual summaries")
        print(f"   • aggregate_report.json              - Batch aggregate report")

        # Exit with error if any scenarios failed
        if aggregate['batch_metadata']['failed_scenarios'] > 0:
            sys.exit(1)

    except Exception as e:
        print()
        print(f"❌ Fatal error: {e}")
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
