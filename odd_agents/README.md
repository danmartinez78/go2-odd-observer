# ODD Agents Module

A shared library for Operational Design Domain (ODD) analysis using Google's Agentic Development Kit (ADK) and Gemini models.

## Overview

The `odd_agents` module provides a complete **6-agent workflow** for analyzing robot sensor data and detecting ODD violations. It serves as a single source of truth for tools, agents, and workflow orchestration.

**Phase 1.4.4 Architecture (Nov 26, 2025):**
- Type-driven COD construction (range/enum/bool)
- Python tools for deterministic evaluation
- Blackboard pattern with ToolContext for token efficiency
- 6 agents: OddSpec, Perception, Motion, Collision, Evaluator, Report

## Quick Start

### Run Analysis
```bash
python scripts/run_odd_analysis.py --scenario sim_test_w010_w011
```

### Chunk Large Scenarios
```bash
python scripts/chunk_large_scenario.py data/production/sim_1_0 --chunk-size 10
```

### Python API
```python
from odd_agents import run_odd_workflow

# Run analysis on a scenario
result = await run_odd_workflow(scenario_name="sim_test_w010_w011")
print(result["report"]["executive_summary"])
```

## Module Structure

```
odd_agents/
├── __init__.py          # Package exports
├── utils.py             # Shared utilities (image loading, JSON parsing)
├── workflow.py          # Workflow orchestration
├── tools/               # Tool functions
│   ├── common.py        # Shared tool utilities
│   ├── perception.py    # Camera + LiDAR BEV analysis
│   ├── motion.py        # IMU sensor analysis (v10.0.0)
│   ├── collision.py     # Collision detection
│   └── cod_construction.py  # Python COD construction functions
└── agents/              # Agent definitions
    ├── odd_spec.py      # ODD specification agent (v5.0.0)
    ├── perception.py    # Perception agent (v5.0.0)
    ├── motion.py        # Motion agent (v5.0.0)
    ├── collision.py     # Collision agent (v5.0.0)
    ├── evaluator.py     # Evaluator agent (v1.0.0) - COD + compliance
    └── report.py        # Report agent (v4.0.0)
```

## Tools

### Motion Tool (v10.0.0)

Analyzes IMU data and derived motion fields:

| Metric | Source | Notes |
|--------|--------|-------|
| `max_speed_mps` | `derived_speed` | From position differentiation |
| `max_accel_mps2` | IMU `accel_x/y` | None if unavailable |
| `max_angular_velocity_radps` | IMU `gyro_z` or `derived_yaw_rate` | IMU preferred |
| `max_tilt_deg` | `roll`, `pitch` | Always available |
| `is_stationary` | `derived_speed < 0.05` | Position-based |

**Output includes `data_availability` dict:**
```json
{
  "data_availability": {
    "speed": "derived",
    "acceleration": "imu",       // or "unavailable"
    "angular_velocity": "imu",   // or "derived"
    "orientation": "available"
  }
}
```

## Agent Pipeline

```
OddSpecAgent → PerceptionAgent → MotionAgent → CollisionAgent → EvaluatorAgent → ReportAgent
     │              │                │              │                │
     │              └── per_window ──┴─── measurements ─────────────→│
     │                                                                │
     └── ODD spec (typed axes) ──────────────────────────────────────→│
```

### Blackboard Keys
- `temp:odd_spec` - ODD specification with type definitions
- `temp:perception_output` - Per-window perception measurements
- `temp:motion_output` - Per-window motion measurements
- `temp:collision_output` - Per-window collision measurements
- `temp:evaluator_output` - COD region + compliance verdict

## Key Concepts

### Type-Driven ODD Specification
```json
{
  "odd_specification": {
    "environment": {
      "categorical": {
        "lighting_conditions": {
          "type": "enum",
          "allowed": ["bright", "moderate", "dim"],
          "description": "Ambient illumination level"
        }
      },
      "numeric": {
        "obstacle_density": {
          "type": "range",
          "min": 0.0,
          "max": 0.7,
          "description": "Normalized obstacle density"
        }
      }
    },
    "ego": {
      "numeric": {
        "max_speed_mps": {
          "type": "range",
          "min": 0.0,
          "max": 1.5,
          "description": "Maximum linear velocity"
        }
      }
    }
  }
}
```

### Per-Window Sensor Measurements
```json
{
  "per_window_measurements": [
    {
      "window_id": "010",
      "measurements": {
        "lighting_conditions": "bright",
        "obstacle_density": 0.35,
        "max_speed_mps": 1.2
      },
      "compliance": {
        "lighting_conditions": "IN_ODD",
        "obstacle_density": "IN_ODD",
        "max_speed_mps": "IN_ODD"
      }
    }
  ]
}
```

### COD Region Construction
The Evaluator uses Python tools (not LLM) to build the COD:
- **range axes**: Compute min/max envelope from measurements
- **enum axes**: Collect set of observed values
- **bool axes**: Any OUT_ODD observation flags entire axis

### Compliance Verdict
```json
{
  "compliance_verdict": {
    "overall": "IN_ODD",
    "rationale": "All measurements within ODD bounds",
    "critical_axes": [],
    "temporal_stability": "STABLE"
  },
  "region_metrics": {
    "distance": 0.0,
    "fraction_outside": {}
  }
}
```

## Model Configuration

| Agent | Model | Reason |
|-------|-------|--------|
| PerceptionAgent | `gemini-2.0-flash-thinking-exp` | Reliable multimodal tool calling |
| MotionAgent | `gemini-2.0-flash-exp` | Text tools work fine |
| CollisionAgent | `gemini-2.0-flash-exp` | Text tools work fine |
| OddSpecAgent | `gemini-2.0-flash-exp` | JSON reasoning |
| EvaluatorAgent | `gemini-2.0-flash-exp` | Simple tool orchestration |
| ReportAgent | `gemini-2.0-flash-exp` | Report synthesis |

## Testing

```bash
# Run individual tests
pytest tests/test_perception_agent.py
pytest tests/test_motion_agent.py
pytest tests/test_collision_agent.py

# Run all tests
pytest tests/
```

## Benefits

✅ **Deterministic COD construction** - Python tools, not LLM hallucination  
✅ **Token efficient** - Tools read from blackboard via ToolContext  
✅ **Type-driven** - ODD types guide measurement and evaluation  
✅ **Clean ODD specs** - No static robot dimensions or measurement_guidance  
✅ **Scalable** - Chunk large scenarios into manageable batches
