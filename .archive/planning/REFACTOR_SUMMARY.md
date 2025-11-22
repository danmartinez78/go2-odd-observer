# Config.py Removal - Refactor Summary

## Overview
Completed full parameterization refactor to remove global state from `config.py`. All tools and agents now accept configuration parameters explicitly instead of importing from a global config module.

## Problem Statement
- **Root Cause**: `config.py` created global `SCENARIO_PATH` variable that was imported at module load time
- **Symptom**: Tests calling `set_scenario("sim_run_test")` had no effect because tools already imported `SCENARIO_PATH="sim_run_new"`
- **Impact**: Tests processed 13 windows instead of 2 windows, using wrong data

## Solution
Removed `config.py` entirely and converted all modules to use parameterized factory functions.

## Changes Made

### Files Deleted
- ✅ `odd_agents/config.py` - Removed global configuration module

### Files Modified (Core Modules)

#### Utils Module
- ✅ `odd_agents/utils.py`
  - Changed `build_image_path(prefix, window_id)` → `build_image_path(scenario_path, prefix, window_id)`
  - Now pure functions with no global dependencies

#### Tool Modules (Factory Pattern)
- ✅ `odd_agents/tools/perception.py`
  - Converted to `create_perception_tools(scenario_path, genai_client, model)` factory
  - Returns tuple of (list_windows_tool, analyze_window_perception_tool)

- ✅ `odd_agents/tools/motion.py`
  - Converted to `create_motion_tools(scenario_path, genai_client, model)` factory
  - Returns analyze_motion_tool

- ✅ `odd_agents/tools/collision.py`
  - Converted to `create_collision_tools(scenario_path, genai_client, model)` factory
  - Returns analyze_collision_risk_tool

- ✅ `odd_agents/tools/__init__.py`
  - Updated exports to only export factory functions

#### Agent Modules (Parameterized Factories)
- ✅ `odd_agents/agents/perception.py`
  - `create_perception_loop_agent(scenario_path, genai_client, model, api_key)` 
  - `create_perception_summary_agent(api_key, model)`

- ✅ `odd_agents/agents/motion.py`
  - `create_motion_loop_agent(scenario_path, genai_client, model, api_key)`
  - `create_motion_summary_agent(api_key, model)`

- ✅ `odd_agents/agents/collision.py`
  - `create_collision_loop_agent(scenario_path, genai_client, model, api_key)`
  - `create_collision_summary_agent(api_key, model)`

- ✅ `odd_agents/agents/odd_spec.py`
  - `create_odd_spec_agent(api_key, model)`

- ✅ `odd_agents/agents/cod_classifier.py`
  - `create_cod_classifier_agent(api_key, model)`

- ✅ `odd_agents/agents/compliance.py`
  - `create_odd_compliance_agent(api_key, model)`

- ✅ `odd_agents/agents/report.py`
  - `create_report_agent(api_key, model)`

- ✅ `odd_agents/agents/__init__.py`
  - Cleaned up duplicate __all__ entries

#### Workflow Module
- ✅ `odd_agents/workflow.py`
  - `create_odd_workflow(scenario_path, genai_client, api_key, model_*)` - Now parameterized
  - `run_odd_workflow(scenario_path, genai_client, api_key, nl_odd_description, model_*)` - Takes explicit paths
  - Removed dependency on `config.set_scenario()`

- ✅ `odd_agents/__init__.py`
  - Removed all config exports
  - Updated docstrings with new usage examples

### Files Modified (Tests & Scripts)

#### Test Files
- ✅ `tests/test_perception_agent.py`
  - Now creates `Client`, sets `API_KEY`, `SCENARIO_PATH` explicitly
  - Graceful error handling for missing API key

- ✅ `tests/test_motion_agent.py`
  - Parameterized agent creation with explicit config

- ✅ `tests/test_collision_agent.py`
  - Parameterized agent creation with explicit config

- ✅ `tests/test_odd_spec_agent.py`
  - Parameterized agent creation with explicit config

#### Production Script
- ✅ `scripts/odd_workflow.py`
  - Creates `Client`, passes `scenario_path` explicitly
  - No dependency on global config

## New Usage Pattern

### Before (Global Config)
```python
from odd_agents import set_scenario, create_odd_workflow

set_scenario("sim_run_test")  # Sets global state
workflow = create_odd_workflow()  # Uses global config
```

### After (Parameterized)
```python
from google.genai import Client
from odd_agents import run_odd_workflow

client = Client(api_key="your-key")
result = await run_odd_workflow(
    scenario_path="data/processed/runs/sim_run_test",
    genai_client=client,
    api_key="your-key"
)
```

## Benefits
1. ✅ **No Global State**: Each workflow invocation is independent
2. ✅ **Test Isolation**: Tests can run in parallel with different scenarios
3. ✅ **Explicit Dependencies**: All configuration passed as parameters
4. ✅ **Flexible**: Easy to run multiple analyses with different configs
5. ✅ **Debuggable**: Clear data flow, no hidden state

## Verification
- ✅ All Python files compile without syntax errors
- ✅ `import odd_agents` succeeds
- ✅ No compilation errors in Pylance/VS Code
- ⏳ Tests ready to run (need API key)

## Next Steps
1. Set `GOOGLE_API_KEY` environment variable
2. Run tests to verify functionality: `python tests/test_perception_agent.py`
3. Update notebook `notebooks/odd_analysis_demo.ipynb` to use new API
4. Test full workflow: `python scripts/odd_workflow.py`

## Files Affected Summary
- **Deleted**: 1 file (config.py)
- **Modified**: 21 files
  - 3 tool modules
  - 7 agent modules
  - 2 __init__ files
  - 1 workflow module
  - 1 utils module
  - 4 test files
  - 1 production script
  - 2 package __init__ files
