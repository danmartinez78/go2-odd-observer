#!/usr/bin/env python3
"""
Create Test Sets from Production Data

Extracts 2-window subsets from production scenarios to create small test datasets.
Copies all necessary files (motion, camera, BEV channels) and creates a CSV index.

Usage:
    python scripts/create_test_sets.py --source data/production/sim_1_0 --windows 10,11 --output test/sim_test_w010_w011
    python scripts/create_test_sets.py --source data/production/sim_1_0 --windows 30-31 --output test/sim_test_w030_w031
    
Interactive mode:
    python scripts/create_test_sets.py
"""

import argparse
import csv
import shutil
from pathlib import Path
from typing import List, Tuple


def parse_window_range(window_spec: str) -> List[int]:
    """Parse window specification (e.g., '10,11' or '10-11' or '10' for single)."""
    if '-' in window_spec:
        start, end = window_spec.split('-')
        return list(range(int(start), int(end) + 1))
    elif ',' in window_spec:
        return [int(w.strip()) for w in window_spec.split(',')]
    else:
        return [int(window_spec)]


def find_production_scenarios() -> List[Path]:
    """Find all production scenario directories."""
    prod_dir = Path("data/production")
    if not prod_dir.exists():
        return []

    scenarios = []
    for scenario_dir in sorted(prod_dir.iterdir()):
        if scenario_dir.is_dir() and not scenario_dir.name.startswith('.'):
            index_files = list(scenario_dir.glob("index_*.csv"))
            if index_files:
                scenarios.append(scenario_dir)

    return scenarios


def read_index_csv(index_path: Path) -> List[dict]:
    """Read the index CSV and return list of window metadata."""
    with open(index_path, 'r') as f:
        reader = csv.DictReader(f)
        return list(reader)


def create_test_set(
    source_scenario: Path,
    window_ids: List[int],
    output_dir: Path,
    test_set_name: str = None
) -> bool:
    """
    Create a test set by copying specified windows from source scenario.

    Args:
        source_scenario: Path to source production scenario
        window_ids: List of window IDs to extract (e.g., [10, 11])
        output_dir: Path to output test directory
        test_set_name: Name for test set (defaults to output dir name)

    Returns:
        True if successful, False otherwise
    """
    # Find source index file
    index_files = list(source_scenario.glob("index_*.csv"))
    if not index_files:
        print(f"❌ No index file found in {source_scenario}")
        return False

    source_index = index_files[0]

    # Read source index
    all_windows = read_index_csv(source_index)

    # Filter to selected windows
    selected_windows = [w for w in all_windows if int(
        w['window_id']) in window_ids]

    if len(selected_windows) != len(window_ids):
        print(
            f"❌ Could not find all requested windows. Found {len(selected_windows)}/{len(window_ids)}")
        print(f"   Available: {[w['window_id'] for w in all_windows]}")
        return False

    # Create output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine test set name
    if test_set_name is None:
        test_set_name = output_dir.name

    print(f"\n📦 Creating test set: {test_set_name}")
    print(f"   Source: {source_scenario.name}")
    print(f"   Windows: {window_ids}")
    print(f"   Output: {output_dir}")

    # Copy files for each window
    copied_files = []
    for window in selected_windows:
        window_id = window['window_id']

        # List of files to copy (based on CSV columns)
        file_fields = [
            'motion_path',
            'cam_image_path',
            'bev_occupancy_path',
            'bev_height_path',
            'bev_roughness_path'
        ]

        for field in file_fields:
            if field in window:
                src_file = source_scenario / window[field]
                if src_file.exists():
                    dst_file = output_dir / src_file.name
                    shutil.copy2(src_file, dst_file)
                    copied_files.append(dst_file.name)
                else:
                    print(f"   ⚠️  Missing: {src_file.name}")

    # Create new index CSV
    output_index = output_dir / f"index_{test_set_name}.csv"
    with open(output_index, 'w', newline='') as f:
        # Use same fields as source
        fieldnames = list(selected_windows[0].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(selected_windows)

    print(f"\n✅ Test set created successfully!")
    print(f"   Files copied: {len(copied_files)}")
    print(f"   Index: {output_index.name}")
    print(f"   Windows: {len(selected_windows)}")

    return True


def interactive_mode():
    """Interactive test set creation."""
    print("\n" + "=" * 80)
    print("CREATE TEST SETS FROM PRODUCTION DATA")
    print("=" * 80)

    # Find production scenarios
    scenarios = find_production_scenarios()
    if not scenarios:
        print("❌ No production scenarios found in data/production/")
        return False

    print(f"\n✅ Found {len(scenarios)} production scenario(s)\n")

    # Select source scenario
    print("Available scenarios:")
    for i, scenario in enumerate(scenarios, 1):
        index_file = list(scenario.glob("index_*.csv"))[0]
        windows = read_index_csv(index_file)
        print(f"{i}. {scenario.name:30s} ({len(windows)} windows)")

    try:
        choice = int(input("\nSelect scenario number: ").strip())
        if choice < 1 or choice > len(scenarios):
            print("❌ Invalid selection")
            return False

        source_scenario = scenarios[choice - 1]
    except (ValueError, KeyboardInterrupt):
        print("\n👋 Cancelled")
        return False

    # Show available windows
    index_file = list(source_scenario.glob("index_*.csv"))[0]
    windows = read_index_csv(index_file)
    print(f"\nAvailable windows: 0 to {len(windows) - 1}")

    # Get window selection
    try:
        window_spec = input(
            "\nEnter window IDs (e.g., '10,11' or '10-11'): ").strip()
        window_ids = parse_window_range(window_spec)

        if len(window_ids) < 1:
            print("❌ Must select at least 1 window")
            return False

        if len(window_ids) > 10:
            confirm = input(
                f"⚠️  You selected {len(window_ids)} windows. Continue? [y/N]: ")
            if confirm.lower() != 'y':
                print("👋 Cancelled")
                return False

    except (ValueError, KeyboardInterrupt):
        print("\n👋 Cancelled")
        return False

    # Get output directory
    try:
        default_name = f"test_{source_scenario.name}_w{'_w'.join(f'{w:03d}' for w in window_ids)}"
        output_spec = input(
            f"\nOutput directory [data/test/{default_name}]: ").strip()

        if not output_spec:
            output_dir = Path("data/test") / default_name
        else:
            output_dir = Path(output_spec)
            if not output_dir.is_absolute():
                output_dir = Path("data") / output_dir

        # Check if exists
        if output_dir.exists():
            confirm = input(
                f"⚠️  {output_dir} already exists. Overwrite? [y/N]: ")
            if confirm.lower() != 'y':
                print("👋 Cancelled")
                return False
            shutil.rmtree(output_dir)

    except KeyboardInterrupt:
        print("\n👋 Cancelled")
        return False

    # Create test set
    return create_test_set(source_scenario, window_ids, output_dir)


def main():
    parser = argparse.ArgumentParser(
        description="Create test sets from production data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python scripts/create_test_sets.py
  
  # Command-line mode
  python scripts/create_test_sets.py --source data/production/sim_1_0 --windows 10,11 --output data/test/sim_test_w010_w011
  python scripts/create_test_sets.py --source data/production/sim_1_0 --windows 30-31 --output data/test/sim_test_w030_w031
  python scripts/create_test_sets.py --source data/production/sim_1_0 --windows 50,51 --output data/test/sim_test_w050_w051
        """
    )

    parser.add_argument(
        '--source',
        type=str,
        help='Source production scenario directory'
    )
    parser.add_argument(
        '--windows',
        type=str,
        help='Window IDs to extract (e.g., "10,11" or "10-11")'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output test set directory'
    )
    parser.add_argument(
        '--name',
        type=str,
        help='Test set name (defaults to output dir name)'
    )

    args = parser.parse_args()

    # Check if command-line mode or interactive
    if args.source and args.windows and args.output:
        # Command-line mode
        source_scenario = Path(args.source)
        if not source_scenario.exists():
            print(f"❌ Source scenario not found: {source_scenario}")
            return 1

        window_ids = parse_window_range(args.windows)
        output_dir = Path(args.output)

        success = create_test_set(
            source_scenario,
            window_ids,
            output_dir,
            test_set_name=args.name
        )

        return 0 if success else 1

    else:
        # Interactive mode
        success = interactive_mode()
        return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
