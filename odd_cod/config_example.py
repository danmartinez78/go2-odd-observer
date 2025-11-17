"""
Example ODD Configurations

Provides sample ODD specifications for testing and reference.
"""

from .odd_spec_schema import OddSpec, AxisSpecNumeric, AxisSpecCategorical


def create_basic_indoor_odd() -> OddSpec:
    """
    Create a basic indoor ODD for Go2 robot.
    
    Suitable for:
    - Indoor office/lab environments
    - Smooth floors
    - Good lighting
    - Low to moderate speeds
    """
    return OddSpec(
        version="1.0",
        description="Basic indoor navigation ODD for Go2 robot",
        axes={
            "speed": AxisSpecNumeric(
                feature="forward_velocity",
                units="m/s",
                in_odd=[0.0, 1.5],
                near_boundary=[0.0, 1.8],
                hard_limit=[0.0, 2.5]
            ),
            "roll_pitch": AxisSpecNumeric(
                feature="max_abs_roll_pitch",
                units="degrees",
                in_odd=[0.0, 15.0],
                near_boundary=[0.0, 20.0],
                hard_limit=[0.0, 30.0]
            ),
            "terrain": AxisSpecCategorical(
                feature="terrain_type",
                allowed_in_odd=["smooth", "moderate"],
                allowed_all=["smooth", "moderate", "rough", "very_rough"]
            ),
            "lighting": AxisSpecCategorical(
                feature="lighting_condition",
                allowed_in_odd=["bright", "dim"],
                allowed_all=["bright", "dim", "dark"]
            ),
            "humans": AxisSpecCategorical(
                feature="human_proximity",
                allowed_in_odd=["none", "visible_far"],
                allowed_all=["none", "visible_far", "very_close"]
            ),
            "collision": AxisSpecCategorical(
                feature="collision_state",
                allowed_in_odd=["no_collision"],
                allowed_all=["no_collision", "collision_suspected"]
            ),
        },
        importance={
            "speed": 1.0,
            "roll_pitch": 1.2,  # Safety critical
            "terrain": 0.8,
            "lighting": 0.5,
            "humans": 1.5,  # Very important for safety
            "collision": 2.0,  # Highest priority
        }
    )


def create_outdoor_rough_odd() -> OddSpec:
    """
    Create an outdoor rough terrain ODD for Go2 robot.
    
    Suitable for:
    - Outdoor environments
    - Uneven terrain
    - Variable lighting
    - Higher speed operation
    """
    return OddSpec(
        version="1.0",
        description="Outdoor rough terrain ODD for Go2 robot",
        axes={
            "speed": AxisSpecNumeric(
                feature="forward_velocity",
                units="m/s",
                in_odd=[0.0, 2.0],
                near_boundary=[0.0, 2.5],
                hard_limit=[0.0, 3.5]
            ),
            "roll_pitch": AxisSpecNumeric(
                feature="max_abs_roll_pitch",
                units="degrees",
                in_odd=[0.0, 25.0],
                near_boundary=[0.0, 35.0],
                hard_limit=[0.0, 45.0]
            ),
            "terrain": AxisSpecCategorical(
                feature="terrain_type",
                allowed_in_odd=["smooth", "moderate", "rough"],
                allowed_all=["smooth", "moderate", "rough", "very_rough"]
            ),
            "lighting": AxisSpecCategorical(
                feature="lighting_condition",
                allowed_in_odd=["bright", "dim"],
                allowed_all=["bright", "dim", "dark"]
            ),
            "humans": AxisSpecCategorical(
                feature="human_proximity",
                allowed_in_odd=["none", "visible_far"],
                allowed_all=["none", "visible_far", "very_close"]
            ),
            "collision": AxisSpecCategorical(
                feature="collision_state",
                allowed_in_odd=["no_collision"],
                allowed_all=["no_collision", "collision_suspected"]
            ),
        },
        importance={
            "speed": 1.0,
            "roll_pitch": 1.5,
            "terrain": 1.0,
            "lighting": 0.6,
            "humans": 1.5,
            "collision": 2.0,
        }
    )


def create_minimal_test_odd() -> OddSpec:
    """
    Create a minimal ODD for unit testing.
    """
    return OddSpec(
        version="0.1",
        description="Minimal test ODD",
        axes={
            "speed": AxisSpecNumeric(
                feature="speed",
                units="m/s",
                in_odd=[0.0, 1.0],
                near_boundary=[0.0, 1.5],
                hard_limit=[0.0, 2.0]
            ),
            "terrain": AxisSpecCategorical(
                feature="terrain",
                allowed_in_odd=["smooth"],
                allowed_all=["smooth", "rough"]
            ),
        },
        importance={
            "speed": 1.0,
            "terrain": 1.0,
        }
    )
