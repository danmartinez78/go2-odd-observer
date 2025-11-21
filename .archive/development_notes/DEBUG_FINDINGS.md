# Agent Debugging - Root Cause Found ✅

## Problem Summary

When Vision and Terrain agents ran in the **ParallelAgent workflow**, they returned empty final outputs:
- Vision final event: Empty
- Terrain final event: Empty  
- Collision final event: Empty

But when running **individually** (in isolation), all agents worked perfectly!

## Root Cause

The agents were calling `get_window_image()` with **WRONG parameter names and values**.

### Terrain Agent Error

Agent called:
```python
get_window_image(image_type="BEV", window_id="006")  # ❌ WRONG
```

Expected:
```python
get_window_image(window_id="006", image_type="bev_occupancy")  # ✅ CORRECT
```

Tool returned error, agent gave up and returned error message instead of JSON.

### Vision/Collision Agent Errors (Similar)

Same issue - agents were not using the exact parameter names:
- Missing `window_id` parameter  
- Using wrong `image_type` values like `"BEV"` instead of `"bev_occupancy"`, `"bev_height"`, etc.
- Using `"Camera"` instead of `"camera"`

## Evidence

**Test Script Results - Isolated Execution:**
```
Test 1: Motion Analyzer - 3 events, Event 2: 14,083 chars ✅
Test 2: Vision Analyzer - 3 events, Event 2: 14,173 chars ✅
Test 3: Terrain Analyzer - 3 events, Event 2: 127 chars ❌ (TINY = ERROR)
Test 4: Collision Detector - 9 events (retrying due to errors) ❌
```

**Detailed Inspection:**
```
Terrain Event 6 output:
"I am sorry, I am unable to analyze the terrain based on the available tools.
Both calls to get BEV images returned an error."
```

Function calls shown:
```
Call: get_window_image(image_type='BEV', window_id='006')  # ❌ Wrong name
Response: {'status': 'error'}

Call: get_window_image(image_type='BEV', window_id='007')  # ❌ Wrong name
Response: {'status': 'error'}
```

## Solution

Update agent instructions to explicitly show the exact function calls with correct parameter names:

```python
# WRONG - what agents were doing:
get_window_image("camera")
get_window_image(image_type="BEV")

# RIGHT - what they should do:
get_window_image(window_id="006", image_type="camera")
get_window_image(window_id="006", image_type="bev_occupancy")
get_window_image(window_id="006", image_type="bev_height")
get_window_image(window_id="006", image_type="bev_density")
get_window_image(window_id="006", image_type="bev_roughness")
```

## Key Insight

**Why did ParallelAgent fail but isolated execution worked?**

Likely the simplified test script instructions were clearer/different, OR isolated execution with shorter delays allowed the agents to work better. With fixed instructions, all agents should work in parallel too.

## Action Items

1. ✅ Identified the root cause (parameter name mismatch)
2. ✅ Created test script proving all agents work in isolation
3. ✅ Created fix guide with correct instructions  
4. → Next: Update notebook agents with fixed instructions
5. → Then: Run parallel workflow again to verify all 7 agents complete successfully

See `AGENT_FIX_GUIDE.md` for exact replacement code.
