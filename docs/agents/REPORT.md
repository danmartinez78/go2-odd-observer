# Report Agent

## Overview

The **ReportAgent** is the final agent in the ODD analysis workflow. It synthesizes all pipeline data into a comprehensive report with executive summary, key findings, and actionable recommendations.

**Version:** 9.1.0  
**Model:** gemini-2.5-flash  
**Purpose:** Generate hybrid report with narrative synthesis + computed data

---

## Architecture: Hybrid Schema Design (v9.1.0)

### Key Principle: Structured Fields + Narrative Synthesis

The ReportAgent v9.1.0 uses a **hybrid schema** that combines:
- **Structured fields**: compliance, scenario_metadata, issues
- **Narrative fields**: executive_summary, key_findings, recommendations

```json
{
  "compliance": {
    "verdict": "IN_ODD",
    "confidence_value": 0.85,
    "region_distance": 0.0,
    "stability": "stable",
    "critical_axes": []
  },
  "executive_summary": "The robot successfully operated in a simulated indoor office environment...",
  "key_findings": [
    "Environment within ODD parameters",
    "Motion patterns indicate stationary rotation",
    "No collision events detected"
  ],
  "scenario_metadata": {
    "data_source": "simulated",
    "window_count": 2,
    "scenario_id": "sim_test_w010_w011"
  },
  "issues": [],
  "recommendations": ["No action required - operation within ODD"]
}
```

---

## Tool: generate_report_tool

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `compliance_verdict` | string | IN_ODD, OUT_ODD, or BOUNDARY |
| `confidence_value` | float | 0.0-1.0 confidence in verdict |
| `region_distance` | float | Distance from ODD boundary |
| `stability` | string | temporal stability assessment |
| `critical_axes` | list | Axes with violations |
| `executive_summary` | string | 2-3 sentence scenario summary |
| `key_findings` | list | Top 3-5 observations |
| `recommendations` | list | Actionable suggestions |
| `issues` | list | Problems or warnings |
| `scenario_data_source` | string | "simulated" or "real" |

### Example Tool Call

```json
{
  "name": "generate_report_tool",
  "args": {
    "compliance_verdict": "IN_ODD",
    "confidence_value": 0.85,
    "region_distance": 0.0,
    "stability": "stable",
    "critical_axes": [],
    "executive_summary": "The robot successfully operated in a simulated indoor office environment with low obstacle density and smooth terrain. All measurements remained within ODD boundaries throughout the analysis window.",
    "key_findings": [
      "Environment type matches ODD: indoor commercial/office setting",
      "Obstacle density (0.02-0.08) well below 0.6 limit",
      "Peak acceleration (0.14 m/s²) far below 10 m/s² limit"
    ],
    "recommendations": ["No action required - operation within ODD"],
    "issues": [],
    "scenario_data_source": "simulated"
  }
}
```

---

## Data Source Integration

### How Data Source Flows

1. **PerceptionAgent** detects simulated vs real from visual cues
2. **Artifact** stores `data_source` in perception output
3. **EvaluatorAgent** passes data_source to report context
4. **ReportAgent** includes in `scenario_metadata`

### Emergent Behavior

Downstream agents naturally incorporate data_source context without explicit prompting:
- Executive summary mentions "simulated environment"
- Key findings reference "simulation" characteristics
- Demonstrates LLM reasoning from metadata

---

## Model Selection

**Current:** `gemini-2.5-flash`

**Why upgraded from flash-lite (v9.0.0 → v9.1.0):**
- flash-lite wasn't reliably calling tools
- flash provides consistent tool calling
- Cost difference minimal at report stage

---

## Example Output

### 2-Window Test (sim_test_w010_w011)

```json
{
  "compliance": {
    "verdict": "IN_ODD",
    "confidence_value": 0.85,
    "region_distance": 0.0,
    "stability": "stable",
    "critical_axes": []
  },
  "executive_summary": "The robot successfully operated in a **simulated** indoor office environment with smooth terrain and low obstacle density. The robot demonstrated controlled rotational behavior with all sensor readings within normal operational parameters.",
  "key_findings": [
    "Environment consistently matched ODD specifications for indoor commercial/office settings",
    "Obstacle density remained low (0.02-0.08), well within the 0.6 maximum threshold",
    "Motion analysis confirmed stationary rotation with peak acceleration (0.14 m/s²) far below limits",
    "No collision events detected across both analysis windows"
  ],
  "scenario_metadata": {
    "data_source": "simulated",
    "window_count": 2,
    "scenario_id": "sim_test_w010_w011"
  },
  "issues": [],
  "recommendations": [
    "No action required - operation within ODD",
    "Consider testing with real-world data to validate sim-to-real transfer"
  ]
}
```

---

## Display Output

The `display_summary()` function in `run_odd_analysis.py` formats the report for terminal:

```
╔════════════════════════════════════════════════════════════════╗
║                      ODD ANALYSIS SUMMARY                       ║
╚════════════════════════════════════════════════════════════════╝

┌─ COMPLIANCE ─────────────────────────────────────────────────────┐
│ Verdict: IN_ODD                                                  │
│ Confidence: 0.85                                                 │
│ Region Distance: 0.0                                             │
│ Stability: stable                                                │
│ Critical Axes: none                                              │
└──────────────────────────────────────────────────────────────────┘

┌─ EXECUTIVE SUMMARY ──────────────────────────────────────────────┐
│ The robot successfully operated in a simulated indoor office     │
│ environment with smooth terrain and low obstacle density...      │
└──────────────────────────────────────────────────────────────────┘

┌─ KEY FINDINGS ───────────────────────────────────────────────────┐
│ • Environment consistently matched ODD specifications            │
│ • Obstacle density remained low (0.02-0.08)                      │
│ • No collision events detected                                   │
└──────────────────────────────────────────────────────────────────┘

┌─ SCENARIO METADATA ──────────────────────────────────────────────┐
│ Data Source: simulated                                           │
│ Windows: 2                                                       │
│ Scenario: sim_test_w010_w011                                     │
└──────────────────────────────────────────────────────────────────┘
```

---

## Version History

| Version | Changes |
|---------|---------|
| 9.1.0 | Hybrid schema + data_source + flash model for reliable tool calling |
| 9.0.0 | Hybrid schema with compliance, executive_summary, key_findings |
| 6.0.0 | Synthesis-focused design - LLM interprets, Python computes |
| 5.0.0 | Hybrid approach with statistics tool |
| 4.0.0 | File-based tool reading |

---

## Related Documentation

- **[Agent Architecture](README.md)**: Pipeline overview
- **[Perception Agent](PERCEPTION.md)**: Data source detection
- **[Architecture Redesign](../ARCHITECTURE_REDESIGN.md)**: Full design rationale
