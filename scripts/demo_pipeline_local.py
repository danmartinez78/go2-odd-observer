"""
Demo Pipeline - Local Testing

Demonstrates the ODD/COD analysis pipeline with placeholder data,
without requiring actual ROS bags or LLM agents.

This script validates the data flow and distance metrics before
integrating with Kaggle/ADK agents.
"""

import sys
from pathlib import Path
import json
import numpy as np
import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from odd_cod import (
    OddSpec,
    build_cod_vector,
    compute_window_distance,
    compute_window_odd_status,
    compute_scenario_distance,
    classify_scenario,
    compute_time_fractions,
)
from odd_cod.config_example import create_basic_indoor_odd


def load_window_data(run_dir: Path) -> pd.DataFrame:
    """Load window index from processed run directory."""
    # Try to find any index CSV file in the directory
    index_files = list(run_dir.glob("index_*.csv"))
    
    if not index_files:
        print(f"Warning: No index file found in {run_dir}")
        return pd.DataFrame()
    
    index_path = index_files[0]
    return pd.read_csv(index_path)


def fake_motion_agent_tags(motion_path: Path) -> dict:
    """
    Simulate Motion Agent analysis with simple heuristics.
    
    In production, this would call Gemini with the motion JSON.
    """
    with open(motion_path, 'r') as f:
        motion_data = json.load(f)
    
    # Simple heuristics
    avg_speed = np.mean(motion_data.get("odom_vx", [0.0]))
    max_speed = np.max(np.abs(motion_data.get("odom_vx", [0.0])))
    
    rolls = motion_data.get("roll", [0.0])
    pitches = motion_data.get("pitch", [0.0])
    max_roll_pitch = max(np.max(np.abs(rolls)), np.max(np.abs(pitches)))
    
    # Compute tracking error
    cmd_vx = np.array(motion_data.get("cmd_vx", [0.0]))
    odom_vx = np.array(motion_data.get("odom_vx", [0.0]))
    tracking_error = np.mean(np.abs(cmd_vx - odom_vx))
    
    return {
        "avg_forward_speed": float(avg_speed),
        "max_forward_speed": float(max_speed),
        "max_abs_roll_pitch_deg": float(max_roll_pitch),
        "tracking_error": float(tracking_error),
        "motion_label": "smooth" if tracking_error < 0.1 else "dynamic",
    }


def fake_image_agent_tags(cam_path: Path) -> dict:
    """
    Simulate Image Agent analysis.
    
    In production, this would call Gemini vision with the camera image.
    """
    # Placeholder: assume good indoor conditions
    return {
        "lighting_class": "bright",
        "humans_visible": False,
        "humans_very_close": False,
        "environment_type": "indoor_office",
    }


def fake_lidar_agent_tags(bev_path: Path) -> dict:
    """
    Simulate LiDAR Agent analysis.
    
    In production, this would call Gemini vision with the BEV image.
    """
    # Placeholder: assume smooth terrain
    return {
        "terrain_roughness_class": "smooth",
        "terrain_roughness_score": 0.1,
        "obstacle_density": "low",
    }


def fake_collision_agent_tags(motion_tags: dict) -> dict:
    """
    Simulate Collision Agent analysis.
    
    In production, this would use multi-modal analysis.
    """
    # Simple heuristic: check for tracking errors
    tracking_error = motion_tags.get("tracking_error", 0.0)
    
    return {
        "collision_suspected": tracking_error > 0.5,
        "collision_confidence": min(1.0, tracking_error),
        "collision_type": "unknown",
    }


def analyze_window(
    window_row: pd.Series,
    run_dir: Path,
    odd_spec: OddSpec,
) -> dict:
    """
    Analyze a single window with fake agents.
    
    Returns window analysis results.
    """
    # Load and analyze motion
    motion_path = run_dir / window_row["motion_path"]
    motion_tags = fake_motion_agent_tags(motion_path)
    
    # Analyze camera
    cam_path = run_dir / window_row["cam_image_path"]
    image_tags = fake_image_agent_tags(cam_path)
    
    # Analyze LiDAR
    bev_path = run_dir / window_row["bev_image_path"]
    lidar_tags = fake_lidar_agent_tags(bev_path)
    
    # Check for collision
    collision_tags = fake_collision_agent_tags(motion_tags)
    
    # Merge all tags
    merged_tags = {
        **motion_tags,
        **image_tags,
        **lidar_tags,
        **collision_tags,
    }
    
    # Convert to COD vector
    cod_vector = build_cod_vector(merged_tags, odd_spec)
    
    # Compute distance
    window_distance, axis_distances, axis_statuses = compute_window_distance(
        cod_vector, odd_spec
    )
    
    # Determine ODD status
    odd_status = compute_window_odd_status(axis_statuses)
    
    return {
        "window_id": window_row["window_id"],
        "tags": merged_tags,
        "cod_vector": cod_vector,
        "distance": window_distance,
        "axis_distances": axis_distances,
        "axis_statuses": axis_statuses,
        "odd_status": odd_status,
    }


def analyze_scenario(run_dir: Path, odd_spec: OddSpec) -> dict:
    """
    Analyze a complete scenario.
    """
    print(f"\nAnalyzing scenario: {run_dir.name}")
    print("=" * 60)
    
    # Load window index
    index_df = load_window_data(run_dir)
    
    if index_df.empty:
        print("No windows found!")
        return {}
    
    print(f"Found {len(index_df)} windows")
    
    # Analyze each window
    window_results = []
    for _, window_row in index_df.iterrows():
        result = analyze_window(window_row, run_dir, odd_spec)
        window_results.append(result)
        
        print(f"\nWindow {result['window_id']}:")
        print(f"  Distance: {result['distance']:.3f}")
        print(f"  ODD Status: {result['odd_status']}")
        print(f"  Speed: {result['tags']['avg_forward_speed']:.2f} m/s")
        print(f"  Roll/Pitch: {result['tags']['max_abs_roll_pitch_deg']:.1f}°")
        print(f"  Collision: {result['tags']['collision_suspected']}")
    
    # Compute scenario-level metrics
    window_distances = [r["distance"] for r in window_results]
    window_statuses = [r["odd_status"] for r in window_results]
    
    scenario_distance = compute_scenario_distance(window_distances, window_statuses)
    time_fractions = compute_time_fractions(window_statuses)
    
    exit_fraction = time_fractions["odd_exit"]
    scenario_class = classify_scenario(scenario_distance, exit_fraction)
    
    print("\n" + "=" * 60)
    print("SCENARIO SUMMARY")
    print("=" * 60)
    print(f"Scenario Distance: {scenario_distance:.3f}")
    print(f"Classification: {scenario_class}")
    print(f"\nTime Fractions:")
    print(f"  In ODD: {time_fractions['in_odd']:.1%}")
    print(f"  Near Boundary: {time_fractions['near_boundary']:.1%}")
    print(f"  ODD Exit: {time_fractions['odd_exit']:.1%}")
    
    return {
        "run_id": run_dir.name,
        "window_results": window_results,
        "scenario_distance": scenario_distance,
        "scenario_class": scenario_class,
        "time_fractions": time_fractions,
    }


def main():
    """Main entry point."""
    print("=" * 60)
    print("Go2 ODD/COD Demo Pipeline")
    print("=" * 60)
    
    # Create ODD spec
    print("\nCreating ODD specification...")
    odd_spec = create_basic_indoor_odd()
    print(f"ODD Version: {odd_spec.version}")
    print(f"ODD Axes: {list(odd_spec.axes.keys())}")
    
    # Look for processed runs
    data_dir = Path(__file__).parent.parent / "data" / "processed" / "runs"
    
    if not data_dir.exists():
        print(f"\nError: Data directory not found: {data_dir}")
        print("Please run extract_windows.py first to create sample data.")
        return 1
    
    # Find all run directories
    run_dirs = sorted([d for d in data_dir.iterdir() if d.is_dir()])
    
    if not run_dirs:
        print(f"\nNo run directories found in {data_dir}")
        print("Please run extract_windows.py first to create sample data.")
        return 1
    
    # Analyze each scenario
    scenario_results = []
    for run_dir in run_dirs:
        result = analyze_scenario(run_dir, odd_spec)
        if result:
            scenario_results.append(result)
    
    # Overall summary
    print("\n" + "=" * 60)
    print("OVERALL SUMMARY")
    print("=" * 60)
    print(f"Total scenarios analyzed: {len(scenario_results)}")
    
    for result in scenario_results:
        print(f"\n{result['run_id']}: {result['scenario_class']} "
              f"(distance: {result['scenario_distance']:.3f})")
    
    print("\n✓ Demo pipeline complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
