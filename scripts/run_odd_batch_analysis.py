#!/usr/bin/env python3
"""
Automated Batch ODD Analysis Runner

Processes all production scenarios and generates aggregate report.
Follows the notebook workflow pattern with model configuration at top.

Usage:
    python scripts/run_odd_batch_analysis.py [OPTIONS]

Options:
    --dry-run           Show what would be processed without running
    --continue-on-error Continue processing even if a scenario fails
    --no-knowledge      Disable knowledge seeding
    --scenario NAME     Run only a specific scenario by name
    --skip NAME         Skip specific scenarios (can be repeated)

Output:
    data/archive/analysis_results/automated/<timestamp>/
        <scenario_1>/
            - full_result.json
            - executive_summary.json
        <scenario_2>/
            ...
        aggregate_report.json
        batch_summary.json
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
from typing import List, Dict, Any, Optional

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
# Options: "gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash-exp"

# Camera + LiDAR analysis (complex vision)
MODEL_PERCEPTION = "gemini-2.5-pro"
# IMU motion detection (straightforward)
MODEL_MOTION = "gemini-2.5-pro"
# Collision risk assessment (complex reasoning)
MODEL_COLLISION = "gemini-2.5-pro"
# ODD specification parsing (complex NLP)
MODEL_ODD_SPEC = "gemini-2.5-pro"
# COD/Compliance evaluation
MODEL_EVALUATOR = "gemini-2.5-pro"
# Final report generation
MODEL_REPORT = "gemini-2.5-pro"

# Cost estimation (per 1K tokens, approximate)
COST_PER_1K_INPUT = 0.00125  # gemini-2.5-pro input
COST_PER_1K_OUTPUT = 0.01    # gemini-2.5-pro output
ESTIMATED_TOKENS_PER_WINDOW = 20000  # Rough estimate

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
"""


def find_production_scenarios(scenario_filter: Optional[str] = None, skip_list: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Find all production scenarios."""
    scenarios = []
    production_dir = project_root / "data" / "production"

    if not production_dir.exists():
        return scenarios

    for scenario_dir in sorted(production_dir.iterdir()):
        if not scenario_dir.is_dir():
            continue
        if scenario_dir.name.startswith('.'):
            continue

        # Apply filters
        if scenario_filter and scenario_dir.name != scenario_filter:
            continue
        if skip_list and scenario_dir.name in skip_list:
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


def build_knowledge_seed() -> Dict[str, Any]:
    """Build knowledge seed for agents (enabled by default)."""
    from odd_agents.knowledge import (
        build_reference_manifest,
        default_fundamentals_sections,
        default_sensor_sections,
        build_memory_seed_entries,
    )

    fundamentals_artifact = "artifact:odd_cod_fundamentals_v1"
    robot_artifact = "artifact:robot_go2_profile_v1"
    sensors_artifact = "artifact:sensor_interpretation_core_v1"

    manifest = build_reference_manifest(
        fundamentals_artifact=fundamentals_artifact,
        robot_artifact=robot_artifact,
        sensors_artifact=sensors_artifact,
    )

    return build_memory_seed_entries(
        manifest=manifest,
        fundamentals_sections=default_fundamentals_sections(
            fundamentals_artifact=fundamentals_artifact
        ),
        sensor_sections=default_sensor_sections(
            sensors_artifact=sensors_artifact
        ),
    )


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

    # Extract executive summary from new structure
    exec_summary = {}
    if 'reports' in result and 'executive_summary' in result['reports']:
        exec_summary = result['reports']['executive_summary']
    elif 'report' in result:
        # Fallback to report agent output
        report = result['report']
        if isinstance(report, str):
            try:
                report = json.loads(report)
            except json.JSONDecodeError:
                report = {'raw': report}
        exec_summary = report

    # Save executive summary
    summary_path = scenario_dir / "executive_summary.json"
    with open(summary_path, 'w') as f:
        json.dump(exec_summary, f, indent=2)

    return scenario_dir


def extract_compliance_verdict(result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract compliance verdict from result, handling various structures."""
    # Try new structure first (Phase 1.4.4+)
    full_analysis = result.get('full_analysis', {})

    # Check for compliance_verdict in evaluator output
    if 'compliance_verdict' in full_analysis:
        verdict = full_analysis['compliance_verdict']
        return {
            'verdict': verdict.get('verdict', 'UNKNOWN'),
            'confidence': verdict.get('confidence', 0.0),
            'rationale': verdict.get('rationale', ''),
        }

    # Check reports structure
    reports = result.get('reports', {})
    if 'executive_summary' in reports:
        compliance = reports['executive_summary'].get('compliance', {})
        return {
            'verdict': compliance.get('verdict', 'UNKNOWN'),
            'confidence': compliance.get('confidence_value', compliance.get('confidence', 0.0)),
        }

    # Fallback: try report agent output
    report = result.get('report', {})
    if isinstance(report, str):
        try:
            report = json.loads(report)
        except json.JSONDecodeError:
            report = {}

    if 'result' in report:
        try:
            inner = json.loads(report['result'])
            compliance = inner.get('compliance', {})
            status = compliance.get('status', 'UNKNOWN')
            return {
                'verdict': status,
                'confidence': 1.0 if compliance.get('confidence') == 'HIGH' else 0.8,
            }
        except (json.JSONDecodeError, TypeError):
            pass

    return {'verdict': 'UNKNOWN', 'confidence': 0.0}


def generate_aggregate_report(results: List[Dict[str, Any]], timestamp: str) -> Dict[str, Any]:
    """Generate aggregate report from all scenario results."""
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]

    # Calculate totals
    total_windows = sum(r.get('window_count', 0) for r in successful)
    total_tokens = sum(r.get('tokens', 0) for r in successful)
    total_cost = sum(r.get('cost', 0.0) for r in successful)
    total_duration = sum(r.get('duration', 0.0) for r in successful)

    aggregate = {
        'batch_metadata': {
            'timestamp': timestamp,
            'total_scenarios': len(results),
            'successful_scenarios': len(successful),
            'failed_scenarios': len(failed),
            'total_windows_analyzed': total_windows,
            'total_tokens_used': total_tokens,
            'total_cost_usd': round(total_cost, 4),
            'total_duration_seconds': round(total_duration, 1),
            'avg_cost_per_window': round(total_cost / total_windows, 4) if total_windows > 0 else 0,
        },
        'scenario_summaries': [],
        'failed_scenarios': [
            {'name': r['scenario_name'], 'error': r.get(
                'error', 'Unknown error')}
            for r in failed
        ],
        'aggregate_statistics': {
            'compliance_distribution': {},
            'data_source_distribution': {},
        },
        'overall_findings': []
    }

    # Aggregate statistics
    verdict_counts = {}
    source_counts = {}

    for result in successful:
        scenario_name = result['scenario_name']
        data = result['data']

        # Extract compliance
        compliance = extract_compliance_verdict(data)
        verdict = compliance.get('verdict', 'UNKNOWN')
        verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1

        # Determine data source from scenario name
        data_source = 'sim' if 'sim' in scenario_name.lower() else 'real'
        source_counts[data_source] = source_counts.get(data_source, 0) + 1

        # Add to summaries
        aggregate['scenario_summaries'].append({
            'scenario_name': scenario_name,
            'windows': result['window_count'],
            'verdict': verdict,
            'confidence': compliance.get('confidence', 0.0),
            'data_source': data_source,
            'tokens': result.get('tokens', 0),
            'cost_usd': round(result.get('cost', 0.0), 4),
            'duration_seconds': round(result.get('duration', 0.0), 1),
        })

    aggregate['aggregate_statistics']['compliance_distribution'] = verdict_counts
    aggregate['aggregate_statistics']['data_source_distribution'] = source_counts

    # Generate findings
    if successful:
        in_odd = verdict_counts.get('IN_ODD', 0)
        out_odd = verdict_counts.get('OUT_ODD', 0)
        boundary = verdict_counts.get('ODD_BOUNDARY', 0)

        aggregate['overall_findings'] = [
            f"Analyzed {len(successful)}/{len(results)} scenarios successfully",
            f"Compliance: {in_odd} IN_ODD, {out_odd} OUT_ODD, {boundary} BOUNDARY",
            f"Total cost: ${total_cost:.4f} ({total_tokens:,} tokens)",
            f"Average: ${total_cost/len(successful):.4f}/scenario, ${total_cost/total_windows:.5f}/window" if total_windows > 0 else "N/A",
            f"Data sources: {', '.join(f'{k}={v}' for k, v in source_counts.items())}",
        ]

    return aggregate


async def process_scenario(
    scenario: Dict[str, Any],
    genai_client: Client,
    api_key: str,
    knowledge_seed: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
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
            model_evaluator=MODEL_EVALUATOR,
            model_report=MODEL_REPORT,
            knowledge_seed=knowledge_seed,
        )

        if result:
            # Extract metrics from result
            analysis_meta = result.get('analysis_metadata', {})
            return {
                'success': True,
                'scenario_name': scenario_name,
                'window_count': scenario['windows'],
                'source_path': scenario_path,
                'tokens': analysis_meta.get('total_tokens_used', 0),
                'cost': analysis_meta.get('estimated_cost_usd', 0.0),
                'duration': analysis_meta.get('analysis_duration_seconds', 0.0),
                'data': result
            }
        else:
            return {
                'success': False,
                'scenario_name': scenario_name,
                'window_count': scenario['windows'],
                'error': 'Workflow returned no results'
            }

    except Exception as e:
        import traceback
        return {
            'success': False,
            'scenario_name': scenario_name,
            'window_count': scenario.get('windows', 0),
            'error': f"{type(e).__name__}: {str(e)}",
            'traceback': traceback.format_exc(),
        }


def estimate_cost(scenarios: List[Dict[str, Any]]) -> Dict[str, float]:
    """Estimate total cost for batch run."""
    total_windows = sum(s['windows'] for s in scenarios)
    estimated_tokens = total_windows * ESTIMATED_TOKENS_PER_WINDOW
    # Assume 90% input, 10% output
    input_tokens = estimated_tokens * 0.9
    output_tokens = estimated_tokens * 0.1
    estimated_cost = (input_tokens / 1000 * COST_PER_1K_INPUT) + \
        (output_tokens / 1000 * COST_PER_1K_OUTPUT)

    return {
        'total_windows': total_windows,
        'estimated_tokens': estimated_tokens,
        'estimated_cost_usd': round(estimated_cost, 2),
        'cost_per_window': round(estimated_cost / total_windows, 4) if total_windows > 0 else 0,
    }


async def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Batch ODD Analysis Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without running",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue processing even if a scenario fails (default: stop on first error)",
    )
    parser.add_argument(
        "--no-knowledge",
        action="store_true",
        help="Disable knowledge seeding",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        help="Run only a specific scenario by name",
    )
    parser.add_argument(
        "--skip",
        type=str,
        action="append",
        default=[],
        help="Skip specific scenarios (can be repeated)",
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
    print("ODD ANALYSIS - AUTOMATED BATCH RUNNER")
    print("=" * 80)
    print()
    print("🔧 Model Configuration:")
    print(f"   Perception:  {MODEL_PERCEPTION}")
    print(f"   Motion:      {MODEL_MOTION}")
    print(f"   Collision:   {MODEL_COLLISION}")
    print(f"   ODD Spec:    {MODEL_ODD_SPEC}")
    print(f"   Evaluator:   {MODEL_EVALUATOR}")
    print(f"   Report:      {MODEL_REPORT}")

    # Find scenarios
    print()
    print("🔍 Scanning for production scenarios...")
    scenarios = find_production_scenarios(
        scenario_filter=args.scenario,
        skip_list=args.skip if args.skip else None,
    )

    if not scenarios:
        print("❌ No production scenarios found in data/production/")
        if args.scenario:
            print(f"   (filter: --scenario {args.scenario})")
        if args.skip:
            print(f"   (skipped: {', '.join(args.skip)})")
        print("Please run extract_windows.py to create data")
        sys.exit(1)

    total_windows = sum(s['windows'] for s in scenarios)
    print(
        f"✅ Found {len(scenarios)} scenarios ({total_windows} total windows)")
    print()
    for scenario in scenarios:
        print(f"  • {scenario['name']:20s} ({scenario['windows']:3d} windows)")

    # Cost estimation
    cost_estimate = estimate_cost(scenarios)
    print()
    print("💰 Cost Estimate:")
    print(f"   Windows:        {cost_estimate['total_windows']}")
    print(f"   Est. tokens:    {cost_estimate['estimated_tokens']:,}")
    print(f"   Est. cost:      ${cost_estimate['estimated_cost_usd']:.2f}")
    print(f"   Per window:     ${cost_estimate['cost_per_window']:.4f}")

    if args.dry_run:
        print()
        print("🔍 DRY RUN - No analysis performed")
        print("Remove --dry-run to execute")
        sys.exit(0)

    # Confirm if not in a script
    if sys.stdin.isatty():
        print()
        response = input(f"Proceed with {len(scenarios)} scenarios? (y/N): ")
        if response.lower() != 'y':
            print("Cancelled")
            sys.exit(0)

    # Build knowledge seed
    knowledge_seed = None
    if not args.no_knowledge:
        print()
        print("📚 Building knowledge seed...")
        knowledge_seed = build_knowledge_seed()
        print(f"   Loaded: {list(knowledge_seed.keys())}")

    # Create timestamp and output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_base = project_root / "data" / "archive" / \
        "analysis_results" / "automated" / timestamp
    output_base.mkdir(parents=True, exist_ok=True)

    print()
    print("=" * 80)
    print("STARTING BATCH ANALYSIS")
    print("=" * 80)
    print(f"  • Scenarios: {len(scenarios)}")
    print(f"  • Total windows: {total_windows}")
    print(f"  • Output: {output_base}")
    print(f"  • Knowledge: {'enabled' if knowledge_seed else 'disabled'}")
    print(f"  • On error: {'continue' if args.continue_on_error else 'stop'}")
    print()

    # Create client
    genai_client = Client(api_key=api_key)

    results = []
    stop_early = False

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

            result = await process_scenario(
                scenario, genai_client, api_key, knowledge_seed
            )
            results.append(result)

            if result['success']:
                # Save individual results
                save_scenario_results(
                    result['data'], result['scenario_name'], output_base, result.get('source_path'))
                if not HAS_TQDM:
                    cost = result.get('cost', 0)
                    tokens = result.get('tokens', 0)
                    print(
                        f"  ✅ Completed: {result['scenario_name']} (${cost:.4f}, {tokens:,} tokens)")
            else:
                print()
                print(f"❌ FAILED: {result['scenario_name']}")
                print(f"   Error: {result['error']}")

                if not args.continue_on_error:
                    print()
                    print(
                        "Stopping on first error (use --continue-on-error to continue)")
                    stop_early = True
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

        # Save batch summary (lighter version for quick review)
        summary_path = output_base / "batch_summary.json"
        summary = {
            'timestamp': timestamp,
            'scenarios_processed': len(results),
            'successful': aggregate['batch_metadata']['successful_scenarios'],
            'failed': aggregate['batch_metadata']['failed_scenarios'],
            'total_windows': aggregate['batch_metadata']['total_windows_analyzed'],
            'total_cost_usd': aggregate['batch_metadata']['total_cost_usd'],
            'compliance': aggregate['aggregate_statistics']['compliance_distribution'],
            'stopped_early': stop_early,
        }
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)

        # Display summary
        meta = aggregate['batch_metadata']
        print()
        print("📊 BATCH SUMMARY:")
        print("-" * 80)
        print(f"  • Total scenarios: {meta['total_scenarios']}")
        print(f"  • Successful: {meta['successful_scenarios']}")
        print(f"  • Failed: {meta['failed_scenarios']}")
        print(f"  • Total windows: {meta['total_windows_analyzed']}")
        print(f"  • Total tokens: {meta['total_tokens_used']:,}")
        print(f"  • Total cost: ${meta['total_cost_usd']:.4f}")
        print(f"  • Avg per window: ${meta['avg_cost_per_window']:.5f}")
        print()
        print("📈 COMPLIANCE DISTRIBUTION:")
        print("-" * 80)
        for status, count in aggregate['aggregate_statistics']['compliance_distribution'].items():
            print(f"  • {status:20s}: {count}")
        print()
        print("💡 OVERALL FINDINGS:")
        print("-" * 80)
        for finding in aggregate['overall_findings']:
            print(f"  • {finding}")

        if aggregate['failed_scenarios']:
            print()
            print("❌ FAILED SCENARIOS:")
            print("-" * 80)
            for fail in aggregate['failed_scenarios']:
                print(f"  • {fail['name']}: {fail['error']}")

        print()
        print("=" * 80)
        if stop_early:
            print("⚠️  BATCH STOPPED EARLY (error encountered)")
        else:
            print("✅ BATCH ANALYSIS COMPLETE")
        print("=" * 80)
        print()
        print(f"📁 Results saved to:")
        print(f"   {output_base}")
        print()
        print(f"   • <scenario>/full_result.json        - Individual scenario results")
        print(f"   • <scenario>/executive_summary.json  - Individual summaries")
        print(f"   • aggregate_report.json              - Batch aggregate report")
        print(f"   • batch_summary.json                 - Quick summary")

        # Exit with error if any scenarios failed
        if meta['failed_scenarios'] > 0:
            sys.exit(1)

    except Exception as e:
        print()
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Clean up client
        try:
            await genai_client.aio.aclose()
        except Exception:
            pass
        # Suppress cleanup warnings
        sys.stderr = open(os.devnull, 'w')


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Cancelled by user")
        sys.exit(0)
