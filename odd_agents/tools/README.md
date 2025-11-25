# Agent Tools

This directory contains the tool implementations used by ODD analysis agents.

## Overview

Each agent type has a corresponding tool module that provides the analysis functions:

- **`perception.py`**: Camera + LiDAR BEV multimodal analysis
- **`motion.py`**: IMU-based motion analysis with visual odometry
- **`collision.py`**: Binary collision detection from IMU thresholds
- **`common.py`**: Shared utilities for CSV index reading and file path resolution

## Common Utilities (`common.py`)

The `common.py` module provides shared functionality used across all agent tools to avoid code duplication:

### CSV Index Reading

```python
from odd_agents.tools.common import load_scenario_index

# Load the CSV index for a scenario
index_df, index_path = load_scenario_index(scenario_path)
```

### Window Listing

```python
from odd_agents.tools.common import list_available_windows

# Get list of all windows with motion data
windows = list_available_windows(scenario_path, require_motion=True)
# Returns: ['010', '011', '012', ...]
```

### File Path Resolution

```python
from odd_agents.tools.common import get_window_file_paths

# Get all file paths for a window
file_paths = get_window_file_paths(scenario_path, '010')
# Returns:
# {
#   "motion": Path("data/test/sim/motion_sim_1_0_w010.json"),
#   "camera": Path("data/test/sim/cam_sim_1_0_w010.png"),
#   "bev_occupancy": Path("data/test/sim/bev_occupancy_sim_1_0_w010.png"),
#   "bev_height": Path("data/test/sim/bev_height_sim_1_0_w010.png"),
#   "bev_roughness": Path("data/test/sim/bev_roughness_sim_1_0_w010.png")
# }
```

### Benefits

1. **Single Source of Truth**: CSV indices are the authoritative source for file paths
2. **Test Set Compatibility**: Works with both production data and test sets (which preserve original filenames)
3. **Error Handling**: Centralized validation and error messages
4. **Maintainability**: Changes to index format only require updates in one place

## Tool Factory Pattern

All tools use a factory function pattern to create configured tool instances:

```python
from odd_agents.tools.perception import create_perception_tools
from google.genai import Client

# Create tools with specific configuration
list_tool, analyze_tool = create_perception_tools(
    scenario_path=Path("data/production/sim_1_0"),
    genai_client=client,
    model="gemini-2.5-flash"
)

# Use the tools
windows = await list_tool.func()
result = await analyze_tool.func(window_id="010", tool_context=ctx)
```

## Data Flow

1. **Index Loading**: Tools read `index_{scenario_name}.csv` to find available windows
2. **Path Resolution**: File paths are read from CSV columns (not constructed from directory names)
3. **Data Access**: Actual sensor data files are loaded using resolved paths
4. **Analysis**: AI models or algorithms process the data
5. **Results**: Structured JSON output with standardized schemas

## File Path Handling

**IMPORTANT**: All file paths are read from CSV indices, NOT constructed from scenario directory names.

This design allows:
- Test sets to preserve original production filenames for traceability
- Flexible directory structures without breaking tools
- Easy validation (CSV paths must exist)

Example CSV index structure:
```csv
window_id,start_time,end_time,motion_path,cam_image_path,bev_occupancy_path,bev_height_path,bev_roughness_path
10,0.0,3.0,motion_sim_1_0_w010.json,cam_sim_1_0_w010.png,bev_occupancy_sim_1_0_w010.png,bev_height_sim_1_0_w010.png,bev_roughness_sim_1_0_w010.png
11,3.0,6.0,motion_sim_1_0_w011.json,cam_sim_1_0_w011.png,bev_occupancy_sim_1_0_w011.png,bev_height_sim_1_0_w011.png,bev_roughness_sim_1_0_w011.png
```

## Testing

The common utilities are tested in:
- Unit tests for individual functions
- Integration tests with real test sets
- Agent runner tests with production data

Example test:
```python
from odd_agents.tools.common import list_available_windows, get_window_file_paths

windows = list_available_windows(Path("data/test/sim_test_w010_w011"))
assert windows == ['010', '011']

paths = get_window_file_paths(Path("data/test/sim_test_w010_w011"), '010')
assert paths["motion"].exists()
```
