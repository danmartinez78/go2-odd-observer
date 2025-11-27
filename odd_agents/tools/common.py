"""
Common utilities for agent tools.
Shared logic for CSV index reading, file path resolution, etc.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import pandas as pd


def load_scenario_index(scenario_path: Path) -> Tuple[pd.DataFrame, Path]:
    """
    Load the CSV index for a scenario.

    Args:
        scenario_path: Path to scenario directory

    Returns:
        Tuple of (DataFrame, index_file_path)

    Raises:
        FileNotFoundError: If no index CSV found
    """
    index_files = sorted(scenario_path.glob("index_*.csv"))
    if not index_files:
        raise FileNotFoundError(f"No index CSV found in {scenario_path}")

    index_df = pd.read_csv(index_files[0])
    return index_df, index_files[0]


def get_window_row(index_df: pd.DataFrame, window_id: str) -> Optional[pd.Series]:
    """
    Get the row for a specific window ID from the index.

    Args:
        index_df: DataFrame from CSV index
        window_id: Window ID (as string, e.g., "010")

    Returns:
        Row as Series, or None if not found
    """
    window_row = index_df[index_df["window_id"] == int(window_id)]
    if window_row.empty:
        return None
    return window_row.iloc[0]


def resolve_file_path(scenario_path: Path, relative_path: str) -> Path:
    """
    Resolve a relative file path from the CSV index to an absolute path.

    Args:
        scenario_path: Path to scenario directory
        relative_path: Relative path from CSV (e.g., "motion_sim_1_0_w010.json")

    Returns:
        Absolute path to file
    """
    return scenario_path / relative_path


def list_available_windows(scenario_path: Path, require_motion: bool = True) -> List[str]:
    """
    List all available window IDs in a scenario.

    Args:
        scenario_path: Path to scenario directory
        require_motion: If True, only include windows with existing motion files

    Returns:
        List of window IDs as zero-padded strings (e.g., ["010", "011"])

    Raises:
        FileNotFoundError: If scenario or index not found
    """
    if not scenario_path.exists():
        raise FileNotFoundError(
            f"Scenario directory not found: {scenario_path}")

    index_df, _ = load_scenario_index(scenario_path)
    windows: List[str] = []

    for _, row in index_df.iterrows():
        window_id = str(row["window_id"]).zfill(3)

        if require_motion:
            # Verify motion file exists
            motion_file = resolve_file_path(scenario_path, row["motion_path"])
            if not motion_file.exists():
                continue

        windows.append(window_id)

    return windows


def get_window_file_paths(
    scenario_path: Path,
    window_id: str
) -> Dict[str, Path]:
    """
    Get all file paths for a window from the CSV index.

    Args:
        scenario_path: Path to scenario directory
        window_id: Window ID (as string, e.g., "010")

    Returns:
        Dict with keys: motion, camera, bev_occupancy, bev_height, bev_roughness
        Values are absolute Path objects

    Raises:
        FileNotFoundError: If index not found
        ValueError: If window_id not found in index
    """
    index_df, _ = load_scenario_index(scenario_path)
    row = get_window_row(index_df, window_id)

    if row is None:
        raise ValueError(f"Window {window_id} not found in index")

    return {
        "motion": resolve_file_path(scenario_path, row["motion_path"]),
        "camera": resolve_file_path(scenario_path, row["cam_image_path"]),
        "bev_occupancy": resolve_file_path(scenario_path, row["bev_occupancy_path"]),
        "bev_height": resolve_file_path(scenario_path, row["bev_height_path"]),
        "bev_roughness": resolve_file_path(scenario_path, row["bev_roughness_path"]),
    }
