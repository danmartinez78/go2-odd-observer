# Perception Agents

## Overview

The perception pipeline performs **multimodal environment analysis** by combining camera and LiDAR data to understand the robot's surroundings. This two-agent system processes time-windowed sensor snapshots and produces environment classifications and obstacle assessments.

---

## PerceptionLoopAgent

### Purpose

Orchestrates per-window perception analysis by iterating through all time windows in a scenario and collecting multimodal sensor analysis results.

**Problem it solves**: Coordinating systematic analysis of all available sensor snapshots without missing windows or duplicating work.

### Inputs

**From User/Workflow:**
- None (receives initial query to start analysis)

**From Tools:**
- `list_windows_tool()`: Available window IDs in the scenario
- `analyze_window_perception_tool(window_id)`: Multimodal analysis results

**Environment Dependencies:**
- Scenario directory with camera images (`cam_*.png`)
- LiDAR BEV occupancy maps (`bev_occupancy_*.png`)

### Outputs

**Output Key:** `temp:perception_data`

**Schema:**
```json
{
  "windows_analyzed": ["001", "002", "003"],
  "per_window_perception": [
    {
      "window_id": "001",
      "environment_type": "indoor_office",
      "lighting_class": "bright",
      "terrain_roughness_class": "smooth",
      "obstacle_density": 0.35,
      "traversability_score": 0.75,
      "occupancy_ratio": 0.18,
      "primary_obstacles": ["desk", "chair", "cabinet"],
      "evidence": "Well-lit office space with furniture obstacles..."
    }
  ]
}
```

### Prompting Strategy

**Key Instructions:**
1. **Sequential processing**: Call `list_windows_tool()` exactly once, then iterate in order
2. **No modifications**: Collect tool responses exactly as returned (no interpretation)
3. **JSON output only**: No commentary or explanations outside JSON structure

**Critical Pattern:**
```
1. list_windows_tool() → ["001", "002", "003"]
2. For each window_id:
     analyze_window_perception_tool(window_id) → {...}
3. Collect all results in order
4. Return JSON with windows_analyzed + per_window_perception arrays
```

**Why this works**: The agent acts as a pure orchestrator, delegating all perception logic to the multimodal tool. This ensures consistent processing and prevents hallucination.

### Model Selection

**Default:** `gemini-2.0-flash-lite`  
**Recommended Upgrade:** `gemini-2.5-pro`

**Rationale:**
- Loop agent only orchestrates tool calls (simple JSON collection)
- **Flash-lite sufficient** for coordination logic
- Upgrade to **2.5-pro** if:
  - Need more reliable tool calling in complex scenarios
  - Scenario has many windows (>20) requiring precise orchestration

**Cost Impact:** flash-lite saves ~70% vs. pro, acceptable for coordination task

### Tool Dependencies

#### 1. `list_windows_tool()`
**Purpose**: Discover available time windows in scenario

**Implementation**: 
- Reads scenario index CSV
- Checks for existence of motion data files (used as ground truth)
- Returns ordered list of window IDs

**Output:**
```json
{
  "status": "success",
  "windows": ["001", "002", "003"],
  "count": 3
}
```

#### 2. `analyze_window_perception_tool(window_id)`
**Purpose**: Multimodal perception analysis of single window

**Implementation:**
- Loads camera image and LiDAR BEV map
- Calls Gemini with multimodal prompt + both images
- Extracts structured JSON from response

**Multimodal Fusion:**
- **Camera image**: Environment type, lighting, visual obstacles
- **LiDAR BEV**: Occupancy ratio, obstacle density, traversability

**Key Distinctions in Prompt:**
- `terrain_roughness_class`: Ground surface elevation (not texture)
  - "smooth" = flat floor with minimal elevation changes (includes rugs/carpets on flat surface)
  - "moderate" = small bumps, gentle slopes, slightly uneven surfaces
  - "rough" = significant elevation changes, stairs, ramps, rocky/unpaved ground
  - "very_rough" = extreme terrain (large boulders, steep slopes, severely uneven surfaces)
- `obstacle_density`: Concentration of objects in forward path
- `traversability_score`: Combined terrain + obstacles assessment

**Output:**
```json
{
  "window_id": "001",
  "environment_type": "indoor_office",
  "lighting_class": "bright",
  "terrain_roughness_class": "smooth",
  "obstacle_density": 0.35,
  "traversability_score": 0.75,
  "occupancy_ratio": 0.18,
  "primary_obstacles": ["desk", "chair"],
  "evidence": "..."
}
```

### Example Output

**Full PerceptionLoopAgent Output:**
```json
{
  "windows_analyzed": ["001", "002"],
  "per_window_perception": [
    {
      "window_id": "001",
      "environment_type": "indoor_office",
      "lighting_class": "bright",
      "terrain_roughness_class": "smooth",
      "obstacle_density": 0.35,
      "traversability_score": 0.75,
      "occupancy_ratio": 0.18,
      "primary_obstacles": ["desk", "chair", "cabinet"],
      "evidence": "Well-lit office space with standard furniture. Smooth floor with clear navigation paths between obstacles."
    },
    {
      "window_id": "002",
      "environment_type": "indoor_office",
      "lighting_class": "bright",
      "terrain_roughness_class": "smooth",
      "obstacle_density": 0.62,
      "traversability_score": 0.45,
      "occupancy_ratio": 0.31,
      "primary_obstacles": ["sofa", "table", "boxes"],
      "evidence": "Office environment with dense furniture arrangement. Navigable but constrained paths."
    }
  ]
}
```

### Common Issues

**Issue 1: Tool not found**
- **Symptom**: Agent reports "tool not available" or tries wrong tool name
- **Cause**: Tool factory not called before agent creation
- **Fix**: Ensure `create_perception_tools()` called in agent factory

**Issue 2: Missing images**
- **Symptom**: Tool returns error "image file not found"
- **Cause**: Scenario path incorrect or images not extracted
- **Fix**: Verify scenario directory structure and run `extract_windows.py`

**Issue 3: Confusion about terrain vs. obstacles**
- **Symptom**: High-pile rug classified as "rough terrain"
- **Cause**: Model confusing surface texture with elevation changes
- **Fix**: Prompt emphasizes terrain = elevation, not texture (already mitigated)

---

## PerceptionSummaryAgent

### Purpose

Synthesizes per-window perception data into aggregate statistics and overall environment classification.

**Problem it solves**: Converting raw window-level observations into scenario-level insights (environment type, data source classification).

### Inputs

**From Previous Agent:**
- `{temp:perception_data?}`: Output from PerceptionLoopAgent

**Schema Expected:**
```json
{
  "windows_analyzed": [...],
  "per_window_perception": [...]
}
```

### Outputs

**Output Key:** `temp:perception_output`

**Schema:**
```json
{
  "windows_analyzed": ["001", "002"],
  "environment_classification": {
    "primary_class": "indoor_office",
    "confidence": 0.95,
    "evidence": ["consistent office furniture", "indoor lighting patterns"]
  },
  "data_source_classification": {
    "source": "simulation",
    "confidence": 1.0,
    "evidence": ["perfect textures", "uniform lighting", "lack of sensor noise"]
  },
  "per_window_perception": [...]
}
```

### Prompting Strategy

**Key Instructions:**
1. **Read input carefully**: Parse `temp:perception_data?` JSON string
2. **Classify environment**: Determine overall environment class from per-window data
   - Allowed classes: `indoor_office`, `indoor_corridor`, `indoor`, `outdoor_urban`, `outdoor_natural`, `open_space`
   - Use majority vote or dominant pattern
3. **Classify data source**: Determine if simulation vs. real-world
   - Simulation indicators: Perfect textures, uniform lighting, geometric regularity
   - Real-world indicators: Natural lighting variation, sensor noise, organic textures
4. **Preserve raw data**: Pass through `per_window_perception` unchanged

**Why data source classification matters**: 
- Simulation data may have different characteristics (perfect geometry, no noise)
- Real-world data requires different expectations for sensor quality
- Flows through entire pipeline to final report for context

### Model Selection

**Default:** `gemini-2.0-flash-lite`  
**Recommended Upgrade:** `gemini-2.5-pro`

**Rationale:**
- Summary involves JSON synthesis (flash-lite capable)
- **Upgrade to 2.5-pro if**:
  - Need more sophisticated environment classification logic
  - Scenario has ambiguous environments (e.g., mixed indoor/outdoor)
  - Data source classification is critical (e.g., validating simulator fidelity)

**Cost Impact:** flash-lite saves ~70% vs. pro

### Tool Dependencies

**None** - Pure synthesis agent using only LLM reasoning on input data.

### Example Output

```json
{
  "windows_analyzed": ["001", "002", "003"],
  "environment_classification": {
    "primary_class": "indoor_office",
    "confidence": 0.95,
    "evidence": [
      "Consistent office furniture across windows",
      "Indoor lighting patterns",
      "Smooth floor surfaces"
    ]
  },
  "data_source_classification": {
    "source": "simulation",
    "confidence": 1.0,
    "evidence": [
      "Perfect texture rendering",
      "Uniform lighting without natural variation",
      "Geometric regularity in furniture placement",
      "Absence of sensor noise"
    ]
  },
  "per_window_perception": [
    {
      "window_id": "001",
      "environment_type": "indoor_office",
      "lighting_class": "bright",
      "terrain_roughness_class": "smooth",
      "obstacle_density": 0.35,
      "traversability_score": 0.75,
      "occupancy_ratio": 0.18,
      "primary_obstacles": ["desk", "chair", "cabinet"],
      "evidence": "Well-lit office space..."
    },
    {
      "window_id": "002",
      "environment_type": "indoor_office",
      "lighting_class": "bright",
      "terrain_roughness_class": "smooth",
      "obstacle_density": 0.62,
      "traversability_score": 0.45,
      "occupancy_ratio": 0.31,
      "primary_obstacles": ["sofa", "table"],
      "evidence": "Dense furniture arrangement..."
    }
  ]
}
```

### Common Issues

**Issue 1: Missing input data**
- **Symptom**: Returns `{"error": "missing_perception_data"}`
- **Cause**: PerceptionLoopAgent failed or `output_key` misconfigured
- **Fix**: Check PerceptionLoopAgent logs and ADK context passing

**Issue 2: Inconsistent environment classification**
- **Symptom**: Primary class doesn't match per-window observations
- **Cause**: Conflicting environment types across windows
- **Fix**: Expected behavior - agent should use majority vote or explain conflict in evidence

**Issue 3: Wrong data source classification**
- **Symptom**: Simulation classified as real-world (or vice versa)
- **Cause**: Ambiguous visual indicators
- **Fix**: Provide more explicit indicators in scenario or accept lower confidence

---

## Integration Example

```python
from odd_agents.agents import create_perception_loop_agent, create_perception_summary_agent
from google.genai import Client

client = Client(api_key=api_key)
scenario_path = "data/processed/runs/sim_run_test"

# Create loop agent with tools
loop_agent = create_perception_loop_agent(
    scenario_path=scenario_path,
    genai_client=client,
    model="gemini-2.5-pro",  # Upgrade for better quality
    api_key=api_key
)

# Create summary agent
summary_agent = create_perception_summary_agent(
    api_key=api_key,
    model="gemini-2.0-flash-lite"  # flash-lite sufficient for synthesis
)

# Use in sequential workflow
from google.adk.agents import SequentialAgent
workflow = SequentialAgent(
    name="PerceptionWorkflow",
    sub_agents=[loop_agent, summary_agent]
)
```

## Related Documentation

- **[Main Agent Architecture](README.md)**: Overall workflow context
- **[Model Selection Guide](../MODEL_SELECTION_GUIDE.md)**: Cost optimization strategies
- **[COD Classifier](COD_CLASSIFIER.md)**: How perception data is used downstream
- **[Tool Implementation](../../odd_agents/tools/perception.py)**: Source code
