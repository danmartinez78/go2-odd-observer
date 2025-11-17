"""
Go2 ODD/COD Analysis Package

This package provides tools for analyzing Operational Design Domain (ODD)
compliance and Conditions of Deployment (COD) for Unitree Go2 robot data.
"""

__version__ = "0.1.0"

from .odd_spec_schema import OddSpec, AxisSpecNumeric, AxisSpecCategorical
from .cod_features import build_cod_vector, TERRAIN_MAP, LIGHTING_MAP, HUMAN_PROX_MAP, COLLISION_MAP
from .distance_metrics import (
    compute_window_distance,
    compute_window_odd_status,
    compute_scenario_distance,
    classify_scenario,
    compute_time_fractions,
)

__all__ = [
    "OddSpec",
    "AxisSpecNumeric",
    "AxisSpecCategorical",
    "build_cod_vector",
    "compute_window_distance",
    "compute_window_odd_status",
    "compute_scenario_distance",
    "classify_scenario",
    "compute_time_fractions",
    "TERRAIN_MAP",
    "LIGHTING_MAP",
    "HUMAN_PROX_MAP",
    "COLLISION_MAP",
]
