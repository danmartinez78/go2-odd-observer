# Pipeline Refactor Audit

## Reference Architecture

From `DATA_FLOW_ARCHITECTURE.md`, the target pattern is:

```
TOOL: Per-window analysis → ARTIFACT (full detail) + Return to Agent
AGENT: Temporal/higher-order analysis → SESSION (summary)
```

This document audits each agent and tool against this pattern.

---

## Audit Summary

| Component | Tool Batch? | Artifact Write? | Tool Returns Full Data? | Agent Does Summary? | State Key Correct? | Status |
|-----------|-------------|-----------------|------------------------|--------------------|--------------------|--------|
| OddSpec | N/A | ✅ | ✅ Fixed | ✅ Full spec + summary | ✅ `temp:odd_spec` | ✅ DONE |
| Perception | ✅ | ✅ | ✅ | ✅ Fixed | ✅ `temp:perception_summary` | ✅ DONE |
| Motion | ✅ | ✅ | ✅ | ✅ Fixed | ✅ `temp:motion_summary` | ✅ DONE |
| Collision | ✅ | ✅ Fixed | ✅ | ✅ Fixed | ✅ `temp:collision_summary` | ✅ DONE |
| Evaluator | N/A | ✅ Fixed | ✅ | ✅ | ✅ `temp:evaluator_output` | ✅ DONE |
| Report | N/A | N/A | N/A | ✅ | ✅ `temp:report_output` | ✅ DONE |

**Note**: OddSpec is unique - outputs BOTH full spec AND summary to session (downstream agents need exact axis definitions).

---

## 1. ODD Spec Agent

### Files
- Agent: `odd_agents/agents/odd_spec.py`
- Tool: `odd_agents/tools/odd_spec.py`

### Tool: `save_odd_spec_tool`

**Scope**: ✅ Correct - Not per-window (ODD is scenario-level)

**Artifact Write**: ✅ Correct
```python
artifact = gtypes.Part.from_bytes(data=json_bytes, mime_type="application/json")
version = await tool_context.save_artifact(filename="odd_spec.json", artifact=artifact)
```

**Return Value**: ❌ ISSUE - Returns summary, not full spec
```python
return {
    "status": "saved",
    "artifact": "odd_spec.json",
    "version": version,
    "total_axes": total_axes,
    "domains": {
        "environment": {"count": env_count, "axes": env_axes},
        # ...
    }
}
```

**Expected**: Should return full `odd_specification` dict so agent can create summary.

### Agent Prompt

**Output Instruction**: ❌ ISSUE
```
After tool call, output a brief summary of axes created
```

**Expected Pattern**: Agent receives full spec from tool, creates summary for downstream.

**Current Problem**: Tool returns summary → Agent has no full data to work with.

### Recommended Fixes

1. **Tool**: Return full spec plus metadata
```python
return {
    "status": "saved",
    "artifact": "odd_spec.json",
    "version": version,
    "odd_specification": odd_specification,  # ADD: full spec
    "total_axes": total_axes,
    "domains": {...}
}
```

2. **Agent Prompt**: Add summary instructions
```
After receiving tool result, output a JSON summary for downstream agents:
{
  "total_axes": <from tool>,
  "key_constraints": ["axis1: range 0-10", "axis2: enum [a,b,c]", ...],
  "environment_axes": [...],
  "actors_axes": [...],
  "ego_axes": [...]
}
```

---

## 2. Perception Agent

### Files
- Agent: `odd_agents/agents/perception.py`
- Tool: `odd_agents/tools/perception.py`

### Tool: `analyze_all_perception_tool`

**Batch Processing**: ✅ Correct - Processes all windows in one call
```python
windows = list_available_windows(scenario_path, require_motion=True)
for window_id in windows:
    result = await _analyze_single_window(window_id, odd_context)
    per_window.append(result)
```

**Per-Window Analysis Scope**: ✅ Correct - Each window gets:
- `odd_measurements` (categorical + numeric values)
- `data_source`
- `explanation`
- `key_insights`

**Artifact Write**: ✅ Correct
```python
output_data = {
    "per_window": per_window,
    "windows_analyzed": len(per_window),
}
version = await tool_context.save_artifact(filename="perception_output.json", artifact=artifact)
```

**Return Value**: ✅ Correct - Returns full per_window data
```python
return {
    "status": "success",
    "per_window": per_window,
    "windows_analyzed": len(per_window),
}
```

### Agent Prompt

**Current Instruction**: ❌ ISSUE - Just echoes tool output
```
OUTPUT: Return the tool result as your final JSON output (no modifications needed).
Include per_window from the tool response.
```

**Expected Pattern**: Agent should do TEMPORAL ANALYSIS and output SUMMARY, not raw per_window.

### Recommended Fixes

1. **Agent Prompt**: Add temporal analysis and summary step
```
WORKFLOW:
1. Extract relevant ODD dimensions (environment, terrain, obstacles, actors)
2. Call analyze_all_perception_tool(odd_context) - receives all window results
3. ANALYZE temporally:
   - Identify trends (improving/degrading lighting, obstacle density changes)
   - Flag anomalies (sudden changes between windows)
   - Note critical issues (stairs detected, humans in path, etc.)
4. OUTPUT summary JSON:

{
  "windows_analyzed": <count>,
  "temporal_analysis": {
    "trend": "stable|improving|degrading",
    "pattern_notes": ["lighting consistent", "obstacle density increasing"]
  },
  "summary": {
    "dominant_environment": "indoor_commercial",
    "lighting_range": "moderate to bright",
    "max_obstacle_density_pct": 35,
    "traversability_range": [0.6, 0.9],
    "stairs_detected": false,
    "humans_detected": true
  },
  "issues": ["Human detected at 0.8m in w002"],
  "alerts": ["Obstacle density peak in w003"]
}

Do NOT output raw per_window data - that's in the artifact.
```

2. **State Key**: Rename to `temp:perception_summary` (consistency)

---

## 3. Motion Agent

### Files
- Agent: `odd_agents/agents/motion.py`
- Tool: `odd_agents/tools/motion.py`

### Tool: `analyze_all_motion_tool`

**Batch Processing**: ✅ Correct - Same pattern as perception

**Per-Window Analysis Scope**: ✅ Correct - Each window gets:
- `odd_measurements` (max_accel, max_speed, roll, pitch, jerk, angular_velocity)
- `is_stationary` with confidence and evidence
- `motion_state`
- `explanation`
- `key_insights`

**Artifact Write**: ✅ Correct
```python
output_data = {"per_window": per_window, "windows_analyzed": len(per_window)}
version = await tool_context.save_artifact(filename="motion_output.json", artifact=artifact)
```

**Return Value**: ✅ Correct
```python
return {"status": "success", "per_window": per_window, "windows_analyzed": len(per_window)}
```

### Agent Prompt

**Current Instruction**: ❌ ISSUE - Same as perception, just echoes
```
OUTPUT: Return the tool result as your final JSON output (no modifications needed).
Include per_window from the tool response.
```

### Recommended Fixes

1. **Agent Prompt**: Add temporal analysis
```
WORKFLOW:
1. Extract relevant ODD dimensions (ego motion: speed, accel, stability)
2. Call analyze_all_motion_tool(odd_context) - receives all window results
3. ANALYZE temporally:
   - Motion state transitions (stationary → moving → rotating)
   - Stability trends (roll/pitch envelope)
   - Anomaly detection (sudden acceleration spikes, jerk)
4. OUTPUT summary JSON:

{
  "windows_analyzed": <count>,
  "temporal_analysis": {
    "motion_transitions": ["stationary→moving at w002", "stable throughout"],
    "stability_trend": "stable|degrading|improving"
  },
  "summary": {
    "dominant_motion_state": "moving",
    "max_accel_observed_mps2": 2.3,
    "max_roll_observed_deg": 8.5,
    "max_pitch_observed_deg": 12.1,
    "peak_jerk_observed_mps3": 15.2,
    "stationary_windows": ["w001"]
  },
  "issues": ["Peak pitch 12.1° in w003 - near limit"],
  "alerts": ["High jerk detected in w002"]
}

Do NOT output raw per_window data - that's in the artifact.
```

2. **State Key**: Rename to `temp:motion_summary` (consistency)

---

## 4. Collision Agent

### Files
- Agent: `odd_agents/agents/collision.py`
- Tool: `odd_agents/tools/collision.py`

### Tool: `analyze_all_collision_tool`

**Batch Processing**: ✅ Correct

**Per-Window Analysis Scope**: ✅ Correct - Each window gets:
- `collision_detected` (bool)
- `confidence`
- `proximity_estimate_m`
- `collision_risk_band`
- `explanation`
- `key_insights`

**Artifact Write**: ⚠️ Conditional - Only if tool_context provided
```python
if tool_context:
    try:
        version = await tool_context.save_artifact(filename="collision_output.json", artifact=artifact)
```

**Return Value**: ✅ Correct
```python
return {"status": "success", "per_window": per_window, "windows_analyzed": len(per_window), "collisions_detected": collisions_detected}
```

### Agent Prompt

**Current Instruction**: ❌ ISSUE - Same pattern, just echoes
```
OUTPUT: Return the tool result as your final JSON output (no modifications needed).
Include per_window and collision_stats from the tool response.
```

### Recommended Fixes

1. **Tool**: Remove conditional artifact save - always save
```python
# Remove: if tool_context:
try:
    version = await tool_context.save_artifact(filename="collision_output.json", artifact=artifact)
```

2. **Agent Prompt**: Add temporal analysis
```
WORKFLOW:
1. Call analyze_all_collision_tool(odd_context, motion_results)
2. ANALYZE temporally:
   - Collision event patterns (isolated vs repeated)
   - Risk band progression
   - Correlation with motion state (if stationary + collision → suspicious)
3. OUTPUT summary JSON:

{
  "windows_analyzed": <count>,
  "temporal_analysis": {
    "collision_pattern": "none|isolated|repeated",
    "risk_progression": "stable|escalating|de-escalating"
  },
  "summary": {
    "total_collisions_detected": 0,
    "max_risk_band": "LOW",
    "min_proximity_m": 1.2,
    "suspicious_events": []
  },
  "issues": [],
  "alerts": [],
  "advisory_note": "Collision is advisory only - does not affect ODD verdict"
}

Do NOT output raw per_window data - that's in the artifact.
```

3. **State Key**: Rename to `temp:collision_summary` (consistency)

---

## 5. Evaluator Agent

### Files
- Agent: `odd_agents/agents/evaluator.py`
- Tool: Defined inline in `evaluator.py` (construct_cod_tool, save_evaluator_output_tool)

### Tool: `construct_cod_tool`

**Scope**: ✅ Correct - Aggregates all artifacts, computes COD

**Loads Artifacts**: ✅ Correct
```python
odd_artifact = await tool_context.load_artifact(filename="odd_spec.json")
p_artifact = await tool_context.load_artifact(filename="perception_output.json")
m_artifact = await tool_context.load_artifact(filename="motion_output.json")
c_artifact = await tool_context.load_artifact(filename="collision_output.json")
```

**Return Value**: ✅ Correct - Returns full COD data
```python
return json.dumps({
    "cod_region": cod_region,
    "time_series": time_series,
    "region_metrics": region_metrics,
    "artifacts_loaded": {...}
}, indent=2)
```

**Artifact Write**: ❌ MISSING - construct_cod_tool doesn't save artifact

### Tool: `save_evaluator_output_tool`

**Artifact Write**: ✅ Correct
```python
version = await tool_context.save_artifact(filename="evaluator_output.json", artifact=artifact)
```

**Return Value**: ✅ Correct - Returns full data
```python
return output_data  # Full dict, not just status
```

### Agent Prompt

**Current Instruction**: ⚠️ Complex but functional

The prompt correctly instructs:
1. Call construct_cod_tool() first
2. Do analysis (per-axis, cross-agent consistency)
3. Output structured verdict JSON
4. Call save_evaluator_output_tool() to persist

**Issues**:
1. `construct_cod_tool` should save artifact for consistency
2. State references use `temp:perception_output` etc. but we're renaming to `_summary`

### Recommended Fixes

1. **construct_cod_tool**: Add artifact save
```python
# After computing COD:
try:
    json_bytes = json.dumps(result, indent=2).encode('utf-8')
    artifact = gtypes.Part.from_bytes(data=json_bytes, mime_type="application/json")
    version = await tool_context.save_artifact(filename="cod_construction.json", artifact=artifact)
    print(f"🟣 [CONSTRUCT_COD_TOOL] Saved artifact v{version}")
except Exception as e:
    print(f"🟣 [CONSTRUCT_COD_TOOL] Artifact save failed: {e}")
```

2. **Agent Prompt**: Update state references when sensor agents change
```
# Current:
**Perception insights:** {temp:perception_output}
**Motion insights:** {temp:motion_output}
**Collision insights:** {temp:collision_output}

# After sensor agent fixes:
**Perception insights:** {temp:perception_summary}
**Motion insights:** {temp:motion_summary}
**Collision insights:** {temp:collision_summary}
```

---

## 6. Report Agent

### Files
- Agent: `odd_agents/agents/report.py`

### Pattern

**No Tools**: ✅ Correct - Report agent just reads state and outputs

**Reads State**: ✅ Correct
```python
{temp:evaluator_output}
{temp:perception_output}
{temp:motion_output}
{temp:collision_output}
```

**Output**: ✅ Correct - Structured JSON for human consumption

### Recommended Fixes

1. **Update state references when sensor agents change**
```
# After sensor agent fixes:
{temp:perception_summary}
{temp:motion_summary}
{temp:collision_summary}
```

---

## Summary of Required Changes

### High Priority (Breaking Issues)

1. **Sensor Agent Prompts** (perception, motion, collision):
   - Remove "echo tool output directly"
   - Add temporal analysis instructions
   - Add summary output format (not raw per_window)

2. **State Key Consistency**:
   - `temp:perception_output` → `temp:perception_summary`
   - `temp:motion_output` → `temp:motion_summary`
   - `temp:collision_output` → `temp:collision_summary`

3. **OddSpec Tool Return**:
   - Return full spec, not just summary metadata

### Medium Priority (Completeness)

4. **construct_cod_tool**:
   - Add artifact save (`cod_construction.json`)

5. **Collision Tool**:
   - Remove conditional artifact save (always save)

### Low Priority (Consistency)

6. **Update all downstream state references**:
   - Evaluator prompt
   - Report prompt

---

## Implementation Order

1. Fix sensor tool returns (if needed - perception/motion already OK)
2. Fix sensor agent prompts (temporal analysis + summary output)
3. Update sensor agent output_key values
4. Update Evaluator prompt state references
5. Update Report prompt state references
6. Add artifact save to construct_cod_tool
7. Test end-to-end with sim_2win

---

## State Key Mapping (Before → After)

| Current | Proposed | Rationale |
|---------|----------|-----------|
| `temp:odd_spec` | `temp:odd_spec` | Keep - not per-window |
| `temp:perception_output` | `temp:perception_summary` | Clarity: it's a summary |
| `temp:motion_output` | `temp:motion_summary` | Clarity: it's a summary |
| `temp:collision_output` | `temp:collision_summary` | Clarity: it's a summary |
| `temp:evaluator_output` | `temp:evaluator_output` | Keep - already a summary |
| `temp:report_output` | `temp:report_output` | Keep - final output |

---

## Artifact Naming (Confirmed)

| Artifact | Saved By | Contents |
|----------|----------|----------|
| `odd_spec.json` | save_odd_spec_tool | Full ODD specification |
| `perception_output.json` | analyze_all_perception_tool | All per-window perception |
| `motion_output.json` | analyze_all_motion_tool | All per-window motion |
| `collision_output.json` | analyze_all_collision_tool | All per-window collision |
| `cod_construction.json` | construct_cod_tool (ADD) | Full COD + metrics |
| `evaluator_output.json` | save_evaluator_output_tool | Verdict + analysis |
