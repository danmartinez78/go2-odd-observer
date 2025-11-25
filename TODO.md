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

### 1.3 COD Agent Redesign 📋 NEXT

**Items to Address After Agent Versioning:**
- Remove `collision_risk` from COD numeric metrics (add `collision_detected` boolean)
- Remove `collision_risk` constraint from ODD spec parsing
- Clarify `visibility_score` vs `lighting_class` semantics in perception prompt
  - Current: `lighting_class` = environmental lighting quality
  - Current: `visibility_score` may = navigable area visibility (explains 0.0 when blocked)
  - Decision needed: Keep separate or merge into single metric?

**Core Redesign Tasks:**
- [ ] Implement per-window ODD compliance checking
  - Compare each window against ODD thresholds
  - Output IN_ODD / BOUNDARY / OUT_ODD per window
- [ ] Implement scenario COD region construction
  - Categorical: collect all unique observed values
  - Numeric: extract min/max/range for each axis
- [ ] Implement ODD overlap analysis
  - Detect categorical violations
  - Detect numeric overlap with OUT_ODD ranges
- [ ] Manual test: verify no averaging, all violations preserved

### 1.5 Collision Agent BEV Enhancement 💡 DEFERRED

**Proposed Enhancement:** Add BEV occupancy visual confirmation to collision detection

**Rationale:**
- Multimodal validation (similar to motion agent using camera to validate IMU)
- Visual confirmation: Obstacle in final frames → collision vs command stop → no obstacle
- Impact geometry: BEV could show contact patterns during collision

**Challenges:**
- **Self-hit complexity**: Robot body appears in BEV center (~0.3m radius)
  - Agent needs clear instructions about masking center region
  - Must understand BEV spatial mapping (pixels → meters)
- **Temporal mismatch**: Current binary detection checks thresholds anywhere in window
  - BEV requires frame-by-frame analysis (which frames show what)
  - Need temporal correlation (obstacle appeared when IMU spiked?)
- **False positive risk**: Robot always near obstacles in cluttered environments
  - Hard to distinguish "near furniture" (normal) vs "contacted furniture" (collision)
- **Scope creep**: Phase 1.2 just completed and validated (0 false positives)
  - Adding BEV requires rewriting collision.py, complex prompts, additional testing
  - Delays Phase 1.3 (COD agent redesign)

**Decision:** Defer to Phase 1.5+ or post-versioning
- Current IMU-only system works (no false positives on test data)
- Better fit for Phase 2 after agent versioning (A/B test IMU-only vs IMU+BEV)
- Need better temporal analysis design first (frame-level reasoning)
- Can revisit with sophisticated temporal reasoning later

**If Implemented Later:**
- Load BEV occupancy frames in collision.py
- Mask robot body center (~0.3m radius) in prompts
- Temporal analysis: "Does BEV show obstacle contact during IMU spike window?"
- More sophisticated evidence gathering (not just boolean)

### 1.4 Evaluator Agent Creation
- [ ] Rename Compliance → Evaluator agent
- [ ] Implement severity calculation from window distribution
  - Formula: `(out_odd × 2.0 + boundary × 0.5) / total × 10`
  - Map to severity levels (MINIMAL/LOW/MEDIUM/HIGH/CRITICAL)
- [ ] Integrate all flags
  - ODD violations from COD agent
  - Sensor quality issues from Perception
  - Motion anomalies from Motion agents
  - Collision detections from Collision agent
- [ ] Generate investigation flags (specific, actionable)
- [ ] Generate executive summary

### 1.5 Manual Validation Suite
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

---

**Last Updated**: November 25, 2025  
**Project**: Go2 ODD Observer - Kaggle ADK Agent Capstone  
**Status**: Phase 1.1 Complete, Starting Phase 1.2

**Current Focus**: Phase 1.2 - Collision Agent Rework

**Recent Completions**:
- ✅ Phase 1.1: BEV Enhancement (merged to dev Nov 25)
  - Auto-crop: 65-72% size reduction
  - Density removed: 3 channels (occupancy, height, roughness)
  - Data reorganized: production/, test/, archive/
  - Sim data ready: 62 production + 6 test windows
  - Documentation updated: 4 docs (transformation status, enhancement summary, versioning, README)
- ✅ Branch cleanup: Deleted 16 merged branches (20→5 remaining)
- ✅ Phase 0: Bagfile audit (no velocity data)
- ✅ Real robot validation (270 windows, 6 scenarios)
- ✅ Production workflow scripts (manual + batch)
- ✅ IMU-based motion analysis

**Next Steps**:
1. Add all 4 BEV channels to perception/collision tools
2. Integrate auto-crop into BEV rendering pipeline
3. Implement COD agent redesign (per-window compliance)
4. Implement Collision agent redesign (binary detection)
5. Implement Evaluator agent (severity-based synthesis)
