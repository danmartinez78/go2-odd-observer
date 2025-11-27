#!/usr/bin/env python3
"""Unit test for collision detection logic.

Tests the binary collision detection without running full agent workflow.
"""

import pytest
import asyncio
from pathlib import Path
from odd_agents.tools.collision import create_collision_tools


@pytest.mark.asyncio
async def test_no_collision_normal_motion():
    """Test that normal motion does not trigger collision detection."""
    # Create the tool
    scenario_path = Path(
        "/workspaces/go2-odd-observer/data/production/sim_1_0")
    detect_collision_tool = create_collision_tools(scenario_path)

    # Motion metrics from a normal window (low acceleration/gyro)
    motion_metrics = {
        "peak_horizontal_accel_mps2": 0.012,  # Below 10.0 threshold
        "avg_horizontal_accel_mps2": 0.004,
        "peak_angular_velocity_radps": 0.06,  # Below 5.0 threshold
        "jerk_mps3": {"peak": 2.5}  # Below 50.0 threshold
    }

    # Run the detection (call the wrapped function directly)
    result = await detect_collision_tool.func(
        window_id="w000",
        motion_metrics=motion_metrics,
        tool_context=None  # Not needed for this test
    )

    # Verify no collision detected
    assert result["window_id"] == "w000"
    assert result["collision_detected"] == False
    assert "No collision indicators" in result["evidence"][0]
    assert result["imu_metrics"]["peak_accel_mps2"] == 0.012
    assert result["imu_metrics"]["peak_gyro_radps"] == 0.06


@pytest.mark.asyncio
async def test_collision_acceleration_spike():
    """Test that acceleration spike triggers collision detection."""
    scenario_path = Path(
        "/workspaces/go2-odd-observer/data/production/sim_1_0")
    detect_collision_tool = create_collision_tools(scenario_path)

    # Motion metrics with high acceleration (collision scenario)
    motion_metrics = {
        "peak_horizontal_accel_mps2": 12.5,  # Above 10.0 threshold
        "avg_horizontal_accel_mps2": 3.2,
        "peak_angular_velocity_radps": 1.2,
        "jerk_mps3": {"peak": 15.0}
    }

    result = await detect_collision_tool.func(
        window_id="w017",
        motion_metrics=motion_metrics,
        tool_context=None
    )

    # Verify collision detected
    assert result["collision_detected"] == True
    assert any("Acceleration spike" in e for e in result["evidence"])
    assert result["imu_metrics"]["peak_accel_mps2"] == 12.5


@pytest.mark.asyncio
async def test_collision_gyro_anomaly():
    """Test that angular velocity anomaly triggers collision detection."""
    scenario_path = Path(
        "/workspaces/go2-odd-observer/data/production/sim_1_0")
    detect_collision_tool = create_collision_tools(scenario_path)

    # Motion metrics with high angular velocity (tip-over/spin-out)
    motion_metrics = {
        "peak_horizontal_accel_mps2": 2.1,
        "avg_horizontal_accel_mps2": 0.8,
        "peak_angular_velocity_radps": 6.8,  # Above 5.0 threshold
        "jerk_mps3": {"peak": 8.0}
    }

    result = await detect_collision_tool.func(
        window_id="w042",
        motion_metrics=motion_metrics,
        tool_context=None
    )

    # Verify collision detected
    assert result["collision_detected"] == True
    assert any("Angular velocity anomaly" in e for e in result["evidence"])
    assert result["imu_metrics"]["peak_gyro_radps"] == 6.8


@pytest.mark.asyncio
async def test_collision_jerk_spike():
    """Test that jerk spike triggers collision detection."""
    scenario_path = Path(
        "/workspaces/go2-odd-observer/data/production/sim_1_0")
    detect_collision_tool = create_collision_tools(scenario_path)

    # Motion metrics with high jerk (sudden acceleration change)
    motion_metrics = {
        "peak_horizontal_accel_mps2": 8.5,
        "avg_horizontal_accel_mps2": 2.1,
        "peak_angular_velocity_radps": 2.3,
        "jerk_mps3": {"peak": 65.0}  # Above 50.0 threshold
    }

    result = await detect_collision_tool.func(
        window_id="w025",
        motion_metrics=motion_metrics,
        tool_context=None
    )

    # Verify collision detected
    assert result["collision_detected"] == True
    assert any("Jerk spike" in e for e in result["evidence"])
    assert result["imu_metrics"]["peak_jerk_mps3"] == 65.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
