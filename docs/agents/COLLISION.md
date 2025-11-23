# Collision Agents

## Overview

The collision risk pipeline performs **multimodal safety assessment** by fusing motion dynamics with camera and LiDAR data to evaluate collision likelihood. This two-agent system analyzes per-window risk and produces aggregate safety statistics.

**Key Innovation**: Combines motion context (acceleration, velocity) with visual/spatial obstacle detection for holistic risk assessment, not just static obstacle proximity.

---

## CollisionLoopAgent

### Purpose

Orchestrates per-window collision risk analysis by iterating through all time windows and collecting multimodal safety assessments.

**Problem it solves**: Evaluating collision risk requires understanding both the environment (obstacles, clearances) AND robot dynamics (motion, speed). This agent fuses both sources of information.

### Inputs

**From User/Workflow:**
- None (receives initial query to start analysis)

**From Tools:**
- `list_windows_tool()`: Available window IDs in the scenario
- `analyze_collision_risk_tool(window_id, motion_metrics)`: Multimodal risk assessment

**Environment Dependencies:**
- Scenario directory with camera images (`cam_*.png`)
- LiDAR BEV occupancy maps (`bev_occupancy_*.png`)
- Motion metrics from MotionLoopAgent (passed via tool parameter)

### Outputs

**Output Key:** `temp:collision_data`

**Schema:**
```json
{
  "windows_analyzed": ["001", "002", "003"],
  "collision_events": [
    {
      "window_id": "001",
      "collision_risk_level": "low",
      "risk_confidence": 0.85,
      "collision_likelihood_score": 0.25,
      "closest_obstacle_meters": 2.5,
      "obstacle_direction": "front",
      "motion_contributes_to_risk": false,
      "camera_hazards": ["desk at 2.5m"],
      "bev_hazards": ["obstacle cluster front-left"],
      "recommended_action": "continue",
      "evidence": "Clear forward path with distant obstacles..."
    }
  ]
}
```

### Prompting Strategy

**Key Instructions:**
1. **Sequential processing**: Call `list_windows_tool()` exactly once, then iterate in order
2. **Pass motion context**: For each window, pass corresponding motion metrics to collision tool
3. **No modifications**: Collect tool responses exactly as returned
4. **JSON output only**: No commentary outside JSON structure

**Critical Pattern:**
```
1. list_windows_tool() → ["001", "002", "003"]
2. For each window_id:
     # Get motion metrics for this window (from context or lookup)
     motion_metrics = {...}
     analyze_collision_risk_tool(window_id, motion_metrics) → {...}
3. Collect all results in order
4. Return JSON with windows_analyzed + collision_events arrays
```

**Important**: The agent must correlate window_id with motion data from previous stage to pass correct motion_metrics to the tool.

### Model Selection

**Default:** `gemini-2.0-flash-lite`  
**Recommended Upgrade:** `gemini-2.5-pro`

**Rationale:**
- Loop agent orchestrates tool calls (simple coordination)
- **Flash-lite sufficient** for basic orchestration
- **Upgrade to 2.5-pro if**:
  - Need more reliable motion context passing
  - Complex scenarios with many windows
  - Critical safety analysis requiring highest quality

**Cost Impact:** flash-lite saves ~70% vs. pro

### Tool Dependencies

#### 1. `list_windows_tool()`
**Purpose**: Discover available time windows (shared with other loop agents)

**Output:**
```json
{
  "status": "success",
  "windows": ["001", "002", "003"],
  "count": 3
}
```

#### 2. `analyze_collision_risk_tool(window_id, motion_metrics)`
**Purpose**: Multimodal collision risk assessment for single window

**Implementation Details:**

**Inputs:**
- `window_id`: Window identifier
- `motion_metrics`: Motion data from MotionLoopAgent
  ```json
  {
    "motion_detected": true,
    "motion_type": "translation",
    "peak_horizontal_accel_mps2": 1.23,
    "peak_angular_velocity_radps": 0.18,
    ...
  }
  ```

**Data Sources:**
1. **Camera image**: Visual obstacle detection, hazard identification
2. **LiDAR BEV**: Spatial obstacle mapping, distance estimation
3. **Motion metrics**: Robot dynamics, speed, direction

**Multimodal Fusion Prompt:**
```
MOTION CONTEXT:
- Status: MOTION DETECTED / STATIONARY
- Type: translation/rotation/combined/stationary
- Peak accel: X.XX m/s²
- Peak angular velocity: X.XX rad/s

IMAGES PROVIDED:
1. Camera feed (egocentric view)
2. BEV LiDAR map (top-down obstacle map)

TASK: Analyze collision risk by fusing motion + camera + BEV data.
```

**Risk Classification Logic:**
- **none**: No obstacles, robot stationary
- **low**: Obstacles distant (>2m) OR robot stationary
- **medium**: Obstacles near (1-2m) AND robot moving slowly
- **high**: Obstacles close (<1m) AND robot moving
- **critical**: Imminent collision (<0.5m) with motion toward obstacle

**Likelihood Score:**
```
0.0-0.2: Safe (low risk)
0.2-0.4: Caution (medium risk)
0.4-0.6: Warning (high risk)
0.6-1.0: Danger (critical risk)
```

**Recommended Actions:**
- `continue`: Safe to proceed
- `slow_down`: Reduce speed, maintain direction
- `stop`: Halt immediately
- `change_direction`: Alter course to avoid obstacle

**Output Schema:**
```json
{
  "window_id": "001",
  "collision_risk_level": "none|low|medium|high|critical",
  "risk_confidence": 0.0-1.0,
  "collision_likelihood_score": 0.0-1.0,
  "closest_obstacle_meters": <float or null>,
  "obstacle_direction": "front|left|right|rear|multiple|none",
  "motion_contributes_to_risk": true|false,
  "camera_hazards": ["list of hazards from camera"],
  "bev_hazards": ["list of hazards from BEV"],
  "recommended_action": "continue|slow_down|stop|change_direction",
  "evidence": "Brief explanation of multimodal fusion analysis"
}
```

### Example Output

**Full CollisionLoopAgent Output:**
```json
{
  "windows_analyzed": ["001", "002", "003"],
  "collision_events": [
    {
      "window_id": "001",
      "collision_risk_level": "low",
      "risk_confidence": 0.85,
      "collision_likelihood_score": 0.25,
      "closest_obstacle_meters": 2.5,
      "obstacle_direction": "front",
      "motion_contributes_to_risk": false,
      "camera_hazards": ["desk at 2.5m front"],
      "bev_hazards": ["sparse obstacles, clear path"],
      "recommended_action": "continue",
      "evidence": "Robot moving forward with desk obstacle at safe distance. Sufficient clearance for navigation."
    },
    {
      "window_id": "002",
      "collision_risk_level": "high",
      "risk_confidence": 0.92,
      "collision_likelihood_score": 0.68,
      "closest_obstacle_meters": 0.8,
      "obstacle_direction": "front",
      "motion_contributes_to_risk": true,
      "camera_hazards": ["sofa directly ahead <1m", "coffee table left"],
      "bev_hazards": ["dense occupancy front", "narrow passage"],
      "recommended_action": "stop",
      "evidence": "Robot approaching sofa at close range while in motion. High collision likelihood due to proximity and movement."
    },
    {
      "window_id": "003",
      "collision_risk_level": "medium",
      "risk_confidence": 0.78,
      "collision_likelihood_score": 0.35,
      "closest_obstacle_meters": 1.5,
      "obstacle_direction": "left",
      "motion_contributes_to_risk": true,
      "camera_hazards": ["cabinet on left side"],
      "bev_hazards": ["moderate occupancy left flank"],
      "recommended_action": "slow_down",
      "evidence": "Robot rotating with cabinet 1.5m to left. Medium risk due to proximity during turning maneuver."
    }
  ]
}
```

### Common Issues

**Issue 1: Motion metrics not correlated with window_id**
- **Symptom**: Wrong motion data passed to tool (e.g., window 3 data used for window 1)
- **Cause**: Agent not properly indexing motion_data array
- **Fix**: Ensure agent understands array indexing or uses window_id as lookup key

**Issue 2: Tool reports missing images**
- **Symptom**: Error "image file not found"
- **Cause**: Scenario path incorrect or images not extracted
- **Fix**: Verify scenario directory structure

**Issue 3: Over-conservative risk assessment**
- **Symptom**: Stationary robot with distant obstacles flagged as "high risk"
- **Cause**: Tool prompt may need tuning for specific robot platform
- **Fix**: Adjust risk thresholds in tool prompt or accept conservative behavior

---

## CollisionSummaryAgent

### Purpose

Synthesizes per-window collision events into aggregate statistics and overall safety profile.

**Problem it solves**: Converting raw window-level risk assessments into scenario-level safety metrics (risk distribution, average likelihood, event counts).

### Inputs

**From Previous Agent:**
- `{temp:collision_data?}`: Output from CollisionLoopAgent

**Schema Expected:**
```json
{
  "windows_analyzed": [...],
  "collision_events": [...]
}
```

### Outputs

**Output Key:** `temp:collision_output`

**Schema:**
```json
{
  "windows_analyzed": ["001", "002", "003"],
  "overall_collision_stats": {
    "total_windows": 3,
    "safe_count": 1,
    "caution_count": 1,
    "alert_count": 1,
    "avg_collision_likelihood": 0.43
  },
  "collision_events": [...]
}
```

### Prompting Strategy

**Key Instructions:**
1. **Read input carefully**: Parse `temp:collision_data?` JSON string
2. **Calculate statistics**:
   - Count by risk level:
     - `safe_count`: risk_level = "none" or "low"
     - `caution_count`: risk_level = "medium"
     - `alert_count`: risk_level = "high" or "critical"
   - Average collision likelihood: Mean of `collision_likelihood_score` across all windows
3. **Preserve raw data**: Pass through `collision_events` unchanged

### Model Selection

**Default:** `gemini-2.0-flash-lite`  
**Recommended Upgrade:** Not typically needed

**Rationale:**
- Simple statistical aggregation (flash-lite capable)
- No complex reasoning required
- **Keep flash-lite** unless debugging aggregation issues

**Cost Impact:** flash-lite optimal for this task

### Tool Dependencies

**None** - Pure synthesis agent using only LLM reasoning on input data.

### Example Output

```json
{
  "windows_analyzed": ["001", "002", "003"],
  "overall_collision_stats": {
    "total_windows": 3,
    "safe_count": 1,
    "caution_count": 1,
    "alert_count": 1,
    "avg_collision_likelihood": 0.43
  },
  "collision_events": [
    {
      "window_id": "001",
      "collision_risk_level": "low",
      "collision_likelihood_score": 0.25,
      "closest_obstacle_meters": 2.5,
      "recommended_action": "continue"
    },
    {
      "window_id": "002",
      "collision_risk_level": "high",
      "collision_likelihood_score": 0.68,
      "closest_obstacle_meters": 0.8,
      "recommended_action": "stop"
    },
    {
      "window_id": "003",
      "collision_risk_level": "medium",
      "collision_likelihood_score": 0.35,
      "closest_obstacle_meters": 1.5,
      "recommended_action": "slow_down"
    }
  ]
}
```

### Common Issues

**Issue 1: Missing input data**
- **Symptom**: Returns `{"error": "missing_collision_data"}`
- **Cause**: CollisionLoopAgent failed or `output_key` misconfigured
- **Fix**: Check CollisionLoopAgent logs and ADK context passing

**Issue 2: Incorrect average calculation**
- **Symptom**: avg_collision_likelihood doesn't match manual calculation
- **Cause**: Agent including null values or misunderstanding float division
- **Fix**: Usually self-corrects; verify input data quality

**Issue 3: Wrong risk category counts**
- **Symptom**: safe_count + caution_count + alert_count ≠ total_windows
- **Cause**: Agent misclassifying risk levels or missing cases
- **Fix**: Check for edge cases (e.g., "none" vs "low" handling)

---

## Multimodal Collision Risk Fusion

### Why Fusion Matters

**Camera alone:**
- ✅ Rich semantic understanding (object types, distances)
- ❌ Poor depth estimation (monocular vision)
- ❌ Limited field of view

**LiDAR BEV alone:**
- ✅ Accurate spatial mapping (obstacle positions)
- ✅ Wide coverage (360° or near-360°)
- ❌ No semantic information (what is the obstacle?)

**Motion alone:**
- ✅ Dynamics understanding (speed, direction)
- ❌ No obstacle awareness

**Fusion advantages:**
- Accurate obstacle distance (LiDAR) + semantic context (camera)
- Motion dynamics contextualize static obstacle proximity
- Redundancy: If one sensor fails, others provide partial information

### Risk Assessment Logic

**Stationary robot:**
```
Low risk regardless of obstacle proximity
(robot not moving toward obstacles)
```

**Moving robot:**
```
if closest_obstacle < 0.5m AND moving toward obstacle:
    risk = "critical"
elif closest_obstacle < 1.0m AND moving:
    risk = "high"
elif closest_obstacle < 2.0m AND moving fast:
    risk = "medium"
else:
    risk = "low"
```

**Motion contribution:**
```
motion_contributes_to_risk = True if:
  - Robot moving AND
  - Movement direction toward obstacle AND
  - Obstacle within risk distance
```

### Performance Characteristics

**Tested on 13-window scenario (sim_run_new):**
- ⚠️ **8 collision warnings** detected (high/critical risk)
- ✅ **Multimodal fusion** correctly identified near-collision events
- ✅ **Motion context** prevented false alarms on stationary windows

**Calibration for different robots:**
- Adjust distance thresholds based on robot size
- Larger robots: Increase thresholds (bigger footprint)
- Faster robots: Increase lookahead distance

---

## Integration Example

```python
from odd_agents.agents import create_collision_loop_agent, create_collision_summary_agent
from google.genai import Client

client = Client(api_key=api_key)
scenario_path = "data/processed/runs/sim_run_test"

# Create loop agent with tools
loop_agent = create_collision_loop_agent(
    scenario_path=scenario_path,
    genai_client=client,
    model="gemini-2.5-pro",  # Upgrade for critical safety analysis
    api_key=api_key
)

# Create summary agent
summary_agent = create_collision_summary_agent(
    api_key=api_key,
    model="gemini-2.0-flash-lite"  # flash-lite sufficient for aggregation
)

# Use in sequential workflow
from google.adk.agents import SequentialAgent
workflow = SequentialAgent(
    name="CollisionWorkflow",
    sub_agents=[loop_agent, summary_agent]
)
```

## Related Documentation

- **[Main Agent Architecture](README.md)**: Overall workflow context
- **[Model Selection Guide](../MODEL_SELECTION_GUIDE.md)**: Cost optimization strategies
- **[Perception Agents](PERCEPTION.md)**: Obstacle detection details
- **[Motion Agents](MOTION.md)**: Motion dynamics analysis
- **[Tool Implementation](../../odd_agents/tools/collision.py)**: Source code
