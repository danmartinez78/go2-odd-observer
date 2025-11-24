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

## Phase 0: Data Source Discovery ⏳ IN PROGRESS

**Goal:** Identify all available sensor data in bagfiles, find integration opportunities

**Status:** Quick investigation phase (2-4 hours)

- [ ] Create bagfile topic audit script
  - Systematically inspect all topics in representative bagfiles
  - Check message rates, data validity, coverage
  - Identify populated vs empty topics
- [ ] Run audit on 2-3 representative scenarios
  - Real robot bagfiles (production data)
  - Different environment types
- [ ] Document findings
  - Available topics inventory (CSV/JSON)
  - Data quality assessment (rates, validity, coverage)
  - Utility ratings for each topic
- [ ] Identify integration opportunities
  - `/joint_states` - Gait analysis for terrain classification?
  - `/cmd_vel` - Commanded vs actual motion comparison?
  - `/contact_states` or foot sensors - Collision detection?
  - Motor currents - High-resistance situations (collisions, difficult terrain)?
- [ ] Update sensor documentation
  - Add "Available Sensors" section to architecture docs
  - Update `DATA_NAMING_CONVENTION.md` with all available topics
  - Flag missing sensors valuable for future hardware

**Deliverables:**
- Topic audit report with findings
- Integration recommendations (prioritized)
- Updated sensor documentation

See [Phase 0 details in ARCHITECTURE_REDESIGN.md](docs/ARCHITECTURE_REDESIGN.md#phase-0-data-source-discovery-quick-investigation)

---

## Phase 1: Architecture Refactor 📋 PLANNED

**Goal:** Get the new architecture working, validate with manual testing

**Status:** Awaiting Phase 0 completion

### 1.1 Collision Agent Rework
- [ ] Remove collision risk scoring logic entirely
- [ ] Implement binary collision detection
  - IMU spike detection (threshold: >10 m/s² acceleration)
  - Angular velocity change patterns
  - Force sensor integration (if available from Phase 0)
- [ ] Update output schema (collisions_detected list, no risk scores)
- [ ] Manual test on 2-3 scenarios

### 1.2 COD Agent Redesign
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

### 1.3 Evaluator Agent Creation
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

### 1.4 Manual Validation Suite
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
- ✅ New pipeline runs end-to-end without errors
- ✅ COD regions capture all observations (no fictional averaged points)
- ✅ Severity scores differentiate scenarios appropriately
- ✅ No violations averaged away

See [Phase 1 details in ARCHITECTURE_REDESIGN.md](docs/ARCHITECTURE_REDESIGN.md#phase-1-architecture-refactor)

---

## Phase 2: Performance Optimization 🔧 PLANNED

**Goal:** Improve pipeline efficiency with high-impact, low-effort changes

**Status:** After Phase 1 validation

### 2.1 BEV Auto-Cropping
- [ ] Implement auto-crop for BEV images (remove empty borders)
- [ ] Expected gain: 50-75% BEV file size reduction

### 2.2 Tool Splitting by Data Type
- [ ] Split tools by required data
  - `camera_image_tool` → Perception Image Agent only
  - `bev_occupancy_tool` → Perception BEV Agent only
  - `imu_data_tool` → Motion agents only
- [ ] Expected gain: 30-40% token reduction

### 2.3 Image Encoding Optimization
- [ ] Camera images: JPEG at quality 85-90
- [ ] BEV images: Keep PNG (sharp geometric features)
- [ ] Expected gain: 40-60% size reduction for camera images

### 2.4 Performance Benchmarking
- [ ] Measure before/after on 10-scenario batch
- [ ] Verify 30-50% overall token reduction
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

### Pipeline Metadata & Telemetry Design

**Status:** Awaiting Issue #1 completion

- [ ] Design metadata structure (pipeline version, ODD spec version, agent versions)
- [ ] Implement ODD versioning (version string, hash)
- [ ] Implement agent versioning (version, model, prompt hash)
- [ ] Add execution stats (duration, token usage, timings)
- [ ] Update reports to display metadata footer
- [ ] Enable A/B testing and performance tracking

See [Metadata design in ARCHITECTURE_REDESIGN.md](docs/ARCHITECTURE_REDESIGN.md#pipeline-metadata--telemetry-new)

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

**Last Updated**: November 24, 2025  
**Project**: Go2 ODD Observer - Kaggle ADK Agent Capstone  
**Status**: Architecture Redesign Planning Phase

**Current Focus**: Phase 0 - Data Source Discovery

**Recent Completions**:
- ✅ Real robot data validation (270 windows, 6 scenarios)
- ✅ Production workflow scripts (manual + batch)
- ✅ IMU-based motion analysis (odometry-independent)
- ✅ Bug fixes (compliance extraction, environment metadata)
- ✅ Documentation cleanup and reorganization

**Next Steps**:
1. Complete Phase 0: Audit bagfile topics and identify integration opportunities
2. Begin Phase 1: Implement architecture refactor (collision, COD, evaluator agents)
3. Continue Kaggle preparation in parallel (evaluation tests, final report)
