# Archive Directory

This directory contains historical exploration and development files that were used during the project's evolution but are not part of the final workflow.

## Purpose

These files demonstrate the learning journey and architectural decisions that led to the final implementation. They are preserved for:
- Historical reference
- Understanding design evolution
- Educational purposes
- Pattern comparison

## Contents

### `/exploration/` - ADK Pattern Testing

Files used to explore different ADK agent architectures and discover the optimal patterns:

- **`compare_agent_variants.py`** - A/B testing of specialized vs unified agent architectures
- **`simple_agent_example.py`** - Basic ADK agent setup and file access testing
- **`single_agent_image_adk_workflow.py`** - Direct image→Gemini approach (pre-tool pattern)
- **`orchestrator_scenario_complete.py`** - Earlier orchestration attempt (pre-loop+summary)

### Reference Implementation

- **`scripts/multi_agent_image_adk_workflow.py`** - The PROVEN loop+summary pattern that became our foundation
  - This file demonstrated the hallucination-free approach
  - Tools call Gemini directly and return text/JSON (not Part objects)
  - Loop agent processes items individually, summary agent aggregates
  - **This pattern was successfully applied to create `odd_workflow_full.py`**

## Key Learnings

1. **Hallucination Prevention**: Tools must call Gemini directly with `types.Part.from_bytes()` and return text/JSON, NOT Part objects
2. **Loop + Summary Pattern**: Process items individually in loop agent, aggregate in summary agent
3. **Model Selection**: Vision/aggregation needs 2.5-pro, simple synthesis can use flash-lite
4. **Data Preservation**: Complex data structures require 2.5-pro to maintain arrays during aggregation

## Final Production Code

The exploration led to these production files (in project root):
- `odd_workflow_full.py` - 9-agent sequential pipeline
- `agent_tests/` - Individual agent implementations
- `notebooks/odd_workflow_interactive.ipynb` - Interactive analysis

## Note

These archived files are **not maintained** and may not work with current dependencies. They are for reference only. See the main README.md for current usage instructions.
