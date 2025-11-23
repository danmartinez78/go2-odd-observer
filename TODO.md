# Project TODO - Kaggle Capstone Preparation

## Priority Tasks

### 0. Validate with Real Robot Data ✅ COMPLETED
- [x] Run complete pipeline on real robot bagfile (not simulation)
  - ✅ Processed 6 real robot collections (270 windows total)
  - ✅ Created standardized test sets (12 windows across 6 scenarios)
  - ✅ Verified workflow with actual movement data
  - ✅ Validated motion detection, collision analysis, ODD compliance
- [x] Document differences between sim and real data
  - ✅ Motion characteristics confirmed (real has non-zero velocities)
  - ✅ ODD violations identified (terrain, obstacles, environment)
  - ✅ Production scripts created for batch processing

### 1. Agent Evaluation & Testing ⚠️ HIGH PRIORITY - KAGGLE COMPETITION
- [x] Implement LLM-as-judge evaluation pattern ✅ COMPLETED
  - ✅ Use gemini-2.5-pro as judge to avoid model similarity bias
  - ✅ Majority voting (num_samples=5) for robustness
  - ✅ Custom rubrics for all 7 agent types
  - ✅ Comprehensive evaluation framework in `odd_agents/evaluation/`
  - ✅ Demo script and test fixtures
  - See `odd_agents/evaluation/README.md` for details
- [ ] **URGENT: Review and fix ADK evaluation tests** ⚠️ CRITICAL FOR KAGGLE
  - [ ] Verify existing eval tests still pass after perception prompt changes
  - [ ] Update test expectations for terrain classification (now correctly classifies rugs as "smooth")
  - [ ] Review and merge agent evaluation PRs (separate branches)
  - [ ] Fix any broken evaluation workflows
  - [ ] Update evaluation datasets for new prompt behavior
  - [ ] Validate rubrics align with updated agent outputs
  - [ ] Run full test suite: `pytest tests/test_adk_evaluation.py -v`
  - **Impact**: Required for Kaggle competition scoring and validation
  - **Notes**: Perception prompt improvements (terrain vs obstacles) may have changed expected outputs
  - **Branch**: `feature/perception-improvements` - ready for testing
- [x] Expand test coverage ✅ COMPLETED
  - ✅ Test scripts for all agents (perception, motion, collision, ODD spec)
  - ✅ Production runners for manual and batch analysis
  - ✅ Validation with real robot data
  - ✅ JSON schema compliance verified
- [ ] Performance benchmarking
  - [ ] Track token usage per agent across batch runs
  - [ ] Measure latency for each workflow stage
  - [ ] Compare model performance (flash vs flash-lite vs pro)

### 2. Production Workflow Scripts ✅ COMPLETED
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

### 3. Generalization Guide for Other Platforms
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

### 4. Kaggle Capstone Evaluation Alignment
**Review competition rubric and maximize points**

- [ ] Review official evaluation criteria
  - Technical depth and innovation
  - Code quality and documentation
  - Real-world applicability
  - Presentation quality
- [ ] Identify point-earning opportunities
  - Novel contributions (multi-agent ODD analysis)
  - Comprehensive documentation
  - Reproducibility (demo data, clear setup)
  - Professional presentation
- [ ] Add missing features based on rubric
  - Quantitative evaluation metrics
  - Comparison with baseline approaches
  - Failure case analysis
  - Future work roadmap

### 5. Final Report Preparation
**According to Kaggle capstone guidelines**

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

### 6. Demo Artifacts Creation
**Video and interactive demonstrations**

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

## Backlog / Nice-to-Have

- [ ] **Debug Plotly Charts in HTML Reports** 🔧 DEFERRED
  - Charts not rendering despite data being present in HTML
  - Tried: min-height CSS, DOMContentLoaded wrapper
  - Data verified: accelData, riskData, accelTimeseriesData, gyroTimeseriesData all populated
  - Plotly.newPlot calls present for all 4 chart divs
  - **Next steps**: Test in local browser with dev tools, check console errors, try iframe embedding
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
- [ ] Web interface for non-technical users
- [ ] Automated report generation pipeline (executive summary export)
- [ ] Real-time monitoring dashboard
- [ ] Historical trend analysis across deployments
- [ ] Compliance certification export (PDF report)
- [ ] Meta-analysis tools for comparing batch runs
- [x] **COMPLETED: IMU-based motion analysis (odometry-independent)** ✅
  - ✅ Enhanced motion analysis to work without odometry data
  - ✅ Added jerk analysis (smoothness assessment) from IMU acceleration
  - ✅ Integrated camera-based visual odometry hints (multimodal approach)
  - ✅ New output schema: `estimated_speed_mps`, `motion_smoothness` fields
  - ✅ Comprehensive IMU statistics (3D gyro, filtered acceleration, jerk metrics)
  - ✅ Backward compatible with existing test expectations
  - **Impact**: Motion analysis now works reliably with real robot data
  - **Technical details**: 
    - Filters zero readings from sensor gaps
    - Calculates jerk (d/dt acceleration) for smoothness
    - Uses Gemini vision to estimate velocity from camera blur/optical flow
    - 3D rotation analysis (roll rate, pitch rate, yaw rate)
    - Horizontal acceleration focus (X-Y plane, gravity-excluded)
  - **Files updated**: `odd_agents/tools/motion.py`
  - **Testing needed**: Run `pytest tests/test_adk_evaluation.py::test_motion_* -v`

## Technical Debt

- [x] Validate test data generation scripts match current workflow ✅ DONE
- [x] Consolidate test fixtures ✅ DONE
- [ ] Add type hints to remaining functions
- [ ] Improve error messages and logging consistency
- [ ] Consider removing old `odd_cod/` module if unused

---

**Last Updated**: November 23, 2025
**Project**: Go2 ODD Observer - Kaggle ADK Agent Capstone
**Status**: Production Ready - Final Validation & Documentation Phase

**Recent Completions**:
- ✅ Real robot data validation (270 windows, 6 scenarios)
- ✅ Production workflow scripts (manual + batch)
- ✅ Bug fixes (compliance extraction, environment metadata)
- ✅ Documentation cleanup and reorganization
- ⚠️ Agent evaluation PRs pending review/merge
