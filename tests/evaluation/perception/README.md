# Perception Agent Evaluation

Automated evaluation tests for the Perception Loop Agent using ADK evaluation framework.

---

## 🎯 Agent Purpose

The **PerceptionLoopAgent** analyzes multimodal sensor data (RGB camera + 4 LiDAR BEV channels) to assess environmental characteristics for ODD compliance.

**Responsibilities**:
- Environment type classification (indoor/outdoor)
- Lighting conditions assessment
- Obstacle detection and density estimation
- Terrain type identification
- Traversability scoring
- Per-window and aggregate analysis

**Architecture**: Loop agent → calls `analyze_window_perception_tool` → makes multimodal LLM inference calls

---

## 📊 Test Cases

**Dataset**: `sim_run_test` windows **006** and **007**

**Test Configuration**:
- **Input**: 2 windows with complete sensor coverage
- **Expected outputs**: JSON with per-window analyses + aggregate summary
- **Total tool calls**: 3 (1x list_windows + 2x analyze_window_perception)

### Window 006
**Sensor Data**:
- Camera: Indoor environment, moderate lighting, visible furniture/obstacles
- BEV Occupancy: Obstacle density ~0.45 (moderate clutter)
- BEV Height: Relatively flat terrain with minor variations
- BEV Density: Consistent LiDAR returns
- BEV Roughness: Smooth surface (indoor floor)

**Expected Analysis**:
- Environment: Indoor
- Lighting: Moderate
- Obstacles: 10-15 detected, moderate density (0.4-0.5)
- Terrain: Smooth/flat
- Traversability: 0.65-0.80

### Window 007
**Sensor Data**:
- Camera: Similar indoor environment, good lighting
- BEV Occupancy: Similar obstacle density
- BEV Height: Flat terrain
- BEV Density: Consistent coverage
- BEV Roughness: Smooth surface

**Expected Analysis**:
- Environment: Indoor
- Lighting: Moderate to bright
- Obstacles: Similar count and density to 006
- Terrain: Smooth/flat
- Traversability: 0.65-0.80

See `../TEST_DATA.md` for detailed sensor data characteristics.

---

## 📋 Rubrics

### 1. `json_structure`
**Purpose**: Validate output format and required fields

**Pass Criteria**:
- Valid JSON (parseable)
- Contains `windows_analyzed` array
- Contains `per_window_perception` dictionary
- Each window has required keys: `window_id`, `environment_type`, `lighting`, `obstacles`, `terrain_type`, `traversability_score`

**Threshold**: 7/10

**Why It Matters**: Downstream agents depend on this structure

### 2. `complete_analysis`
**Purpose**: Ensure all windows were processed

**Pass Criteria**:
- `windows_analyzed` includes both "006" and "007"
- `per_window_perception` has entries for both windows
- No windows skipped or missing

**Threshold**: 7/10

**Why It Matters**: Incomplete analysis leads to incorrect ODD compliance assessment

### 3. `data_integrity`
**Purpose**: Verify tool outputs preserved without modification

**Pass Criteria**:
- Tool outputs appear in final JSON
- No hallucinated data (fabricated windows, fake obstacles)
- Consistent structure across windows

**Threshold**: 7/10

**Why It Matters**: Ensures agent orchestration doesn't corrupt inference results

---

## 🧪 Running Tests

### Fast Validation (~23s)
Tests tool calling sequence only - no quality assessment.

```bash
pytest tests/test_adk_evaluation.py::test_perception_tool_trajectory_only -v
```

**What it validates**:
- ✅ Calls `list_windows_tool` first
- ✅ Calls `analyze_window_perception_tool` for window 006
- ✅ Calls `analyze_window_perception_tool` for window 007
- ✅ Tool call order is correct

**Threshold**: 1.0 (strict - must be perfect)

### Quality Check (~71s)
Tests output quality using LLM-as-judge rubrics.

```bash
pytest tests/test_adk_evaluation.py::test_perception_rubric_quality -v
```

**What it validates**:
- ✅ JSON structure is valid and complete
- ✅ All windows analyzed
- ✅ Data integrity maintained
- ✅ **Inference quality** (because tool makes real LLM calls!)

**Threshold**: 0.7 (industry standard)

**Why it's slow**: Makes actual multimodal LLM inference calls (camera + 4 BEV images per window) + LLM judge calls

### Comprehensive Validation (~120-150s)
Tests everything: tool trajectory + rubrics + hallucination detection.

```bash
pytest tests/test_adk_evaluation.py::test_perception_comprehensive -v
```

**What it validates**:
- ✅ All tool trajectory checks
- ✅ All rubric quality checks
- ✅ Hallucination detection (no fabricated data)

**Thresholds**: Tool trajectory 1.0, Rubrics 0.7, Hallucinations 1.0

---

## 📁 Files

```
perception/
├── README.md                           # This file
├── perception_agent.py                 # Agent export for ADK
├── perception_agent.test.json          # EvalSet test cases
├── test_config.json                    # Main config (tool + rubric)
├── test_config_tool_only.json          # Fast validation config
├── test_config_rubric_only.json        # Quality-only config
├── test_config_comprehensive.json      # Full validation config
└── test_config_response_only.json      # Legacy config
```

---

## ✅ Expected Results

### Good Output Example
```json
{
  "windows_analyzed": ["006", "007"],
  "per_window_perception": {
    "006": {
      "window_id": "006",
      "environment_type": "indoor",
      "lighting": "moderate",
      "obstacles": {
        "count": 12,
        "types": ["furniture", "walls"],
        "density": 0.45
      },
      "terrain_type": "smooth",
      "traversability_score": 0.72
    },
    "007": {
      "window_id": "007",
      "environment_type": "indoor",
      "lighting": "bright",
      "obstacles": {
        "count": 11,
        "types": ["furniture", "walls"],
        "density": 0.43
      },
      "terrain_type": "smooth",
      "traversability_score": 0.75
    }
  }
}
```

### Common Issues

❌ **Missing windows**:
```json
{
  "windows_analyzed": ["006"],  // Missing 007!
  "per_window_perception": { ... }
}
```

❌ **Invalid structure**:
```json
{
  "results": [ ... ]  // Wrong key! Should be "windows_analyzed"
}
```

❌ **Hallucinated data**:
```json
{
  "windows_analyzed": ["006", "007", "008"],  // 008 doesn't exist!
  ...
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
Runtime: ~80-90s, Validates: Orchestration + quality

**test_config_tool_only.json**:
```json
{
  "criteria": [
    {"name": "tool_trajectory", "weight": 1.0}
  ]
}
```
Runtime: ~23s, Validates: Tool calls only

**test_config_rubric_only.json**:
```json
{
  "criteria": [
    {"name": "rubric_based", "weight": 1.0}
  ],
  "config": {"max_workers": 3}
}
```
Runtime: ~71s, Validates: Output quality (+ inference!)

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
Runtime: ~120-150s, Validates: Everything

---

## 🎓 Key Insights

### Why Rubric Tests = Inference Tests

When `test_perception_rubric_quality` runs:
1. Test calls `PerceptionLoopAgent`
2. Agent calls `list_windows_tool` → gets ["006", "007"]
3. Agent calls `analyze_window_perception_tool("006")`
   - Tool loads: `cam_sim_run_test_w006.png` + 4 BEV images
   - Tool calls: `genai_client.models.generate_content()` with multimodal input
   - **Actual LLM inference happens here** (vision model analyzes images)
   - Tool returns: Environment analysis JSON
4. Agent calls `analyze_window_perception_tool("007")` (repeat inference)
5. Agent aggregates results into final JSON
6. LLM judge evaluates output quality using rubrics

**Evidence**: Test takes 71 seconds (not 2-3s for JSON validation alone)

**Conclusion**: Rubric tests validate BOTH orchestration AND multimodal vision inference quality!

---

## 📚 Related Documentation

- **Parent docs**: `../README.md`
- **Test data specs**: `../TEST_DATA.md`
- **Lessons learned**: `../LESSONS_LEARNED.md`
- **Agent implementation**: `../../../odd_agents/agents/perception.py`
- **Tool implementation**: `../../../odd_agents/tools/perception.py`
- **Manual testing**: `../../../tests/test_perception_agent.py`

---

**Last Updated**: November 22, 2025  
**Agent Version**: PerceptionLoopAgent v1.0  
**Test Coverage**: Tool trajectory ✅, Rubrics ✅, Comprehensive ⏳
