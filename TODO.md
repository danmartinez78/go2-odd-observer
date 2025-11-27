# ODD Observer Development Roadmap

See [`docs/ARCHITECTURE_REDESIGN.md`](docs/ARCHITECTURE_REDESIGN.md) for detailed design and rationale.

---

**Last Updated**: November 27, 2025  
**Project**: Go2 ODD Observer - Kaggle ADK Agent Capstone  
**Status**: Phase 1.4.5 Complete, HTML reports v2.0 deployed to GitHub Pages

**Current Focus**: Bug investigation (window failures), then production testing

## 🧠 Memory & Knowledge System

**Status:** 📋 DESIGNED - See [docs/MEMORY_KNOWLEDGE_DESIGN.md](docs/MEMORY_KNOWLEDGE_DESIGN.md)

**Target Phase:** 2.2 (after production validation + real data testing)

**What It Provides:**
- **Cross-run knowledge**: Aggregate ODD profiles, typical COD distances, common failure axes
- **Few-shot examples**: Reference past runs for better reasoning
- **Terminology grounding**: Consistent definitions via reference docs

**Three-Layer Architecture:**
| Layer | Purpose | Example |
|-------|---------|---------|
| Artifacts | Per-run outputs | ODD spec, COD distance, report |
| Memory | Cross-run knowledge | ODD profiles, case summaries |
| Reference Docs | Static fundamentals | ODD/COD definitions, policies |

**Quick Win (Phase 1.x):**
- [ ] Create `ODD_COD_FUNDAMENTALS.md` reference doc
- [ ] Inject into OddSpec + Evaluator prompts (solves terminology issue)

**Full Implementation (Phase 2.2):**
- [ ] Memory schema: `ref:*`, `global:odd_profile:*`, `case:run:*`
- [ ] Consolidator tool/agent (updates memory after each run)
- [ ] Evaluator/Report read memory for cross-scenario context
- [ ] "This run's COD distance is higher than typical for this ODD"

---

## 🔥 HIGH PRIORITY: Reference Doc for Agent Grounding

**Goal:** Create `ODD_COD_FUNDAMENTALS.md` reference doc for consistent agent grounding

**This is the "quick win" from Memory & Knowledge design** - solves terminology issues without full memory system.

**Motivation:**
- Terminology confusion (COD = "Current Operating Domain", not "Conditions of Operation Domain")
- Large prompts with repeated domain knowledge
- Inconsistent understanding across agents

**Content to Include:**
- ODD/COD definitions and relationships
- Verdict criteria (IN_ODD, BOUNDARY, OUT_ODD)  
- Sensor interpretation guidance (LiDAR BEV, IMU data)
- Go2 robot specifications and capabilities

**Implementation:**
1. Create `docs/guides/ODD_COD_FUNDAMENTALS.md`
2. Add reference to OddSpec + Evaluator prompts
3. Test terminology consistency in outputs

**Status:** 📋 PLANNED - Quick win before full Memory system

---

## ✅ HTML Reports v2.0 + GitHub Pages Update

**Completed:** November 27, 2025

**Branch:** `feature/html-reports-update` (12 commits) → merged to `dev` → merged to `main`

**Deliverables:**
- [x] **HTML Generator v2.0** (`scripts/generate_html_report.py`)
  - Inline SVG charts (spider radar for ODD compliance, donut for cost breakdown)
  - Even window sampling (max 6 evenly distributed windows displayed)
  - Phase 1.4.5 schema support (agent_outputs structure)
  - Data source detection from `agent_outputs.PerceptionAgent.data_source`
  - Conditional data source footer (only shown if source identified)
  
- [x] **Production Reports Generated**
  - `docs/reports/sim_1_0_chunk_000_009_report.html` (10 windows)
  - `docs/reports/sim_1_0_chunk_020_029_report.html` (10 windows)
  - `docs/reports/sim_1_0_chunk_040_049_report.html` (10 windows)
  
- [x] **index.html Updates**
  - ODD/COD explanation section (What is ODD? What is COD?)
  - Fixed pipeline flow diagram (replaced ASCII art with styled boxes)
  - Removed test scenario report from visible links
  - Added 3 production IN_ODD report cards
  - Added agent reasoning showcase section
  - Consistent badge styling (version/phase badges same size)

- [x] **Terminology Fixes**
  - COD = "Current Operating Domain" (not "Conditions of Operation Domain")
  - BOUNDARY = "at or near edge of ODD limits" (not "minor violations")
  - Added explicit TERMINOLOGY section to evaluator.py prompt
  - Fixed compliance.py ODD_BOUNDARY description

**Known Issues Documented:**
- Token accounting bug: Tool API calls bypass ADK tracking (actual cost 2-3x higher)
- Getting Started page needs update for Phase 1.4.5

---

## 🐛 KNOWN ISSUES

### Token Accounting Bug - Tool API Calls Not Tracked

**Problem:** Perception, Motion, and Collision tools make **direct genai.Client API calls** for multimodal analysis, but these calls are NOT tracked in ADK event metadata.

**Impact:**
- Reported: PerceptionAgent ~2,664 tokens ($0.003)
- Actual estimate: ~45,000 tokens per 10 windows (images + prompts)
- **Total pipeline cost is significantly underreported**

**Root Cause:**
- `genai_client.models.generate_content()` calls in tools bypass ADK Runner
- ADK only tracks agent-level invocations, not tool-internal API calls
- Image token costs (camera + BEV) not captured

**Fix Options:**
1. Track tool API calls manually (add usage_metadata extraction in tools)
2. Return token usage from tools and aggregate in workflow
3. Estimate based on image sizes + prompt lengths

**Status:** 📋 NEEDS FIX - Affects cost reporting accuracy

---

### Sporadic Window Analysis Failures - Tool Agent Errors

**Problem:** Random windows fail to process in tool agents (Perception, Motion, Collision), causing data gaps in analysis.

**Observed Symptoms:**
- `"Motion data for window '044' was missing due to a processing error."`
- `"Data processing failed for two windows (Perception '021', Motion '024') due to server errors"`
- `"Collision analysis data was not available, leading to an incomplete safety assessment."`
- Not all windows, not all agents - sporadic/random pattern

**Impact:**
- Incomplete per-window analysis (gaps in data)
- Report agent correctly identifies and documents gaps
- Pipeline continues but with reduced observability

**Possible Causes (not yet confirmed):**
1. **API Rate Limiting** - 30+ API calls in quick succession (10 windows × 3 agents)
2. **Transient Server Errors** - 500/503 from Gemini API
3. **Image Loading Issues** - BEV/camera file read failures
4. **Timeout Issues** - Long-running multimodal analysis times out
5. **Memory Issues** - Large image payloads causing OOM

**RCA Needed:**
- [ ] Add detailed error logging to tool agents (perception.py, motion.py, collision.py)
- [ ] Log: which window, which file, what exception type, API response status
- [ ] Capture stack traces on failure
- [ ] Run 5-10 production scenarios and analyze error patterns

**Status:** 🐛 BUG - Needs investigation before fix

---

## 📚 GitHub Pages & Documentation

### Add More GitHub Pages Content

**Status:** 📋 TODO

- [ ] **Update Getting Started Guide** - Phase 1.4.5 changes, new API examples
- [ ] **Agent Deep Dive pages** - Individual pages for each agent:
  - OddSpecAgent: Input/output schemas, prompt design
  - PerceptionAgent: Multimodal analysis, BEV interpretation
  - MotionAgent: IMU analysis, motion state classification
  - CollisionAgent: Safety detection logic
  - EvaluatorAgent: COD construction, compliance reasoning
  - ReportAgent: Output schema, executive summary generation
- [ ] **Architecture Overview** - Visual diagram of pipeline flow
- [ ] **Data Formats** - Window structure, JSON schemas
- [ ] **Cost & Performance** - Benchmarks, optimization tips

---

**Recent Completions (Nov 27, 2025)**:
- ✅ Phase 1.4.5: Artifact Handoff, Categorical Reasoning, Data Source Detection
  - **Artifact-based data handoff**: Sensor agents save to artifacts, Evaluator loads reliably
  - **Categorical micro-agent**: LLM-based semantic mismatch (understands "indoor_commercial" ≈ "office")
  - **Data source detection**: Automatically identifies simulated vs real data
  - **Report v9.1.0**: Hybrid schema with compliance, executive_summary, key_findings, scenario_metadata
  - **Model standardization**: All agents on gemini-2.5-flash for reliability
  - **Pricing module**: Accurate per-model cost calculation
  - **Production validated**: 2-window ($0.0155, 148s) and 10-window ($0.0372, 510s) tests passing

**Agent Versions (v1.4.5)**:
| Agent | Version | Model |
|-------|---------|-------|
| OddSpecAgent | 6.1.0 | gemini-2.5-flash |
| PerceptionAgent | 7.4.0 | gemini-2.5-flash |
| MotionAgent | 7.3.0 | gemini-2.5-flash |
| CollisionAgent | 7.3.0 | gemini-2.5-flash |
| EvaluatorAgent | 5.0.0 | gemini-2.5-pro |
| ReportAgent | 9.1.0 | gemini-2.5-flash |
| CODTool | 1.1.0 | gemini-2.5-flash (categorical micro-agent) |

**Tool Versions (v1.4.5)**:
| Tool | Version | Description |
|------|---------|-------------|
| PerceptionTool | 5.1.0 | Multimodal analysis + data source detection |
| MotionTool | 5.0.0 | IMU analysis + motion state |
| CollisionTool | 5.0.0 | Multimodal collision detection |
| CODTool | 1.1.0 | Categorical micro-agent for semantic matching |

**Suggested Next Phases**:
| Phase | Focus | Description | Priority |
|-------|-------|-------------|----------|
| 1.6 | Test updates | Update unit tests for new API (loop→consolidated agents) | MEDIUM |
| 1.7 | Full production run | Run on all sim_1_0 chunks (100 windows) | HIGH |
| 2.0 | Performance optimization | Visual/LiDAR odometry, tool splitting | LOW |
| 2.1 | Real data validation | Test on real robot data (not sim) | HIGH |

---

## ✅ Architecture Redesign Complete

**Original problems (all resolved in Phase 1.x):**
- ~~Averaging destroys violations~~ → COD-as-region approach preserves all observations
- ~~Collision agent false positives~~ → Binary collision detection (yes/no)
- ~~COD represents fictional point~~ → Per-window measurements + statistics

**Current architecture (v1.4.4):**
- Type-driven COD construction (Python computes, LLM interprets)
- Synthesis-focused reports (LLM for narrative, Python for data)
- Per-window compliance tracking (no violations lost)
- 6-agent pipeline: OddSpec → Perception → Motion → Collision → Evaluator → Report

See [`docs/ARCHITECTURE_REDESIGN.md`](docs/ARCHITECTURE_REDESIGN.md) for complete technical details.

---

## Phase 0: Data Source Discovery ✅ COMPLETED

**Goal:** Identify all available sensor data in bagfiles, find integration opportunities

**Status:** Complete - Critical findings documented

- [x] Create bagfile topic audit script ✅
  - `data/development/bagfile_audit/dump_topic_samples.py` - Extract message samples
  - `data/development/bagfile_audit/sample_throughout_bag.py` - Check values across entire bag
- [x] Run audit on 2-3 representative scenarios ✅
  - Real: `collection_20251122_173442` (60s, 1117 messages)
  - Sim: `sim_run_new_01` (60s, full topic coverage)
- [x] Document findings ✅
  - `data/development/bagfile_audit/PHASE0_FINDINGS.md` (225 lines)
  - `data/development/bagfile_audit/bagfile_audit_results.json` (structured metadata)
  - Sample data: `real_01_samples/` (7 topics × 3 samples), `sim_01_samples/` (11 topics × 3 samples)
- [x] Identify integration opportunities ✅
  - **CRITICAL DISCOVERY**: No velocity data available (must compute from sensors)
  - `/odom`: Position populated, velocity = [0,0,0] always
  - `/go2_states`: Only in sim, not on real robot
  - IMU: Primary reliable sensor (19 Hz real, 12 Hz sim)
  - Joint states: 0.92 Hz on real (too slow), no velocities
- [x] Update sensor documentation ✅
  - Findings documented in `PHASE0_FINDINGS.md`
  - Phase 2 plan updated with visual/LiDAR odometry requirement

**Key Findings:**
- **No velocity data from robot** - Must compute visual/LiDAR odometry (Phase 2)
- Real vs sim IMU differences (custom msg type vs standard)
- Joint states too slow for motion analysis
- Camera + LiDAR must be primary motion sources

See [Phase 0 details in ARCHITECTURE_REDESIGN.md](docs/ARCHITECTURE_REDESIGN.md#phase-0-data-source-discovery-quick-investigation)

---

## Phase 1: Architecture Refactor � IN PROGRESS (1.4.4 complete)

**Goal:** Get the new architecture working, validate with manual testing

**Status:** v1.4.4 tagged, production validation next

### 1.1 BEV Data Enhancement ✅ COMPLETED (Nov 25, 2025)
- [x] Implement `auto_crop_bev()` function ✅
  - Location: `odd_agents/utils.py`
  - Removes 50-75% empty borders
  - Maintains square aspect ratio
  - Handles edge cases (empty, full, single-pixel)
- [x] Create comprehensive test suite ✅
  - 12 tests in `tests/test_bev_cropping.py`
  - All tests passing
  - Coverage: size reduction, content preservation, edge cases
- [x] Integrate auto-crop into BEV rendering pipeline ✅
  - `scripts/extract_windows.py` updated
  - 90° rotation + horizontal flip + auto-crop
  - 65-72% size reduction on sim data
- [x] Remove density BEV channel ✅
  - **Decision**: Density redundant with occupancy/height/roughness
  - **Final channels**: Occupancy, Height, Roughness (3 total)
  - Sim data: Density was just proximity to sensor (not useful)
  - Real data blocked: Needs per-scan LiDAR (accumulated maps cause aliasing)
- [x] Update all 3 BEV channels in tools ✅
  - Perception tool: occupancy, height, roughness
  - Collision tool: occupancy, height, roughness
  - Prompts updated to explain each channel
- [x] Generate production data ✅
  - 62 sim windows in `data/production/sim_1_0/`
  - 6 test windows in `data/test/sim/`
  - Data versioning: `{source}_{id}_v{version}` schema
- [x] Update documentation ✅
  - `docs/BEV_TRANSFORMATION_STATUS.md` - detailed status
  - `docs/BEV_ENHANCEMENT_SUMMARY.md` - merge summary
  - `data/DATA_VERSIONS.md` - versioning schema
  - `data/README.md` - reorganized structure
- [x] Data directory reorganization ✅
  - `data/production/` - batch processed data
  - `data/test/` - all test samples (unified location)
  - `data/archive/` - old analysis results
  - Removed: `data/processed/`, `data/processed/test_data/`
- [x] Merge to dev ✅
  - Branch: `feature/phase1.1-bev-enhancement`
  - Merged: Nov 25, 2025
  - 23 files changed, 932 insertions(+), 391 deletions(-)

**Outcome**: 3-channel BEV pipeline ready for Phase 1.2

### 1.2 Collision Agent Rework ✅ COMPLETED (Nov 25, 2025)
- [x] Remove collision risk scoring logic entirely ✅
  - Old: 0-1 risk scores based on multimodal fusion
  - New: Binary collision detection (yes/no)
- [x] Implement binary collision detection ✅
  - IMU spike detection (threshold: >10 m/s² acceleration)
  - Angular velocity anomalies (threshold: >5 rad/s)
  - Jerk spikes (threshold: >50 m/s³)
- [x] Update output schema ✅
  - New: `collision_detected` boolean + `evidence` array
  - New: `collisions_detected` list (scenario-level)
  - Removed: `collision_risk` scores, risk levels
  - Kept: Window-level summary for reporting
- [x] Update agent files ✅
  - `odd_agents/agents/collision.py` - binary detection prompts
  - `odd_agents/tools/collision.py` - threshold-based tool
  - Test: `tests/test_collision_agent.py` - updated expectations
  - Created: `tests/test_collision_detection_logic.py` - unit tests (4/4 passing)
- [x] Manual test on sim data ✅
  - Test data: `data/test/sim_test_w010_w011` (2 windows)
  - Command: `python scripts/run_odd_analysis.py`
  - Result: No false positives, correct binary detection

**Outcome**: Binary collision detection working correctly. No false positives on normal motion (accel 0.11-0.14 m/s², gyro 0.94-0.99 rad/s, both well below thresholds).

**Data Usage Verified**: All agents using correct data sources
- ✅ Perception: 1 Camera + 3 BEV channels (occupancy, height, roughness)
- ✅ Motion: IMU + Camera (both used, camera prioritized)
- ✅ Collision: IMU metrics only (from motion output)
- ✅ Previous BEV bug FIXED (all 3 channels now loaded)

### 1.3 COD Agent Redesign ✅ COMPLETED (Nov 25, 2025)

**Architecture Changes:**
- [x] Remove `collision_risk` from ODD spec parsing ✅
  - Collision is operational outcome, not environmental constraint
  - Removed from numeric_constraints and NL prompt
- [x] Simplify ODD spec to max/min limits only ✅
  - Removed 3-zone structure (in_odd/boundary/out_odd)
  - New schema: {"max": 10.0, "min": 0.0} for numeric constraints
- [x] Add semantic context to ODD spec ✅
  - Added `description` field (what the metric means)
  - Added `measurement_guidance` field (how agents should measure it)
  - Creates shared vocabulary for Perception, Motion, COD, Evaluator
- [x] Decouple COD agent from compliance checking ✅
  - Renamed to CodMeasurementAgent
  - Pure measurement extraction (no compliance logic)
  - Output: per_window_measurements + cod_region + statistics
- [x] Update Compliance agent ✅
  - Removed collision_risk from numeric_compliance checks
  - Will become Evaluator in Phase 1.4 (region comparison + distance)

**Validation:**
- [x] Manual test run on sim_test_w010_w011 (2 windows) ✅
- [x] All agents executed successfully (9/9) ✅
- [x] ODD spec semantic context working ✅
- [x] No schema mismatches ✅

**Outcome**: COD agent successfully decoupled. Compliance checking working with new architecture.

### 1.4 Agent Versioning & Telemetry ✅ COMPLETED (Nov 25, 2025)

**Goal**: Track agent versions, prompts, models, and token usage for reproducibility and A/B testing

**Implementation:**
- [x] Create prompt extraction system ✅
  - `odd_agents/agent_prompts.py` - Extracts prompts from agent factory functions
  - Dynamic extraction via dummy agent instantiation
  - Lazy caching to avoid repeated instantiation
  - 10 prompt extraction functions (one per agent)
- [x] Create metadata tracking utilities ✅
  - `odd_agents/metadata.py` - SHA-256 hash, registry building, event parsing
  - `hash_text()` for prompts/ODD specs (16-char hex)
  - `build_agent_registry()` maps agents to versions/models/hashes
  - `extract_pipeline_metadata()` parses ADK event stream
- [x] Create prompt catalog system ✅
  - `odd_agents/prompt_catalog.py` - Hash-to-description lookup
  - Generated catalog: `odd_agents/prompt_catalog.json` (24KB, 91 lines)
  - `build_prompt_catalog()` creates catalog from current prompts
  - `reconstruct_workflow_config()` rebuilds full config from metadata
- [x] Integrate into workflow ✅
  - `odd_agents/workflow.py` enhanced with metadata tracking
  - Builds agent registry before execution
  - Captures events via `runner.run_debug()`
  - Extracts metadata from event stream
  - Returns: report + full_analysis + analysis_metadata + pipeline_metadata
- [x] Add metadata display to reports ✅
  - `scripts/run_odd_analysis.py` displays analysis_metadata
  - Shows: pipeline version, duration, agents executed, tokens, estimated cost
  - Metadata saved in JSON outputs
  - HTML reports: footer + collapsible accordion with per-agent details
- [x] Documentation updates ✅
  - `scripts/README.md` - metadata field reference with examples
  - `docs/ARCHITECTURE_REDESIGN.md` - Phase 1.4 completion details

**Architecture Decision:**
- **Event-based extraction** (Approach F) - simpler than documented callback approach
- ADK `runner.run_debug()` returns `List[Event]` with comprehensive metadata
- Event attributes: author, timestamp, invocation_id, model_version, usage_metadata
- No ADK callback API exists (`google.adk.callbacks` module not found)

**Test Results (sim_test_w010_w011):**
- ✅ Duration: 214.86 seconds (~3.6 minutes)
- ✅ Total tokens: 62,860 tokens
- ✅ Estimated cost: $1.26 USD
- ✅ Agents executed: 9/9 successfully
- ✅ Prompt hashes: All 9 unique (c562d20a787ea343, efea7cba0ac6164b, etc.)
- ✅ Models verified: Declared vs actual match
- ✅ Metadata captured and saved to JSON

**Outcome**: Complete pipeline metadata tracking ready for A/B testing and reproducibility.

### 1.4.1 ODD-Schema Driven Architecture ✅ COMPLETED (Nov 26, 2025)

**Problem Identified**: Hardcoded agent measurement schemas prevent generalization

**Root Cause:**
- ODD Spec agent produces dynamic dimension schemas from natural language
- Perception/Motion/COD agents had hardcoded measurement expectations
- Example: COD agent expected `max_acceleration`, `lighting_class`, etc.
- If ODD spec changes (add `max_speed`, remove `terrain_roughness`), agents break

**Solution Implemented:**

1. **ODD Spec v3.0.0** - Environment/Actors/Ego Structure:
   - [x] Added `environment`, `actors`, `ego` sections to ODD spec output
   - [x] Each dimension includes `description` and `measurement_guidance` metadata
   - [x] Flexible structure: agents can add sections (temporal, operational) as needed
   - [x] Example-driven prompts prevent over-constraining

2. **Perception/Motion v3.0.0** - Dual-Output Structure:
   - [x] Read ODD spec for dimension guidance (not strict requirements)
   - [x] Extract `odd_measurements`: ODD-aligned dimensions where measurable
   - [x] Extract `observations`: Safety/reliability/effectiveness context
   - [x] Graceful degradation: note unmeasurable dimensions in observations

3. **COD v3.0.0** - Fully Dynamic Schema:
   - [x] Read ODD spec structure (environment/actors/ego + dimensions)
   - [x] Build per_window_measurements matching ODD schema
   - [x] Construct cod_region with same structure
   - [x] Handle missing dimensions gracefully (list in dimensions_missing)
   - [x] Pass through all observations to Evaluator

**Design Philosophy:**
- **ODD spec = guidance, not contract**: Agents extract what they can observe
- **Formal/Flexible/Hybrid spectrum**: ODD/COD formal, Perception/Motion flexible, Evaluator hybrid
- **No forced fit**: Agents can measure beyond ODD or note unmeasurable dimensions

**Testing Results:**

**Test 1 - Ground Robot (Baseline):**
- Scenario: sim_test_w010_w011 (2 windows)
- ✅ Pipeline completed successfully
- ✅ COD region structure: environment/actors/ego
- ✅ Dimensions measured: environment_type, lighting_conditions, terrain_type, obstacle_density, traversability_score, max_accel_mps2
- ✅ Dimensions missing: max_incline_deg, max_step_height_m, etc. (gracefully handled)
- ✅ ODD compliance: Detected OUT_ODD violation (traversability_score: 0.0 < 0.3 minimum)
- ✅ Tokens: 88,485 (+41% vs v2.0.0 baseline, expected due to ODD spec context)

**Test 2 - Drone ODD (Generalization):**
- Input: DJI Matrice 300 RTK inspection drone ODD (completely different domain)
- ✅ ODD Spec v3.0.0 automatically generated drone-specific dimensions:
  - Environment: weather_conditions, wind_speed_ms, temperature_celsius, visibility_km
  - Actors: min_human_distance_m, min_airport_distance_m, no_fly_zones
  - Ego: max_altitude_agl_m, min_altitude_agl_m, max_horizontal_speed_mps, max_vertical_speed_mps, battery_pct
- ✅ No ground-robot assumptions leaked through
- ✅ Measurement_guidance adapted to drone sensors (GPS, barometric altimeter, etc.)

**Architectural Benefits Achieved:**
- ✅ **Generalization**: Same agents work for ground robots, drones, underwater vehicles
- ✅ **Flexibility**: Change ODD spec without modifying agent code
- ✅ **Correctness**: COD measurements always align with ODD dimensions
- ✅ **Robustness**: Graceful handling of unmeasurable dimensions
- ✅ **Intelligence**: Agents can observe beyond ODD scope (observations field)

**Version Tracking:**
- ODD Spec: 2.0.0 → 3.0.0 (breaking: environment/actors/ego structure + metadata)
- Perception Loop: 2.0.0 → 3.0.0 (breaking: odd_measurements + observations)
- Perception Summary: 2.0.0 → 3.0.0 (breaking: odd_measurements + observations)
- Motion Loop: 3.0.0 (breaking: odd_measurements + observations)
- Motion Summary: 3.0.0 (breaking: odd_measurements + observations)
- COD Classifier: 2.0.0 → 3.0.0 (breaking: dynamic schema from ODD spec)

**Token Impact:**
- Per-analysis increase: +41% (62,860 → 88,485 tokens)
- Reason: ODD spec context included in Perception/Motion/COD prompts
- Tradeoff: Acceptable for generalization capability gained

**Outcome**: System is now truly domain-agnostic. Same codebase works for any robot type or operating domain.

**Deliverables Completed:**
- [x] Update ODD Spec agent v3.0.0 with environment/actors/ego structure
- [x] Update Perception agent v3.0.0 to read ODD spec dimensions
- [x] Update Motion agent v3.0.0 to read ODD spec dimensions
- [x] Update COD v3.0.0 to build dynamic schema from ODD spec
- [x] Test with ground robot ODD (baseline validation)
- [x] Test with drone ODD (generalization validation)
- [x] Measure token impact (+41%)
- [x] Update documentation (TODO.md, ARCHITECTURE_REDESIGN.md)
- [x] Merge to dev branch

### 1.4.2 Three-Tier Intelligence Architecture ✅ COMPLETED (Nov 26, 2025)

**Problem Identified**: Tool agents (not loop agents) are the real workers but missed in Phase 1.4.1

**Discovery:**
- Phase 1.4.1 made summary agents ODD-schema driven ✅
- BUT: Tool agents (the actual multimodal workers) still had hardcoded schemas ❌
- Loop agents were just "dumb iterators" - calling tools N times without adding intelligence ❌

**Architecture Insight - Three-Tier Intelligence:**

1. **Tool Agents** (per-window deep analysis):
   - Perception tool: Camera + 3 BEV channels → multimodal reasoning
   - Motion tool: IMU data + camera → motion state detection
   - Collision tool: Multimodal → binary collision detection
   - These agents do the REAL work (grounded observations)

2. **Loop Agents** (cross-window pattern recognition):
   - Currently: Dumb iterators (call tool N times, collect responses)
   - Should: Temporal reasoning (transitions, trends, anomalies)
   - Should: Intelligently filter ODD spec to pass only relevant portions to tools

3. **Summary Agents** (aggregation + ODD mapping):
   - Already working well from Phase 1.4.1
   - Read tool outputs + ODD spec → map to ODD dimensions
   - Build structured odd_measurements + pass observations to Evaluator

**Solution Implemented:**

**1. Tool Agent Changes (v3.0.0):**
- [x] Added versioning constants:
  - `PERCEPTION_TOOL_AGENT_VERSION = "3.0.0"`
  - `MOTION_TOOL_AGENT_VERSION = "3.0.0"`
  - `COLLISION_TOOL_AGENT_VERSION = "3.0.0"`
- [x] Updated tool signatures to accept `odd_context: dict` parameter
- [x] Replaced rigid schemas with flexible observation structures
- [x] Tool agents produce narrative observations, not hardcoded fields
- [x] Summary agents handle ODD mapping (separation of concerns)

**2. Loop Agent Changes:**
- [x] Intelligent ODD filtering (not hardcoded rules):
  - Loop agent reads full ODD spec
  - Uses its intelligence to determine what's relevant to its tool
  - Perception: typically environment + actors
  - Motion: typically ego dimensions
  - Collision: minimal context needed
  - Agent decides dynamically based on ODD structure
- [x] Cross-window reasoning added:
  - Environmental stability/transitions
  - Temporal patterns and trends
  - Anomaly detection across windows
  - Overall scenario assessment
- [x] Output structure: `{"per_window": [...], "cross_window_observations": [...]}`

**Design Philosophy:**
- **Intelligent filtering**: Loop agents decide ODD relevance, not hardcoded rules
- **Guidance not contract**: ODD context guides tool agents, doesn't constrain
- **Separation of concerns**: Tools observe, summaries map to ODD structure
- **Three-tier intelligence**: Tool (grounded) → Loop (temporal) → Summary (structural)

**Testing Results:**

**Test - Perception Agent (sim_test_w010_w011):**
- ✅ Loop agent intelligently filtered ODD: "I'll exclude ego-vehicle dynamics and operational policies"
- ✅ Tool agent produced flexible observations (not rigid schema)
- ✅ Cross-window reasoning working: "Environmental stability: consistent across both windows"
- ✅ Summary agent mapped observations to odd_measurements
- ✅ Pipeline completed successfully

**Architectural Benefits Achieved:**
- ✅ **Tool agent versioning**: Can now track tool agent changes in metadata
- ✅ **Flexible observations**: Tool agents produce rich narratives, not limited schemas
- ✅ **Temporal intelligence**: Loop agents add cross-window reasoning
- ✅ **Intelligent filtering**: Loop agents decide ODD relevance dynamically
- ✅ **Token efficiency**: Pass only relevant ODD portions to tools
- ✅ **Future-proof**: Works with any ODD structure without code changes

**Version Tracking:**
- Perception Tool Agent: v3.0.0 (new: versioning, odd_context, flexible output)
- Motion Tool Agent: v3.0.0 (new: versioning, odd_context, flexible output)
- Collision Tool Agent: v3.0.0 (new: versioning, odd_context, flexible output)
- Perception Loop: 3.0.0 (enhanced: intelligent ODD filtering, cross-window reasoning)
- Motion Loop: 3.0.0 (enhanced: intelligent ODD filtering, cross-window reasoning)
- Collision Loop: (enhanced: minimal ODD filtering, cross-window collision patterns)

**Implementation Summary:**
- Files modified: 6 (3 tool agents + 3 loop agents)
- Lines changed: +222 insertions, -91 deletions
- Design pattern: Intelligence-guided filtering + flexible observations + temporal reasoning

**Outcome**: Complete three-tier architecture where each tier adds distinct value - tools provide grounded observations, loops add temporal context, summaries create ODD-aligned structure.

**Testing Results:**

**Test - Full Pipeline (sim_test_w010_w011, 2 windows):**
- ✅ All 9 agents executed successfully
- ✅ Tool agents producing flexible narrative observations
- ✅ Loop agents performing intelligent ODD filtering (observed in logs)
- ✅ Summary agents mapping observations to ODD dimensions correctly
- ✅ Rich, grounded observations captured:
  - "LiDAR data is very sparse... could pose a safety risk"
  - "IMU gyroscope reported high angular velocity while robot was stationary"
  - Camera evidence correctly prioritized over IMU (intelligent reasoning)
- ⚠️ Cross-window observations not preserved in final structure (minor issue)

**Performance Metrics:**
- Duration: 358.69 seconds (~6 minutes)
- Total tokens: 104,176 (+18% vs Phase 1.4.1)
- Cost: $2.08 USD ($1.04/window)
- Token increase: Expected due to flexible observations + cross-window reasoning

**Quality Improvements:**
- ✅ Sensor anomalies detected automatically (sparse LiDAR, IMU drift)
- ✅ Multimodal reasoning working (IMU vs camera correlation)
- ✅ Safety implications identified proactively
- ✅ Much richer observations than rigid v2.0.0 schemas

**Known Issues for Future Optimization:**
- Cost: $1.04/window is high - optimization pass needed
- Missing dimensions: Some COD dimensions not measured (obstacle_density, traversability_score)
- Ego physical dimensions should be hardcoded constants, not measured
- Cross-window observations need better preservation in output structure

**Outcome**: Three-tier architecture working successfully. Tool agents provide grounded observations, loop agents add temporal context (though not fully captured), summary agents create ODD-aligned structure. Quality of observations significantly improved over rigid schemas.

**Deliverables Completed:**
- [x] Add tool agent versioning (PERCEPTION_TOOL_AGENT_VERSION, etc.)
- [x] Update tool agent signatures to accept odd_context parameter
- [x] Restructure tool agent prompts for flexible observations
- [x] Update loop agents for intelligent ODD filtering
- [x] Add cross-window reasoning to loop agents
- [x] Fix JSON output format issues (markdown markers, bracket placeholders)
- [x] Test full pipeline on sim_test_w010_w011
- [x] Validate intelligent ODD filtering working
- [x] Validate flexible observations generated
- [x] Measure performance metrics (tokens, cost, duration)
- [x] Document known issues for optimization
- [x] Commit changes to feature/phase1.4.2-three-tier-intelligence branch
- [x] Merge to dev branch
- [x] Update documentation (TODO.md)

### 1.4.3 Performance & Measurement Optimization 📋 DEFERRED

**Goal:** Reduce cost/window and improve COD dimension measurement coverage

**Status:** Deferred - Phase 1.4.4 prioritized for architectural improvements

**Note:** This phase was deferred in favor of 1.4.4 (Type-Driven COD + Synthesis Reports). Some cost optimizations were achieved in 1.4.4 through the new architecture. Consider revisiting after production validation.

**Original Issues Identified:**
1. **Cost too high**: $1.04/window ($2.08 for 2 windows)
2. **Missing COD dimensions**: obstacle_density, traversability_score, min_corridor_width_m
3. **Ego dimensions not measured**: footprint_length_m, footprint_width_m, max_height_m (should be constants)
4. **Cross-window observations**: Generated but not preserved in final output

**Partial Resolution in Phase 1.4.4:**
- Cost reduced to ~$0.50/window through model changes (flash models for sensor agents)
- Cross-window observations improved through thinking model
- COD dimensions partially addressed through type-driven construction

**Remaining Optimization Opportunities:**
- [ ] Prompt optimization (reduce verbose BEV descriptions)
- [ ] Hardcode ego physical dimensions (robot model constants)
- [ ] Hybrid tool output with quantitative_metrics dict

### 1.4.4 Type-Driven COD + Synthesis-Focused Reports ✅ COMPLETED (Nov 26, 2025)

**Goal:** Reliable data pipeline with synthesis-focused reporting architecture

**Problem Identified:**
1. **COD construction unreliable**: LLM constructing COD from observations was inconsistent
2. **Executive summary nulls**: LLM not reliably copying computed values to output
3. **Mixed responsibilities**: Agents doing both computation AND synthesis

**Architecture Decision - Separation of Concerns:**
- **Python computes**: Deterministic data (stats, measurements, data_quality)
- **LLM synthesizes**: Interpretation, recommendations, narrative summaries
- Never ask LLM to copy values - that's Python's job

**Solution Implemented:**

**1. Type-Driven COD Construction (CodClassifierTool v2.0.0):**
- [x] Python-constructed COD objects from measurement data
- [x] Explicit typing: `CodRegion`, `CodDimensionStats`, `PerWindowCOD`
- [x] Build statistics programmatically (min/max/mean/values)
- [x] LLM interprets and synthesizes from structured data
- [x] Thinking model (gemini-2.5-flash-preview) for COD reasoning

**2. Synthesis-Focused Reports (ReportAgent v6.0.0):**
- [x] LLM generates only narrative content:
  - `scenario_overview`: High-level synthesis of scenario conditions
  - `key_observations`: Top 3-5 findings across all agents
  - `recommendations`: Actionable suggestions based on analysis
  - `pipeline_quality_assessment`: 1-sentence summary of agent health
- [x] Python computes all deterministic values:
  - `compliance`: verdict, confidence_value, stability, critical_axes
  - `data_quality`: all_agents_healthy, warnings, anomalies
  - `measurement_summary`: all min/max/mean statistics
  - Scenario and analysis metadata

**3. Sensor Agent Improvements:**
- [x] Perception/Motion/Collision upgraded to thinking model
- [x] Type-driven tools for all sensor agents
- [x] Acceleration computation fixed (was using absolute, now using vector magnitude)
- [x] All agents calling tools correctly (verified via telemetry)

**Test Results (sim_test_w010_w011, 2 windows):**
- ✅ Pipeline completed: 96.67 seconds
- ✅ Total tokens: 32,576 (51% reduction from 1.4.2!)
- ✅ Cost: ~$0.65 ($0.32/window)
- ✅ No null values in data_quality or measurement_summary
- ✅ Rich narrative synthesis in executive summary
- ✅ All imports working on dev branch

**Version Tracking:**
| Agent | Version | Model | Change |
|-------|---------|-------|--------|
| OddSpecAgent | 5.0.0 | gemini-2.0-flash-exp | (unchanged) |
| PerceptionAgent | 6.0.0 | gemini-2.5-flash-preview (thinking) | Type-driven tool |
| MotionAgent | 6.0.0 | gemini-2.5-flash-preview (thinking) | Type-driven tool |
| CollisionAgent | 6.0.0 | gemini-2.5-flash-preview (thinking) | Type-driven tool |
| EvaluatorAgent | 2.0.0 | gemini-2.0-flash-exp | (unchanged) |
| ReportAgent | 6.0.0 | gemini-2.0-flash-exp | Synthesis-focused |

**Key Insight:**
> "Why have the LLM copy deterministic values at all?"
> The root issue isn't model quality - it's architectural. LLMs excel at synthesis
> and interpretation. Python excels at exact computation. Let each do what it does best.

**Deliverables Completed:**
- [x] CodClassifierTool v2.0.0 with Python-constructed COD
- [x] ReportAgent v6.0.0 with synthesis-focused prompts
- [x] report_builder.py updated for LLM+Python merge
- [x] Sensor agents (Perception/Motion/Collision) on thinking model
- [x] Type definitions for COD structures
- [x] Fix acceleration computation (vector magnitude)
- [x] Full pipeline test - all agents calling tools
- [x] Documentation: PHASE_1_4_4_SUMMARY.md, REPORT.md updated
- [x] Merged to dev branch
- [x] Tagged v1.4.4

**Outcome**: Robust data pipeline with clear separation of concerns. LLM provides high-quality synthesis, Python ensures accurate computation. No more null fields or copy failures.

### 1.4.5 Artifact Handoff, Categorical Reasoning, Data Source Detection ✅ COMPLETED (Nov 27, 2025)

**Goal:** Reliable inter-agent data flow, semantic ODD matching, and automatic data source identification

**Problems Identified:**
1. **Session state unreliable**: Agents couldn't reliably access upstream outputs via session state
2. **Categorical mismatch false positives**: LLM flagging "indoor_commercial" vs "office" as mismatch
3. **No sim/real distinction**: Pipeline couldn't tell if data was simulated or real
4. **Report tool calling unreliable**: flash-lite model not reliably calling tools

**Solutions Implemented:**

**1. Artifact-Based Data Handoff:**
- [x] InMemoryArtifactService for inter-agent communication
- [x] Sensor agents save outputs as artifacts (`perception_output.json`, etc.)
- [x] Evaluator loads artifacts reliably (no more session state issues)
- [x] Tool call tracking for debugging

**2. Categorical Micro-Agent (CODTool v1.1.0):**
- [x] LLM-based semantic mismatch assessment
- [x] Understands equivalences: "indoor_commercial" ≈ "office", "clear" ≈ "good"
- [x] Anti-cheat design: generalizes beyond training examples
- [x] Model: gemini-2.5-flash for reliability
- [x] Comprehensive test suite: `scripts/test_categorical_agent.py`

**3. Data Source Detection:**
- [x] Perception tool assesses simulated vs real from visual cues
- [x] Output: `{type: "simulated"|"real", confidence: 0.0-1.0, indicators: [...]}`
- [x] Flows through: Perception → Artifact → Report → Display
- [x] **Emergent behavior**: Downstream agents naturally incorporate data_source context without explicit prompting

**4. Report Agent v9.1.0:**
- [x] Upgraded from flash-lite to flash (reliable tool calling)
- [x] Hybrid schema: compliance, executive_summary, key_findings, scenario_metadata
- [x] Added `scenario_data_source` to scenario_metadata
- [x] Display function shows Data Source

**5. Tool-Based ODD Spec (v8.0.0):**
- [x] save_odd_spec_tool with strict parameter enforcement
- [x] Consistent downstream COD construction
- [x] Validates all required ODD dimensions

**6. Pricing Module (NEW):**
- [x] `odd_agents/pricing.py` for accurate cost calculation
- [x] Per-model pricing for all Gemini models
- [x] Used in display_summary for cost reporting

**Test Results:**

**2-Window Test (sim_test_w010_w011):**
- ✅ Verdict: IN_ODD
- ✅ Region distance: 0.0
- ✅ Data source: simulated (correctly identified)
- ✅ Cost: $0.0155
- ✅ Duration: 148 seconds

**10-Window Test (sim_1_0_chunk_000_009):**
- ✅ Verdict: BOUNDARY
- ✅ Region distance: 0.2
- ✅ Data source: simulated
- ✅ Cost: $0.0372 (sub-linear scaling: 5x windows → 2.4x cost)
- ✅ Duration: 510 seconds

**Emergent Behavior Observed:**
- Executive summary naturally incorporated "simulated" context
- Key findings referenced simulation without explicit prompting
- Demonstrates agents can reason from metadata without instruction

**Version Tracking:**
| Agent | Version | Model | Change |
|-------|---------|-------|--------|
| OddSpecAgent | 6.1.0 | gemini-2.5-flash | Tool-based spec |
| PerceptionAgent | 7.4.0 | gemini-2.5-flash | Data source detection |
| MotionAgent | 7.3.0 | gemini-2.5-flash | Artifact save |
| CollisionAgent | 7.3.0 | gemini-2.5-flash | Artifact save |
| EvaluatorAgent | 5.0.0 | gemini-2.5-pro | Artifact load |
| ReportAgent | 9.1.0 | gemini-2.5-flash | Hybrid schema + data_source |
| CODTool | 1.1.0 | gemini-2.5-flash | Categorical micro-agent |

**New Files:**
- `odd_agents/pricing.py` - Cost calculation module
- `odd_agents/tools/odd_spec.py` - ODD specification tools
- `scripts/test_categorical_agent.py` - Anti-cheat test suite
- `scripts/test_adk_artifacts.py` - Artifact pattern example
- `scripts/test_adk_blackboard.py` - Blackboard pattern example

**Known Issues:**
- Some test files need API updates (old loop/summary pattern)
- ADK evaluation tests have breaking changes (upstream ADK API)

**Deliverables Completed:**
- [x] Artifact-based data handoff (InMemoryArtifactService)
- [x] Categorical micro-agent for semantic ODD matching
- [x] Data source detection (sim vs real)
- [x] Report schema v9.1.0 with data_source
- [x] Pricing module for accurate cost tracking
- [x] Tool-based ODD spec generation
- [x] 2-window and 10-window production tests
- [x] Committed and pushed to dev branch

**Outcome**: Pipeline now has reliable inter-agent communication via artifacts, intelligent semantic matching for ODD categories, and automatic data source identification. Cost tracking is accurate. Model configuration standardized on gemini-2.5-flash for reliability.

### 1.5 Evaluator Agent Upgrade 📋 PLANNED

**Originally Deferred, Completed During Phase 1.4**

**Implementation:**
- [x] Refactored collision agent to multimodal design ✅
  - Data: IMU (motion.json) + camera.png + 3 BEV channels
  - BEV channels: occupancy, height, roughness
  - Independent loading (no upstream dependencies)
- [x] Enhanced collision detection with BEV reasoning ✅
  - LLM reasoning across all modalities (not hardcoded thresholds)
  - BEV spatial guidance: 0.05m/pixel, 400×400, robot at (200,200), 15px exclusion
  - Evidence structure: IMU metrics + camera + BEV analysis
- [x] Fixed data loading independence ✅
  - Removed motion_metrics parameter (was causing None values)
  - Direct motion.json loading in collision tool
  - Calculate metrics: peak_accel, peak_gyro, max_tilt, peak_jerk from raw data
- [x] Updated agent architecture ✅
  - Removed {temp:motion_output?} dependency
  - Simplified instruction (no motion data parsing)
  - Tool call: analyze_collision_tool(window_id=...) without motion_metrics

**Test Results (sim_test_w010_w011):**
- ✅ Window 010: 0.98 confidence no collision
- ✅ Window 011: 0.95 confidence no collision
- ✅ Multimodal evidence structured correctly
- ✅ BEV reasoning operational (obstacle awareness)
- ✅ No false positives on normal motion

**Architectural Improvement:**
- Before: Hardcoded thresholds (>10 m/s² = collision)
- After: LLM reasoning with multimodal evidence
- Result: More nuanced collision detection with visual confirmation

**Outcome**: Collision agent upgraded from IMU-only to full multimodal (IMU + camera + BEV), maintaining independence and improving reasoning quality.

### 1.6 Evaluator Agent Enhancement 📋 PLANNED

**Goal**: Enhance Evaluator with distance-from-limits calculation and severity scoring

**Tasks**:
- [ ] Implement ODD/COD distance computation for severity
  - For violations: calculate magnitude (how far beyond limit?)
  - Example: COD max_accel = 15 m/s², ODD limit = 10 m/s² → 50% overage
  - Use distance + frequency for severity scoring
- [ ] Implement severity calculation from per-window compliance
  - Input: per_window_measurements from COD + ODD spec
  - Check each window against ODD limits
  - Formula: Based on violation magnitude × frequency
  - Map to severity levels (MINIMAL/LOW/MEDIUM/HIGH/CRITICAL)
- [ ] Integrate collision detection flags
  - Check COD boolean: collision_detected
  - Flag as critical safety event (separate from ODD compliance)
- [ ] Integrate other agent flags
  - Sensor quality issues from Perception
  - Motion anomalies from Motion agents
- [ ] Generate investigation flags (specific, actionable)
- [ ] A/B test with telemetry: severity scoring v1 vs v2

### 1.7 Manual Validation Testing 📋 PLANNED

**Goal**: Validate new architecture with diverse scenarios

**Tasks**:
- [ ] Select 3-5 representative scenarios
  - Fully compliant
  - Boundary case
  - Isolated violation
  - Mixed violations
  - Frequent violations
- [ ] Verify per-window compliance matches expectations
- [ ] Verify COD region preserves all observed conditions
- [ ] Verify severity scores align with violation distribution
- [ ] Verify no violations averaged away

**Success Criteria:**
- ✅ Auto-crop function implemented and tested (50-75% size reduction)
- ✅ Agents receive all 4 BEV channels (height, density, roughness, occupancy)
- ✅ New pipeline runs end-to-end without errors
- ✅ COD regions capture all observations (no fictional averaged points)
- ✅ Severity scores differentiate scenarios appropriately
- ✅ No violations averaged away

See [Phase 1 details in ARCHITECTURE_REDESIGN.md](docs/ARCHITECTURE_REDESIGN.md#phase-1-architecture-refactor)

---

## Phase 2: Performance Optimization 🔧 PLANNED

**Goal:** Improve pipeline efficiency and add visual/LiDAR odometry

**Status:** After Phase 1 validation

### 2.1 Tool Splitting by Data Type
- [ ] Split tools by required data
  - `camera_image_tool` → Perception Image Agent only
  - `bev_occupancy_tool` → Perception BEV Agent only
  - `imu_data_tool` → Motion agents only
- [ ] Expected gain: 30-40% token reduction

### 2.2 Image Encoding Optimization
- [ ] Camera images: JPEG at quality 85-90
- [ ] BEV images: Keep PNG (sharp geometric features)
- [ ] Expected gain: 40-60% size reduction for camera images

### 2.3 Visual & LiDAR Odometry Integration (NEW!)
**Goal:** Add reliable motion estimates from high-rate sensor data

**Background:** Phase 0 findings showed no velocity data available:
- `/odom` twist = [0, 0, 0] (not populated)
- `/go2_states` not available on real robot
- Only option: Compute odometry from visual/LiDAR sensors

**Approach:**
1. Create standalone odometry functions:
   - `scripts/compute_visual_odometry.py` - Feature tracking (ORB/SIFT) between camera frames
   - `scripts/compute_lidar_odometry.py` - ICP alignment between point cloud scans
2. Validate accuracy on test scenarios (visual vs LiDAR agreement)
3. Add to window preprocessing - enrich motion JSON with odometry data
4. Update motion tool to use odometry (additive - preserves existing IMU arrays)

**Dependencies:**
- OpenCV for visual odometry (add to requirements.txt)
- Open3D for LiDAR ICP (add to requirements.txt)

**Validation Criteria:**
- Visual and LiDAR odometry agree within 10% on test scenarios
- Documented drift characteristics over time
- Confidence scoring based on feature quality / ICP convergence

**Expected Impact:**
- Motion agent can now estimate velocity (differentiate stationary vs moving)
- Cross-validation between visual/LiDAR increases confidence
- Odometry discrepancies flag potential sensor issues

### 2.4 Performance Benchmarking
- [ ] Measure before/after on 10-scenario batch
- [ ] Verify 30-50% overall token reduction (from all Phase 2 items)
- [ ] Verify same accuracy as Phase 1

See [Phase 2 details in ARCHITECTURE_REDESIGN.md](docs/ARCHITECTURE_REDESIGN.md#phase-2-performance-optimization-quick-wins)

---

## Phase 3: Evaluation Framework 📊 PLANNED

**Goal:** Create systematic measurement framework for continuous improvement

**Status:** After Phase 2 optimization

### 3.1 Ground Truth Dataset Creation
- [ ] Create 5-10 hand-labeled scenarios
  - Compliant scenarios (2-3)
  - Boundary scenarios (2-3)
  - Violation scenarios (3-4)
  - Mixed scenarios (1-2)
- [ ] Label per-window: IN_ODD / BOUNDARY / OUT_ODD
- [ ] Label axis-specific violations
- [ ] Label expected severity levels

### 3.2 Evaluator Setup
- [ ] Configure Gemini 3 Pro as evaluator model
- [ ] Create evaluation rubric
  - Per-window accuracy
  - Violation detection (precision, recall)
  - False positive rate
  - Severity alignment
  - COD region accuracy

### 3.3 Baseline Measurement
- [ ] Run Phase 1 architecture on ground truth dataset
- [ ] Document per-window accuracy
- [ ] Measure false positive rate
- [ ] Identify failure modes
- [ ] Classify errors (prompt issue, data quality, edge case)

### 3.4 Iterative Refinement
- [ ] Tune prompts for agents with <95% accuracy
- [ ] Adjust severity thresholds if misaligned
- [ ] Add edge case handling
- [ ] Re-run evals, measure improvement

**Success Criteria:**
- ✅ Per-window accuracy >95%
- ✅ False positive rate <10% (down from 40-60%)
- ✅ Severity scoring aligns with ground truth (±1 level)

See [Phase 3 details in ARCHITECTURE_REDESIGN.md](docs/ARCHITECTURE_REDESIGN.md#phase-3-evaluation-framework-systematic-refinement)

---

## Phase 4: Model Testing & Report Updates 🎨 PLANNED

**Goal:** Test best available models on complex agents, update reports

**Status:** After Phase 3 evaluation

### 4.1 Model Performance Testing
- [ ] Test Gemini 3 Pro on COD Agent
  - Measure accuracy improvement vs flash-lite
  - Measure latency increase and cost impact
- [ ] Test Gemini 3 Pro on Evaluator Agent
  - Measure synthesis quality improvement
  - Measure flag specificity and summary coherence
- [ ] Keep flash-lite for Perception/Motion agents

### 4.2 Report Updates
- [ ] Add per-window compliance table
- [ ] Add severity score and level visualization
- [ ] Add COD region summary
- [ ] Add window distribution chart (IN_ODD/BOUNDARY/OUT_ODD)
- [ ] Add investigation flags section
- [ ] Add executive summary from Evaluator agent
- [ ] Remove collision risk charts
- [ ] Add collision detection events display

### 4.3 Example Reports
- [ ] Create example reports for each severity level
- [ ] Document model selection recommendation

See [Phase 4 details in ARCHITECTURE_REDESIGN.md](docs/ARCHITECTURE_REDESIGN.md#phase-4-model-testing--report-updates)

---

## Additional Tasks

### Pipeline Metadata & Telemetry Design ✅ COMPLETED

**Status:** Design complete in `docs/METADATA_DESIGN.md` (1,476 lines)

- [x] Research ADK capabilities and patterns ✅
- [x] Analyze 5 approaches (prompt-only, infrastructure, workflow, hybrid, callback-based) ✅
- [x] Create proof-of-concept code for recommended approaches ✅
- [x] Document two-tier recommendation ✅
  - **PRIMARY**: Approach E (Callback-Based) using `google.adk.callbacks.BaseCallback`
  - **FALLBACK**: Approach D (Hybrid) with self-report + validation

**Next Steps:**
- [ ] Verify ADK callbacks availability in current version
- [ ] Implement chosen approach (~100 lines for callbacks, ~230 for hybrid)
- [ ] Integrate metadata into pipeline
- [ ] Update reports to display metadata footer
- [ ] Enable A/B testing and performance tracking

See [`docs/METADATA_DESIGN.md`](docs/METADATA_DESIGN.md) for complete design.

### Kaggle Capstone Preparation

**Priority:** HIGH - Required for competition

#### Agent Evaluation & Testing 📋 NEEDS UPDATE

**Current State (as of Nov 27, 2025):**
- ❌ Agent wrappers use old API (`create_perception_loop_agent` → should be `create_perception_agent`)
- ❌ Test scenario paths outdated (`data/processed/runs/sim_run_test` → `data/test/sim/sim_test_w010_w011`)
- ❌ Judge model outdated (`gemini-2.5-pro` → should be `gemini-3-pro`)
- ❌ Rubrics reference old schemas (separate COD/Compliance → now Evaluator)
- ❌ Only Perception has .test.json, other 5 agents missing
- ✅ Framework structure exists (`odd_agents/evaluation/`, `tests/evaluation/`)
- ✅ 40 rubrics defined in ADK dict format

**ADK Evaluation Criteria to Use:**
| Criteria | Purpose | Agents |
|----------|---------|--------|
| `tool_trajectory_avg_score` | Verify correct tool sequence | All (CI/CD) |
| `rubric_based_final_response_quality_v1` | Custom quality rubrics | All |
| `rubric_based_tool_use_quality_v1` | Tool usage quality | Sensor agents |
| `hallucinations_v1` | Detect fabricated claims | Report agent |

**Implementation Plan:**

**Phase 1: Fix Infrastructure (Do 2-3 agents as examples)**
- [ ] Update `tests/evaluation/perception/perception_agent.py` to use new API
- [ ] Update judge model to `gemini-3-pro` in test configs
- [ ] Update scenario path to `data/test/sim/sim_test_w010_w011`
- [ ] Fix Perception agent wrapper + test file
- [ ] Fix Motion agent wrapper + create test file
- [ ] Validate both work with `pytest tests/test_adk_evaluation.py -v`

**Phase 2: Update Rubrics (Align with current schemas)**
- [ ] Update Perception rubrics (add data_source detection)
- [ ] Update Motion rubrics (artifact-based output)
- [ ] Consolidate COD/Compliance rubrics → Evaluator rubrics
- [ ] Update Report rubrics (v9.1.0 hybrid schema)

**Phase 3: Cloud Agent Pattern Matching**
- [ ] Document the pattern from Phase 1-2 examples
- [ ] Let cloud agents implement remaining agents:
  - [ ] Collision agent wrapper + test file
  - [ ] OddSpec agent wrapper + test file
  - [ ] Evaluator agent wrapper + test file
  - [ ] Report agent wrapper + test file

**Mock Data Strategy:**
- Use existing `data/test/sim/sim_test_w010_w011` (2 windows, real sensor data)
- Expected tool trajectories captured from production runs
- Reference responses generated from validated pipeline outputs

**References:**
- ADK Evaluation Docs: https://google.github.io/adk-docs/evaluate/
- Current rubrics: `odd_agents/evaluation/rubrics.py`
- Test structure: `tests/evaluation/*/`

- [ ] Performance benchmarking
  - [ ] Track token usage per agent across batch runs
  - [ ] Measure latency for each workflow stage
  - [ ] Compare model performance (flash vs flash-lite vs pro)

#### Kaggle Competition Alignment
- [ ] Review official evaluation criteria
- [ ] Identify point-earning opportunities
  - Novel contributions (multi-agent ODD analysis)
  - Comprehensive documentation
  - Reproducibility (demo data, clear setup)
- [ ] Add missing features based on rubric
  - Quantitative evaluation metrics
  - Comparison with baseline approaches
  - Failure case analysis
  - Future work roadmap

#### Final Report Preparation
- [ ] Executive Summary
  - Problem statement and motivation
  - Approach overview
  - Key results and contributions
- [ ] Technical Sections
  - Architecture deep dive
  - Agent design patterns
  - Multi-modal sensor fusion
  - ODD formalization and distance metrics
- [ ] Evaluation and Results
  - Test scenarios and datasets
  - Performance metrics
  - Comparison with manual analysis
  - Error analysis
- [ ] Documentation Quality
  - Clear diagrams (architecture, data flow)
  - Code examples with explanations
  - API reference
  - Troubleshooting guide

#### Demo Artifacts Creation
- [ ] Screen recording video (5-10 minutes)
  - Introduction and problem context
  - Live workflow demonstration
  - Results visualization and interpretation
  - Key takeaways
- [ ] Jupyter notebook walkthrough
  - Step-by-step execution
  - Inline explanations and visualizations
  - Interactive parameter tuning
- [ ] Static demo materials
  - Architecture diagrams
  - Sample reports (PDF/HTML)
  - Before/after comparisons
- [ ] GitHub README showcase
  - Badges (tests, docs, license)
  - GIF demonstrations
  - Quick start guide
  - Links to video and docs

### Generalization Guide for Other Platforms

**Document: "Adapting ODD/COD Analysis to Your Robot"**

- [ ] Template for defining custom ODD specifications
  - Axes selection (numeric vs categorical)
  - Boundary definition guidelines
  - Importance weight tuning
- [ ] Sensor integration guide
  - Mapping different sensor types to analysis agents
  - Custom feature extraction examples
  - Multi-modal fusion patterns
- [ ] Example adaptations
  - Aerial drone (altitude, wind, GPS quality)
  - Autonomous vehicle (road type, traffic, weather)
  - Warehouse AMR (floor type, shelf proximity, charging)
- [ ] Code templates
  - Agent instruction templates for different domains
  - Tool function patterns for custom sensors
  - Distance metric customization

---

## Completed Tasks

### Validate with Real Robot Data ✅ COMPLETED
- [x] Run complete pipeline on real robot bagfile (not simulation)
  - ✅ Processed 6 real robot collections (270 windows total)
  - ✅ Created standardized test sets (12 windows across 6 scenarios)
  - ✅ Verified workflow with actual movement data
  - ✅ Validated motion detection, collision analysis, ODD compliance
- [x] Document differences between sim and real data
  - ✅ Motion characteristics confirmed (real has non-zero velocities)
  - ✅ ODD violations identified (terrain, obstacles, environment)
  - ✅ Production scripts created for batch processing

### Production Workflow Scripts ✅ COMPLETED
- [x] Create manual interactive runner
  - ✅ `scripts/run_odd_analysis.py` - scenario selection, single runs
  - ✅ Outputs to `data/analysis_results/manual/`
  - ✅ Model configuration at module level
  - ✅ Clean output with warning suppression
- [x] Create automated batch processor
  - ✅ `scripts/run_odd_batch_analysis.py` - process all production data
  - ✅ Outputs to `data/analysis_results/automated/`
  - ✅ Progress bars and fail-fast error handling
  - ✅ Aggregate reporting across scenarios
- [x] Bug fixes and improvements
  - ✅ Fixed ODD compliance double-nesting extraction
  - ✅ Added environment_class to report metadata
  - ✅ Preserve source_scenario_path in results
  - ✅ Standardized data naming convention (underscores)
- [x] Documentation
  - ✅ Updated scripts/README.md with production workflow
  - ✅ Moved DATA_NAMING_CONVENTION.md to docs/
  - ✅ Archived superseded scripts to .archive/

### IMU-based Motion Analysis ✅ COMPLETED
- [x] Enhanced motion analysis to work without odometry data
- [x] Added jerk analysis (smoothness assessment) from IMU acceleration
- [x] Integrated camera-based visual odometry hints (multimodal approach)
- [x] New output schema: `estimated_speed_mps`, `motion_smoothness` fields
- [x] Comprehensive IMU statistics (3D gyro, filtered acceleration, jerk metrics)
- [x] Backward compatible with existing test expectations

**Technical details:**
- Filters zero readings from sensor gaps
- Calculates jerk (d/dt acceleration) for smoothness
- Uses Gemini vision to estimate velocity from camera blur/optical flow
- 3D rotation analysis (roll rate, pitch rate, yaw rate)
- Horizontal acceleration focus (X-Y plane, gravity-excluded)
- Files updated: `odd_agents/tools/motion.py`

---

## Technical Debt & Future Improvements

### Known Issues (Deferred)
- [ ] **Debug Plotly Charts in HTML Reports** 🔧 DEFERRED
  - Charts not rendering despite data being present in HTML
  - Tried: min-height CSS, DOMContentLoaded wrapper
  - Data verified: accelData, riskData, accelTimeseriesData, gyroTimeseriesData all populated
  - Plotly.newPlot calls present for all 4 chart divs
  - **Next steps**: Test in local browser with dev tools, check console errors
  - **Workaround**: Charts section removed from reports for now
  - **Files**: `scripts/generate_html_report.py` (template has chart code commented out)

- [ ] **BEV Ground Filtering Validation** ⚠️ NEXT STEP
  - [x] Implemented 10cm height threshold for ground filtering ✅ MERGED TO DEV
  - [ ] Reprocess production data with filtered BEV occupancy
  - [ ] Compare perception metrics before/after (occupancy ratio, obstacle density)
  - [ ] Validate on scenario 17 (emergency stop) - expect reduced false positives
  - [ ] Update batch statistics (100 windows) with new filtering
  - **Expected improvements**:
    - Occupancy ratio: 60-80% reduction on flat terrain
    - Obstacle density: More accurate (matches camera-visible objects)
    - Traversability: Better correlation with actual path clearance
  - **Technical details**: `docs/BEV_GROUND_FILTERING.md`
  - **Status**: Ready for full data regeneration

### Code Quality Improvements
- [x] Validate test data generation scripts match current workflow ✅ DONE
- [x] Consolidate test fixtures ✅ DONE
- [ ] Add type hints to remaining functions
- [ ] Improve error messages and logging consistency
- [ ] Consider removing old `odd_cod/` module if unused

### Nice-to-Have Features
- [ ] Web interface for non-technical users
- [ ] Automated report generation pipeline (executive summary export)
- [ ] Real-time monitoring dashboard
- [ ] Historical trend analysis across deployments
- [ ] Compliance certification export (PDF report)
- [ ] Meta-analysis tools for comparing batch runs

### Future Research: Intelligent Data Selection Agent

**Current Limitation**: Fixed window sampling strategy
- Programmatically select observation windows (e.g., every 5 seconds)
- Single camera frame + single LiDAR scan per window
- May miss critical events (sudden obstacle, lighting change, collision)
- Compute efficiency vs. data coverage trade-off

**Proposed Enhancement**: Pre-Analysis Triage Agent
- **Goal**: Intelligent selection of "interesting" data for detailed analysis
- **Method**: Lightweight LLM scan of full scenario data
- **Output**: Prioritized windows/frames for detailed processing

**Implementation Approach**:
1. **Quick Scan Phase** (low-cost model, e.g., flash-lite):
   - Load all camera thumbnails (downsampled 128x128)
   - Load IMU time series (full resolution, low token cost)
   - Load LiDAR occupancy overview (downsampled BEV)
   
2. **Triage Analysis**:
   - Detect regime changes (bright → dark, clear → cluttered)
   - Identify motion anomalies (acceleration spikes, sudden stops)
   - Flag potential safety events (collision signatures, near-miss)
   - Score each window: ROUTINE / INTERESTING / CRITICAL
   
3. **Adaptive Sampling**:
   - ROUTINE windows: Skip or sample 1 per 10 seconds
   - INTERESTING windows: Standard sampling (current 5s cadence)
   - CRITICAL windows: Dense sampling (1-2s cadence, multiple frames)

**Benefits**:
- **Better violation detection**: Don't miss transient events
- **Compute efficiency**: Focus expensive analysis on important data
- **Adaptive fidelity**: Match analysis depth to scenario complexity
- **Post-incident investigation**: Automatic zoom-in on anomalies

**Example Use Case**:
```
Scenario: 60-second navigation run
Full data: 60 camera frames, 720 IMU samples, 12 LiDAR scans

Triage agent output:
- Seconds 0-30: ROUTINE (slow corridor walk)
  → Sample: 3 windows (10s cadence)
- Seconds 30-35: INTERESTING (furniture cluster detected)
  → Sample: 1 window (5s cadence)
- Seconds 35-38: CRITICAL (IMU spike + sudden stop)
  → Sample: 2 windows (1.5s cadence, 2 frames each)
- Seconds 38-60: ROUTINE (resumed slow walk)
  → Sample: 2 windows (10s cadence)

Total windows: 8 (vs 12 uniform) but better event coverage
```

**Technical Challenges**:
- Downsampling strategy (maintain detectability of events)
- Triage agent prompt design (what makes data "interesting"?)
- Confidence calibration (avoid false negatives on subtle violations)
- Cost/benefit analysis (triage overhead vs. savings on main analysis)

**Integration Point**: Phase 5+ or post-Kaggle capstone
- Requires stable Phase 1-4 architecture first
- Enables scaling to longer scenarios (5-10 minute runs)
- Research contribution: Multi-stage adaptive analysis pipeline

**Related Work**:
- Active learning for robotics (selective labeling)
- Video summarization (keyframe extraction)
- Anomaly detection for time series (changepoint detection)

---

**Last Updated**: November 27, 2025  
**Project**: Go2 ODD Observer - Kaggle ADK Agent Capstone  
**Status**: Phase 1.4.5 Complete, HTML Reports v2.0 deployed

**Current Focus**: RAG knowledge base, then production testing

**Recent Completions (Nov 27, 2025)**:
- ✅ HTML Reports v2.0: Inline SVG charts, data source detection, Phase 1.4.5 schema
- ✅ GitHub Pages Update: ODD/COD explanation, pipeline diagram, 3 production reports
- ✅ Terminology Fixes: COD/BOUNDARY definitions corrected across all agents
- ✅ Phase 1.4.5: Artifact Handoff, Categorical Reasoning, Data Source Detection

**Agent Versions (v1.4.5)**:
| Agent | Version | Model |
|-------|---------|-------|
| OddSpecAgent | 6.1.0 | gemini-2.5-flash |
| PerceptionAgent | 7.4.0 | gemini-2.5-flash |
| MotionAgent | 7.3.0 | gemini-2.5-flash |
| CollisionAgent | 7.3.0 | gemini-2.5-flash |
| EvaluatorAgent | 5.0.0 | gemini-2.5-pro |
| ReportAgent | 9.1.0 | gemini-2.5-flash |
| CODTool | 1.1.0 | gemini-2.5-flash (categorical micro-agent) |

**Suggested Next Phases**:
| Phase | Focus | Description | Priority |
|-------|-------|-------------|----------|
| 1.6 | Test updates | Update unit tests for new API (loop→consolidated agents) | MEDIUM |
| 1.7 | Full production run | Run on all sim_1_0 chunks (100 windows) | HIGH |
| 2.0 | Performance optimization | Visual/LiDAR odometry, tool splitting | LOW |
| 2.1 | Real data validation | Test on real robot data (not sim) | HIGH |
