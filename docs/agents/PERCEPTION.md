# Perception Agent

## Overview

The **PerceptionAgent** performs **multimodal environment analysis** by combining camera and LiDAR data to understand the robot's surroundings. It produces environment classifications, obstacle assessments, and **data source detection** (simulated vs real).

**Version:** 7.4.0  
**Model:** gemini-2.5-flash  
**Purpose:** Per-window perception analysis with artifact-based output

---

## Architecture (Phase 1.4.5)

### Consolidated Agent Design

The PerceptionAgent v7.x is a **consolidated agent** that combines:
- Window iteration (previously PerceptionLoopAgent)
- Multimodal analysis (via perception tool)
- Data aggregation (previously PerceptionSummaryAgent)

### Artifact-Based Output

Instead of session state, the agent saves output to an artifact:

```python
# Agent saves output to artifact store
await artifact_service.save_artifact(
    "perception_output.json",
    perception_data,
    artifact_type="application/json"
)
```

This ensures reliable data handoff to the EvaluatorAgent.

---

## Tool: analyze_window_perception_tool

### Version: 5.1.0

### Purpose
Multimodal perception analysis of a single time window, including **data source detection**.

### Inputs

| Parameter | Type | Description |
|-----------|------|-------------|
| `window_id` | string | Window identifier (e.g., "010") |

The tool automatically loads:
- Camera image: `cam_{window_id}.png`
- LiDAR BEV: `bev_occupancy_{window_id}.png`

### Multimodal Fusion

- **Camera image**: Environment type, lighting, visual obstacles
- **LiDAR BEV**: Occupancy ratio, obstacle density, traversability
  - **Ground filtering**: BEV shows only obstacles >10cm above ground
  - **Robot position**: Center of 400×400 grid (pixel 200,200)
  - **Spatial layout**: Upper half = forward path

### Output Schema

```json
{
  "window_id": "010",
  "environment_type": "indoor_office",
  "lighting_class": "bright",
  "terrain_roughness_class": "smooth",
  "obstacle_density": 0.08,
  "traversability_score": 0.9,
  "occupancy_ratio": 0.05,
  "primary_obstacles": ["desk", "chair"],
  "evidence": "Well-lit office space with furniture...",
  "data_source": {
    "type": "simulated",
    "confidence": 0.95,
    "indicators": [
      "Perfect lighting uniformity",
      "Unnaturally clean surfaces",
      "Geometric precision in furniture"
    ]
  }
}
```

---

## Data Source Detection (New in v5.1.0)

### Purpose

Automatically identify whether sensor data is from simulation or real robot.

### How It Works

The perception tool prompts the model to assess data source from visual cues:

**Simulation Indicators:**
- Perfect lighting uniformity
- Unnaturally clean/smooth surfaces
- Geometric precision in object placement
- Lack of natural wear/imperfections
- Consistent shadows (no real-world variation)

**Real Data Indicators:**
- Natural lighting variations
- Surface imperfections/wear
- Organic object placement
- Sensor noise/artifacts
- Environmental clutter

### Output Format

```json
{
  "data_source": {
    "type": "simulated",    // or "real"
    "confidence": 0.95,     // 0.0 to 1.0
    "indicators": [
      "Perfect lighting uniformity",
      "Unnaturally clean surfaces"
    ]
  }
}
```

### Emergent Downstream Behavior

**Key Discovery:** Downstream agents (Motion, Collision, Evaluator, Report) naturally incorporate data_source context into their reasoning **without explicit prompting**.

Example from executive summary:
> "The robot successfully operated in a **simulated** indoor office environment..."

This demonstrates LLM reasoning capabilities - agents use available metadata to improve their analysis.

---

## Terrain Classification Guide

### terrain_roughness_class

| Class | Elevation Change | Examples |
|-------|-----------------|----------|
| `smooth` | <5cm | Flat floors, carpet, tile |
| `moderate` | 5-15cm | Small bumps, gentle slopes |
| `rough` | 15-30cm | Stairs, ramps, unpaved |
| `very_rough` | >30cm | Boulders, steep slopes |

**Important:** Terrain refers to **elevation changes**, not surface texture. A plush carpet on a flat floor is "smooth" terrain.

---

## Agent Output Schema

### Full PerceptionAgent Output

```json
{
  "windows_analyzed": ["010", "011"],
  "per_window_perception": [
    {
      "window_id": "010",
      "environment_type": "indoor_office",
      "lighting_class": "bright",
      "terrain_roughness_class": "smooth",
      "obstacle_density": 0.05,
      "traversability_score": 0.92,
      "occupancy_ratio": 0.05,
      "primary_obstacles": ["desk", "chair"],
      "evidence": "Well-lit office environment...",
      "data_source": {
        "type": "simulated",
        "confidence": 0.95,
        "indicators": ["Perfect lighting", "Clean surfaces"]
      }
    },
    {
      "window_id": "011",
      "environment_type": "indoor_office",
      "lighting_class": "bright",
      "terrain_roughness_class": "smooth",
      "obstacle_density": 0.08,
      "traversability_score": 0.90,
      "occupancy_ratio": 0.08,
      "primary_obstacles": ["desk", "cabinet"],
      "evidence": "Office space with sparse furniture...",
      "data_source": {
        "type": "simulated",
        "confidence": 0.92,
        "indicators": ["Uniform lighting", "Geometric precision"]
      }
    }
  ],
  "data_source_assessment": {
    "overall_type": "simulated",
    "confidence": 0.94,
    "window_consensus": "all windows identified as simulated"
  }
}
```

---

## Model Selection

**Current:** `gemini-2.5-flash`

**Why flash (not flash-lite):**
- Multimodal analysis requires reliable visual reasoning
- Data source detection benefits from stronger model
- Artifact saving ensures data reliability

**Alternative:** Use `gemini-2.5-pro` for:
- Complex scenes with many obstacles
- Critical applications requiring highest accuracy
- Low-light or degraded image quality

---

## Common Issues

### Issue 1: High occupancy ratio on flat floors
- **Symptom**: 70-80% occupancy on flat terrain
- **Cause**: Old data without ground filtering
- **Fix**: Regenerate data (10cm ground filtering applied in extraction)

### Issue 2: Terrain confusion
- **Symptom**: Carpet classified as "rough terrain"
- **Cause**: Model confusing texture with elevation
- **Fix**: Prompt clarifies terrain = elevation changes

### Issue 3: Data source detection errors
- **Symptom**: Real data marked as simulated
- **Cause**: Very clean real environment
- **Fix**: Check confidence value; low confidence (<0.7) indicates uncertainty

---

## Version History

| Version | Changes |
|---------|---------|
| 7.4.0 | Data source detection, artifact-based output |
| 7.3.0 | Consolidated agent (loop + summary merged) |
| 6.0.0 | Type-driven measurements |
| 5.0.0 | ODD-schema driven analysis |

---

## Related Documentation

- **[Agent Architecture](README.md)**: Pipeline overview
- **[Report Agent](REPORT.md)**: How data_source flows to reports
- **[Architecture Redesign](../ARCHITECTURE_REDESIGN.md)**: Full design rationale
