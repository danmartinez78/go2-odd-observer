"""
Unit tests for distance metrics module.
"""

import pytest
import numpy as np
from odd_cod.odd_spec_schema import OddSpec, AxisSpecNumeric, AxisSpecCategorical
from odd_cod.distance_metrics import (
    compute_window_distance,
    compute_window_odd_status,
    compute_scenario_distance,
    classify_scenario,
    compute_time_fractions,
)
from odd_cod.cod_features import build_cod_vector
from odd_cod.config_example import create_minimal_test_odd, create_basic_indoor_odd


class TestWindowDistance:
    """Test window-level distance computation."""
    
    def test_perfect_compliance(self):
        """Test window at ODD center."""
        odd_spec = create_minimal_test_odd()
        cod_vector = {"speed": 0.5, "terrain": 0.0}  # smooth terrain, moderate speed
        
        distance, axis_distances, axis_statuses = compute_window_distance(cod_vector, odd_spec)
        
        assert distance < 0.3, "Perfect compliance should have low distance"
        assert axis_statuses["speed"] == "in_odd"
        assert axis_statuses["terrain"] == "in_odd"
    
    def test_odd_boundary(self):
        """Test window at ODD boundary."""
        odd_spec = create_minimal_test_odd()
        cod_vector = {"speed": 1.0, "terrain": 0.0}  # at upper ODD limit
        
        distance, axis_distances, axis_statuses = compute_window_distance(cod_vector, odd_spec)
        
        assert distance <= 0.3, "At ODD boundary should still be low distance"
        assert axis_statuses["speed"] == "in_odd"
    
    def test_odd_violation(self):
        """Test window violating ODD."""
        odd_spec = create_minimal_test_odd()
        # terrain 1.0 maps to "rough" which is out_of_odd for minimal spec
        cod_vector = {"speed": 1.8, "terrain": 1.0}  # rough terrain, high speed
        
        distance, axis_distances, axis_statuses = compute_window_distance(cod_vector, odd_spec)
        
        assert distance > 0.5, "Violation should have high distance"
        # Speed 1.8 is beyond near_boundary (1.5), so it's out_of_odd
        assert axis_statuses["speed"] == "out_of_odd"
        # Note: terrain status depends on categorical mapping, may be "unknown"
    
    def test_missing_data(self):
        """Test handling of missing COD data."""
        odd_spec = create_minimal_test_odd()
        cod_vector = {"speed": 0.5}  # terrain missing
        
        distance, axis_distances, axis_statuses = compute_window_distance(cod_vector, odd_spec)
        
        assert "terrain" in axis_statuses
        assert axis_statuses["terrain"] == "unknown"


class TestWindowOddStatus:
    """Test window ODD status classification."""
    
    def test_all_in_odd(self):
        """Test window with all axes in ODD."""
        axis_statuses = {"speed": "in_odd", "terrain": "in_odd"}
        status = compute_window_odd_status(axis_statuses)
        assert status == "in_odd"
    
    def test_any_near_boundary(self):
        """Test window with any axis near boundary."""
        axis_statuses = {"speed": "near_boundary", "terrain": "in_odd"}
        status = compute_window_odd_status(axis_statuses)
        assert status == "near_boundary"
    
    def test_any_out_of_odd(self):
        """Test window with any axis out of ODD."""
        axis_statuses = {"speed": "in_odd", "terrain": "out_of_odd"}
        status = compute_window_odd_status(axis_statuses)
        assert status == "odd_exit"
    
    def test_unknown_triggers_exit(self):
        """Test that unknown data triggers ODD exit."""
        axis_statuses = {"speed": "in_odd", "terrain": "unknown"}
        status = compute_window_odd_status(axis_statuses)
        assert status == "odd_exit"


class TestScenarioDistance:
    """Test scenario-level distance computation."""
    
    def test_all_compliant_windows(self):
        """Test scenario with all windows in ODD."""
        window_distances = [0.1, 0.15, 0.2, 0.12]
        window_statuses = ["in_odd"] * 4
        
        scenario_dist = compute_scenario_distance(window_distances, window_statuses)
        
        assert scenario_dist < 0.3, "All compliant should have low distance"
    
    def test_mixed_windows(self):
        """Test scenario with mixed compliance."""
        window_distances = [0.2, 0.5, 0.8, 0.3]
        window_statuses = ["in_odd", "near_boundary", "odd_exit", "in_odd"]
        
        scenario_dist = compute_scenario_distance(window_distances, window_statuses)
        
        assert 0.3 < scenario_dist < 0.7, "Mixed should have moderate distance"
    
    def test_many_exits(self):
        """Test scenario with many ODD exits."""
        window_distances = [0.7, 0.8, 0.9, 0.75]
        window_statuses = ["odd_exit"] * 4
        
        scenario_dist = compute_scenario_distance(window_distances, window_statuses)
        
        assert scenario_dist > 0.7, "Many exits should have high distance"
    
    def test_no_penalty_mode(self):
        """Test scenario distance without exit penalty."""
        window_distances = [0.7, 0.8, 0.9, 0.75]
        window_statuses = ["odd_exit"] * 4
        
        scenario_dist = compute_scenario_distance(
            window_distances, window_statuses, penalize_exits=False
        )
        
        expected_mean = np.mean(window_distances)
        assert abs(scenario_dist - expected_mean) < 0.01, "Should be pure mean"


class TestScenarioClassification:
    """Test scenario classification."""
    
    def test_in_odd_classification(self):
        """Test IN_ODD classification."""
        result = classify_scenario(scenario_distance=0.2, exit_fraction=0.05)
        assert result == "IN_ODD"
    
    def test_boundary_heavy_classification(self):
        """Test BOUNDARY_HEAVY classification."""
        result = classify_scenario(scenario_distance=0.5, exit_fraction=0.2)
        assert result == "BOUNDARY_HEAVY"
    
    def test_odd_exit_classification(self):
        """Test ODD_EXIT classification."""
        result = classify_scenario(scenario_distance=0.8, exit_fraction=0.4)
        assert result == "ODD_EXIT"
    
    def test_high_exit_fraction_triggers_exit(self):
        """Test that high exit fraction triggers ODD_EXIT even with moderate distance."""
        result = classify_scenario(scenario_distance=0.4, exit_fraction=0.5)
        assert result == "ODD_EXIT"


class TestTimeFractions:
    """Test time fraction computation."""
    
    def test_all_in_odd(self):
        """Test fractions with all windows in ODD."""
        statuses = ["in_odd"] * 10
        fractions = compute_time_fractions(statuses)
        
        assert fractions["in_odd"] == 1.0
        assert fractions["near_boundary"] == 0.0
        assert fractions["odd_exit"] == 0.0
    
    def test_mixed_statuses(self):
        """Test fractions with mixed statuses."""
        statuses = ["in_odd"] * 5 + ["near_boundary"] * 3 + ["odd_exit"] * 2
        fractions = compute_time_fractions(statuses)
        
        assert fractions["in_odd"] == 0.5
        assert fractions["near_boundary"] == 0.3
        assert fractions["odd_exit"] == 0.2
    
    def test_empty_list(self):
        """Test handling of empty status list."""
        fractions = compute_time_fractions([])
        
        assert fractions["in_odd"] == 0.0
        assert fractions["near_boundary"] == 0.0
        assert fractions["odd_exit"] == 0.0


class TestIntegration:
    """Integration tests with realistic scenarios."""
    
    def test_indoor_compliant_scenario(self):
        """Test a compliant indoor scenario."""
        odd_spec = create_basic_indoor_odd()
        
        # Simulate 5 compliant windows
        window_tags = [
            {
                "avg_forward_speed": 0.8,
                "max_abs_roll_pitch_deg": 5.0,
                "terrain_roughness_class": "smooth",
                "lighting_class": "bright",
                "humans_visible": False,
                "collision_suspected": False,
            }
            for _ in range(5)
        ]
        
        distances = []
        statuses = []
        
        for tags in window_tags:
            cod_vector = build_cod_vector(tags, odd_spec)
            distance, _, axis_statuses = compute_window_distance(cod_vector, odd_spec)
            status = compute_window_odd_status(axis_statuses)
            
            distances.append(distance)
            statuses.append(status)
        
        scenario_dist = compute_scenario_distance(distances, statuses)
        classification = classify_scenario(scenario_dist, statuses.count("odd_exit") / len(statuses))
        
        assert classification == "IN_ODD"
        assert scenario_dist < 0.3
    
    def test_collision_scenario(self):
        """Test a scenario with collision."""
        odd_spec = create_basic_indoor_odd()
        
        # Window with collision
        tags = {
            "avg_forward_speed": 0.5,
            "max_abs_roll_pitch_deg": 3.0,
            "terrain_roughness_class": "smooth",
            "lighting_class": "bright",
            "humans_visible": False,
            "collision_suspected": True,  # Collision!
        }
        cod_vector = build_cod_vector(tags, odd_spec)
        distance, axis_distances, axis_statuses = compute_window_distance(cod_vector, odd_spec)
        status = compute_window_odd_status(axis_statuses)
        
        assert axis_statuses["collision"] == "out_of_odd"
        assert status == "odd_exit"
        # Collision has high importance (2.0) but is weighted with other axes
        # that are all compliant, so overall distance is moderate
        assert distance > 0.3, "Collision should increase distance"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
