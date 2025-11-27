# Collision Agent

**Version:** Phase 1.2 (Binary Detection)  
**Last Updated:** November 25, 2025

## Overview

The collision agent performs **binary collision detection** using IMU sensor data to identify actual collision events (not proximity risk). This simplified single-agent design replaces the previous multimodal risk scoring system.

**Key Design Decision**: Collision detection is based on IMU threshold analysis (sudden impacts), NOT proximity to obstacles. Close navigation around furniture is normal and expected behavior.

---

## CollisionAgent

### Purpose

Analyzes motion metrics from the motion agent to detect actual collision events using IMU spike detection.

**Problem it solves**: Distinguishes normal dynamic motion (obstacle avoidance, turning) from collision events (sudden impacts, spin-outs).

### Inputs

**From MotionAgent:**
- `motion_metrics`: Per-window motion analysis data including:
  - `peak_horizontal_accel_mps2`: Maximum horizontal acceleration
  - `peak_angular_velocity_radps`: Maximum angular velocity (gyro)
  - `max_jerk_mps3`: Maximum jerk (rate of acceleration change)

### Outputs

**Output Key:** `collision_output`

**Schema:**
```json
{
  "collision_detected": false,
  "evidence": [
    "Window 001: Peak accel 0.14 m/s² (threshold: 10.0)",
    "Window 002: Peak gyro 0.99 rad/s (threshold: 5.0)",
    "No collision indicators detected"
  ],
  "thresholds": {
    "acceleration_spike_threshold": 10.0,
    "angular_velocity_threshold": 5.0,
    "jerk_spike_threshold": 50.0
  }
}
```

### Detection Logic

**Binary Thresholds (Tuned for Go2 Quadruped):**

1. **Acceleration Spike**: `>10 m/s²` horizontal acceleration
   - Normal quadruped motion: 0.1-2.0 m/s² (walking, turning)
   - Obstacle avoidance reactions: 2.0-8.0 m/s² (acceptable)
   - **Collision indicator**: >10 m/s² (sudden impact)

2. **Angular Velocity**: `>5 rad/s` rotation rate
   - Normal turning: 0.5-2.0 rad/s
   - Quick direction changes: 2.0-4.0 rad/s (acceptable)
   - **Collision indicator**: >5 rad/s (severe spin-out)

3. **Jerk Spike**: `>50 m/s³` acceleration change
   - Normal motion smoothness: <20 m/s³
   - Reactive maneuvers: 20-40 m/s³ (acceptable)
   - **Collision indicator**: >50 m/s³ (violent sudden change)

**Collision Detected If:** Any threshold exceeded in any window

### Prompting Strategy

**Key Instructions:**
1. **Threshold-based detection**: Simple binary check (>threshold = collision)
2. **Evidence collection**: Record peak values for each window
3. **No interpretation**: Thresholds are pre-calibrated, agent just applies them
4. **JSON output only**: No narrative commentary

**Critical Pattern:**
```
For each window in motion_metrics:
  if peak_accel > 10.0 OR peak_gyro > 5.0 OR max_jerk > 50.0:
    collision_detected = True
    evidence.append(f"Window {id}: COLLISION - accel={peak_accel}")
  else:
    evidence.append(f"Window {id}: Normal - accel={peak_accel}")
```

### Model Selection

**Default:** `gemini-2.5-pro`  
**Rationale:**
- Binary threshold logic is simple, but we want high reliability
- Pro model ensures consistent threshold application
- Cost difference minimal (single agent call per scenario)

**Not Recommended:**
- flash-lite: May occasionally misapply thresholds
- flash: Acceptable but pro preferred for safety-critical detection

### Tool Dependencies

#### `detect_collision_tool(motion_metrics)`

**Purpose**: Binary collision detection from IMU thresholds

**Implementation:** `odd_agents/tools/collision.py`

**Inputs:**
```json
{
  "motion_metrics": [
    {
      "window_id": "001",
      "peak_horizontal_accel_mps2": 0.14,
      "peak_angular_velocity_radps": 0.99,
      "max_jerk_mps3": 5.2
    }
  ]
}
```

**Processing:**
```python
def detect_collision(motion_metrics):
    ACCEL_THRESHOLD = 10.0  # m/s²
    GYRO_THRESHOLD = 5.0    # rad/s
    JERK_THRESHOLD = 50.0   # m/s³
    
    collision_detected = False
    evidence = []
    
    for window in motion_metrics:
        accel = window['peak_horizontal_accel_mps2']
        gyro = window['peak_angular_velocity_radps']
        jerk = window.get('max_jerk_mps3', 0)
        
        if accel > ACCEL_THRESHOLD:
            collision_detected = True
            evidence.append(f"Window {window['window_id']}: COLLISION - Accel spike {accel:.2f} m/s²")
        elif gyro > GYRO_THRESHOLD:
            collision_detected = True
            evidence.append(f"Window {window['window_id']}: COLLISION - Gyro spike {gyro:.2f} rad/s")
        elif jerk > JERK_THRESHOLD:
            collision_detected = True
            evidence.append(f"Window {window['window_id']}: COLLISION - Jerk spike {jerk:.2f} m/s³")
        else:
            evidence.append(f"Window {window['window_id']}: Normal motion")
    
    return {
        "collision_detected": collision_detected,
        "evidence": evidence,
        "thresholds": {...}
    }
```

### Example Outputs

**Example 1: No Collision (Normal Navigation)**
```json
{
  "collision_detected": false,
  "evidence": [
    "Window 001: Peak accel 0.14 m/s² (threshold: 10.0) - Normal",
    "Window 002: Peak accel 0.11 m/s² (threshold: 10.0) - Normal",
    "Window 001: Peak gyro 0.94 rad/s (threshold: 5.0) - Normal",
    "Window 002: Peak gyro 0.99 rad/s (threshold: 5.0) - Normal",
    "No collision indicators detected across 2 windows"
  ],
  "thresholds": {
    "acceleration_spike_threshold": 10.0,
    "angular_velocity_threshold": 5.0,
    "jerk_spike_threshold": 50.0
  }
}
```

**Example 2: Collision Detected**
```json
{
  "collision_detected": true,
  "evidence": [
    "Window 001: Peak accel 0.8 m/s² - Normal",
    "Window 002: Peak accel 1.2 m/s² - Normal",
    "Window 003: Peak accel 12.5 m/s² - COLLISION DETECTED (threshold: 10.0)",
    "Window 003: Peak gyro 6.8 rad/s - COLLISION DETECTED (threshold: 5.0)",
    "COLLISION EVENT in window 003: Accel spike 12.5 m/s², Gyro spike 6.8 rad/s"
  ],
  "thresholds": {
    "acceleration_spike_threshold": 10.0,
    "angular_velocity_threshold": 5.0,
    "jerk_spike_threshold": 50.0
  }
}
```

### Validation Results

**Test Data:** `sim_test_w010_w011` (2 windows, normal navigation)

**Results:**
- ✅ Collision detected: `false` (correct)
- ✅ Peak acceleration: 0.11-0.14 m/s² (well below 10.0 threshold)
- ✅ Peak gyro: 0.94-0.99 rad/s (well below 5.0 threshold)
- ✅ No false positives

**Production Data:** `sim_1_0` (62 windows, various scenarios)
- ✅ No false positives on normal navigation
- ✅ Correctly identifies collision-free scenarios

### Common Issues

**Issue 1: False positives on aggressive maneuvering**
- **Symptom**: Collision detected during normal obstacle avoidance
- **Cause**: Thresholds too low for aggressive robots
- **Fix**: Increase thresholds (e.g., 15 m/s² for accel)

**Issue 2: Missing actual collisions**
- **Symptom**: Real collision not detected
- **Cause**: Thresholds too high or IMU data quality issues
- **Fix**: Review IMU data, lower thresholds if needed

**Issue 3: Incomplete motion metrics**
- **Symptom**: Missing jerk or gyro data
- **Cause**: Motion agent didn't compute all metrics
- **Fix**: Ensure motion agent provides complete metrics

---

## Design Rationale

### Why Binary Detection?

**Previous System (Phase 1.1):**
- Risk scoring (0-1 likelihood scores)
- Multimodal fusion (camera + BEV + IMU)
- Per-window risk levels (none/low/medium/high/critical)

**Problems:**
- **False positives**: Close proximity to furniture flagged as "high risk"
- **Confusion**: Risk scores didn't reflect actual collisions
- **Complexity**: Multimodal fusion added tokens without improving accuracy

**New System (Phase 1.2):**
- Binary detection (yes/no collision)
- IMU-only (threshold-based)
- Simple, reliable, no false positives

**Trade-off:**
- ❌ Lost: Proximity awareness (how close to obstacles)
- ✅ Gained: Reliable collision detection, no false alarms
- ✅ Gained: Simpler system, faster execution

### Why IMU-Only?

**Considered enhancements:**
- BEV occupancy for visual confirmation
- Camera for obstacle contact detection

**Deferred because:**
1. **Self-hit complexity**: Robot body appears in BEV center
2. **Temporal mismatch**: Frame-by-frame analysis needed (complex)
3. **False positive risk**: Always near obstacles in cluttered environments
4. **Current system works**: 0 false positives on test data

**Future enhancement** (Phase 1.5+):
- Add BEV visual confirmation with proper temporal reasoning
- A/B test IMU-only vs IMU+BEV
- Implement after agent versioning system

### ODD Integration

**In ODD Specification:**
```
MOTION CHARACTERISTICS:
- Quick reactive maneuvers acceptable (acceleration up to 10 m/s²)
- Brief "abrupt" motion normal during obstacle avoidance
- NOT designed for violent/erratic motion in open spaces
```

**COD Agent Usage:**
- COD agent receives `collision_detected` boolean
- If true → OUT_ODD violation
- Evidence passed to report agent for context

**Compliance Evaluation:**
- `collision_detected: false` → No motion violations
- `collision_detected: true` → Investigate collision event

---

## Integration Example

```python
from odd_agents.agents import create_collision_agent
from google.genai import Client

client = Client(api_key=api_key)

# Motion metrics from previous agent
motion_metrics = [
    {
        "window_id": "001",
        "peak_horizontal_accel_mps2": 0.14,
        "peak_angular_velocity_radps": 0.94,
        "max_jerk_mps3": 5.2
    }
]

# Create collision agent
collision_agent = create_collision_agent(
    api_key=api_key,
    model="gemini-2.5-pro"
)

# Run detection
result = collision_agent.query(
    f"Analyze motion metrics for collision detection: {motion_metrics}"
)

# Parse result
collision_output = result['collision_output']
print(f"Collision detected: {collision_output['collision_detected']}")
print("\n".join(collision_output['evidence']))
```

## Related Documentation

- **[Architecture Redesign](../ARCHITECTURE_REDESIGN.md)**: Phase 1.2 design details
- **[Motion Agent](MOTION.md)**: Motion metrics source
- **[COD Agent](COD_CLASSIFIER.md)**: How collision detection integrates
- **[Tool Implementation](../../odd_agents/tools/collision.py)**: Source code
- **[Tests](../../tests/test_collision_agent.py)**: Validation tests
