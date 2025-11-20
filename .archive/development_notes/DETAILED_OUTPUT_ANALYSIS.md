# Detailed Output Analysis

## Test Results - Isolated Agent Execution

### Event Size Comparison

| Agent | Total Events | Event 0 | Event 1 | Event 2 (Final) | Status |
|-------|--------------|---------|---------|-----------------|--------|
| Motion_Analyzer | 3 | ✅ | ✅ | 14,083 chars | ✅ SUCCESS |
| Vision_Analyzer | 3 | ✅ | ✅ | 14,173 chars | ✅ SUCCESS |
| Terrain_Analyzer | 3 | ✅ | ✅ | 127 chars | ❌ FAILED |
| Collision_Detector | 9 | ✅ | ✅ | Multiple small | ❌ FAILED (retrying) |

**Key Finding**: Terrain and Collision final events are way too small!
- Motion/Vision final output: ~14,000 chars (full JSON analysis)
- Terrain final output: 127 chars (error message!)
- Collision final output: fragmented across 9 events

### Terrain Analyzer - Failure Details

**Actual Tool Calls Made by Agent:**
```
Event 2: get_window_image(image_type='BEV', window_id='006')
Response: {'status': 'error'}  ← Tool rejected!

Event 4: get_window_image(image_type='BEV', window_id='007')  
Response: {'status': 'error'}  ← Tool rejected!
```

**Agent's Final Response:**
```
"I am sorry, I am unable to analyze the terrain based on the available tools.
I can get the scenario data and BEV images, but I am unable to process them to analyze the terrain.
Both calls to get BEV images returned an error."
```

**Why Failed:**
- Called with `image_type='BEV'` but function expects `'bev_occupancy'`, `'bev_height'`, etc.
- Missing proper window_id parameter handling
- When tool returned error, agent gave up instead of using fallback values

### Vision Analyzer - Success Details

**Expected but didn't show in full workflow:**
- In isolated test: Worked perfectly, returned 14KB of JSON
- In parallel workflow: Also had final event with content
- But in COD Evaluator merge, vision data appeared as empty `{}`

### Motion Analyzer - Success Details

**Always worked in both contexts:**
- 14,083 chars of valid JSON  
- Properly formatted motion metrics
- Successfully merged into COD evaluation

### Collision Detector - Fragmentation Details

**Generated 9 events instead of 3:**
- Suggests agent retrying after incomplete responses
- Multiple small function_call and function_response pairs
- Never consolidated into a final JSON response

## Comparison: Isolated vs Parallel Execution

### Isolated Execution (Test Script)
- Each agent runs in its own InMemoryRunner session
- Gets fresh configuration
- Simpler instructions (no ODD spec context)
- **Result**: All 4 agents successful ✅

### Parallel Execution (Notebook)
- 4 agents run simultaneously in ParallelAgent
- Share ODD spec JSON context
- More complex instructions with more requirements  
- **Result**: Vision/Terrain/Collision fail ❌

### Hypothesis
The combination of:
1. Complex image processing (large base64 strings)
2. Parallel execution coordination
3. Unclear parameter instructions
4. Shared state management

...caused the agents to make wrong tool calls and give up when they failed.

## The Fix

Make instructions **explicit** about exact parameters:

**Before (Wrong):**
```
"Call get_window_image() with image_type: bev_occupancy"
(agent interpreted as: get_window_image(image_type="BEV"))
```

**After (Correct):**
```
"Call get_window_image(window_id="006", image_type="bev_occupancy")"
(explicit function call shows exact format)
```

## Verification

Run this command to test fixed agents:
```bash
python test_agents_isolated_debug.py
```

Should show all agents returning large final outputs if instructions are fixed correctly.
