# Report Agent

## Overview

The **ReportAgent** is the final agent in the ODD analysis workflow. It synthesizes pipeline statistics and sensor insights into a concise executive summary with actionable recommendations.

**Version:** 6.0.0  
**Purpose:** Transform computed statistics into human-readable narrative insights.

---

## Architecture: Synthesis-Focused Design

### Key Principle: LLM Synthesizes, Python Computes

| Component | Responsibility | Example |
|-----------|----------------|---------|
| **Python Tool** | Compute statistics | `{all_agents_healthy: true, warnings: []}` |
| **LLM** | Synthesize narrative | "All agents executed successfully with complete data." |
| **Post-Processing** | Assemble final report | Merge LLM narrative + Python data |

This separation ensures:
- **Reliability:** Deterministic data is never hallucinated
- **Quality:** LLM focuses on what it's good at (synthesis)
- **Efficiency:** No token waste on copying data

---

## Tools

### 1. `compute_report_statistics_tool()`

Computes comprehensive statistics from all pipeline outputs:

```json
{
  "window_stats": {
    "total_windows": 2,
    "perception_windows": 2,
    "motion_windows": 2,
    "collision_windows": 2,
    "window_ids": ["010", "011"]
  },
  "agent_health": {
    "perception": {"windows_processed": 2, "empty_windows": [], "status": "OK"},
    "motion": {"windows_processed": 2, "zero_acceleration_windows": [], "status": "OK"},
    "collision": {"windows_processed": 2, "collision_count": 0, "status": "OK"},
    "evaluator": {"has_compliance_verdict": true, "verdict": "IN_ODD", "status": "OK"}
  },
  "measurement_stats": {
    "obstacle_density": {"min": 0.05, "max": 0.1, "mean": 0.075, "samples": 2},
    "max_accel_mps2": {"min": 0.1082, "max": 0.1394, "mean": 0.1238, "samples": 2}
  },
  "compliance_stats": {
    "verdict": "IN_ODD",
    "confidence": 0.95,
    "temporal_stability": "STABLE",
    "critical_axes": []
  },
  "data_quality": {
    "all_agents_healthy": true,
    "missing_data_warnings": [],
    "anomalies": []
  }
}
```

### 2. `get_sensor_insights_tool()`

Returns qualitative insights from sensor agents (minimal tokens):

```json
{
  "perception_insights": ["Environment within ODD parameters", "Low obstacle density"],
  "motion_insights": ["Rotational motion dominant", "Acceleration within limits"],
  "collision_insights": ["No collisions detected", "Safe proximity maintained"],
  "evaluator_concerns": [],
  "evaluator_rationale": "All measurements within ODD boundaries..."
}
```

---

## LLM Output Schema

The LLM generates **only narrative fields** - no data copying:

```json
{
  "scenario_overview": "<1-2 sentences: what the robot was doing and where>",
  
  "compliance_verdict": "<IN_ODD | OUT_OF_ODD | BORDERLINE>",
  "confidence": "<HIGH | MEDIUM | LOW>",
  "stability": "<STABLE | UNSTABLE | TRANSITIONING>",
  
  "key_observations": [
    "<Most significant perception finding with numbers>",
    "<Most significant motion finding with numbers>",
    "<Most significant collision/safety finding with numbers>"
  ],
  
  "recommendations": [
    "<Action item or 'No action required - operation within ODD'>",
    "<Additional recommendation if warranted>"
  ],
  
  "pipeline_quality_assessment": "<1 sentence summarizing agent health>"
}
```

---

## Final Report Assembly (Python Post-Processing)

The `report_builder.py` module merges LLM synthesis with computed data:

### Executive Summary Report

```json
{
  "report_type": "executive_summary",
  "generated_at": "2025-11-26T15:34:40.444009Z",

  // LLM-synthesized (narrative)
  "scenario_overview": "The robot navigated an indoor commercial space...",
  "key_observations": ["Obstacle density low (0.02-0.08)...", ...],
  "recommendations": ["No action required..."],
  "pipeline_quality_assessment": "All agents executed successfully...",

  // Python-computed (deterministic)
  "compliance": {
    "verdict": "IN_ODD",
    "confidence": "HIGH",
    "confidence_value": 0.95,
    "stability": "STABLE",
    "critical_axes": []
  },
  "data_quality": {
    "all_agents_healthy": true,
    "warnings": [],
    "anomalies": []
  },
  "measurement_summary": {
    "obstacle_density": {"min": 0.02, "max": 0.08, "mean": 0.05},
    "max_accel_mps2": {"min": 0.1082, "max": 0.1394, "mean": 0.1238}
  },
  "scenario": {"name": "sim_test_w010_w011", "windows_analyzed": 2},
  "analysis": {"duration_seconds": 96.67, "total_tokens": 32576}
}
```

### Full Technical Report

Contains everything above plus:
- Raw agent outputs (audit trail)
- Per-window data (all measurements)
- Temporal analysis (trends, anomalies)
- ODD specification
- Pipeline metadata

---

## Model Selection

**Default:** `gemini-2.0-flash-exp`

The ReportAgent uses a fast model because:
- Synthesis is simpler than tool calling
- No complex reasoning required
- Cost optimization for final step

**Alternative:** Use `gemini-2.5-flash-preview` if synthesis quality needs improvement.

---

## Example Output

**Scenario:** sim_test_w010_w011 (2 windows, indoor commercial)

```json
{
  "scenario_overview": "The Unitree Go2 robot is navigating in an indoor commercial environment, rotating in place to change direction. The environment is brightly lit with smooth floors and sparse obstacles.",
  
  "compliance_verdict": "IN_ODD",
  "confidence": "HIGH",
  "stability": "STABLE",
  
  "key_observations": [
    "The robot operated in an indoor commercial environment with low obstacle density (0.02-0.08) and high traversability (0.9-0.95), adhering to the ODD.",
    "The robot primarily rotated in place, with angular velocity peaking at approximately 0.99 rad/s. Linear acceleration remained low at 0.11-0.14 m/s², well within the ODD limit of 10 m/s².",
    "No collisions were detected, and the robot maintained a minimum proximity of 0.8 meters to obstacles, ensuring safe operation."
  ],
  
  "recommendations": [
    "No action required - operation within ODD"
  ],
  
  "pipeline_quality_assessment": "All agents executed successfully with complete data across 2 windows."
}
```

---

## Synthesis Guidelines

### scenario_overview
- What robot, where, what doing
- 1-2 sentences max
- Plain English, no jargon

### key_observations
- One per sensor domain (perception, motion, collision)
- Include specific numbers for context
- Interpret what the data MEANS, don't just report it

### recommendations
- Actionable or "No action required"
- If issues found, be specific about what to do
- Prioritize most critical first

### pipeline_quality_assessment
- Summarize agent_health in one sentence
- Flag any warnings or anomalies
- Examples:
  - "All agents executed successfully with complete data across N windows."
  - "Motion agent reported N windows with zero acceleration - potential sensor issue."
  - "Perception data incomplete for 2 windows; results may be partial."

---

## Version History

| Version | Changes |
|---------|---------|
| 6.0.0 | Synthesis-focused design - LLM interprets, Python computes |
| 5.0.0 | Hybrid approach with statistics tool |
| 4.0.0 | File-based tool reading |
| 3.0.0 | Original blackboard-based design |

---

## Related Documentation

- **[Report Builder](../../odd_agents/report_builder.py):** Post-pipeline assembly
- **[Workflow](../../odd_agents/workflow.py):** Pipeline orchestration
- **[Phase 1.4.4 Summary](../PHASE_1_4_4_SUMMARY.md):** Architecture overview
