# Bulletproof Prompts Plan

## Problem Statement

The pipeline is producing **false OUT_ODD verdicts** due to multiple issues:

### Evidence from `real_2win` run (2024-11-30)

**Issues flagged:**
1. Observed hazardous terrain 'unclassified_clutter' is not defined in the ODD
2. Observed terrain 'carpet' was flagged as outside ODD specifications
3. The minimum proximity to obstacles (0.76m) violated the specified safe distance for actors (1.0m)
4. Critically low traversability (0.1) in w010
5. Persistently low traversability scores (<0.3)

**Analysis:**
- Issue 1: Perception outputting "unclassified_clutter" - not a valid terrain type
- Issue 2: Perception outputting "carpet" but ODD allows "low_pile_carpet" - categorical matcher should handle this but may be failing
- Issue 3: **Critical bug** - BEV obstacle distance (0.76m) being treated as actor proximity
- Issues 4-5: Traversability being reported but it's unclear if this is even an ODD axis

---

## Root Cause Analysis

### Issue 1: Perception Outputting Invalid Terrain Types

**Problem:** Perception tool outputs "unclassified_clutter" which isn't a recognized terrain type.

**Root cause:** The VLA sees clutter on the floor and doesn't know what to call it. The prompt doesn't give guidance on what to do when terrain is unrecognizable.

**Fix:** Add to perception prompt:
```
For terrain_type:
- Output one of the ALLOWED values from ODD spec
- If unsure, output the CLOSEST match (e.g., if cluttered floor, output the base floor type visible)
- NEVER output "unclassified", "unknown", or made-up categories
- If truly unrecognizable terrain, output "other" and note in odd_concerns
```

### Issue 2: "carpet" vs "low_pile_carpet" Mismatch

**Problem:** Perception outputs "carpet" but ODD allows "low_pile_carpet", causing categorical mismatch.

**Root cause 1:** Perception prompt doesn't emphasize using EXACT ODD values.
**Root cause 2:** Categorical mismatch agent should score "carpet" → "low_pile_carpet" as 0.0 (superset) but may be failing.

**Fix 1:** Perception prompt:
```
For categorical axes, output EXACTLY one of the allowed values from the ODD spec.
Do NOT paraphrase or simplify (e.g., output "low_pile_carpet" not "carpet").
```

**Fix 2:** Verify categorical mismatch agent handles this case. May need to add example:
```
- 'carpet' is a superset of 'low_pile_carpet', 'area_rug' → score 0.0
```

### Issue 3: Obstacle Distance → Actor Proximity Confusion

**Problem:** BEV measures 0.76m to nearest obstacle (furniture/wall). This gets mapped to `min_proximity_m` (actor distance). No humans detected, but flagged as proximity violation.

**Root causes:**
1. ODD Spec agent creates `min_proximity_m` as numeric instead of categorical bands
2. Collision tool outputs `proximity_estimate_m` which gets mapped to `min_proximity_m`
3. COD construction has legacy mapping code

**Fixes:** (detailed in original plan)
- ODD Spec: Force categorical proximity bands for actors
- Perception: Don't output obstacle distance as ODD measurement
- COD Construction: Remove collision proximity → min_proximity_m mapping

### Issue 4-5: Traversability Reported But NOT In ODD Spec

**Problem:** Perception reports `traversability_score: 0.1` causing "critically low traversability" concerns, but **traversability_score is NOT defined in the generated ODD spec**.

**Evidence from real_2win:** The ODD spec has these axes:
- environment: lighting_conditions, terrain_type, obstacle_density, stairs_present
- actors: min_proximity_m  
- ego: max_speed_mps, max_accel_mps2, max_roll_deg, max_pitch_deg

**NO traversability_score axis exists**, yet it's being reported and flagged.

**Root causes:**
1. `odd_agents/tools/odd_spec.py` line 63 has traversability_score in the EXAMPLE
2. `odd_agents/tools/perception.py` line 84 outputs traversability_score unconditionally
3. Pipeline reports it as a concern even though it's not an ODD axis

**Fix:** 
1. Remove traversability from hardcoded examples in odd_spec.py
2. Perception should ONLY output measurements for axes that exist in ODD spec

---

## Proposed Changes (Updated)

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

### Change 2: Perception Tool - Strict ODD Axis Output

**File:** `odd_agents/tools/perception.py`

**Proposed additions to prompt:**

```
## CRITICAL OUTPUT RULES

1. ONLY output measurements for axes that EXIST in the ODD spec
   - Check the ODD spec for the exact axis names
   - Do NOT invent new axes (no "traversability_score" unless in spec)

2. For CATEGORICAL axes, output EXACTLY one of the allowed values
   - Do NOT paraphrase (output "low_pile_carpet" not "carpet")
   - Do NOT invent new values (no "unclassified_clutter")
   - If uncertain, pick the CLOSEST allowed value

3. For TERRAIN TYPE specifically:
   - Look at the ODD spec's terrain_type.allowed list
   - Output one value from that list
   - If you see carpet, check if "low_pile_carpet" or "area_rug" is allowed - use that
   - NEVER output "unclassified", "unknown", or "other"

4. For ACTOR PROXIMITY:
   - Output categorical bands only (none/far/medium/close/immediate)
   - Assess from CAMERA only, not BEV
   - Do NOT output any numeric distance

5. BEV metrics are for INTERNAL use only:
   - obstacle_density: OK to output as ODD measurement IF in spec
   - min_obstacle_distance_m: NEVER output (not an ODD axis)
```

### Change 3: COD Construction - Remove Collision Proximity Mapping

**File:** `odd_agents/tools/cod_construction.py`

**Current:**
```python
def _normalize_collision_measurements(raw, window_data):
    if "proximity_estimate_m" in window_data:
        normalized["min_proximity_m"] = window_data["proximity_estimate_m"]
```

**Proposed:**
```python
def _normalize_collision_measurements(raw, window_data):
    # Collision is ADVISORY ONLY - no measurements affect ODD compliance
    return {}
```

### Change 4: Categorical Mismatch Agent - Add Carpet Example

**File:** `odd_agents/tools/cod_construction.py`

Add to the categorical mismatch prompt:

```
ADDITIONAL RULES:

- 'carpet' is a superset of 'low_pile_carpet', 'area_rug', 'high_pile_carpet' → score 0.0
- 'wood' is a superset of 'hardwood', 'laminate' → score 0.0
- 'tile' includes 'ceramic_tile', 'porcelain_tile' → score 0.0

When the measured value is a GENERAL term and the ODD allowed values are SPECIFIC variants,
this is COMPATIBLE (score 0.0) because the robot IS on that type of surface.
```

### Change 5: Evaluator Agent - Actor Proximity Clarity

**File:** `odd_agents/agents/evaluator.py`

Add to prompt:
```
## ACTOR PROXIMITY RULES

- human_proximity_band and animal_proximity_band are CATEGORICAL axes
- If band is "none" → N/A (no actor detected, skip this axis in violation calc)
- If band is "far" or "medium" → IN ODD (compliant)
- If band is "close" or "immediate" → OUT OF ODD (violation)

- min_proximity_m should NOT exist as an axis
- If you see it, flag as spec error in key_concerns

- BEV obstacle distance is NOT actor proximity
- A chair at 0.5m is NOT a human proximity violation
```

### Change 6: Perception Agent Summary - Reinforce Band Output

**File:** `odd_agents/agents/perception.py`

Update the output schema in prompt:
```
"actor_detection": {
  "humans_detected": true|false,
  "human_proximity_band": "none|far|medium|close|immediate",  // REQUIRED
  "human_band_reasoning": "Full body visible, appears 3-4m away",
  "animals_detected": true|false,
  "animal_proximity_band": "none|far|medium|close|immediate",  // REQUIRED
  "animal_type": "dog|cat|other|none"
}

RULES:
- If humans_detected=false, human_proximity_band MUST be "none"
- If animals_detected=false, animal_proximity_band MUST be "none"
- Bands are assessed from CAMERA only
- Do NOT report numeric distances
```

### Change 7: Fix Traversability Threshold and Perception Calibration

**Files:** 
- `odd_agents/tools/odd_spec.py`
- `odd_agents/agents/perception.py`

**Problem:** 
1. ODD Spec may set traversability min too high (e.g., 0.7)
2. Perception reports 0.1 for indoor clutter when it should be ~0.6-0.7

**What traversability ACTUALLY means:**
- **0.0-0.2:** Truly impassable - rocky outcroppings, steep drops, dense brush
- **0.3-0.5:** Difficult terrain - outdoor uneven ground, construction debris
- **0.6-0.8:** Normal indoor - carpet with clutter, furniture to navigate around
- **0.9-1.0:** Clear path - empty hallway, open floor

**Fix odd_spec.py - Add guidance:**
```
For traversability_score:
- Indoor ODDs: min=0.3 (only truly blocked paths are OUT OF ODD)
- Outdoor ODDs: min=0.2 (rougher terrain expected)
- Do NOT set min=0.7+ unless robot requires perfectly clear paths
```

**Fix perception.py - Calibrate scoring:**
```
## TRAVERSABILITY CALIBRATION

traversability_score reflects path navigability, NOT tidiness:
- 0.9-1.0: Clear, open path (empty room, hallway)
- 0.7-0.9: Minor obstacles easily avoided (some furniture)
- 0.5-0.7: Moderate clutter, navigable with care (typical lived-in room)
- 0.3-0.5: Significant obstacles but passable (crowded space)
- 0.1-0.3: Barely passable (dense clutter, narrow gaps)
- 0.0-0.1: Impassable (blocked doorway, cliff edge, dense rocks)

Indoor clutter (rugs, toys, cables) = 0.5-0.7, NOT 0.1
A messy room is NOT the same as a rocky outcropping.
```

---

## Alternative: Binary Actor Presence

If categorical bands prove unreliable, simplify to binary:

**ODD Spec:**
```
actors_boolean:
- human_present: allowed=0 (humans present = OUT OF ODD)
- animal_present: allowed=0 (animals present = OUT OF ODD)
```

**Perception:**
```
- Output 1 if ANY human/animal visible in camera
- Output 0 if no human/animal visible
```

Simpler but loses granularity. Categorical bands preferred since NL ODD implies presence at distance is OK.

---

## Validation Checklist

After implementing changes, verify:

1. [ ] ODD spec agent NEVER creates `min_proximity_m` numeric axis
2. [ ] ODD spec agent ALWAYS creates `human_proximity_band` and `animal_proximity_band` as categorical
3. [ ] ODD spec agent sets traversability_score min ~0.3 for indoor ODDs (not 0.7+)
4. [ ] Perception tool outputs categorical bands, NOT numeric distances
5. [ ] Perception tool outputs EXACT allowed values for terrain_type
6. [ ] Perception tool reports ~0.6-0.7 traversability for typical indoor clutter (not 0.1)
7. [ ] COD construction does NOT map obstacle distance to actor proximity
8. [ ] Real scenario with no humans → "none" band → no proximity violation
9. [ ] Terrain "carpet" matches "low_pile_carpet" with distance 0.0

---

## Files to Modify

| File | Change | Risk |
|------|--------|------|
| `odd_agents/agents/odd_spec.py` | Harden proximity band + traversability threshold guidance | Low |
| `odd_agents/tools/perception.py` | Strict ODD axis output rules | Low |
| `odd_agents/tools/cod_construction.py` | Remove collision→proximity mapping + superset examples | Low |
| `odd_agents/agents/evaluator.py` | Add actor proximity clarity | Low |
| `odd_agents/agents/perception.py` | Reinforce categorical band output + traversability calibration | Low |

---

## Next Steps

1. ✅ Review this plan
2. Implement changes one file at a time
3. Run `sim_2win` test to verify pipeline works
4. Run `real_2win` test to verify false positives fixed
5. Commit with detailed message
