"""
Unit tests for common tool utilities.
Tests CSV index reading, file path resolution, and window listing.
"""

import pytest
from pathlib import Path
from odd_agents.tools.common import (
    load_scenario_index,
    get_window_row,
    resolve_file_path,
    list_available_windows,
    get_window_file_paths
)


def test_list_available_windows():
    """Test listing windows from a test scenario."""
    scenario = Path("data/test/sim_test_w010_w011")
    if not scenario.exists():
        pytest.skip("Test scenario not available")

    windows = list_available_windows(scenario, require_motion=True)

    assert isinstance(windows, list)
    assert len(windows) == 2
    assert windows == ['010', '011']
    # Verify zero-padded format
    assert all(len(w) == 3 for w in windows)


def test_get_window_file_paths():
    """Test file path resolution for a window."""
    scenario = Path("data/test/sim_test_w010_w011")
    if not scenario.exists():
        pytest.skip("Test scenario not available")

    paths = get_window_file_paths(scenario, '010')

    # Verify all expected keys present
    expected_keys = {"motion", "camera",
                     "bev_occupancy", "bev_height", "bev_roughness"}
    assert set(paths.keys()) == expected_keys

    # Verify all paths are Path objects
    assert all(isinstance(p, Path) for p in paths.values())

    # Verify all files exist
    assert all(p.exists() for p in paths.values()), \
        f"Missing files: {[p for p in paths.values() if not p.exists()]}"

    # Verify correct file types
    assert paths["motion"].suffix == ".json"
    assert paths["camera"].suffix == ".png"
    assert all(paths[k].suffix == ".png" for k in [
               "bev_occupancy", "bev_height", "bev_roughness"])


def test_load_scenario_index():
    """Test loading CSV index."""
    scenario = Path("data/test/sim_test_w010_w011")
    if not scenario.exists():
        pytest.skip("Test scenario not available")

    df, index_path = load_scenario_index(scenario)

    # Verify DataFrame structure
    assert len(df) == 2  # 2 windows in test set
    expected_columns = {
        "window_id", "start_time", "end_time",
        "motion_path", "cam_image_path",
        "bev_occupancy_path", "bev_height_path", "bev_roughness_path"
    }
    assert set(df.columns) == expected_columns

    # Verify index file path
    assert index_path.exists()
    assert index_path.name.startswith("index_")
    assert index_path.suffix == ".csv"


def test_get_window_row():
    """Test getting a specific window row from index."""
    scenario = Path("data/test/sim_test_w010_w011")
    if not scenario.exists():
        pytest.skip("Test scenario not available")

    df, _ = load_scenario_index(scenario)

    # Test valid window
    row = get_window_row(df, '010')
    assert row is not None
    assert row["window_id"] == 10
    assert "motion_path" in row

    # Test invalid window
    row = get_window_row(df, '999')
    assert row is None


def test_resolve_file_path():
    """Test path resolution."""
    scenario = Path("data/test/sim_test_w010_w011")
    relative = "motion_sim_1_0_w010.json"

    resolved = resolve_file_path(scenario, relative)

    assert isinstance(resolved, Path)
    assert resolved.name == relative
    # Verify path is under scenario directory
    assert str(resolved).startswith(str(scenario))


def test_error_handling():
    """Test error handling for missing scenarios."""
    nonexistent = Path("data/nonexistent/scenario")

    # list_available_windows should raise FileNotFoundError
    with pytest.raises(FileNotFoundError):
        list_available_windows(nonexistent)

    # load_scenario_index should raise FileNotFoundError
    with pytest.raises(FileNotFoundError):
        load_scenario_index(nonexistent)


def test_require_motion_filter():
    """Test that require_motion filters windows correctly."""
    scenario = Path("data/test/sim_test_w010_w011")
    if not scenario.exists():
        pytest.skip("Test scenario not available")

    # With require_motion=True (default)
    windows_filtered = list_available_windows(scenario, require_motion=True)

    # With require_motion=False
    windows_all = list_available_windows(scenario, require_motion=False)

    # In a valid test set, should be the same
    assert windows_filtered == windows_all

    # All windows should have motion files
    for window_id in windows_filtered:
        paths = get_window_file_paths(scenario, window_id)
        assert paths["motion"].exists()
