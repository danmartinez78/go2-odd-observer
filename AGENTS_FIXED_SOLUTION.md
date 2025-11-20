# Fixed Agents Script - Complete Working Solution

## Overview
`agents_fixed.py` is a complete, working Python script that demonstrates all four agents functioning correctly with proper parameter names and tool usage.

## Status
✅ **ALL AGENTS PASSING**
- Motion Analyzer: ✅ SUCCESS
- Vision Analyzer: ✅ SUCCESS  
- Terrain Analyzer: ✅ SUCCESS
- Collision Detector: ✅ SUCCESS

## Key Fixes Applied

### 1. Correct Parameter Names for `get_window_image()`
The root cause of failures was incorrect parameter names. The function now requires EXACT parameter values:

```python
# CORRECT FORMAT:
get_window_image(window_id="006", image_type="camera")
get_window_image(window_id="006", image_type="bev_occupancy")
get_window_image(window_id="006", image_type="bev_height")
get_window_image(window_id="006", image_type="bev_density")
get_window_image(window_id="006", image_type="bev_roughness")

# WRONG (will fail):
get_window_image(image_type='BEV')  # Wrong value and wrong case
get_window_image(image_type="occupancy")  # Missing "bev_" prefix
```

### 2. Crystal Clear Agent Instructions
Each agent now has explicit instructions on:
- Which tools to call
- Exact parameter format and values
- Processing order (get data first, then retrieve images, then analyze)
- Output schema expectations
- What NOT to include (raw image bytes)

Example instruction section:
```
CRITICAL INSTRUCTIONS FOR TOOL USAGE:
1. FIRST: Call get_scenario_data() tool to get actual window IDs
2. Do NOT make up window IDs - use ONLY what the tool returns
3. For EACH window from the tool, retrieve images using:
   - get_window_image(window_id="006", image_type="bev_occupancy")
   - NOTE: image_type MUST be exactly "bev_occupancy" (lowercase, with underscore)
4. ANALYZE each retrieved image immediately after retrieval
```

### 3. Proper JSON Extraction from Markdown Code Blocks
The script includes an `extract_json_from_text()` function that properly extracts JSON from agent responses that may contain markdown formatting:

```python
def extract_json_from_text(text: str):
    """Extract JSON from text that may contain markdown code blocks."""
    # Handles: ```json ... ``` blocks, direct JSON, and embedded JSON objects
```

### 4. Correct Event Analysis
The `analyze_events()` function properly:
- Looks for agent author by exact name match
- Iterates through `content.parts` structure
- Checks for None values (some events have None text)
- Extracts and validates JSON from agent responses

## Agent Details

### Motion Analyzer
- **Tool**: `get_scenario_data()`
- **Output**: Motion metrics for all windows (speed, roll/pitch, motion label)
- **Sample**: 2 windows analyzed, smooth motion detected

### Vision Analyzer
- **Tools**: `get_scenario_data()`, `get_window_image()`
- **Image Type**: `"camera"`
- **Output**: Lighting conditions, human detection, visibility scores
- **Sample**: 2 windows analyzed with visibility assessments

### Terrain Analyzer
- **Tools**: `get_scenario_data()`, `get_window_image()`
- **Image Types**: `"bev_occupancy"`, `"bev_height"`, `"bev_density"`, `"bev_roughness"`
- **Output**: Terrain classification, occupancy ratios, traversability scores
- **Sample**: 2 windows analyzed with terrain roughness classification

### Collision Detector
- **Tools**: `get_scenario_data()`, `get_window_image()`
- **Image Types**: `"camera"`, `"bev_occupancy"`, `"bev_height"`
- **Output**: Collision risk assessment, confidence levels, hazard types
- **Sample**: 2 windows analyzed with collision risk evaluation

## Running the Script

```bash
cd /workspaces/go2-odd-observer
python agents_fixed.py
```

### Expected Output
```
================================================================================
FIXED AGENT TEST SUITE - All agents with corrected parameter names
================================================================================
Dataset: /workspaces/go2-odd-observer/data/processed/runs/sim_run_test
Model: gemini-2.0-flash-lite

[...agent execution output...]

================================================================================
SUMMARY - Agent Performance
================================================================================
MOTION               ✅ SUCCESS
  - Total events: 3
  - Agent messages: 3
  - Output size: 379 chars
  - Windows analyzed: 2

VISION               ✅ SUCCESS
  - Total events: 5
  - Agent messages: 5
  - Output size: 715 chars
  - Windows analyzed: 2

TERRAIN              ✅ SUCCESS
  - Total events: 5
  - Agent messages: 5
  - Output size: 506 chars
  - Windows analyzed: 2

COLLISION            ✅ SUCCESS
  - Total events: 5
  - Agent messages: 5
  - Output size: 469 chars
  - Windows analyzed: 2

================================================================================
✅ ALL AGENTS PASSED!
================================================================================
```

## Key Implementation Details

### Tool Wrapper Pattern
```python
def scenario_data_wrapper() -> dict:
    return get_scenario_data(str(scenario_path))

def image_wrapper(window_id: str, image_type: str) -> dict:
    return get_window_image_raw(window_id, image_type, str(scenario_path))

scenario_data_tool = FunctionTool(func=scenario_data_wrapper)
get_image_tool = FunctionTool(func=image_wrapper)
```

### Event Structure
```
Event
  ├── author: str (e.g., "Motion_Analyzer")
  ├── content: Content object
  │   └── parts: list[Part]
  │       └── Part.text: str (may be None or contain markdown-wrapped JSON)
  └── [other fields]
```

### JSON Output Format (Standard)
```json
{
  "windows": [
    {
      "window_id": "006",
      "[agent-specific fields]": "..."
    },
    {
      "window_id": "007",
      "[agent-specific fields]": "..."
    }
  ]
}
```

## Next Steps for Notebook Integration

To apply these fixes to the main notebook (`odd_cod_workflow.ipynb`):

1. **Update agent instructions** - Replace vague instructions with explicit parameter names
2. **Fix tool parameter documentation** - Add clear comments showing valid values
3. **Update JSON extraction logic** - Use the same `extract_json_from_text()` function
4. **Verify event parsing** - Use proper `content.parts` iteration instead of tuple unpacking

## Files in This Solution

- **agents_fixed.py** - Main working script with all agents ✅
- **debug_json_extraction.py** - Debugging script for JSON extraction verification
- **check_authors.py** - Utility for checking agent author names in events

## Important Notes

1. **Image Type Values Must Be Exact**: The tool validates parameter values strictly. Use lowercase with underscores: `"bev_occupancy"` not `"BEV"` or `"occupancy"`

2. **Window IDs Must Come from Tool**: Never hardcode window IDs. Always call `get_scenario_data()` first to get the actual available windows

3. **Analyze Immediately After Retrieval**: Don't batch all retrievals then analyze. Analyze each image immediately after getting it to maintain token efficiency

4. **No Raw Image Bytes in Output**: Always ensure agent instructions explicitly state not to include raw binary data in final JSON output

5. **Test in Isolation First**: When debugging, test individual agents rather than the full parallel workflow to identify specific issues

