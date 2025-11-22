# Archive Directory

This directory contains historical exploration, development files, and planning documents from the project's evolution.

## Organization

```
.archive/
├── development_notes/    # Debug findings, agent fixes, migration notes
├── docs/                 # Old documentation (factory pattern, IMU updates, reference patterns)
├── experimental_agents/  # Early agent implementations and debugging scripts
├── experimental_orchestrators/  # Orchestration pattern exploration
├── exploration/          # ADK pattern testing and proof-of-concepts
├── notebooks/           # Archived notebooks (educational, minimal, old workflows)
├── planning/            # Planning docs (refactor plans, TODO lists, project plans)
└── scripts/             # Old workflow scripts and backups
```

## Purpose

These files demonstrate the learning journey and architectural decisions that led to the final implementation:
- Historical reference for design evolution
- Educational examples of what worked and what didn't
- Pattern comparison and A/B testing results
- Development documentation and debugging notes

## Key Archived Items

### Planning & Documentation
- **`planning/REFACTOR_PLAN.md`** - Complete shared-agent-module refactor plan (completed)
- **`planning/REFACTOR_SUMMARY.md`** - Config.py removal refactor summary
- **`planning/TODO.md`** - Historical TODO list and feature tracking
- **`planning/project_plan.md`** - Original ODD/COD project architecture plan
- **`docs/FACTORY_PATTERN.md`** - Factory pattern implementation guide
- **`docs/IMU_MOTION_DETECTION_UPDATE.md`** - IMU-based motion detection changes
- **`docs/REFERENCE_multi_agent_pattern.md`** - Loop+summary pattern reference

### Notebooks
- **`notebooks/odd_workflow_educational.ipynb`** - Full implementation with visible code
- **`notebooks/odd_workflow_minimal.ipynb`** - Minimal interface using odd_agents module
- **`notebooks/odd_cod_workflow_ARCHIVED.ipynb`** - Earlier ODD/COD workflow version
- **`notebooks/odd_cod_misc.ipynb`** - Miscellaneous ODD/COD explorations

### Scripts
- **`scripts/odd_workflow_full.py`** - Complete 9-agent sequential pipeline (before parameterization)
- **`scripts/multi_agent_image_adk_workflow.py`** - PROVEN loop+summary pattern reference

### Exploration
- **`exploration/compare_agent_variants.py`** - A/B testing of agent architectures
- **`exploration/odd_cod/`** - Early ODD/COD distance metric implementations
- **`exploration/orchestrator_scenario_complete.py`** - Pre-loop+summary orchestration

## Key Learnings

1. **Hallucination Prevention**: Tools must call Gemini directly with `types.Part.from_bytes()` and return text/JSON, NOT Part objects
2. **Loop + Summary Pattern**: Process items individually in loop agent, aggregate in summary agent
3. **No Global State**: Parameterized factory functions prevent test isolation issues
4. **Model Selection**: Vision/aggregation needs 2.5-pro, simple synthesis can use flash-lite
5. **IMU Over Odometry**: Accelerometer/gyroscope more robust than broken odometry

## Current Production Code

The final implementation is in the project root:
- **`odd_agents/`** - Parameterized module (tools, agents, workflow)
- **`scripts/odd_workflow.py`** - Production CLI script
- **`notebooks/odd_analysis_demo.ipynb`** - Current demo notebook
- **`tests/`** - Isolated test suite

## Note

Archived files are **not maintained** and may not work with current dependencies. They are for reference only. See the main `README.md` for current usage instructions.
