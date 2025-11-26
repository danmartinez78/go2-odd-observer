# ODD Observer Development Roadmap

See [`docs/ARCHITECTURE_REDESIGN.md`](docs/ARCHITECTURE_REDESIGN.md) for detailed design and rationale.

## 🚨 CRITICAL: Architecture Redesign in Progress

**Current system has fundamental flaws:**
- **Averaging destroys violations**: COD agent averages per-window observations, hiding OUT_ODD windows (e.g., dark lighting window averaged to "bright")
- **Collision agent produces false positives**: Risk scoring flags too many scenarios; should detect actual collisions only
- **COD represents fictional point**: Averaging creates a point that never existed vs. representing the actual operational region

**Redesign addresses these with:**
- COD-as-multidimensional-region approach (preserves all observations)
- Severity-based assessment (nuanced beyond binary pass/fail)
- Per-window compliance tracking (no violations lost to averaging)

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

## Phase 1: Architecture Refactor 📋 PLANNED

**Goal:** Get the new architecture working, validate with manual testing

**Status:** Ready to begin

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
- [x] Update COD agent v3.0.0 for dynamic schema (reads ODD spec)
- [x] Test with current ground robot ODD (baseline validation)
- [x] Test with alternate drone ODD (generalization validation)
- [x] Documentation updates in TODO.md

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

### 1.7 Manual Validation Testing 📋 PLANNED

**Goal**: Rename Compliance to Evaluator, add distance-from-limits calculation with telemetry

**Tasks**:
- [ ] Rename Compliance → Evaluator agent
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

#### Agent Evaluation & Testing
- [x] Implement LLM-as-judge evaluation pattern ✅ COMPLETED
  - ✅ Use gemini-2.5-pro as judge to avoid model similarity bias
  - ✅ Majority voting (num_samples=5) for robustness
  - ✅ Custom rubrics for all 7 agent types
  - ✅ Comprehensive evaluation framework in `odd_agents/evaluation/`
  - See `odd_agents/evaluation/README.md` for details
- [ ] **URGENT: Review and fix ADK evaluation tests** ⚠️ CRITICAL FOR KAGGLE
  - [ ] Verify existing eval tests still pass after perception prompt changes
  - [ ] Update test expectations for terrain classification
  - [ ] Review and merge agent evaluation PRs
  - [ ] Fix any broken evaluation workflows
  - [ ] Update evaluation datasets for new prompt behavior
  - [ ] Validate rubrics align with updated agent outputs
  - [ ] Run full test suite: `pytest tests/test_adk_evaluation.py -v`
- [x] Expand test coverage ✅ COMPLETED
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

**Last Updated**: November 25, 2025  
**Project**: Go2 ODD Observer - Kaggle ADK Agent Capstone  
**Status**: Phase 1.4 Complete, Phase 1.4.1 Planned

**Current Focus**: Phase 1.4 wrap-up and merge preparation

**Recent Completions**:
- ✅ Phase 1.4: Agent Versioning & Telemetry (completed Nov 25)
  - Event-based metadata extraction (62,860 tokens, $1.26, 214s)
  - Version registry, prompt catalog, metadata utilities
  - Terminal/JSON/HTML metadata display
  - Per-agent execution tracking with prompt hashes
  - Documentation updated: scripts/README.md, ARCHITECTURE_REDESIGN.md
- ✅ Phase 1.6: Collision BEV Enhancement (completed Nov 25, originally deferred)
  - Multimodal collision detection (IMU + camera + 3 BEV channels)
  - Independent data loading (removed motion_metrics dependency)
  - LLM reasoning vs hardcoded thresholds
  - Test results: 0.95-0.98 confidence, no false positives
- ✅ Phase 1.1-1.3: BEV Enhancement, Collision Rework, COD Redesign (merged to dev)
- ✅ Branch cleanup: 16 merged branches deleted
- ✅ Real robot validation (270 windows, 6 scenarios)

**Critical Discovery**:
- ⚠️ ODD-Schema architectural flaw identified (Phase 1.4.1)
  - Problem: Agents have hardcoded dimension expectations
  - ODD Spec generates dynamic schemas, but agents don't read them
  - Blocks generalization to different ODD structures
  - Fix planned: Schema-driven agents reading ODD spec dynamically

**Next Steps**:
1. Complete Phase 1.4 wrap-up (tests, integration, git commit)
2. Phase 1.4.1: ODD-Schema Driven Architecture (critical fix)
3. Phase 1.5: Evaluator Agent Enhancement (severity-based synthesis)
4. Phase 1.7: Manual Validation Testing
