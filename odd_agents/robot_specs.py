"""
Robot physical specifications.

These are constant platform properties that do NOT need to be measured or evaluated.
They provide context to agents but are NOT part of the ODD specification.

ODD specification contains OPERATIONAL limits (max speed, accel, etc.)
Robot specs contain PHYSICAL constants (dimensions, weight, etc.)
"""

# Unitree Go2 quadruped robot specifications
# Source: https://www.unitree.com/products/go2/
GO2_ROBOT_SPECS = {
    "platform": "Unitree Go2",
    "physical_dimensions": {
        "footprint_length_m": 0.646,  # Body length: 646mm
        "footprint_width_m": 0.280,   # Body width: 280mm
        # Standing height: ~400mm (varies with leg posture)
        "max_height_m": 0.400,
        "weight_kg": 15.0,            # Approximate weight: 15kg
    },
    "sensor_suite": {
        "cameras": "Front-facing RGB camera",
        "lidar": "3D LiDAR scanner",
        "imu": "6-axis IMU (accelerometer + gyroscope)",
    },
    "notes": "Physical specs for context only. NOT evaluated against ODD."
}


def get_robot_specs(robot_type: str = "go2") -> dict:
    """Get robot specifications by type.

    Args:
        robot_type: Robot platform identifier (default: "go2")

    Returns:
        Dictionary of robot specifications
    """
    if robot_type.lower() == "go2":
        return GO2_ROBOT_SPECS
    else:
        raise ValueError(f"Unknown robot type: {robot_type}")
