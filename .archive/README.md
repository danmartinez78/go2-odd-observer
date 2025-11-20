# Archive - Experimental Development Artifacts

This directory contains experimental files, debug scripts, and development notes from the orchestration development process. These are kept for reference but are not part of the active codebase.

## Directory Structure

### `experimental_orchestrators/`
Various orchestration patterns explored during development:

- `orchestrator_notebook_ready.py` - 3-agent unified perception model (superseded by scenario-complete)
- `orchestrator_loop.py` - Experimental LoopAgent pattern (rejected - too complex)
- `orchestrator_loop_production.py` - Production variant of LoopAgent (rejected)
- `orchestrator_complete.py` - Early complete implementation
- `orchestrator_final.py` - Another iteration
- `orchestrator_pattern.py` - Pattern exploration
- `orchestrator_working.py` - Early working version

**Why archived:** `orchestrator_scenario_complete.py` consolidates all learnings into a clean 7-agent pipeline that:
- Operates at scenario level (not per-window)
- Has proper window aggregation
- Includes ODD Spec Agent and Data Source Agent
- Generalizes to any number of windows

### `experimental_agents/`
Individual agent implementations and debug utilities:

**Agent Implementations:**
- `agents_bulletproof.py` - Hardened agent definitions
- `agents_fixed.py` - Fixed versions with corrections
- `perception_agent.py` - Early perception agent
- `sensors_generalist.py` - Multi-sensor fusion attempt
- `FIXED_AGENT_DEFINITIONS.py` - Corrections to agent logic

**Debug Scripts:**
- `check_authors.py` - Debugging agent author tracking
- `debug_events.py` - Event stream analysis
- `debug_json_extraction.py` - JSON parsing diagnostics
- `debug_terrain.py` - Terrain agent debugging
- `debug_terrain_output.py` - Terrain output analysis
- `test_agents_isolated.py` - Isolated agent testing
- `test_agents_isolated_debug.py` - Debug variant
- `test_inspect_terrain.py` - Terrain inspection

**Why archived:** Modern orchestrators use the Google ADK agent pattern directly without these intermediate implementations.

### `development_notes/`
Documentation of the development journey:

- `AGENTS_FIXED_SOLUTION.md` - How agent issues were resolved
- `AGENT_ARCHITECTURE_REFERENCE.md` - 4-agent vs 3-agent comparison
- `AGENT_FIX_GUIDE.md` - Troubleshooting guide
- `BULLETPROOF_VERIFICATION_REPORT.md` - Agent validation report
- `DEBUG_FINDINGS.md` - Key debugging discoveries
- `DETAILED_OUTPUT_ANALYSIS.md` - Output analysis
- `ORCHESTRATION_MIGRATION.md` - Migration from 4-agent to 3-agent
- `TOKEN_LIMIT_FIX.md` - Token optimization notes

**Why archived:** Historical reference. Current approach documented in main `project_plan.md` and `README.md`.

## Key Decisions Documented

### Orchestration Patterns Tested
1. ✅ **ParallelAgent + SequentialAgent** (ADOPTED) - Clean, composable, scales well
2. ❌ **LoopAgent** - Too complex for this use case, hard to debug
3. ❌ **Custom iteration patterns** - Not needed with proper agent composition

### Agent Counts
- ✅ **3-agent unified perception** (ADOPTED) - Better performance than 4-agent specialized
  - Motion, Unified Perception (camera+LiDAR), Collision
- ✅ **7-agent scenario pipeline** (CURRENT) - Adds aggregation and evaluation
  - Added: ODD Spec, Data Source, Window Evaluator, Scenario Aggregator, ODD Classifier

### Key Learnings
- Base64-encoded images in LLM context cause token overflow - removed in favor of descriptive analysis
- Per-window analysis must aggregate to scenario level for proper ODD/COD comparison
- Window-specific violation tagging enables precise error localization
- Generic agents (data-driven window lists) scale better than hardcoded window IDs

## How to Use This Archive

If you need to:
- **Understand LoopAgent experiments**: See `experimental_orchestrators/orchestrator_loop*.py`
- **Review agent development**: See `experimental_agents/agents_*.py`
- **Trace debugging process**: See `development_notes/`
- **Compare agent counts**: See `.archive/development_notes/AGENT_ARCHITECTURE_REFERENCE.md`

## Migration Path

If resurrecting old code, understand:
1. Old code uses hardcoded window IDs (006, 007)
2. New code dynamically calls `get_scenario_windows()`
3. Old code analyzes per-window
4. New code aggregates to scenario level
5. Old code lacked ODD Spec and Data Source agents
6. New architecture: 7 coordinated agents following Google ADK pattern
