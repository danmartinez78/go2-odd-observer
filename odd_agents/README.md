# ODD Agents Module

A shared library for Operational Design Domain (ODD) analysis using Google's Agentic Development Kit (ADK) and Gemini models.

## Overview

The `odd_agents` module provides a complete multi-agent workflow for analyzing robot sensor data and detecting ODD violations. It serves as a **single source of truth** for tools, agents, and workflow orchestration.

## Quick Start

### Production Script
```bash
python scripts/odd_workflow.py
```

### Production Notebook
Open and run `notebooks/odd_workflow_minimal.ipynb` for an interactive workflow.

### Python API
```python
from odd_agents import run_odd_workflow

# Run analysis on a scenario
result = await run_odd_workflow(scenario_name="sim_run_test")
print(result["report"]["executive_summary"])
```

## Module Structure

```
odd_agents/
├── __init__.py          # Package exports
├── config.py            # Model assignments, paths, API setup
├── utils.py             # Shared utilities (image loading, JSON parsing)
├── workflow.py          # Workflow orchestration
├── tools/               # Tool functions
│   ├── perception.py    # Camera + LiDAR analysis
│   ├── motion.py        # IMU sensor analysis
│   └── collision.py     # Collision risk assessment
└── agents/              # Agent definitions
    ├── perception.py    # Perception agent (consolidated v4.0.0)
    ├── motion.py        # Motion agent (consolidated v4.0.0)
    ├── collision.py     # Collision agent (consolidated v4.0.0)
    ├── odd_spec.py      # ODD specification agent
    ├── cod_classifier.py # COD measurement agent
    ├── compliance.py    # ODD compliance agent
    └── report.py        # Report generation agent
```

## Usage Patterns

### 1. Run Complete Workflow
```python
from odd_agents import run_odd_workflow

result = await run_odd_workflow(
    scenario_name="sim_run_test",
    nl_odd_description="Your ODD description here..."  # Optional
)
```

### 2. Use Individual Agents
```python
from odd_agents.agents import create_perception_agent, create_motion_agent
from google.adk.agents import SequentialAgent
from google.adk.runners import InMemoryRunner
from google.genai import Client
from pathlib import Path

genai_client = Client(api_key="your-api-key")
scenario_path = Path("data/test/sim/sim_test_w010_w011")

perception_agent = create_perception_agent(
    scenario_path=scenario_path,
    genai_client=genai_client,
    model="gemini-2.0-flash-exp"
)

workflow = SequentialAgent(
    name="CustomWorkflow",
    sub_agents=[perception_agent]
)

runner = InMemoryRunner(agent=workflow, app_name="MyApp")
events = await runner.run_debug("Analyze perception")
```

### 3. Access Tools Directly
```python
from odd_agents.tools import list_windows_tool, analyze_window_perception_tool

windows = await list_windows_tool()
perception = await analyze_window_perception_tool(window_id="000", tool_context=ctx)
```

## Configuration

The module uses environment variables for API keys:
```bash
export GOOGLE_API_KEY="your-api-key"
```

Model assignments are configured in `odd_agents/config.py`:
- **Vision/Data agents:** `gemini-2.5-pro` (accuracy)
- **Synthesis agents:** `gemini-2.0-flash-lite` (cost efficiency)

## Testing

All tests use the shared module:
```bash
# Run individual tests
python tests/test_perception_agent.py
python tests/test_motion_agent.py
python tests/test_collision_agent.py
python tests/test_odd_spec_agent.py

# Or use pytest
pytest tests/
```

## Notebooks

- **`odd_workflow_minimal.ipynb`**: Production interface (9 cells, imports-only)
- **`odd_workflow_educational.ipynb`**: Full implementation for learning (29 cells)

## Development

### Adding New Tools
1. Create tool function in `odd_agents/tools/your_tool.py`
2. Import utilities from `odd_agents.config` and `odd_agents.utils`
3. Export from `odd_agents/tools/__init__.py`

### Adding New Agents
1. Create agent in `odd_agents/agents/your_agent.py`
2. Import from shared tools and config
3. Export from `odd_agents/agents/__init__.py`

### Modifying Workflow
Edit `odd_agents/workflow.py` to add/remove agents in the `SequentialAgent`.

## Migration from Legacy Code

**Before (scripts/odd_workflow_full.py):** 857 lines with everything inline

**After (scripts/odd_workflow.py):** 40 lines importing from `odd_agents`

All functionality is preserved - the shared module contains identical implementations extracted from the validated reference code.

## Benefits

✅ **Single source of truth** - Change once, propagates everywhere  
✅ **Reduced code duplication** - 74% reduction in test code  
✅ **Maintainable** - Clear module organization  
✅ **Testable** - Tests use production code  
✅ **Reusable** - Can be pip-installed as a package  

## Reference

The golden reference implementation is preserved at `scripts/odd_workflow_full.py` (read-only, backed up at `scripts/odd_workflow_full.py.backup`).

All code in `odd_agents/` was extracted verbatim from this validated reference.
