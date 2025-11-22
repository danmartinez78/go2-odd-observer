# Motion Agent Evaluation

Automated evaluation tests for the Motion Loop Agent using ADK evaluation framework.

---

## 🎯 Agent Purpose

The **MotionLoopAgent** analyzes IMU sensor data (gyroscope + accelerometer) to assess robot motion characteristics for ODD compliance.

**Responsibilities**:
- Motion classification (stationary/moving/turning)
- Angular velocity (gyro) statistics
- Linear acceleration statistics
- Platform stability assessment
- Per-window and aggregate motion analysis

**Architecture**: Loop agent → calls `analyze_motion_tool` → makes LLM inference calls

**⚠️ Critical**: Uses **IMU data only** (gyro + accel). Does NOT use odometry (stuck at zero in sim data).

---

## 📊 Test Cases

**Dataset**: `sim_run_test` windows **006** and **007**

**Test Configuration**:
- **Input**: 2 windows with IMU time series data (~24 samples per window)
- **Expected outputs**: JSON with per-window analyses + aggregate statistics
- **Total tool calls**: 3 (1x list_windows + 2x analyze_motion)

### Window 006 - Turning Motion
**IMU Data**:
- **Gyro** (rad/s):
  - X: -1.409 to 0.710 (mean -0.037)
  - Y: -0.386 to 0.863 (mean 0.131)
  - Z: **-0.859 to 0.164 (mean -0.187)** ← Turning left!
- **Accel** (m/s²):
  - X: 0.329 to 0.921 (mean 0.672) ← Forward acceleration
  - Y: 0.052 to 0.222 (mean 0.117)
  - Z: -0.148 to 0.175 (mean 0.036)

**Motion Interpretation**: Robot rotating left (Z gyro -0.187 rad/s ≈ -10.7°/s) with forward acceleration

**Expected Analysis**:
- Motion type: Turning/rotating
- Gyro Z: Negative mean (~-0.18 to -0.20 rad/s)
- Accel X: Positive (forward movement)
- Platform stability: Moderate to high (0.6-0.8)

### Window 007 - Forward Motion
**IMU Data**:
- **Gyro** (rad/s):
  - X: -0.852 to 1.238 (mean 0.039)
  - Y: -0.682 to 1.129 (mean -0.081)
  - Z: -0.044 to 0.133 (mean 0.036) ← Minimal rotation
- **Accel** (m/s²):
  - X: **0.808 to 0.975 (mean 0.907)** ← Strong forward!
  - Y: -0.017 to 0.037 (mean 0.003)
  - Z: -0.099 to 0.205 (mean 0.023)

**Motion Interpretation**: Robot moving mostly forward (X accel 0.907 m/s²) with minimal rotation

**Expected Analysis**:
- Motion type: Moving forward/translating
- Accel X: High positive (~0.85-0.95 m/s²)
- Gyro: Low magnitude across all axes
- Platform stability: High (0.7-0.9)

**⚠️ Odometry Issue**: All `odom_*` fields stuck at 0.0 (known sim issue). Agent MUST use IMU data.

See `../TEST_DATA.md` for detailed IMU statistics.

---

## 📋 Rubrics

### 1. `json_structure`
**Purpose**: Validate output format and required fields

**Pass Criteria**:
- Valid JSON (parseable)
- Contains `windows_analyzed` array
- Contains `per_window_motion` or similar structure
- Contains `overall_stats` with motion statistics

**Threshold**: 7/10

**Why It Matters**: Collision agent depends on this structure

### 2. `motion_completeness`
**Purpose**: Ensure all motion metrics calculated

**Pass Criteria**:
- Statistics for both windows present
- Metrics include: gyro stats, accel stats, motion classification
- No missing data for analyzed windows

**Threshold**: 7/10

**Why It Matters**: Incomplete motion data leads to incorrect risk assessment

### 3. `metrics_validity`
**Purpose**: Verify physically plausible values

**Pass Criteria**:
- Gyro values in reasonable range (±10 rad/s for Go2)
- Accel values in reasonable range (0-10 m/s² typical)
- Statistics match input data characteristics
- No obviously fabricated numbers

**Threshold**: 7/10

**Why It Matters**: Invalid metrics propagate to ODD compliance evaluation

---

## 🧪 Running Tests

### Fast Validation (~21s)
Tests tool calling sequence only - no quality assessment.

```bash
pytest tests/test_adk_evaluation.py::test_motion_tool_trajectory_only -v
```

**What it validates**:
- ✅ Calls `list_windows_tool` first
- ✅ Calls `analyze_motion_tool` for window 006
- ✅ Calls `analyze_motion_tool` for window 007
- ✅ Tool call order is correct

**Threshold**: 1.0 (strict - must be perfect)

### Quality Check (~80s)
Tests output quality using LLM-as-judge rubrics.

```bash
pytest tests/test_adk_evaluation.py::test_motion_rubric_quality -v
```

**What it validates**:
- ✅ JSON structure is valid and complete
- ✅ All motion metrics calculated
- ✅ Values are physically plausible
- ✅ **Inference quality** (because tool makes real LLM calls analyzing IMU data!)

**Threshold**: 0.7 (industry standard)

**Why it's slow**: Makes actual LLM inference calls (IMU data analysis) + LLM judge calls

### Comprehensive Validation (~120-200s)
Tests everything: tool trajectory + rubrics + hallucination detection.

```bash
pytest tests/test_adk_evaluation.py::test_motion_comprehensive -v
```

**What it validates**:
- ✅ All tool trajectory checks
- ✅ All rubric quality checks
- ✅ Hallucination detection (no fabricated data)

**Thresholds**: Tool trajectory 1.0, Rubrics 0.7, Hallucinations 1.0

---

## 📁 Files

```
motion/
├── README.md                        # This file
├── motion_agent.py                  # Agent export for ADK
├── motion_agent.test.json           # EvalSet test cases
├── test_config.json                 # Main config (tool + rubric)
├── test_config_tool_only.json       # Fast validation config
├── test_config_rubric_only.json     # Quality-only config
└── test_config_comprehensive.json   # Full validation config
```

---

## ✅ Expected Results

### Good Output Example
```json
{
  "windows_analyzed": ["006", "007"],
  "per_window_motion": {
    "006": {
      "window_id": "006",
      "motion_type": "turning",
      "gyro_stats": {
        "x": {"mean": -0.037, "max": 0.710, "variance": 0.3},
        "y": {"mean": 0.131, "max": 0.863, "variance": 0.15},
        "z": {"mean": -0.187, "max": 0.164, "variance": 0.08}
      },
      "accel_stats": {
        "x": {"mean": 0.672, "max": 0.921, "variance": 0.05},
        "y": {"mean": 0.117, "max": 0.222, "variance": 0.003},
        "z": {"mean": 0.036, "max": 0.175, "variance": 0.008}
      },
      "platform_stability": 0.72
    },
    "007": {
      "window_id": "007",
      "motion_type": "forward",
      "gyro_stats": { ... },
      "accel_stats": { ... },
      "platform_stability": 0.85
    }
  },
  "overall_stats": {
    "total_windows": 2,
    "motion_types": ["turning", "forward"],
    "avg_stability": 0.785
  }
}
```

### Common Issues

❌ **Using odometry** (will be all zeros):
```json
{
  "velocity": {
    "mean": 0.0,  // Wrong! Odometry stuck at zero
    "max": 0.0
  }
}
```

❌ **Unrealistic values**:
```json
{
  "gyro_stats": {
    "z": {"mean": 15.7}  // Impossible! Go2 max ~10 rad/s
  }
}
```

❌ **Missing windows**:
```json
{
  "windows_analyzed": ["006"],  // Missing 007!
  "per_window_motion": { ... }
}
```

---

## 🔧 Configuration Details

### Test Config Files

**test_config.json** (Main):
```json
{
  "criteria": [
    {"name": "tool_trajectory", "weight": 1.0},
    {"name": "rubric_based", "weight": 1.0}
  ],
  "config": {"max_workers": 3}
}
```
Runtime: ~90-100s, Validates: Orchestration + quality

**test_config_tool_only.json**:
```json
{
  "criteria": [
    {"name": "tool_trajectory", "weight": 1.0}
  ]
}
```
Runtime: ~21s, Validates: Tool calls only

**test_config_rubric_only.json**:
```json
{
  "criteria": [
    {"name": "rubric_based", "weight": 1.0}
  ],
  "config": {"max_workers": 3}
}
```
Runtime: ~80s, Validates: Output quality (+ inference!)

**test_config_comprehensive.json**:
```json
{
  "criteria": [
    {"name": "tool_trajectory", "weight": 1.0},
    {"name": "rubric_based", "weight": 1.0},
    {"name": "hallucinations", "weight": 1.0}
  ],
  "config": {"max_workers": 3}
}
```
Runtime: ~120-200s, Validates: Everything

---

## 🎓 Key Insights

### Why Rubric Tests = Inference Tests

When `test_motion_rubric_quality` runs:
1. Test calls `MotionLoopAgent`
2. Agent calls `list_windows_tool` → gets ["006", "007"]
3. Agent calls `analyze_motion_tool("006")`
   - Tool loads: `motion_sim_run_test_w006.json`
   - Tool extracts: Gyro (x,y,z) and Accel (x,y,z) time series
   - Tool calls: `genai_client.models.generate_content()` with IMU data
   - **Actual LLM inference happens here** (analyzes motion patterns)
   - Tool returns: Motion analysis JSON
4. Agent calls `analyze_motion_tool("007")` (repeat inference)
5. Agent aggregates results into final JSON
6. LLM judge evaluates output quality using rubrics

**Evidence**: Test takes ~80 seconds (not 2-3s for JSON validation alone)

**Conclusion**: Rubric tests validate BOTH orchestration AND IMU data inference quality!

### IMU vs Odometry

**Why IMU Only**:
- Odometry stuck at zero in sim data (known issue)
- IMU provides direct motion sensing (gyro + accel)
- No integration/drift issues with raw IMU

**What IMU Tells Us**:
- **Gyro**: Angular velocity (rotation rate) in rad/s
  - Positive Z = turning right
  - Negative Z = turning left
  - High magnitude = fast rotation
- **Accel**: Linear acceleration in m/s²
  - Positive X = forward acceleration
  - Negative X = braking/backward
  - High magnitude = aggressive motion

**Physical Ranges** (Unitree Go2):
- Gyro: ±10 rad/s typical
- Accel: 0-10 m/s² typical (within 1g most of the time)

---

## 📚 Related Documentation

- **Parent docs**: `../README.md`
- **Test data specs**: `../TEST_DATA.md` (⚠️ Read odometry issue section!)
- **Lessons learned**: `../LESSONS_LEARNED.md`
- **Agent implementation**: `../../../odd_agents/agents/motion.py`
- **Tool implementation**: `../../../odd_agents/tools/motion.py`
- **Manual testing**: `../../../tests/test_motion_agent.py`

---

**Last Updated**: November 22, 2025  
**Agent Version**: MotionLoopAgent v1.0  
**Test Coverage**: Tool trajectory ✅, Rubrics ⏳, Comprehensive ⏳
