# Motion Agents

## Overview

The motion pipeline performs **IMU-based motion analysis** using accelerometer and gyroscope data to detect robot movement and characterize motion patterns. This two-agent system processes time-windowed sensor data and produces motion statistics without relying on unreliable odometry.

**Key Innovation**: Uses raw IMU data (acceleration + angular velocity) instead of wheel odometry, which is often broken or unreliable in quadruped robots.

---

## MotionLoopAgent

### Purpose

Orchestrates per-window motion analysis by iterating through all time windows and collecting IMU-based motion metrics.

**Problem it solves**: Reliable motion detection when wheel odometry is unavailable or unreliable. IMU-based analysis works even when odometry subsystems fail.

### Inputs

**From User/Workflow:**
- None (receives initial query to start analysis)

**From Tools:**
- `list_windows_tool()`: Available window IDs in the scenario
- `analyze_motion_tool(window_id)`: IMU analysis results for single window

**Environment Dependencies:**
- Scenario directory with motion data files (`motion_*.json`)
  - Contains: `accel_x`, `accel_y`, `accel_z`, `gyro_x`, `gyro_y`, `gyro_z`, `roll`, `pitch`, `timestamps`
  - **Data source**: Custom `go2_interfaces/msg/IMU` message type (requires go2_ros2_sdk)
  - Extracted from `/imu` topic during rosbag processing

### Outputs

**Output Key:** `temp:motion_data`

**Schema:**
```json
{
  "windows_analyzed": ["001", "002", "003"],
  "per_window_motion": [
    {
      "window_id": "001",
      "motion_detected": true,
      "motion_type": "translation",
      "motion_smoothness": "smooth",
      "peak_horizontal_accel_mps2": 1.23,
      "avg_horizontal_accel_mps2": 0.45,
      "peak_angular_velocity_radps": 0.18,
      "max_roll_deg": 3.2,
      "max_pitch_deg": 2.8,
      "platform_stability": "stable",
      "confidence": 0.9,
      "evidence": "Consistent forward acceleration..."
    }
  ]
}
```

### Prompting Strategy

**Key Instructions:**
1. **Sequential processing**: Call `list_windows_tool()` exactly once, then iterate in order
2. **No modifications**: Collect tool responses exactly as returned
3. **JSON output only**: No commentary outside JSON structure

**Critical Pattern:**
```
1. list_windows_tool() → ["001", "002", "003"]
2. For each window_id:
     analyze_motion_tool(window_id) → {...}
3. Collect all results in order
4. Return JSON with windows_analyzed + per_window_motion arrays
```

### Model Selection

**Default:** `gemini-2.0-flash-lite`  
**Recommended Upgrade:** `gemini-2.5-pro`

**Rationale:**
- Loop agent only orchestrates tool calls
- **Flash-lite sufficient** for coordination
- **Upgrade to 2.5-pro if**:
  - Need more reliable data structure preservation
  - Complex scenarios with many windows
  - Debugging tool calling issues

**Cost Impact:** flash-lite saves ~70% vs. pro

### Tool Dependencies

#### 1. `list_windows_tool()`
**Purpose**: Discover available time windows (shared with PerceptionLoopAgent)

**Output:**
```json
{
  "status": "success",
  "windows": ["001", "002", "003"],
  "count": 3
}
```

#### 2. `analyze_motion_tool(window_id)`
**Purpose**: IMU-based motion analysis for single window

**Implementation Details:**

**Data Extraction:**
```python
# Load motion_*.json file (extracted from go2_interfaces/msg/IMU)
accel_x, accel_y, accel_z  # Linear acceleration (m/s²) from IMU.accelerometer
gyro_x, gyro_y, gyro_z     # Angular velocity (rad/s) from IMU.gyroscope
roll, pitch                 # Platform orientation (degrees) from odometry quaternion
timestamps                  # Sample timestamps (relative to window start)
```

**Important**: IMU data requires `go2_interfaces` package (from go2_ros2_sdk). If package not available during extraction, IMU fields will be zeros.

**Statistical Analysis:**
- **Horizontal acceleration**: `sqrt(accel_x² + accel_y²)` - planar motion magnitude
- **Zero filtering**: Remove sensor gaps (values < 1e-6)
- **Peak/average/median**: Statistical summary of acceleration
- **Angular velocity**: Full 3D rotation analysis (roll, pitch, yaw)
- **Platform stability**: Max tilt angles from roll/pitch

**Motion Detection Logic:**
```python
# Motion detected if:
peak_horizontal_accel > 0.15 m/s²  OR
peak_angular_velocity > 0.1 rad/s   OR
avg_horizontal_accel > 0.08 m/s²

# Motion type classification:
if peak_angular_velocity > 0.3 rad/s:
    motion_type = "rotation"
elif peak_horizontal_accel > 1.0 m/s²:
    motion_type = "translation"
elif motion_detected:
    motion_type = "combined"
else:
    motion_type = "stationary"
```

**Smoothness Classification:**
```python
# Based on jerk (rate of change of acceleration)
if jerk_estimate > 2.0 m/s³:
    smoothness = "abrupt"
elif jerk_estimate > 1.0 m/s³:
    smoothness = "moderate"
else:
    smoothness = "smooth"
```

**Visual Odometry (Optional):**
- If camera image available, LLM analyzes for visual motion cues
- Used as sanity check, not primary motion indicator
- Helps detect camera issues or validate IMU

**Output Schema:**
```json
{
  "window_id": "001",
  "motion_detected": true,
  "motion_type": "translation|rotation|combined|stationary",
  "motion_smoothness": "smooth|moderate|abrupt",
  "peak_horizontal_accel_mps2": 1.23,
  "avg_horizontal_accel_mps2": 0.45,
  "median_horizontal_accel_mps2": 0.38,
  "peak_angular_velocity_radps": 0.18,
  "peak_gyro_x_radps": 0.05,
  "peak_gyro_y_radps": 0.04,
  "max_roll_deg": 3.2,
  "max_pitch_deg": 2.8,
  "platform_stability": "stable|tilted|unstable",
  "confidence": 0.0-1.0,
  "evidence": "Explanation of motion analysis"
}
```

### Example Output

**Full MotionLoopAgent Output:**
```json
{
  "windows_analyzed": ["001", "002", "003"],
  "per_window_motion": [
    {
      "window_id": "001",
      "motion_detected": true,
      "motion_type": "translation",
      "motion_smoothness": "smooth",
      "peak_horizontal_accel_mps2": 1.23,
      "avg_horizontal_accel_mps2": 0.45,
      "median_horizontal_accel_mps2": 0.38,
      "peak_angular_velocity_radps": 0.18,
      "peak_gyro_x_radps": 0.05,
      "peak_gyro_y_radps": 0.04,
      "max_roll_deg": 3.2,
      "max_pitch_deg": 2.8,
      "platform_stability": "stable",
      "confidence": 0.9,
      "evidence": "Consistent forward acceleration with minimal rotation. Stable platform orientation."
    },
    {
      "window_id": "002",
      "motion_detected": false,
      "motion_type": "stationary",
      "motion_smoothness": "smooth",
      "peak_horizontal_accel_mps2": 0.08,
      "avg_horizontal_accel_mps2": 0.03,
      "median_horizontal_accel_mps2": 0.02,
      "peak_angular_velocity_radps": 0.04,
      "peak_gyro_x_radps": 0.01,
      "peak_gyro_y_radps": 0.01,
      "max_roll_deg": 1.5,
      "max_pitch_deg": 1.2,
      "platform_stability": "stable",
      "confidence": 0.95,
      "evidence": "Minimal acceleration and rotation. Robot appears stationary."
    },
    {
      "window_id": "003",
      "motion_detected": true,
      "motion_type": "rotation",
      "motion_smoothness": "moderate",
      "peak_horizontal_accel_mps2": 0.45,
      "avg_horizontal_accel_mps2": 0.18,
      "median_horizontal_accel_mps2": 0.15,
      "peak_angular_velocity_radps": 0.52,
      "peak_gyro_x_radps": 0.12,
      "peak_gyro_y_radps": 0.08,
      "max_roll_deg": 5.1,
      "max_pitch_deg": 3.9,
      "platform_stability": "stable",
      "confidence": 0.88,
      "evidence": "High angular velocity indicates turning motion. Moderate acceleration during rotation."
    }
  ]
}
```

### Common Issues

**Issue 1: All windows show motion_detected=false despite visible motion**
- **Symptom**: Motion thresholds too high for scenario
- **Cause**: Default thresholds calibrated for typical quadruped motion
- **Fix**: Adjust thresholds in tool implementation or validate IMU calibration

**Issue 2: Noisy IMU data causing false positives**
- **Symptom**: Stationary robot shows motion_detected=true
- **Cause**: Sensor noise or vibration exceeding thresholds
- **Fix**: Increase zero-filtering threshold or use median instead of peak

**Issue 3: Missing motion data files**
- **Symptom**: Tool returns error "Motion file not found"
- **Cause**: Scenario not extracted properly or wrong path
- **Fix**: Verify scenario directory and run `extract_windows.py`

---

## MotionSummaryAgent

### Purpose

Synthesizes per-window motion data into aggregate statistics and overall activity assessment.

**Problem it solves**: Converting raw window-level motion metrics into scenario-level insights (motion detection rate, activity level, peak dynamics).

### Inputs

**From Previous Agent:**
- `{temp:motion_data?}`: Output from MotionLoopAgent

**Schema Expected:**
```json
{
  "windows_analyzed": [...],
  "per_window_motion": [...]
}
```

### Outputs

**Output Key:** `temp:motion_output`

**Schema:**
```json
{
  "windows_analyzed": ["001", "002", "003"],
  "overall_stats": {
    "total_windows": 3,
    "motion_detected_count": 2,
    "motion_detection_rate": 0.67,
    "motion_type_distribution": {
      "stationary": 1,
      "translation": 1,
      "rotation": 1,
      "combined": 0
    },
    "max_horizontal_accel_mps2": 1.23,
    "max_angular_velocity_radps": 0.52,
    "overall_assessment": "moderate_activity"
  },
  "per_window_motion": [...]
}
```

### Prompting Strategy

**Key Instructions:**
1. **Read input carefully**: Parse `temp:motion_data?` JSON string
2. **Calculate statistics**:
   - Motion detection rate: `motion_detected_count / total_windows`
   - Motion type distribution: Count by type
   - Peak values: Max across all windows
3. **Assess activity level**:
   - `stationary_scenario`: motion_detection_rate < 0.2
   - `low_activity`: 0.2 <= rate < 0.5
   - `moderate_activity`: 0.5 <= rate < 0.8
   - `high_activity`: rate >= 0.8
4. **Preserve raw data**: Pass through `per_window_motion` unchanged

### Model Selection

**Default:** `gemini-2.0-flash-lite`  
**Recommended Upgrade:** Not typically needed

**Rationale:**
- Simple statistical aggregation (flash-lite capable)
- No complex reasoning required
- **Keep flash-lite** unless:
  - Debugging aggregation logic issues
  - Need more sophisticated activity classification

**Cost Impact:** flash-lite optimal for this task

### Tool Dependencies

**None** - Pure synthesis agent using only LLM reasoning on input data.

### Example Output

```json
{
  "windows_analyzed": ["001", "002", "003"],
  "overall_stats": {
    "total_windows": 3,
    "motion_detected_count": 2,
    "motion_detection_rate": 0.67,
    "motion_type_distribution": {
      "stationary": 1,
      "translation": 1,
      "rotation": 1,
      "combined": 0
    },
    "max_horizontal_accel_mps2": 1.23,
    "max_angular_velocity_radps": 0.52,
    "overall_assessment": "moderate_activity"
  },
  "per_window_motion": [
    {
      "window_id": "001",
      "motion_detected": true,
      "motion_type": "translation",
      "peak_horizontal_accel_mps2": 1.23,
      "peak_angular_velocity_radps": 0.18,
      "platform_stability": "stable"
    },
    {
      "window_id": "002",
      "motion_detected": false,
      "motion_type": "stationary",
      "peak_horizontal_accel_mps2": 0.08,
      "peak_angular_velocity_radps": 0.04,
      "platform_stability": "stable"
    },
    {
      "window_id": "003",
      "motion_detected": true,
      "motion_type": "rotation",
      "peak_horizontal_accel_mps2": 0.45,
      "peak_angular_velocity_radps": 0.52,
      "platform_stability": "stable"
    }
  ]
}
```

### Common Issues

**Issue 1: Missing input data**
- **Symptom**: Returns `{"error": "missing_motion_data"}`
- **Cause**: MotionLoopAgent failed or `output_key` misconfigured
- **Fix**: Check MotionLoopAgent logs and ADK context passing

**Issue 2: Incorrect motion_detection_rate calculation**
- **Symptom**: Rate doesn't match manual count
- **Cause**: Agent misunderstanding boolean logic or division
- **Fix**: Usually self-corrects; verify input data quality

**Issue 3: Activity assessment doesn't match expectations**
- **Symptom**: High motion rate classified as "low_activity"
- **Cause**: Thresholds in prompt may need adjustment
- **Fix**: Modify prompt thresholds or accept agent's judgment

---

## IMU-Based Motion Analysis: Technical Details

### Why IMU Instead of Odometry?

**Problem with Odometry:**
- Wheel encoders often broken or uncalibrated on quadruped robots
- Slip/drift accumulates over time
- May not be available in all scenarios

**IMU Advantages:**
- Always available (accelerometer + gyroscope on every robot)
- Direct measurement of motion dynamics
- No drift (measures instantaneous acceleration/rotation)
- Robust to wheel slip

**Trade-offs:**
- Cannot estimate absolute position (only motion presence/type)
- Requires threshold tuning for different robot platforms
- Sensitive to vibration and sensor noise

### Motion Detection Thresholds

**Default thresholds (empirically validated on Unitree Go2):**
```python
# These are default values that may need adjustment for different robot platforms
MOTION_THRESHOLDS = {
    "peak_horizontal_accel": 0.15,  # m/s²
    "peak_angular_velocity": 0.1,   # rad/s
    "avg_horizontal_accel": 0.08    # m/s²
}
```

**Note:** These thresholds are embedded in the tool implementation and can be adjusted by modifying the tool code for different robot platforms.

**Adjust for other platforms:**
- Larger robots: Increase thresholds (more mass, less responsive)
- Smaller robots: Decrease thresholds (more agile, sharper motions)
- Wheeled robots: Focus on `accel_x/y`, ignore `gyro_x/y` (rotation less relevant)

### Performance Metrics

**Tested on 13-window scenario (sim_run_new):**
- ✅ **100% motion detection accuracy** (validated against ground truth)
- ✅ **Robust to odometry failures** (works when odometry broken)
- ✅ **Low false positive rate** (<5% in stationary windows)

---

## Integration Example

```python
from odd_agents.agents import create_motion_loop_agent, create_motion_summary_agent
from google.genai import Client

client = Client(api_key=api_key)
scenario_path = "data/processed/runs/sim_run_test"

# Create loop agent with tools
loop_agent = create_motion_loop_agent(
    scenario_path=scenario_path,
    genai_client=client,
    model="gemini-2.0-flash-lite",  # flash-lite sufficient
    api_key=api_key
)

# Create summary agent
summary_agent = create_motion_summary_agent(
    api_key=api_key,
    model="gemini-2.0-flash-lite"
)

# Use in sequential workflow
from google.adk.agents import SequentialAgent
workflow = SequentialAgent(
    name="MotionWorkflow",
    sub_agents=[loop_agent, summary_agent]
)
```

## Related Documentation

- **[Main Agent Architecture](README.md)**: Overall workflow context
- **[Motion Analysis Improvements](../MOTION_ANALYSIS_IMPROVEMENTS.md)**: IMU implementation details
- **[COD Classifier](COD_CLASSIFIER.md)**: How motion data is used downstream
- **[Tool Implementation](../../odd_agents/tools/motion.py)**: Source code
