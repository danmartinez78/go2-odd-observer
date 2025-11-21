# Example Artifacts

This directory contains real output examples from the ODD Observer system.

## Files

### `example_report.json`
Complete analysis report from the `sim_run_new` dataset (13 windows, 26 seconds).

**Key findings from this run:**
- Environment: `indoor_office` (95% confidence)
- Windows analyzed: 13
- Collision risk: 8 alert-level events detected
- ODD compliance: `OUT_ODD` overall
- Violations: lighting_conditions, obstacle_density, traversability, collision_risk

**Usage:**
```bash
# View executive summary
jq '.report.executive_summary' example_report.json

# View key findings
jq '.report.key_findings' example_report.json

# View COD compliance
jq '.full_analysis.cod.cod_analysis' example_report.json

# View collision events
jq '.full_analysis.collision.collision_events[] | select(.risk_level == "alert")' example_report.json
```

### `example_motion_window.json`
Sample motion data for a single time window (truncated for readability).

Full motion windows contain:
- ~20 timestamped samples at 10 Hz
- Command velocities (cmd_vx, cmd_wz)
- Odometry velocities (odom_vx, odom_wz)
- IMU orientation (roll, pitch, yaw in degrees)
- Accelerations (accel_x, accel_y, accel_z in m/s²)

**Usage:**
```python
import json

with open('example_motion_window.json') as f:
    motion = json.load(f)

# Extract features
avg_speed = sum(motion['odom_vx']) / len(motion['odom_vx'])
max_roll = max(abs(r) for r in motion['roll'])
```

## Generating Your Own Examples

```bash
# Run the full workflow on your data
python odd_workflow_full.py

# The report is saved to:
# data/processed/runs/{scenario_name}/odd_analysis_report.json

# Copy to examples:
cp data/processed/runs/my_scenario/odd_analysis_report.json \
   docs/examples/my_example_report.json
```

## Report Schema

```json
{
  "report": {
    "executive_summary": "string",
    "scenario_metadata": {
      "total_windows_analyzed": "int",
      "scenario_path": "string"
    },
    "perception_summary": "string",
    "motion_summary": "string",
    "collision_summary": "string",
    "odd_classification_summary": "string",
    "cod_compliance_summary": "string",
    "key_findings": ["string"],
    "recommendations": ["string"],
    "timestamp": "ISO 8601 datetime"
  },
  "full_analysis": {
    "perception": {
      "windows_analyzed": ["string"],
      "environment_classification": {
        "primary_class": "string",
        "confidence": "float",
        "evidence": ["string"]
      },
      "per_window_perception": [
        {
          "window_id": "string",
          "lighting_class": "bright|dim|dark",
          "visibility_score": "float",
          "terrain_roughness_class": "smooth|moderate|rough|very_rough",
          "obstacle_density": "float",
          "traversability_score": "float",
          "humans_detected": "boolean"
        }
      ]
    },
    "motion": {
      "windows_analyzed": ["string"],
      "overall_motion_stats": {
        "avg_speed_across_windows": "float",
        "max_observed_speed": "float",
        "predominant_motion_class": "smooth|dynamic"
      },
      "per_window_motion": [
        {
          "window_id": "string",
          "avg_forward_speed": "float",
          "max_forward_speed": "float",
          "max_abs_roll_pitch_deg": "float",
          "motion_label": "smooth|dynamic"
        }
      ]
    },
    "collision": {
      "windows_analyzed": ["string"],
      "overall_collision_stats": {
        "total_windows": "int",
        "safe_count": "int",
        "caution_count": "int",
        "alert_count": "int",
        "avg_collision_likelihood": "float"
      },
      "collision_events": [
        {
          "window_id": "string",
          "risk_level": "safe|caution|alert",
          "collision_likelihood_score": "float",
          "motion_risk_factors": ["string"],
          "vision_risk_factors": ["string"],
          "lidar_risk_factors": ["string"]
        }
      ]
    },
    "odd_spec": {
      "odd_classification": {
        "categorical": {
          "environment_type": "string",
          "lighting_conditions": "string",
          "terrain_type": "string"
        },
        "numeric": {
          "speed_range": ["float", "float"],
          "obstacle_density": ["float", "float"],
          "traversability": ["float", "float"],
          "collision_risk": ["float", "float"]
        }
      },
      "confidence_scores": {
        "environment_type": "float",
        "lighting_conditions": "float",
        "terrain_type": "float"
      }
    },
    "cod": {
      "cod_analysis": {
        "categorical_compliance": {
          "environment_type": "IN_ODD|OUT_ODD",
          "lighting_conditions": "IN_ODD|OUT_ODD",
          "terrain_type": "IN_ODD|OUT_ODD"
        },
        "numeric_compliance": {
          "speed_range": "IN_ODD|ODD_BOUNDARY|OUT_ODD",
          "obstacle_density": "IN_ODD|ODD_BOUNDARY|OUT_ODD",
          "traversability": "IN_ODD|ODD_BOUNDARY|OUT_ODD",
          "collision_risk": "IN_ODD|ODD_BOUNDARY|OUT_ODD"
        },
        "overall_compliance": "IN_ODD|ODD_BOUNDARY|OUT_ODD",
        "violations": ["string"],
        "warnings": ["string"],
        "summary": "string"
      }
    }
  }
}
```

## Interpreting Results

### Compliance States
- **IN_ODD**: All parameters within design limits ✅
- **ODD_BOUNDARY**: Some parameters near safety limits ⚠️
- **OUT_ODD**: One or more parameters exceed limits ❌

### Risk Levels
- **safe**: Collision likelihood < 0.3 (normal operation)
- **caution**: Collision likelihood 0.3-0.7 (increased vigilance)
- **alert**: Collision likelihood > 0.7 (intervention required)

### Motion Classes
- **smooth**: Max speed ≤ 1.0 m/s, roll/pitch ≤ 10°
- **dynamic**: Higher speeds or aggressive orientation changes
