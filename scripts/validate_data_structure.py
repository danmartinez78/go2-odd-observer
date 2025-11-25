#!/usr/bin/env python3
"""
Validate data directory structure and naming conventions.

This script checks that:
1. Directory names match the scenario names in filenames
2. Index files exist and have correct naming
3. All expected file types are present

Usage:
    python scripts/validate_data_structure.py [directory]
    
    # Validate all production data
    python scripts/validate_data_structure.py data/processed/production
    
    # Validate all test data
    python scripts/validate_data_structure.py data/processed/test_data
    
    # Validate everything
    python scripts/validate_data_structure.py data/processed
"""

import argparse
import sys
from pathlib import Path
from typing import List, Tuple


def validate_scenario(scenario_path: Path) -> Tuple[bool, List[str]]:
    """
    Validate a single scenario directory.

    Returns:
        (is_valid, list_of_issues)
    """
    issues = []
    scenario_name = scenario_path.name

    # Skip metadata files
    if scenario_path.is_file() or scenario_name.startswith('.'):
        return True, []

    # Check for index file
    index_files = list(scenario_path.glob("index_*.csv"))
    if not index_files:
        issues.append(f"❌ No index file found")
        return False, issues

    index_file = index_files[0]
    index_name = index_file.stem.replace('index_', '')

    # CRITICAL CHECK: Directory name must match index file name
    if index_name != scenario_name:
        issues.append(
            f"❌ NAMING MISMATCH: Directory '{scenario_name}' but index file is 'index_{index_name}.csv'"
        )

    # Check for motion files
    motion_files = list(scenario_path.glob("motion_*.json"))
    if not motion_files:
        issues.append(f"⚠️  No motion files found")
    else:
        # Check if motion filenames match directory name
        sample_motion = motion_files[0].name
        # Extract scenario name from: motion_collection_20251122_173442_chunk_01_w000.json
        parts = sample_motion.replace('.json', '').rsplit('_w', 1)
        if len(parts) == 2:
            motion_scenario = parts[0].replace('motion_', '')
            if motion_scenario != scenario_name:
                issues.append(
                    f"❌ NAMING MISMATCH: Directory '{scenario_name}' but motion files use '{motion_scenario}'"
                )

    # Check for camera files
    cam_files = list(scenario_path.glob("cam_*.png"))
    if not cam_files:
        issues.append(f"⚠️  No camera files found")

    # Check for BEV files
    bev_files = list(scenario_path.glob("bev_*.png"))
    if not bev_files:
        issues.append(f"⚠️  No BEV files found")

    return len(issues) == 0, issues


def validate_directory(base_path: Path, recursive: bool = True) -> None:
    """Validate all scenarios in a directory."""

    if not base_path.exists():
        print(f"❌ Directory not found: {base_path}")
        sys.exit(1)

    print(f"\n{'='*80}")
    print(f"Validating: {base_path}")
    print(f"{'='*80}\n")

    total_scenarios = 0
    valid_scenarios = 0
    all_issues = []

    # Find all scenario directories
    if base_path.is_dir():
        if recursive:
            # Check immediate children and subdirectories
            scenario_dirs = [
                d for d in base_path.rglob("*")
                if d.is_dir() and not d.name.startswith('.') and list(d.glob("index_*.csv"))
            ]
        else:
            scenario_dirs = [
                d for d in base_path.iterdir()
                if d.is_dir() and not d.name.startswith('.') and list(d.glob("index_*.csv"))
            ]
    else:
        print(f"❌ Not a directory: {base_path}")
        sys.exit(1)

    if not scenario_dirs:
        print(f"⚠️  No scenarios found (directories with index files)")
        return

    print(f"Found {len(scenario_dirs)} scenarios to validate\n")

    for scenario_path in sorted(scenario_dirs):
        total_scenarios += 1
        is_valid, issues = validate_scenario(scenario_path)

        rel_path = scenario_path.relative_to(base_path)

        if is_valid:
            print(f"✅ {rel_path}")
            valid_scenarios += 1
        else:
            print(f"❌ {rel_path}")
            for issue in issues:
                print(f"   {issue}")
                all_issues.append((rel_path, issue))

    # Summary
    print(f"\n{'='*80}")
    print(f"VALIDATION SUMMARY")
    print(f"{'='*80}")
    print(f"Total scenarios: {total_scenarios}")
    print(
        f"Valid: {valid_scenarios} ({valid_scenarios/total_scenarios*100:.1f}%)")
    print(f"Invalid: {total_scenarios - valid_scenarios}")

    if all_issues:
        print(f"\n⚠️  ISSUES FOUND ({len(all_issues)}):")
        print(f"{'='*80}")
        for path, issue in all_issues:
            print(f"{path}")
            print(f"  {issue}")
        print(f"\n❌ Validation FAILED - please fix naming mismatches above")
        print(f"\nTo fix naming issues:")
        print(f"  1. Rename directories to match their index file names")
        print(f"  2. Or regenerate data with correct --run-id parameter")
        sys.exit(1)
    else:
        print(f"\n✅ All scenarios VALID - naming conventions are correct!")


def main():
    parser = argparse.ArgumentParser(
        description="Validate data directory structure and naming conventions"
    )
    parser.add_argument(
        "directory",
        type=str,
        nargs='?',
        default="data/production",
        help="Directory to validate (default: data/production)"
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Only check immediate children, not subdirectories"
    )

    args = parser.parse_args()

    base_path = Path(args.directory)
    validate_directory(base_path, recursive=not args.no_recursive)


if __name__ == "__main__":
    main()
