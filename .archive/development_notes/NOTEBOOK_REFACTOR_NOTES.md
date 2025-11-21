# ADK Notebook Refactor - Architecture Summary

**Commit:** c343093  
**Date:** 2025-11-18  
**Change Type:** Architecture refactor - eliminate cloud agent filesystem access

## Problem Solved

Original architecture had a **Data Loader Agent** that tried to call `load_all_scenario_data()` tool from the cloud (Gemini). Cloud agents can't access local filesystem, causing:
```
FileNotFoundError: No index file found in data/processed/runs/sim_run_test
```

## Solution: Pre-load Locally, Pass to Agents

```
┌─ NOTEBOOK KERNEL (local, has filesystem access) ──────────────┐
│                                                                 │
│  1. Load CSV index + PNG images from disk                      │
│  2. Convert to JSON + base64 (JSON-serializable)              │
│  3. Pass via state_delta to runner.run_debug()                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
          ↓
        STATE
          ↓
┌─ CLOUD AGENTS (Gemini - no filesystem access needed) ─────────┐
│                                                                 │
│  1. ODD Spec Agent reads scenario_data from state             │
│  2. Motion/Vision/Terrain/Collision agents (parallel)         │
│  3. COD Evaluator aggregates results                          │
│  4. Report Agent generates output with charts                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Changes Made

### 1. **Removed Data Loader Agent**
- **Before:** 8 agents (including Data Loader)
- **After:** 7 agents (no Data Loader)

### 2. **Added Section 3.5: Local Pre-loading**
```python
# Load from disk in notebook kernel
motion_json, camera_bytes, bev_bytes = load_window_data(...)

# Convert to JSON-serializable format
scenario_data = {
    "scenario": "sim_run_test",
    "windows": [
        {
            "window_id": "006",
            "motion_json": {...},                           # Already JSON
            "camera_png_base64": "iVBORw0KGgo...",        # base64 string
            "bev_png_base64": {                             # Dict of base64
                "occupancy": "iVBORw0KGgo...",
                "height": "iVBORw0KGgo...",
                ...
            }
        }
    ]
}
```

### 3. **Simplified Orchestration**
**SequentialAgent workflow:**
```python
root_agent = SequentialAgent(
    name="ODD_COD_Analysis_System",
    sub_agents=[
        odd_spec_agent,           # 1. Parse natural language ODD
        parallel_sensor_team,     # 2. Analyze all sensors in parallel
        cod_evaluator_agent,      # 3. Evaluate compliance
        report_agent              # 4. Generate report
    ]
)
# NO data_loader_agent needed!
```

### 4. **Updated Execution**
**Before:**
```python
response_events = await runner.run_debug(odd_natural_language)
# Agent tries to load data via tool → FileNotFoundError
```

**After:**
```python
initial_state = {
    "scenario_data": json.dumps(scenario_data)  # Pre-loaded!
}

response_events = await runner.run_debug(
    odd_natural_language,
    state_delta=initial_state  # Pass data directly
)
```

## Data Flow Details

### What Agents Read from State
```python
# Session state automatically available to all agents:
{
    "scenario_data": "JSON string with all windows",
    "odd_spec_json": "Parser output",
    "motion_features": "Motion analyzer output",
    "vision_features": "Vision analyzer output",
    "terrain_features": "Terrain analyzer output",
    "collision_features": "Collision analyzer output",
    "cod_evaluation": "COD evaluator output",
    "final_report": "Report generator output"
}
```

### How Agents Process Images
1. **Receive:** base64 PNG strings from `scenario_data`
2. **Decode:** `base64.b64decode(image_base64)` → raw PNG bytes
3. **Inference:** Pass to Gemini via `inline_data` with proper MIME type

**Example agent instruction snippet:**
```python
"""From scenario_data, you have access to:
- motion_json: Motion time series (already parsed JSON)
- camera_png_base64: Camera image as base64 PNG string
- bev_png_base64: Dict of BEV images as base64 PNG strings

For each window:
1. Decode base64 images back to PNG bytes
2. Analyze the motion_json and images
3. Return structured JSON with extracted features
"""
```

## Benefits of This Approach

| Aspect | Old | New |
|--------|-----|-----|
| **Filesystem Access** | Cloud agent tries (fails) | Local kernel only ✓ |
| **Agent Count** | 8 (includes Data Loader) | 7 (focused on reasoning) |
| **I/O Pattern** | Tool-based | Direct state pre-load ✓ |
| **API Calls** | 10-12 per run | 6-8 per run (fewer!) |
| **Code Complexity** | More (cross-process I/O) | Simpler (local only) |
| **Scalability** | Breaks with large data | Clean (local pre-load) |

## Testing the New Architecture

Run the refactored notebook:
```bash
# Cell 1: Imports
# Cell 2-3: Configuration  
# Cell 3.5: Pre-load data ← NEW, will show: "✅ Total windows pre-loaded: 2"
# Cell 4: Tools (motion/vision/terrain analysis)
# Cell 5-6: Agent definitions
# Cell 7: Execution ← Now uses state_delta
```

Expected execution flow:
```
✓ Loaded index: 2 windows
✓ Window 006: motion + camera + 4 BEV channels
✓ Window 007: motion + camera + 4 BEV channels
✅ Total windows pre-loaded: 2

EXECUTING ODD/COD ANALYSIS WORKFLOW
...
Workflow steps:
  1. ODD Spec: Convert NL → JSON
  2. Parallel Sensors: Motion, Vision, Terrain, Collision
  3. COD Evaluator: Aggregate against ODD
  4. Report: Generate markdown report

⚠️  Total: ~6-8 API calls on 2-window test set
```

## Next Steps

1. **Test execution** - Run the refactored notebook with actual Gemini API
2. **Monitor API calls** - Should be ~6-8 calls total (fewer than before)
3. **Validate agent outputs** - Check each agent's JSON output format
4. **Debug base64 decoding** - If vision agents struggle, check base64 → bytes conversion
5. **Scale to full dataset** - Test with `sim_run_new` (13 windows) if quota allows

## Architecture Decisions Documented

- ✅ Why no Data Loader Agent? I/O doesn't need AI reasoning
- ✅ Why base64 for transport? JSON serialization requirement for state_delta
- ✅ Why local pre-load? Avoids cloud agent filesystem access issues
- ✅ Why 7 agents? Maximum benefit-to-cost ratio (fewer calls, focused agents)

## References
- ADK Documentation: Session state management via `state_delta` in `run_debug()`
- Gemini API: `inline_data` for embedding images directly in multipart messages
- Architecture Pattern: Separation of concerns (I/O local, reasoning in cloud)
