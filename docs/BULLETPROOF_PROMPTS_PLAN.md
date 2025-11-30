# Bulletproof Prompts Plan

## Problem Statement

The pipeline is producing **false OUT_ODD verdicts** due to confusion between:
1. **Obstacle proximity** (furniture, walls - measured from BEV) 
2. **Actor proximity** (humans, animals - should be assessed from camera only)

### Evidence from `real_2win` run (2024-11-30)

```
"min_proximity_m": 0.76m
```

The pipeline flagged this as OUT_ODD because:
- ODD spec says humans/animals must be >1.0m away
- BEV measured 0.76m to nearest obstacle
- Pipeline incorrectly treated obstacle distance as actor distance
- **No humans or animals were detected** (`humans_detected: false`)

This is a **critical false positive** - the robot was compliant but flagged as non-compliant.

---

## Root Cause Analysis

### Issue 1: ODD Spec Agent Ignoring Proximity Band Instructions

The prompt says:
```
- actors_categorical should include:
  - human_proximity_band: allowed ["medium", "far", "none"]
  - animal_proximity_band: allowed ["medium", "far", "none"]
- Do NOT use actors_numeric for proximity (no min_proximity_m)
```

But the agent created:
```json
"actors": {
  "numeric": {
    "min_proximity_m": {"min": 1, "max": 10, "type": "range"}
  }
}
```

**Root cause:** The prompt guidance is too easily ignored. The agent sees "1m safe distance" in the NL ODD and defaults to numeric.

### Issue 2: Perception Tool Conflating Obstacle & Actor Distance

The perception tool outputs BEV-derived `min_obstacle_distance_m` and this gets mapped to `min_proximity_m` somewhere in the pipeline.

The tool prompt clearly says:
```
⚠️ OBSTACLES are assessed from BEV occupancy:
- "min_obstacle_distance_m" from BEV metrics is to ANY obstacle (furniture, walls, etc.)
- This is NOT actor proximity - do not confuse them
```

But this isn't working reliably.

### Issue 3: COD Construction Has Lingering Legacy Mapping

In `cod_construction.py`, `_normalize_collision_measurements()`:
```python
if "proximity_estimate_m" in window_data:
    normalized["min_proximity_m"] = window_data["proximity_estimate_m"]
```

This maps collision proximity (obstacle) to `min_proximity_m` (actors).

---

## Proposed Changes (Minimal, No Major Refactors)

### Change 1: ODD Spec Agent - Hardcode Actor Proximity as Categorical

**File:** `odd_agents/agents/odd_spec.py`

**Current:** Agent decides whether to use categorical or numeric for actors.

**Proposed:** Make the prompt much more forceful:

```
## ACTOR PROXIMITY (MANDATORY - DO NOT USE NUMERIC)

The NL ODD mentions proximity to humans/animals. You MUST:
1. Create human_proximity_band as CATEGORICAL in actors_categorical
2. Create animal_proximity_band as CATEGORICAL in actors_categorical  
3. DO NOT create min_proximity_m or any numeric proximity axis
4. The camera CANNOT measure distance - only qualitative bands work

Allowed bands: ["medium", "far", "none"] (immediate/close = OUT OF ODD)

If the NL ODD says "1m safe distance", this maps to:
- immediate = <0.5m (OUT OF ODD)
- close = 0.5-1m (OUT OF ODD)
- medium = 1-3m (IN ODD)
- far = >3m (IN ODD)
- none = no actor detected (N/A)

⚠️ NEVER create actors_numeric for proximity. The system cannot reliably measure distance.
```

### Change 2: Perception Tool - Remove BEV Distance from ODD Measurements

**File:** `odd_agents/tools/perception.py`

**Current:** The tool outputs `min_obstacle_distance_m` from BEV.

**Proposed:** 
1. Keep BEV metrics for internal use (obstacle density, path blocked)
2. Do NOT output `min_obstacle_distance_m` as an ODD measurement
3. For actor detection, output ONLY categorical bands

Add to prompt:
```
## WHAT TO OUTPUT IN odd_measurements

For ACTORS (human_proximity_band, animal_proximity_band):
- Output the categorical band: "none", "far", "medium", "close", or "immediate"
- Base this on CAMERA visual analysis ONLY
- If no humans/animals detected, output "none"

DO NOT output any of these as ODD measurements:
- min_obstacle_distance_m (this is internal BEV data, not an ODD axis)
- min_proximity_m (this axis should not exist)
- Any numeric distance to actors (camera cannot measure this)
```

### Change 3: COD Construction - Remove Proximity Mapping

**File:** `odd_agents/tools/cod_construction.py`

**Current:** `_normalize_collision_measurements()` maps `proximity_estimate_m` → `min_proximity_m`

**Proposed:** Remove this mapping entirely. Collision proximity is advisory only.

```python
def _normalize_collision_measurements(raw: Dict[str, Any], window_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize collision measurements.
    Collision is ADVISORY ONLY - no measurements affect ODD compliance.
    """
    # Return empty - collision doesn't contribute ODD measurements
    return {}
```

### Change 4: Evaluator Agent - Add Actor Proximity Clarity

**File:** `odd_agents/agents/evaluator.py`

Add to the prompt:
```
## ACTOR PROXIMITY RULES

- human_proximity_band and animal_proximity_band are CATEGORICAL axes
- If band is "none" → N/A (no actor detected, skip this axis)
- If band is "far" or "medium" → IN ODD (compliant)
- If band is "close" or "immediate" → OUT OF ODD (violation)

- min_proximity_m should NOT exist as an axis
- If you see it, this is a specification error - flag it in key_concerns

- BEV obstacle distance (min_obstacle_distance_m) is NOT actor proximity
- A chair at 0.5m is NOT a human proximity violation
```

### Change 5: Perception Agent - Simplify Actor Detection Schema

**File:** `odd_agents/agents/perception.py`

Current output schema has:
```json
"actor_detection": {
    "humans_detected": true|false,
    "human_closest_band": "...",
    ...
}
```

This is good but add reinforcement:
```
## ACTOR DETECTION OUTPUT

Output EXACTLY this structure for each window:
{
  "human_proximity_band": "none|far|medium|close|immediate",
  "animal_proximity_band": "none|far|medium|close|immediate"
}

Rules:
- "none" if no human/animal detected
- Assess from CAMERA only (not BEV)
- Do NOT invent numeric distances
- If unsure between bands, choose the MORE conservative (farther) band
```

---

## Alternative: Binary Actor Presence

If categorical bands prove unreliable, simplify to binary:

### ODD Spec Change
```
actors_boolean:
- human_present: allowed=0 (humans present = OUT OF ODD)
- animal_present: allowed=0 (animals present = OUT OF ODD)
```

### Perception Change
```
For human_present and animal_present:
- Output 1 if ANY human/animal visible in camera
- Output 0 if no human/animal visible
```

This is simpler but loses granularity. The NL ODD says "persons within ~0.5-1m" is OUT OF ODD, implying presence at distance is OK. So categorical bands are preferred.

---

## Validation Checklist

After implementing changes, verify:

1. [ ] ODD spec agent NEVER creates `min_proximity_m` numeric axis
2. [ ] ODD spec agent ALWAYS creates `human_proximity_band` and `animal_proximity_band` as categorical
3. [ ] Perception tool outputs categorical bands, NOT numeric distances
4. [ ] COD construction does NOT map obstacle distance to actor proximity
5. [ ] Real scenario with no humans → "none" band → no proximity violation
6. [ ] Real scenario with humans at >1m → "medium" or "far" band → no violation
7. [ ] Real scenario with humans at <1m → "close" or "immediate" → OUT OF ODD

---

## Files to Modify

| File | Change | Risk |
|------|--------|------|
| `odd_agents/agents/odd_spec.py` | Harden proximity band instructions | Low |
| `odd_agents/tools/perception.py` | Remove min_obstacle_distance_m from ODD measurements | Low |
| `odd_agents/tools/cod_construction.py` | Remove collision→proximity mapping | Low |
| `odd_agents/agents/evaluator.py` | Add actor proximity clarity | Low |
| `odd_agents/agents/perception.py` | Reinforce categorical band output | Low |

---

## Estimated Impact

- **False positive reduction:** High (eliminates obstacle→actor confusion)
- **Breaking changes:** None (just prompt/logic fixes)
- **Token usage:** Neutral (slightly longer prompts, simpler outputs)
- **Test coverage:** Existing tests should pass, add specific actor proximity tests

---

## Next Steps

1. Review this plan
2. Implement changes one file at a time
3. Run `sim_2win` test to verify pipeline works
4. Run `real_2win` test to verify false positive is fixed
5. Commit with detailed message
