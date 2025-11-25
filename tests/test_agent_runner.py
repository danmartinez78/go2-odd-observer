#!/usr/bin/env python3
"""
Interactive Agent Test Runner

Allows manual testing of individual agents with custom configuration:
- Select from available datasets (production, test_data)
- Choose which agent(s) to test  
- Pick model for testing
- Run and view results

Usage:
    python tests/test_agent_runner.py
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Optional
from dotenv import load_dotenv

# Load environment
load_dotenv()


def find_scenarios() -> List[Tuple[str, Path, int]]:
    """
    Find all available scenarios across production and test data.

    Returns:
        List of (name, path, window_count) tuples
    """
    scenarios = []
    data_dir = Path("data")

    # Search production/ and test/ subdirectories
    search_dirs = [
        data_dir / "production",
        data_dir / "test",
    ]

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue

        # Standard structure for both production and test directories
        for scenario_dir in sorted(search_dir.iterdir()):
            if not scenario_dir.is_dir():
                continue
            # Skip special directories
            if scenario_dir.name in ['.', '..', 'images'] or scenario_dir.name.startswith('.'):
                continue

            # Check for index file
            index_files = list(scenario_dir.glob("index_*.csv"))
            if not index_files:
                continue

            # Count windows
            with open(index_files[0]) as f:
                window_count = len(f.readlines()) - 1  # Subtract header

            # Get relative path for display
            rel_path = scenario_dir.relative_to(data_dir)

            scenarios.append((str(rel_path), scenario_dir, window_count))

    return scenarios


def select_scenario(scenarios: List[Tuple[str, Path, int]]) -> Optional[Path]:
    """Prompt user to select a scenario."""

    print("\n" + "=" * 80)
    print("AVAILABLE SCENARIOS")
    print("=" * 80)

    for i, (name, _, window_count) in enumerate(scenarios, 1):
        print(f"{i:2d}. {name:50s} ({window_count:3d} windows)")

    print()
    try:
        choice = input("Select scenario number (or 'q' to quit): ").strip()
        if choice.lower() == 'q':
            return None

        idx = int(choice) - 1
        if 0 <= idx < len(scenarios):
            return scenarios[idx][1]
        else:
            print("❌ Invalid selection")
            return None
    except (ValueError, KeyboardInterrupt):
        return None


def select_agent() -> Optional[str]:
    """Prompt user to select agent(s) to test."""

    agents = {
        '1': ('perception', 'Perception (Camera + LiDAR BEV)'),
        '2': ('motion', 'Motion (IMU Analysis)'),
        '3': ('collision', 'Collision (Binary Detection)'),
        '4': ('odd_spec', 'ODD Specification'),
        '5': ('all', 'All Agents (Sequential)'),
    }

    print("\n" + "=" * 80)
    print("SELECT AGENT TO TEST")
    print("=" * 80)

    for key, (_, description) in agents.items():
        print(f"{key}. {description}")

    print()
    try:
        choice = input("Select agent (or 'q' to quit): ").strip()
        if choice.lower() == 'q':
            return None

        if choice in agents:
            return agents[choice][0]
        else:
            print("❌ Invalid selection")
            return None
    except KeyboardInterrupt:
        return None


def select_model() -> Optional[str]:
    """Prompt user to select model."""

    models = {
        '1': ('gemini-2.5-flash', '2.5 Flash (Fast, Recommended)'),
        '2': ('gemini-2.5-flash-lite', '2.5 Flash Lite (Economical)'),
        '3': ('gemini-2.5-pro', '2.5 Pro (Most Capable)'),
        '4': ('gemini-3-pro', '3 Pro (Latest)'),
        '5': ('gemini-robotics-er-1.5-preview', 'Robotics ER 1.5 (Experimental)'),
    }

    print("\n" + "=" * 80)
    print("SELECT MODEL")
    print("=" * 80)

    for key, (model, description) in models.items():
        print(f"{key}. {description}")

    print()
    try:
        choice = input(
            "Select model (or press Enter for default '2.5-flash'): ").strip()

        if not choice:  # Default
            return 'gemini-2.5-flash'

        if choice.lower() == 'q':
            return None

        if choice in models:
            return models[choice][0]
        else:
            print("❌ Invalid selection")
            return None
    except KeyboardInterrupt:
        return None


def run_agent_test(
    agent_type: str,
    scenario_path: Path,
    model: str
) -> bool:
    """
    Run the selected agent test using subprocess.

    Returns:
        True if test succeeded, False otherwise
    """

    print("\n" + "=" * 80)
    print(f"RUNNING: {agent_type.upper()} Agent")
    print("=" * 80)
    print(f"Scenario: {scenario_path.name}")
    print(f"Model: {model}")
    print("=" * 80 + "\n")

    try:
        if agent_type == 'all':
            # Run all agents sequentially
            print("\n🔄 Running all agents sequentially...\n")

            for agent in ['perception', 'motion', 'collision', 'odd_spec']:
                success = run_agent_test(agent, scenario_path, model)
                if not success:
                    print(f"\n⚠️  {agent} agent failed, but continuing...\n")

            return True

        # Map agent type to test script
        test_scripts = {
            'perception': 'tests/test_perception_agent.py',
            'motion': 'tests/test_motion_agent.py',
            'collision': 'tests/test_collision_agent.py',
            'odd_spec': 'tests/test_odd_spec_agent.py',
        }

        script = test_scripts.get(agent_type)
        if not script:
            print(f"❌ Unknown agent type: {agent_type}")
            return False

        # Build command
        cmd = [
            sys.executable,
            script,
            '--model', model,
        ]

        # Add scenario for agents that need it (not odd_spec)
        if agent_type != 'odd_spec':
            cmd.extend(['--scenario', str(scenario_path)])

        # Run the test script
        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent.parent,  # Run from project root
            capture_output=False,  # Show output directly
            text=True
        )

        return result.returncode == 0

    except Exception as e:
        print(f"\n❌ Error running {agent_type} agent: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main interactive test runner."""

    # Check API key
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY not set in environment")
        print("Please create a .env file with: GOOGLE_API_KEY=your-key")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("AGENT TEST RUNNER")
    print("=" * 80)
    print("Interactive testing for ODD analysis agents")
    print()

    # Find available scenarios
    print("🔍 Scanning for scenarios...")
    scenarios = find_scenarios()

    if not scenarios:
        print("❌ No scenarios found in data/production/ or data/test/")
        print("Please run extract_windows.py to create scenario data")
        sys.exit(1)

    print(f"✅ Found {len(scenarios)} scenarios")

    # Select scenario
    scenario_path = select_scenario(scenarios)
    if scenario_path is None:
        print("\n👋 Cancelled")
        return

    # Select agent
    agent_type = select_agent()
    if agent_type is None:
        print("\n👋 Cancelled")
        return

    # Select model
    model = select_model()
    if model is None:
        print("\n👋 Cancelled")
        return

    # Run test
    success = run_agent_test(agent_type, scenario_path, model)

    # Summary
    print("\n" + "=" * 80)
    if success:
        print("✅ TEST COMPLETED")
    else:
        print("❌ TEST FAILED")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Cancelled by user")
        sys.exit(0)
