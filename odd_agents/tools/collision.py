"""
Collision detection tools.
Factory functions that create tools with specific configuration.
"""

from pathlib import Path
from typing import Any, Dict, Union
from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext


def create_collision_tools(scenario_path: Union[str, Path]):
    """
    Create collision detection tools for a specific scenario.

    Args:
        scenario_path: Path to scenario directory (string or Path object)

    Returns:
        FunctionTool for binary collision detection
    """
    # Ensure scenario_path is a Path object
    scenario_path = Path(scenario_path) if isinstance(
        scenario_path, str) else scenario_path

    async def detect_collision_tool(
        window_id: str,
        motion_metrics: Dict[str, Any],
        tool_context: ToolContext
    ) -> Dict[str, Any]:
        """Tool: Binary collision detection based on IMU data.

        Detects actual collisions using:
        - Acceleration spikes >10 m/s² (sudden impact)
        - Angular velocity anomalies (spin-out, tip-over)

        Returns: collision detected (yes/no) with evidence from IMU data.
        """
        try:
            # Extract IMU data from motion metrics
            peak_accel = motion_metrics.get("peak_horizontal_accel_mps2", 0.0)
            peak_gyro = motion_metrics.get("peak_angular_velocity_radps", 0.0)
            avg_accel = motion_metrics.get("avg_horizontal_accel_mps2", 0.0)

            # Get jerk (smoothness) if available
            jerk_stats = motion_metrics.get("jerk_mps3", {})
            peak_jerk = jerk_stats.get("peak", 0.0) if isinstance(
                jerk_stats, dict) else 0.0

            # Collision detection thresholds (based on Phase 1.2 spec)
            ACCEL_SPIKE_THRESHOLD = 10.0  # m/s² - sudden impact
            GYRO_ANOMALY_THRESHOLD = 5.0  # rad/s - severe rotation
            JERK_SPIKE_THRESHOLD = 50.0   # m/s³ - sudden acceleration change

            # Detect collision indicators
            accel_spike = peak_accel > ACCEL_SPIKE_THRESHOLD
            gyro_anomaly = peak_gyro > GYRO_ANOMALY_THRESHOLD
            jerk_spike = peak_jerk > JERK_SPIKE_THRESHOLD

            collision_detected = accel_spike or gyro_anomaly or jerk_spike

            # Build evidence list
            evidence = []
            if accel_spike:
                evidence.append(
                    f"Acceleration spike: {peak_accel:.2f} m/s² (threshold: {ACCEL_SPIKE_THRESHOLD})")
            if gyro_anomaly:
                evidence.append(
                    f"Angular velocity anomaly: {peak_gyro:.2f} rad/s (threshold: {GYRO_ANOMALY_THRESHOLD})")
            if jerk_spike:
                evidence.append(
                    f"Jerk spike: {peak_jerk:.2f} m/s³ (threshold: {JERK_SPIKE_THRESHOLD})")

            if not collision_detected:
                evidence.append(
                    f"No collision indicators (accel: {peak_accel:.2f}, gyro: {peak_gyro:.2f}, jerk: {peak_jerk:.2f})")

            return {
                "window_id": window_id,
                "collision_detected": collision_detected,
                "evidence": evidence,
                "imu_metrics": {
                    "peak_accel_mps2": peak_accel,
                    "avg_accel_mps2": avg_accel,
                    "peak_gyro_radps": peak_gyro,
                    "peak_jerk_mps3": peak_jerk
                }
            }

        except Exception as err:
            return {
                "status": "error",
                "window_id": window_id,
                "message": str(err),
                "collision_detected": False,
                "evidence": ["Error during collision detection"]
            }

    # Return FunctionTool wrapper
    return FunctionTool(func=detect_collision_tool)
