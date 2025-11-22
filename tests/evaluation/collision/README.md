# Collision Agent Evaluation

Automated evaluation tests for the Collision Loop Agent using ADK evaluation framework.

---

## 🎯 Agent Purpose

The **CollisionLoopAgent** analyzes collision risk by fusing multimodal sensor data (camera, LiDAR BEV, and motion context) to assess safety for robot navigation.

**Responsibilities**:
- Collision risk classification (none/low/medium/high/critical)
- Obstacle detection and distance estimation
- Multimodal sensor fusion (camera + BEV + motion)
- Risk confidence assessment
- Actionable safety recommendations
- Per-window and aggregate collision analysis

**Architecture**: Loop agent → calls `analyze_collision_risk_tool` → makes LLM inference calls with multimodal inputs

---

## 📊 Test Cases

**Dataset**: `sim_run_test` windows **006** and **007**

**Test Configuration**:
- **Input**: 2 windows with camera images, BEV occupancy maps, and motion context
- **Expected outputs**: JSON with per-window collision risk assessments
- **Total tool calls**: 3 (1x list_windows + 2x analyze_collision_risk)

### Window 006 - Turning Motion + Obstacles
**Environment**:
- **Scene**: Indoor environment with moderate obstacle density (~0.45)
- **Lighting**: Moderate indoor lighting
- **Terrain**: Flat, smooth surface

**Motion Context** (from motion agent):
- Robot rotating left (Z gyro ~-0.187 rad/s ≈ -10.7°/s)
- Forward acceleration (X accel ~0.672 m/s²)
- Platform stability: Moderate (0.6-0.8)

**Expected Analysis**:
- Risk level: Low to medium (moving + obstacles present)
- Closest obstacle: 0.5-3m range (indoor navigation)
- Hazards: Specific obstacles visible in camera/BEV
- Recommendation: slow_down or continue with caution
- Confidence: Moderate to high (0.6-0.9)

### Window 007 - Forward Motion + Obstacles
**Environment**:
- **Scene**: Similar indoor environment
- **Lighting**: Good indoor lighting
- **Terrain**: Flat, smooth surface

**Motion Context** (from motion agent):
- Robot moving forward (X accel ~0.907 m/s²)
- Minimal rotation (Z gyro ~0.036 rad/s)
- Platform stability: High (0.7-0.9)

**Expected Analysis**:
- Risk level: Low to medium (active forward motion)
- Closest obstacle: 0.5-3m range
- Hazards: Forward obstacles identified
- Recommendation: Appropriate for speed and obstacles
- Confidence: High (0.7-0.9)

See `../TEST_DATA.md` for detailed sensor data specifications.

---

## 📋 Rubrics

### 1. `json_structure`
**Purpose**: Validate output format and required fields

**Pass Criteria**:
- Valid JSON (parseable)
- Contains `windows_analyzed` array
- Contains `collision_events` array
- Proper data types and nesting

**Threshold**: 7/10

**Why It Matters**: Downstream agents depend on this structure

### 2. `completeness`
**Purpose**: Ensure all windows analyzed

**Pass Criteria**:
- Both windows 006 and 007 present in windows_analyzed
- Exactly 2 collision events (one per window)
- Window IDs consistent between arrays
- No missing or duplicate windows

**Threshold**: 7/10

**Why It Matters**: Incomplete analysis leads to incorrect safety assessments

### 3. `risk_score_validity`
**Purpose**: Verify collision risk metrics are valid

**Pass Criteria**:
- Risk level in valid set: none/low/medium/high/critical
- Risk confidence between 0.0 and 1.0 (exclusive)
- Closest obstacle distance positive or null
- Values reasonable for indoor navigation

**Threshold**: 7/10

**Why It Matters**: Invalid metrics compromise safety decisions

### 4. `collision_detection_quality`
**Purpose**: Evaluate multimodal reasoning quality

**Pass Criteria**:
- Evidence references camera observations
- Evidence references BEV/occupancy data
- Specific hazards identified (not generic)
- Recommendations appropriate for risk level
- Multimodal fusion demonstrated

**Threshold**: 7/10

**Why It Matters**: Quality of hazard detection directly impacts robot safety

### 5. `data_integrity`
**Purpose**: Verify tool outputs preserved correctly

**Pass Criteria**:
- collision_events contains actual tool responses
- All fields from tool output present
- Window IDs consistent throughout
- No contradictions (e.g., high risk + continue)

**Threshold**: 7/10

**Why It Matters**: Data loss or corruption invalidates safety analysis

---

## 🧪 Running Tests

### Fast Validation (~20s)
Tests tool calling sequence only - no quality assessment.

```bash
pytest tests/test_adk_evaluation.py::test_collision_tool_trajectory_only -v
```

**What it validates**:
- ✅ Calls `list_windows_tool` first
- ✅ Calls `analyze_collision_risk_tool` for window 006
- ✅ Calls `analyze_collision_risk_tool` for window 007
- ✅ Tool call order is correct

**Threshold**: 1.0 (strict - must be perfect)

### Quality Check (~70-80s)
Tests output quality using LLM-as-judge rubrics.

```bash
pytest tests/test_adk_evaluation.py::test_collision_rubric_quality -v
```

**What it validates**:
- ✅ JSON structure is valid and complete
- ✅ All collision risk metrics calculated
- ✅ Multimodal reasoning quality
- ✅ **Inference quality** (tool makes real multimodal LLM calls!)

**Threshold**: 0.7 (industry standard)

**Why it's slow**: Makes actual LLM inference calls (multimodal analysis) + LLM judge calls

### Comprehensive Validation (~120-200s)
Tests everything: tool trajectory + rubrics + hallucination detection.

```bash
pytest tests/test_adk_evaluation.py::test_collision_comprehensive -v
```

**What it validates**:
- ✅ All tool trajectory checks
- ✅ All rubric quality checks
- ✅ Hallucination detection (no fabricated hazards)

**Thresholds**: Tool trajectory 1.0, Rubrics 0.7, Hallucinations 1.0

---

## 📁 Files

```
collision/
├── README.md                        # This file
├── collision_agent.py               # Agent export for ADK
├── collision_agent.test.json        # EvalSet test cases
├── test_config_tool_traj.json       # Fast validation config
├── test_config_rubric_only.json     # Quality-only config
└── test_config_comprehensive.json   # Full validation config
```

---

## ✅ Expected Results

### Good Output Example
```json
{
  "windows_analyzed": ["006", "007"],
  "collision_events": [
    {
      "window_id": "006",
      "collision_risk_level": "low",
      "risk_confidence": 0.75,
      "closest_obstacle_meters": 1.8,
      "obstacle_direction": "front",
      "motion_contributes_to_risk": true,
      "camera_hazards": ["obstacle ahead", "narrow passage"],
      "bev_hazards": ["occupied cells in forward path"],
      "recommended_action": "slow_down",
      "evidence": "Forward obstacles detected in camera and BEV. Robot turning left with moderate speed. Recommend reducing velocity."
    },
    {
      "window_id": "007",
      "collision_risk_level": "low",
      "risk_confidence": 0.82,
      "closest_obstacle_meters": 2.1,
      "obstacle_direction": "front",
      "motion_contributes_to_risk": true,
      "camera_hazards": ["distant obstacle"],
      "bev_hazards": ["sparse occupancy ahead"],
      "recommended_action": "continue",
      "evidence": "Clear path ahead with distant obstacles. Strong forward motion detected. Safe to continue at current speed."
    }
  ]
}
```

### Common Issues

❌ **Invalid risk level**:
```json
{
  "collision_risk_level": "very_high"  // Wrong! Must be: none/low/medium/high/critical
}
```

❌ **Out of range confidence**:
```json
{
  "risk_confidence": 1.0  // Unrealistic! Should be 0.0-1.0 exclusive
}
```

❌ **Missing windows**:
```json
{
  "windows_analyzed": ["006"],  // Missing 007!
  "collision_events": [...]
}
```

❌ **Generic hazards**:
```json
{
  "camera_hazards": ["objects detected"],  // Too vague!
  "bev_hazards": []  // Empty - should identify specific hazards
}
```

❌ **Inconsistent recommendations**:
```json
{
  "collision_risk_level": "high",
  "recommended_action": "continue"  // Contradiction!
}
```

---

## 🔧 Configuration Details

### Test Config Files

**test_config_tool_traj.json**:
```json
{
  "criteria": {
    "tool_trajectory_avg_score": {
      "threshold": 1.0,
      "match_type": "IN_ORDER"
    }
  }
}
```
Runtime: ~20s, Validates: Tool calls only

**test_config_rubric_only.json**:
```json
{
  "criteria": {
    "rubric_based_avg_score": {
      "threshold": 0.7
    }
  },
  "config": {"max_workers": 3}
}
```
Runtime: ~70-80s, Validates: Output quality (+ inference!)

**test_config_comprehensive.json**:
```json
{
  "criteria": {
    "tool_trajectory_avg_score": {"threshold": 1.0, "match_type": "IN_ORDER"},
    "rubric_based_avg_score": {"threshold": 0.7},
    "hallucinations_avg_score": {"threshold": 1.0}
  },
  "config": {"max_workers": 3}
}
```
Runtime: ~120-200s, Validates: Everything

---

## 🎓 Key Insights

### Why Rubric Tests = Inference Tests

When `test_collision_rubric_quality` runs:
1. Test calls `CollisionLoopAgent`
2. Agent calls `list_windows_tool` → gets ["006", "007"]
3. Agent calls `analyze_collision_risk_tool("006")`
   - Tool loads: Camera image + BEV occupancy map
   - Tool receives: Motion metrics context
   - Tool calls: `genai_client.models.generate_content()` with multimodal inputs
   - **Actual LLM multimodal inference happens here**
   - Tool returns: Collision risk analysis JSON
4. Agent calls `analyze_collision_risk_tool("007")` (repeat inference)
5. Agent aggregates results into final JSON
6. LLM judge evaluates output quality using rubrics

**Evidence**: Test takes ~70-80 seconds (not 2-3s for JSON validation alone)

**Conclusion**: Rubric tests validate BOTH orchestration AND multimodal collision inference quality!

### Multimodal Fusion

**Collision agent uses 3 data sources**:
1. **Camera** (egocentric view): Visual obstacle detection, scene context
2. **BEV Occupancy** (LiDAR top-down): Precise spatial obstacle mapping
3. **Motion Context**: Speed, direction, platform stability

**Good analysis should**:
- Reference all three sources in evidence
- Identify specific hazards from each modality
- Integrate motion into risk assessment (higher speed = higher risk)
- Provide concrete, actionable recommendations

**Quality markers**:
- Specific obstacle descriptions (not "objects detected")
- Distance estimates grounded in BEV/camera data
- Recommendations consistent with risk level
- Evidence explains multimodal reasoning

---

## 📚 Related Documentation

- **Parent docs**: `../README.md`
- **Test data specs**: `../TEST_DATA.md`
- **Lessons learned**: `../LESSONS_LEARNED.md`
- **Agent implementation**: `../../../odd_agents/agents/collision.py`
- **Tool implementation**: `../../../odd_agents/tools/collision.py`
- **Manual testing**: `../../../tests/test_collision_agent.py`

---

**Last Updated**: November 22, 2025  
**Agent Version**: CollisionLoopAgent v1.0  
**Test Coverage**: Tool trajectory ✅, Rubrics ✅, Comprehensive ✅
