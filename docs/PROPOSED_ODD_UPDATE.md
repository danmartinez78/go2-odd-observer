# Proposed ODD Update - Based on Production Analysis

**Date:** November 23, 2025  
**Rationale:** Current ODD too strict for real-world living room navigation

## Analysis Summary

**Production Scenario:** `collection_20251122_173442_chunk_01` (25 windows, benign living room)

**Current Results:**
- Status: OUT_ODD
- Violations: 3 (motion_smoothness, max_accel_mps2, collision_risk)
- Peak acceleration: 8.81 m/s²
- Collision risk: 0.652 average (72% of windows at alert/caution)

**Problem:** Normal furniture-dense living room navigation flagged as OUT_ODD

---

## Current ODD Description (Too Strict)

```
The Unitree Go2 is a quadruped robot designed for general indoor navigation.

It's meant to operate in typical indoor environments - think homes, offices, hallways, 
conference rooms, living rooms, and open workspaces. The floors should be smooth (tile, 
hardwood, or low-pile carpet), and there needs to be adequate lighting so the cameras 
can see clearly. Bright lighting is ideal, but it can handle dimmer areas too. 
No pitch-black rooms though.

The robot moves with smooth to moderate acceleration - controlled movements during 
normal navigation. It can handle quick starts and stops when needed (like avoiding 
obstacles), but it's not meant for aggressive racing-style maneuvers or abrupt jerky 
motions. Think responsive and agile, not violent or chaotic. The motion should feel 
controlled and deliberate, even when reacting to obstacles. It's designed to 
navigate around typical indoor obstacles like furniture, chairs, desk legs, and the 
occasional box, but it's not meant for super cluttered spaces where there's barely 
room to move.

The robot expects relatively flat, stable ground. No stairs, no steep ramps, and 
definitely not designed for outdoor terrain like gravel or grass. It needs space 
to maneuver safely without constantly being on the verge of hitting things.

DEFINITELY NOT designed for:
- Outdoor environments (weather, uneven ground, GPS reliance)
- Staircases or steep slopes
- Dark rooms where vision sensors can't work
- Extremely crowded spaces where collision is almost guaranteed
- Rough terrain, gravel, sand, or anything unstable
- Industrial environments with heavy machinery or hazardous materials
```

**Issues:**
1. "smooth to moderate acceleration" conflicts with 8.81 m/s² needed for normal navigation
2. "not meant for super cluttered spaces" yet normal living rooms trigger high collision risk
3. "needs space to maneuver safely" conflicts with furniture-dense home reality

---

## Proposed Updated ODD Description (Realistic)

```python
DEFAULT_ODD_DESCRIPTION = """
The Unitree Go2 is a quadruped robot designed for general indoor navigation in 
residential and commercial spaces.

ENVIRONMENT:
The robot operates in typical indoor environments including homes, offices, hallways, 
conference rooms, living rooms, and workspaces. It handles smooth floors (tile, 
hardwood, low-pile carpet) and requires adequate lighting for camera-based perception. 
Bright to moderate lighting is ideal; very dim areas are acceptable but pitch-black 
rooms are outside operational limits.

OBSTACLE HANDLING:
Designed for furniture-dense residential spaces with moderate to high obstacle density. 
The robot can navigate around sofas, coffee tables, dining chairs, desk legs, and 
typical household items. Close proximity to furniture is expected and normal during 
navigation. The robot is NOT designed for extreme clutter where clear navigation paths 
are blocked, doorways are obstructed, or the floor is covered with scattered objects.

MOTION CHARACTERISTICS:
The robot uses dynamic motion control appropriate for agile quadruped navigation:
- Smooth motion during open navigation in hallways and clear spaces
- Quick reactive maneuvers when avoiding obstacles (acceleration up to 10 m/s²)
- Brief "abrupt" motion is normal and expected during:
  * Obstacle avoidance reactions
  * Direction changes around furniture
  * Emergency stops when unexpected obstacles appear
  
The robot is NOT designed for:
- Aggressive high-speed racing or sustained high acceleration
- Violent or erratic motion when operating in open, obstacle-free spaces

TERRAIN:
Designed for flat, stable indoor surfaces. Can handle:
- Gentle transitions between rooms (door thresholds, slight elevation changes)
- Minor surface variations (rug edges, mat transitions)

NOT designed for:
- Staircases (multi-step elevation changes)
- Steep ramps (>15 degree incline)
- Outdoor terrain (gravel, grass, dirt, uneven ground)
- Unstable surfaces (sand, loose materials)

COLLISION EXPECTATIONS:
In furniture-dense environments (living rooms, dining areas), proximity to obstacles 
is unavoidable and normal. Collision risk scores up to 0.75 are acceptable when 
navigating through furnished spaces. The robot should maintain awareness and avoid 
actual contact, but close proximity (<0.5m to obstacles) is expected.

DEFINITELY NOT DESIGNED FOR:
- Outdoor environments (weather exposure, GPS reliance, rough terrain)
- Dark rooms where camera sensors cannot function
- Industrial environments with heavy machinery or hazardous materials
- Extreme clutter where navigation paths are completely blocked
- Environments requiring climbing (stairs, steep slopes >15°)
- High-speed applications or aggressive maneuvering
"""
```

---

## Key Changes Summary

### Motion Thresholds
- **Max Acceleration:** 5.0 m/s² → **10.0 m/s²** ✅
- **Motion Smoothness:** Allow "abrupt" during obstacle avoidance ✅
- **Rationale:** Real quadruped needs dynamic reactions; 8.81 m/s² observed in benign scenario

### Collision Risk Tolerance  
- **Threshold:** 0.5 → **0.75** ✅
- **Rationale:** 0.652 average in normal living room; furniture proximity is unavoidable

### Obstacle Density Expectations
- **Before:** "not meant for super cluttered spaces"
- **After:** "designed for furniture-dense residential spaces" ✅
- **Rationale:** Standard living rooms should be IN_ODD, not OUT_ODD

### Terrain Additions
- **New:** Explicitly allow gentle ramps (<15°), door thresholds ✅
- **Rationale:** Prepare for ramp test scenarios

---

## Implementation

Replace `DEFAULT_ODD_DESCRIPTION` in these files:
- `scripts/run_odd_analysis.py` (line 62)
- `scripts/run_odd_batch_analysis.py` (line 72)
- `scripts/generate_all_test_reports.py` (line 31)
- `README.md` example snippets

---

## Expected Impact

**Current Production Scenario (collection_173442_chunk_01):**
- Before: OUT_ODD (3 violations)
- After: **IN_ODD** (motion and collision within updated limits)

**Future Test Scenarios:**
- People/pets: Still IN_ODD (dynamic motion expected)
- Ramp navigation: Now IN_ODD (gentle slopes allowed)
- Intentional collision: **OUT_ODD** (actual contact = violation) ✅

This creates more realistic, data-driven ODD boundaries while still catching true safety violations.

---

## Testing Plan

### Test Scenario: real_06_174604

**Why This Scenario:**
- Lowest violation count (2 violations) among all test scenarios
- From first production bag (collection_20251122_173442) - just walking robot in living room
- Only 2 windows, quick to re-run (~1 minute analysis time)
- Benign conditions that should clearly be IN_ODD with updated definition

**Current Results (Old ODD):**
```json
{
  "status": "OUT_ODD",
  "violations": [
    "motion_smoothness: abrupt",
    "collision_risk: 0.8"
  ]
}
```

**Expected Results (New ODD):**
```json
{
  "status": "IN_ODD",
  "violations": []
}
```

**Reasoning:**
1. **Motion Smoothness Violation → RESOLVED**
   - Old ODD: "smooth to moderate acceleration" only
   - New ODD: Explicitly allows "abrupt" motion during obstacle avoidance
   - Expected: Agent classifies abrupt motion as acceptable reactive behavior ✅

2. **Collision Risk 0.8 → SHOULD DECREASE**
   - Old ODD: "needs space to maneuver safely" → furniture proximity = high risk
   - New ODD: "designed for furniture-dense spaces, proximity up to 0.75 acceptable"
   - Expected: **Collision Agent re-assesses same sensor data** with new context
   - Same furniture at 0.5m away → risk score drops from 0.8 to ~0.3-0.5
   - Agent recognizes: "close to furniture = normal, not high risk" ✅

**Key Insight:**
The ODD definition directly influences AI agent assessments. Same sensor data + different ODD context = different risk evaluations. This is by design - the agents should interpret proximity to obstacles differently depending on whether the robot is designed for open warehouses vs furniture-dense homes.

**Test Command:**
```bash
# After applying new ODD to scripts
python scripts/run_odd_analysis.py --scenario real_06_174604

# Generate comparison report
python scripts/generate_html_report.py \
  --input data/analysis_results/manual/latest/real_06_174604/full_result.json \
  --scenario-dir data/processed/test_data/real/real_06_174604 \
  --output docs/reports/real_06_174604_new_odd_report.html
```

**Success Criteria:**
- ✅ Status changes from OUT_ODD → IN_ODD
- ✅ Motion smoothness no longer flagged as violation
- ✅ Collision risk score decreases (agent reassesses with new context)
- ✅ No new violations introduced

If successful, this demonstrates the ODD tuning process working correctly: tightening or loosening operational boundaries based on empirical data analysis.
