# Project TODO - Kaggle Capstone Preparation

## Priority Tasks

### 0. Validate with Real Robot Data
- [ ] Run complete pipeline on real robot bagfile (not simulation)
  - Current sim data has stationary robot (zero velocities)
  - Need to verify workflow with actual movement data
  - Test with data/raw_rosbags/real/ if available
  - Expected: Non-zero motion features, realistic ODD violations
- [ ] Document differences between sim and real data
  - Motion characteristics
  - Sensor noise patterns
  - ODD compliance patterns

### 1. Improve Agent Testing ✅ COMPLETED
- [x] Implement LLM-as-judge evaluation pattern
  - ✅ Use gemini-2.5-pro as judge to avoid model similarity bias
  - ✅ Majority voting (num_samples=5) for robustness
  - ✅ Custom rubrics for all 7 agent types
  - ✅ Comprehensive evaluation framework in `odd_agents/evaluation/`
  - ✅ Demo script and test fixtures
  - See `odd_agents/evaluation/README.md` for details
- [ ] Expand test coverage
  - [ ] Integrate LLM-as-judge into existing test suite
  - [ ] Add edge cases (extreme values, missing data, malformed inputs)
  - [ ] Test error handling and recovery
  - [ ] Validate JSON schema compliance
- [ ] Performance benchmarking
  - [ ] Track token usage per agent
  - [ ] Measure latency for each workflow stage
  - [ ] Compare model performance (flash-lite vs pro)

### 2. Generalization Guide for Other Platforms
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

### 3. Kaggle Capstone Evaluation Alignment
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

### 4. Final Report Preparation
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

### 5. Demo Artifacts Creation
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

- [ ] Web interface for non-technical users
- [ ] Automated report generation pipeline
- [ ] Integration with ROS2 bagfile processing
- [ ] Real-time monitoring dashboard
- [ ] Historical trend analysis across deployments
- [ ] Compliance certification export (PDF report)

## Technical Debt

- [ ] Remove unused `odd_cod/` module (check if still referenced)
- [ ] Validate test data generation scripts match current workflow
- [ ] Consolidate test fixtures
- [ ] Add type hints to all functions
- [ ] Improve error messages and logging

---

**Last Updated**: November 21, 2025
**Project**: Go2 ODD Observer - Kaggle ADK Agent Capstone
**Status**: Development Phase - Preparing for Final Submission
