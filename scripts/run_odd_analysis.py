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
from odd_agents.odd_definition import DEFAULT_ODD_DESCRIPTION, ODD_DEFINITION_VERSION
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

# Phase 1.4.4 - Type-driven COD construction
# Using 2.5-flash-lite for all agents (cheaper, testing reliability)
# NOTE: 2.5-flash-lite may not reliably call tools - monitor carefully
MODEL_PERCEPTION = "gemini-2.5-pro"
MODEL_MOTION = "gemini-2.5-flash"
MODEL_COLLISION = "gemini-2.5-flash"
MODEL_ODD_SPEC = "gemini-2.5-pro"
MODEL_EVALUATOR = "gemini-2.5-pro"
# Upgraded from flash-lite for reliable tool calling
MODEL_REPORT = "gemini-2.5-flash"

# ============================================================================
# ODD DESCRIPTION (Centralized in odd_agents/odd_definition.py)
# ============================================================================
# Imported from odd_agents.odd_definition - see that file for the full definition
# Version: {ODD_DEFINITION_VERSION} - includes human/animal proximity, carpet, no collision axis


def find_scenarios():
    """Find all available scenarios (production + test datasets)."""
    scenarios = []
    data_dir = project_root / "data"

    # Search production/, production/chunks/, and test/ subdirectories
    search_dirs = [
        ("production", data_dir / "production"),
        ("chunks", data_dir / "production" / "chunks"),
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
    # Phase 1.4.4: Check report.compliance_summary first (new flat structure)
    if 'report' in result and 'compliance_summary' in result['report']:
        return result['report']['compliance_summary']

    # Fallback: Check full_analysis.compliance_verdict (evaluator output)
    if 'full_analysis' in result and 'compliance_verdict' in result['full_analysis']:
        return result['full_analysis']['compliance_verdict']

    # Old Phase 1.4.3 structure
    if 'full_analysis' in result and 'odd_compliance' in result['full_analysis']:
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
    """Display executive summary and compliance status.

    Supports multiple report schema versions:
    - v9.0.0 (current): compliance, executive_summary, key_findings dict, scenario_metadata dict
    - v8.x: verdict, narrative dict
    - Legacy: executive_summary string, key_findings list
    """
    # Phase 1.4.4: handle both flat structure and old nested structure
    if 'report' in result:
        report = result['report']
        # Handle nested JSON string from ReportAgent
        if isinstance(report, dict) and 'result' in report:
            try:
                report = json.loads(report['result'])
            except (json.JSONDecodeError, TypeError):
                pass
    else:
        report = result  # Flat structure from Phase 1.4.4

    compliance_data = get_compliance_data(result)
    analysis_meta = result.get('analysis_metadata', {})

    print("\n" + "=" * 80)
    print("EXECUTIVE SUMMARY")
    print("=" * 80)
    print()
    # Phase 1.4.6: Support v9.0.0 schema (compliance + executive_summary)
    if 'executive_summary' in report and report.get('executive_summary'):
        # v9.0.0: Direct executive_summary field
        print(report['executive_summary'])
    elif 'verdict' in report and isinstance(report['verdict'], dict):
        # v8.x: verdict.summary is the executive summary
        print(report['verdict'].get('summary', 'N/A'))
    elif 'compliance' in report and isinstance(report['compliance'], dict):
        # v9.0.0 fallback: compliance.summary
        print(report['compliance'].get('summary', 'N/A'))
    else:
        print('N/A')
    print()

    print("=" * 80)
    print("KEY FINDINGS")
    print("=" * 80)
    # Phase 1.4.6: Support v9.0.0 key_findings dict, v8.x narrative, or legacy list
    if 'key_findings' in report and isinstance(report['key_findings'], dict):
        # v9.0.0: key_findings is a dict with perception, motion, safety, temporal_trends
        key_findings = report['key_findings']
        sections = [
            ('Perception', key_findings.get('perception')),
            ('Motion', key_findings.get('motion')),
            ('Safety', key_findings.get('safety')),
            ('Temporal Trends', key_findings.get('temporal_trends')),
        ]
        for name, content in sections:
            if content:
                print(f"\n• {name}: {content}")
    elif 'narrative' in report and isinstance(report['narrative'], dict):
        # v8.x: narrative dict
        narrative = report['narrative']
        sections = [
            ('Scenario', narrative.get('scenario')),
            ('Perception', narrative.get('perception')),
            ('Motion', narrative.get('motion')),
            ('Safety', narrative.get('safety')),
            ('Temporal', narrative.get('temporal')),
        ]
        for name, content in sections:
            if content:
                print(f"\n• {name}: {content}")
    elif 'key_findings' in report and isinstance(report['key_findings'], list):
        # Legacy: key_findings as list
        for i, finding in enumerate(report['key_findings'], 1):
            print(f"\n{i}. {finding}")
    else:
        print("\nNo key findings available.")

    print()
    print("=" * 80)
    print("SCENARIO METADATA")
    print("=" * 80)

    # Phase 1.4.6: Try v9.0.0 scenario_metadata first, then fall back to extracting from full_analysis
    if 'scenario_metadata' in report and isinstance(report['scenario_metadata'], dict):
        # v9.0.0: scenario_metadata dict
        scenario_meta = report['scenario_metadata']
        print(
            f"  • Windows analyzed: {scenario_meta.get('windows_analyzed', 'N/A')}")
        print(f"  • Environment: {scenario_meta.get('environment', 'N/A')}")
        print(f"  • Data Quality: {scenario_meta.get('data_quality', 'N/A')}")
        # v9.1.0: Data source (sim vs real)
        data_source = scenario_meta.get('data_source', 'N/A')
        print(f"  • Data Source: {data_source}")
    else:
        # Legacy: extract from full_analysis
        full_analysis = result.get('full_analysis', {})
        cod_region = full_analysis.get('cod_region', {})
        region_metrics = full_analysis.get('region_metrics', {})

        total_windows = region_metrics.get('total_windows', 'N/A')
        print(f"  • Windows analyzed: {total_windows}")

        # Try to get environment info from COD region
        env_type = cod_region.get('environment_type', {})
        if isinstance(env_type, dict):
            env_labels = [k for k in env_type.keys() if k != 'type']
            env_str = ', '.join(env_labels) if env_labels else 'N/A'
        else:
            env_str = str(env_type) if env_type else 'N/A'
        print(f"  • Environment: {env_str}")

        lighting = cod_region.get('lighting_conditions', {})
        if isinstance(lighting, dict):
            light_labels = [k for k in lighting.keys() if k != 'type']
            light_str = ', '.join(light_labels) if light_labels else 'N/A'
        else:
            light_str = str(lighting) if lighting else 'N/A'
        print(f"  • Lighting: {light_str}")

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
        knowledge_refs = analysis_meta.get('knowledge_refs') or result.get(
            'pipeline_metadata', {}).get('knowledge_refs')
        if knowledge_refs:
            print("  • Knowledge references:")
            for k, v in knowledge_refs.items():
                print(f"    - {k}: {v}")

    print()
    print("=" * 80)
    print("ODD COMPLIANCE")
    print("=" * 80)
    # Phase 1.4.6: Support v9.0.0 compliance object, v8.x verdict, or legacy overall
    report_compliance = report.get('compliance', {})
    if isinstance(report_compliance, dict) and report_compliance:
        # v9.0.0: Use compliance from report
        overall = report_compliance.get('status', 'UNKNOWN')
        confidence = report_compliance.get('confidence', 'N/A')
        summary = report_compliance.get('summary', 'N/A')
        print(f"  • Status: {overall}")
        print(f"  • Confidence: {confidence}")
        if summary != 'N/A':
            print(f"  • Summary: {summary}")
    else:
        # Legacy/v8.x: Use compliance_data from full_analysis
        overall = compliance_data.get(
            'verdict', compliance_data.get('overall', 'UNKNOWN'))
        rationale = compliance_data.get('rationale', 'N/A')
        temporal_stability = compliance_data.get('temporal_stability', 'N/A')
        print(f"  • Overall: {overall}")
        print(f"  • Temporal Stability: {temporal_stability}")
        if rationale != 'N/A':
            print(f"  • Rationale: {rationale}")

    # Critical axes from compliance_data (always from full_analysis)
    critical_axes = compliance_data.get('critical_axes', [])
    print(f"  • Critical Axes: {len(critical_axes)}")

    if critical_axes:
        print()
        print("⚠️  CRITICAL AXES (Violations):")
        for axis in critical_axes:
            print(f"    • {axis}")

    # Display issues if present (v9.0.0)
    issues = report.get('issues', [])
    if issues:
        print()
        print("=" * 80)
        print("IDENTIFIED ISSUES")
        print("=" * 80)
        for i, issue in enumerate(issues, 1):
            if isinstance(issue, dict):
                severity = issue.get('severity', 'unknown')
                desc = issue.get('description', str(issue))
                print(f"\n{i}. [{severity.upper()}] {desc}")
            else:
                print(f"\n{i}. {issue}")

    print()
    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    recommendations = report.get('recommendations', [])
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            if isinstance(rec, dict):
                priority = rec.get('priority', 'medium')
                action = rec.get('action', str(rec))
                print(f"\n{i}. [{priority.upper()}] {action}")
            else:
                print(f"\n{i}. {rec}")
    else:
        print("\nNo recommendations provided.")


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
    parser.add_argument(
        "--no-knowledge",
        action="store_true",
        help="Disable knowledge seeding (fundamentals + sensors + Go2 profile are seeded by default)",
    )
    parser.add_argument(
        "--knowledge-manifest",
        type=str,
        help="Path to JSON file containing a manifest dict to seed (overrides defaults if provided)",
    )
    parser.add_argument(
        "--knowledge-robot",
        type=str,
        help="Override robot profile artifact (e.g., artifact:robot_go2_profile_v1)",
    )
    parser.add_argument(
        "--knowledge-app",
        type=str,
        help="Override app profile artifact (optional)",
    )
    args = parser.parse_args()

    # Load environment
    load_dotenv()
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY not set in environment")
        print("Please create a .env file with: GOOGLE_API_KEY=your-key")
        sys.exit(1)

    # Build knowledge seed (enabled by default, use --no-knowledge to disable)
    knowledge_seed = None
    if not args.no_knowledge:
        from odd_agents.knowledge import (
            build_reference_manifest,
            default_fundamentals_sections,
            default_sensor_sections,
            build_memory_seed_entries,
        )

        if args.knowledge_manifest:
            try:
                with open(args.knowledge_manifest) as f:
                    manifest = json.load(f)
            except Exception as e:
                print(f"❌ Failed to load knowledge manifest JSON: {e}")
                sys.exit(1)
        else:
            # Defaults: core fundamentals + sensors + Go2 profile
            fundamentals_artifact = "artifact:odd_cod_fundamentals_v1"
            sensors_artifact = "artifact:sensor_interpretation_core_v1"
            robot_artifact = args.knowledge_robot or "artifact:robot_go2_profile_v1"
            app_artifact = args.knowledge_app or None

            manifest = build_reference_manifest(
                fundamentals_artifact=fundamentals_artifact,
                sensors_artifact=sensors_artifact,
                robot_artifact=robot_artifact,
                app_artifact=app_artifact,
            )

        fundamentals_sections = default_fundamentals_sections(
            fundamentals_artifact=manifest.get(
                "fundamentals", "artifact:odd_cod_fundamentals_v1")
        ) if "fundamentals" in manifest else None
        sensor_sections = default_sensor_sections(
            sensors_artifact=manifest.get(
                "sensors", "artifact:sensor_interpretation_core_v1"),
            sensors_overlay_artifact=manifest.get("sensors_overlay"),
        ) if "sensors" in manifest else None

        knowledge_seed = build_memory_seed_entries(
            manifest=manifest,
            fundamentals_sections=fundamentals_sections,
            sensor_sections=sensor_sections,
        )

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
            knowledge_seed=knowledge_seed,
            debug=True,
        )

        if result:
            # Save results
            if args.output_dir:
                # Use specified output directory
                output_base = Path(args.output_dir)
                output_dir = output_base / scenario_name
            else:
                # Use default timestamp-based directory
                output_base = project_root / "data" / "development" / \
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
