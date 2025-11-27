# 🤖 Go2 ODD Observer

<div align="center">

**Multi-Agent AI System for Autonomous Robot Safety Assessment**

*Automatically assess if robots are operating within their design limits using vision, motion, and LiDAR fusion*

[![Kaggle Agents Intensive](https://img.shields.io/badge/Kaggle-5--Day_Agents-20BEFF?style=for-the-badge&logo=kaggle)](https://www.kaggle.com/learn-guide/5-day-agents)
[![Google ADK](https://img.shields.io/badge/Google-ADK_v1.18-4285F4?style=for-the-badge&logo=google)](https://github.com/google/generative-ai-python)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python)](https://www.python.org)
[![ROS2 Humble](https://img.shields.io/badge/ROS2-Humble-22314E?style=for-the-badge&logo=ros)](https://docs.ros.org/en/humble/)

[**Quick Start**](#-quick-start) • [**Live Demo**](https://danmartinez78.github.io/go2-odd-observer/) • [**Documentation**](docs/guides/GETTING_STARTED.md) • [**Features**](#-key-features)
[**Agent Knowledge**](docs/agent_knowledge/README.md)

</div>

---

## 🎯 What This Does

**Deploying autonomous robots? Need to know if they're operating safely?**

This system uses **6 pipeline agents + 4 tool agents** (10 LLM-calling entities) to analyze multi-modal sensor data (camera, LiDAR, IMU) and automatically answer:

✅ **Is the robot within its design limits?** (Operational Design Domain compliance)  
⚠️ **Are conditions approaching safety boundaries?** (Warning detection)  
❌ **Has the robot exceeded safe operating conditions?** (Violation detection)

### Key Concepts

**🎯 ODD (Operational Design Domain)**
> The specific conditions and environments a robot is **designed** to operate in. Think of it as the robot's "safe operating zone" - like speed limits, terrain types, and obstacle densities it was built to handle.

**📊 COD (Current Operating Domain)**  
> The actual conditions the robot is **currently experiencing**, measured from its sensors. This is "where the robot actually is" at any moment.

**⚖️ ODD Compliance**
> Comparing COD vs ODD to detect when actual conditions exceed design specifications. Like a safety check: "Are we still within safe operating limits?"

**Example:** A delivery robot designed for smooth indoor floors (ODD) suddenly encounters gravel parking lot (COD) → System flags `OUT_ODD` violation.

---

## 🌟 Why This Matters

**For Autonomous Systems:**
- 🚨 **Safety Assessment**: Automatically detect when robots enter unsafe conditions
- 📋 **Compliance Documentation**: Generate audit trails for regulatory requirements  
- 🔍 **Post-Incident Analysis**: Understand what went wrong after failures
- 🎯 **Deployment Screening**: Assess new environments before go-live

**Technical Innovation:**
- **ODD-First Architecture**: Define safety constraints before analyzing data (not after)
- **Parameterized Design**: No global state → fully isolated, parallel-safe execution
- **IMU-Based Motion**: Robust motion detection using accelerometers (works when odometry fails)
- **Cost-Optimized AI**: Smart model selection defaults to flash-lite (~70% cheaper than pro models)

---

## ⚡ Quick Start

### 1️⃣ Install

```bash
git clone https://github.com/danmartinez78/go2-odd-observer.git
cd go2-odd-observer
pip install -r requirements.txt
echo "GOOGLE_API_KEY=your-api-key-here" > .env  # Get free key: https://aistudio.google.com
```

### 2️⃣ Run Analysis

```bash
# Interactive analysis CLI (select from test/production scenarios)
python scripts/run_odd_analysis.py
```

### 3️⃣ View Results

**Option A: Interactive HTML Report (Recommended)**
```bash
python scripts/generate_html_report.py \
  --input data/analysis_results/automated/latest/full_result.json \
  --scenario-dir data/processed/test_data/real/real_03_174232 \
  --output report.html

open report.html  # or: $BROWSER report.html
```

**Option B: JSON Analysis**
```bash
jq '.odd_compliance.overall_status' data/analysis_results/automated/latest/full_result.json
# Output: "OUT_ODD"

jq '.odd_compliance.violations[].parameter' data/analysis_results/automated/latest/full_result.json
# Output: "motion_smoothness", "max_accel_mps2", "collision_risk"
```

🌐 **Live Examples:** [https://danmartinez78.github.io/go2-odd-observer/](https://danmartinez78.github.io/go2-odd-observer/)  
📚 **Full Setup Guide:** [docs/guides/GETTING_STARTED.md](docs/guides/GETTING_STARTED.md)

---

## 🤖 How It Works

### 6 Pipeline Agents + 4 Tool Agents

**Pipeline Agents** (tracked by ADK):
```mermaid
graph LR
    A[📝 ODD Spec] --> B[👁️ Perception]
    B --> C[🎯 Motion]
    C --> D[⚠️ Collision]
    D --> E[⚖️ Evaluator<br/>COD + Compliance]
    E --> F[📋 Report]
    
    style A fill:#e3f2fd,stroke:#333,stroke-width:2px,color:#000
    style B fill:#fff9c4,stroke:#333,stroke-width:2px,color:#000
    style C fill:#fff9c4,stroke:#333,stroke-width:2px,color:#000
    style D fill:#ffccbc,stroke:#333,stroke-width:2px,color:#000
    style E fill:#f8bbd0,stroke:#333,stroke-width:2px,color:#000
    style F fill:#f8bbd0,stroke:#333,stroke-width:2px,color:#000
    style G fill:#c8e6c9,stroke:#333,stroke-width:2px,color:#000
```

**Phase 1.4.5 Architecture (Current - Nov 2025):**

**Two-Tier Design:**
- **Pipeline Agents** (6 total): Orchestrated by ADK, tracked in metadata
  - OddSpecAgent, PerceptionAgent, MotionAgent, CollisionAgent, EvaluatorAgent, ReportAgent
- **Tool Agents** (4 total): Embedded LLM calls within tools (NOT tracked by ADK)
  - `perception_tool`: Camera + 3 BEV channels → multimodal vision analysis
  - `motion_tool`: IMU + camera → motion state with reasoning
  - `collision_tool`: Multimodal fusion → binary collision detection
  - `cod_construction_tool`: Categorical micro-agent for semantic ODD matching
  
**Key Features:**
- **Artifact-Based Handoff**: Reliable inter-agent data transfer via InMemoryArtifactService
- **ODD-Schema Driven**: Agents adapt to any ODD structure (ground robots, drones, etc.)
- **Categorical Micro-Agent**: Semantic matching ("indoor_commercial" ≈ "office")
- **Data Source Detection**: Automatic sim vs real identification from visual cues

### Multi-Modal Sensor Fusion

| Sensor | What We Extract | Why It Matters |
|--------|----------------|----------------|
| 📷 **Camera** | Environment type, lighting, obstacles | "Is this the indoor office we designed for?" |
| 📡 **LiDAR** | Terrain roughness, traversability, density | "Can the robot physically navigate this space?" |
| 🎯 **IMU** | Acceleration, rotation, platform stability | "Is the robot actually moving? Is it stable?" |

**Smart Fusion:** AI agents combine all three to make holistic safety judgments.

---

## 🔬 Key Features

### 1. Natural Language ODD Specification

Define safety constraints in plain English - AI converts to formal specification:

```python
odd_description = """
Quadruped robot designed for indoor office navigation.
- Designed for: smooth floors, bright/dim lighting, low obstacles
- Prohibited: outdoor, stairs, dark environments, dense clutter
- Speed limit: 0-1.5 m/s
- Collision risk threshold: <0.3 (low risk only)
"""
```

### 2. Real-World Performance

**Current Status:** Phase 1.4.2 Complete (Three-Tier Intelligence Architecture)

**Latest Features (Nov 2025):**
- ✅ **ODD-Schema Driven** - Agents adapt to any robot domain (tested: ground robots + drones)
- ✅ **Dynamic COD Mapping** - Measurements auto-align with ODD dimensions
- ✅ **Three-Tier Intelligence** - Tool agents (grounded) → Loop agents (temporal) → Summary agents (structural)
- ✅ **Flexible Observations** - Rich narrative + quantitative metrics
- ✅ **Intelligent ODD Filtering** - Loop agents decide what's relevant, not hardcoded rules
- ✅ **Sensor Anomaly Detection** - Automatically flags sparse LiDAR, IMU drift, etc.
- ✅ **Multimodal Collision Detection** - IMU + camera + BEV fusion with LLM reasoning

**Production Data:**
- 📊 **62 windows** sim_1_0 production dataset + 6 test windows
- 🏭 **Auto-cropped BEVs** - 65-72% size reduction with square aspect ratio
- ✅ **3-channel BEV fusion** - Occupancy, Height, Roughness (ground-filtered)
- 📦 **Latest Data**: sim_1_0_v1 with transformed BEVs

**Test Results:**
- ⏱️ **6 minutes** for 2-window analysis (sim_test_w010_w011)
- 💰 **$2.08** total cost ($1.04/window)
- 🎯 **9/9 agents** executed successfully
- 📊 **104K tokens** with rich observations and cross-window reasoning

**Test Data Analysis:**
- 📝 **6 test scenarios** (sim_test_w010_w011, plus production scenarios)
- ⚡ **2-window quick tests** + 62-window full production dataset
- 🤖 **Validated agents**: Perception (3 BEV), Motion (IMU+camera), Collision (binary detection)

### 3. Interactive HTML Reports

**Professional Analysis Reports** with:
- 📊 **Visual summaries** - ODD status, violation counts, key metrics
- 🖼️ **Embedded images** - All BEV LiDAR and camera frames
- 📥 **JSON downloads** - Raw analysis data for custom processing
- 🔗 **GitHub Pages** - Deployed reports at [danmartinez78.github.io/go2-odd-observer](https://danmartinez78.github.io/go2-odd-observer/)
- 📱 **Responsive design** - View on desktop, tablet, or mobile

**Batch Generation:**
```bash
python scripts/generate_all_test_reports.py  # All 7 test scenarios
python scripts/generate_html_report.py --input ... --output ...  # Single report
```

### 4. Cost-Optimized Execution

| Agent Type | Model | Cost |
|------------|-------|------|
| Vision Analysis (Perception, Collision) | gemini-2.5-pro | Baseline |
| Motion & Synthesis | gemini-2.5-flash | **~50% cheaper** |

**Scalable Analysis:**
- 2-window test: ~$0.02 per scenario
- 25-window production: ~$0.15 per chunk
- 332-window full dataset: ~$2.00 total

📊 **Details:** [docs/MODEL_SELECTION_GUIDE.md](docs/MODEL_SELECTION_GUIDE.md)

---

## 📊 Example Results

🌐 **Live Interactive Reports:** [https://danmartinez78.github.io/go2-odd-observer/](https://danmartinez78.github.io/go2-odd-observer/)

### Production Scenario: Living Room Navigation (25 Windows)

**Dataset:** `collection_20251122_173442_chunk_01` - Real Unitree Go2 in indoor living room

### ODD Compliance Analysis

```
Overall Status: OUT_ODD
Windows Analyzed: 25
Violations: 3

❌ VIOLATIONS:
   • motion_smoothness: "abrupt" (all 25 windows)
     → Consistent jerky motion patterns across entire scenario
   
   • max_accel_mps2: 8.81 m/s² (limit: 5.0)
     → Extreme acceleration detected, exceeds safe threshold
   
   • collision_risk: 0.652 average (threshold: 0.5)
     → 18 high/critical collision events detected

🔍 SENSOR DISCREPANCY:
   • Camera detects low-lying obstacles (furniture legs, tables)
   • BEV LiDAR fails to detect same obstacles (ground filtering)
   • Risk: Undetected collision hazards in navigation path

✅ IN_ODD:
   • environment_type: indoor_living_room ✓
   • lighting_conditions: adequate ✓
   • terrain_type: smooth_floor ✓
```

### AI-Generated Executive Summary

> *"The Unitree Go2 demonstrates consistent OUT_ODD status across all 25 analysis windows due to abrupt motion patterns and high collision risk. While the indoor living room environment generally aligns with the intended operational domain, the robot exhibits motion characteristics (8.81 m/s² peak acceleration) that significantly exceed design specifications. A critical sensor fusion issue exists: the camera detects low obstacles that the BEV LiDAR system fails to identify due to ground filtering, creating undetected collision hazards."*

### Key Findings

1. 🚨 **Abrupt Motion Patterns**: All 25 windows show "abrupt" motion smoothness classification
2. ⚡ **Extreme Acceleration**: Peak of 8.81 m/s² exceeds 5.0 m/s² safety limit by 76%
3. ⚠️ **High Collision Risk**: 18 of 25 windows (72%) at alert level, avg risk 0.652
4. 🔍 **Sensor Fusion Gap**: BEV ground filtering (10cm threshold) misses low obstacles visible in camera

### Recommendations

1. **Motion Control Tuning**: Review acceleration limits and motion smoothing parameters
2. **BEV Configuration**: Adjust ground filtering threshold or cross-check with camera data
3. **Collision Avoidance**: Implement sensor fusion to reconcile camera vs LiDAR obstacle detection
4. **Path Planning**: Reduce aggressive maneuvers in cluttered indoor environments

📁 **View Full Reports:**
- 🌐 [**Interactive HTML Report**](https://danmartinez78.github.io/go2-odd-observer/reports/collection_20251122_173442_chunk_01_report.html) (51MB with all images)
- 📥 [**JSON Data**](https://danmartinez78.github.io/go2-odd-observer/reports/collection_20251122_173442_chunk_01_full_result.json) (18KB raw analysis)
- 📊 [**Test Scenarios**](https://danmartinez78.github.io/go2-odd-observer/) (7 additional reports)

---

## 🗂️ Repository Structure

```
go2-odd-observer/
├── odd_agents/              # Core AI agent module (parameterized, no global state)
│   ├── agents/              # 7 agent implementations (perception, motion, collision, etc.)
│   ├── tools/               # Agent tool functions (Gemini API wrappers)
│   └── workflow.py          # Pipeline orchestration
├── scripts/
│   ├── run_odd_analysis.py         # Interactive analysis CLI
│   ├── generate_html_report.py     # HTML report generator
│   ├── generate_all_test_reports.py # Batch processing for test scenarios
│   ├── extract_windows.py          # ROS2 bag → time windows converter
│   └── render_bev.py               # BEV LiDAR visualization
├── notebooks/
│   └── odd_analysis_demo.ipynb  # Interactive analysis with visualizations
├── tests/                   # Unit tests for each agent
├── data/
│   ├── processed/
│   │   ├── production/      # 19 production scenarios (332 windows total)
│   │   └── test_data/       # 7 test scenarios (real + sim)
│   └── analysis_results/    # JSON outputs from pipeline runs
└── docs/
    ├── guides/              # Setup, usage, patterns
    ├── reports/             # GitHub Pages HTML reports + JSON downloads
    ├── examples/            # Sample reports
    └── index.html           # GitHub Pages landing page
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [**Live Demo**](https://danmartinez78.github.io/go2-odd-observer/) | Interactive HTML reports deployed on GitHub Pages |
| [**Getting Started**](docs/guides/GETTING_STARTED.md) | Complete setup, usage examples, troubleshooting |
| [**Agent Architecture**](docs/agents/README.md) | Comprehensive documentation for all 7 agents in the pipeline |
| [**Model Selection**](docs/MODEL_SELECTION_GUIDE.md) | Cost optimization, when to use flash vs 2.5-pro |
| [**Scripts Guide**](scripts/README.md) | Extract windows, render visualizations, generate reports |
| [**Notebooks Guide**](notebooks/README.md) | Interactive analysis, visualizations, exports |
| [**Module API**](odd_agents/README.md) | Parameterized workflow API reference |

---

## 🛠️ Use Cases

### Batch Analysis of Test Scenarios

```bash
# Generate HTML reports for all test scenarios (6 real + 1 sim)
python scripts/generate_all_test_reports.py

# Reports automatically saved to:
# - JSON: data/analysis_results/automated/test_reports_TIMESTAMP/
# - HTML: docs/reports/{scenario_name}_report.html
```

### Production Data Analysis

```bash
# Run interactive CLI for scenario selection
python scripts/run_odd_analysis.py

# Or specify production scenario directly
python scripts/run_odd_analysis.py --scenario collection_20251122_173442_chunk_01

# Generate HTML report with all embedded images
python scripts/generate_html_report.py \
  --input data/analysis_results/manual/latest/full_result.json \
  --scenario-dir data/processed/production/collection_20251122_173442_chunk_01 \
  --output docs/reports/production_report.html
```

### Post-Incident Analysis

```bash
# Extract windows from incident rosbag
python scripts/extract_windows.py \
  --rosbag incident_2025_11_21.db3 \
  --output data/processed/incident_analysis

# Run analysis
python scripts/run_odd_analysis.py --scenario incident_analysis

# Generate report and check violations
python scripts/generate_html_report.py \
  --input data/analysis_results/manual/latest/full_result.json \
  --scenario-dir data/processed/incident_analysis \
  --output incident_report.html

open incident_report.html
```

### Custom ODD for Different Robots

```python
from odd_agents import run_odd_workflow
from google.genai import Client
import os

# Outdoor delivery robot ODD
outdoor_odd = """
Delivery robot for outdoor sidewalk navigation.
- Designed for: outdoor_urban, concrete/asphalt, moderate slopes
- Lighting: bright daylight to dusk (requires daylight)
- Speed: 0-3.0 m/s
- Obstacles: moderate density OK (designed for pedestrians)
- Weather: dry conditions only
"""

client = Client(api_key=os.getenv("GOOGLE_API_KEY"))
result = await run_odd_workflow(
    scenario_path="data/processed/outdoor_test",
    genai_client=client,
    api_key=os.getenv("GOOGLE_API_KEY"),
    nl_odd_description=outdoor_odd
)
```

---

## 🧪 Testing

```bash
# Test individual agents
python tests/test_perception_agent.py
python tests/test_motion_agent.py
python tests/test_collision_agent.py

# Run unit tests
pytest tests/ -v
```

---

## ⚠️ Limitations and Future Work

### Current System Limitations

**1. Fixed Window Sampling May Miss Critical Events**

**Limitation:** The current system uses **programmatic window selection** (e.g., every 5 seconds) with a single camera frame and LiDAR scan per window. This approach optimizes compute costs but may miss important transient events:

- 💡 **Sudden lighting changes** (bright room → shadow → bright) may be averaged to "moderate"
- 🚨 **Brief collision moments** occurring between sample points go undetected
- 🎯 **Near-miss events** (obstacle appears then disappears) lost in sparse sampling
- 📊 **Rapid regime changes** (clear hallway → sudden clutter) underrepresented

**Impact:** Analysis may underestimate violations or miss safety-critical moments that occur between observation windows.

**Example:**
```
60-second scenario with 5-second sampling:
✅ Captures: 12 windows (general behavior trends)
❌ Misses: Collision at t=17.3s (falls between t=15s and t=20s samples)
❌ Misses: Brief dark hallway t=32-34s (sampled at t=30s in bright room)
```

### Proposed Solution: Intelligent Data Selection Agent

**Multi-Stage Adaptive Pipeline** (Future Phase 5+):

```mermaid
graph TB
    A[Full Scenario Data] --> B[Triage Agent<br/>Low-Cost Scan]
    B --> C{Event Scoring}
    C -->|ROUTINE| D[Sparse Sampling<br/>1 per 10s]
    C -->|INTERESTING| E[Standard Sampling<br/>1 per 5s]
    C -->|CRITICAL| F[Dense Sampling<br/>1-2s + multi-frame]
    D --> G[Detail Analysis<br/>Main Pipeline]
    E --> G
    F --> G
    
    style A fill:#e3f2fd,stroke:#333,stroke-width:2px,color:#000
    style B fill:#fff9c4,stroke:#333,stroke-width:2px,color:#000
    style C fill:#ffccbc,stroke:#333,stroke-width:2px,color:#000
    style D fill:#c8e6c9,stroke:#333,stroke-width:2px,color:#000
    style E fill:#fff9c4,stroke:#333,stroke-width:2px,color:#000
    style F fill:#ffccbc,stroke:#333,stroke-width:2px,color:#000
    style G fill:#f8bbd0,stroke:#333,stroke-width:2px,color:#000
```

**Approach:**
1. **Quick Scan** (gemini-flash-lite, low-cost):
   - Downsample all camera frames to 128×128 thumbnails
   - Load full IMU time series (low token cost)
   - Generate low-res BEV overview
   
2. **Triage Classification**:
   - Detect regime changes (lighting, obstacle density, motion patterns)
   - Identify anomalies (acceleration spikes, sudden stops, near-misses)
   - Score windows: **ROUTINE** / **INTERESTING** / **CRITICAL**
   
3. **Adaptive Sampling**:
   - ROUTINE: 1 window per 10 seconds (sparse)
   - INTERESTING: 1 window per 5 seconds (current standard)
   - CRITICAL: 1-2 second cadence with multiple frames

**Expected Benefits:**
- ✅ **Better violation detection** - Don't miss transient safety events
- ⚡ **Improved compute efficiency** - Focus expensive analysis on important data
- 🎯 **Adaptive fidelity** - Match analysis depth to scenario complexity
- 📊 **Post-incident investigation** - Automatic zoom-in on anomalies

**Example Impact:**
```
60-second scenario analysis:
Current:   12 windows × $0.02 = $0.24 (may miss events)
Triage:    8 windows × $0.02 + $0.01 triage = $0.17
           ↑ 30% cost savings + better event coverage
```

**Technical Challenges:**
- Downsampling while maintaining event detectability
- Triage agent prompt design (what signals "interesting"?)
- Confidence calibration (avoiding false negatives on subtle violations)

**Timeline:** Phase 5+ or post-Kaggle capstone research project

📚 **Detailed Design:** See [TODO.md § Future Research: Intelligent Data Selection Agent](TODO.md#future-research-intelligent-data-selection-agent)

### Other Known Limitations

**2. BEV Ground Filtering Sensitivity**
- Current 10cm threshold may miss low obstacles (furniture legs, cables)
- Sensor fusion gap: Camera detects obstacles LiDAR filters out
- **Mitigation:** Phase 1.4 will add cross-validation between camera and BEV

**3. No Velocity Estimation**
- Robot odometry not available in current data
- Cannot distinguish stationary vs. slow motion
- **Planned:** Phase 2 will add visual/LiDAR odometry computation

**4. Single-Window Collision Detection**
- Thresholds checked per window (may miss gradual degradation)
- No temporal correlation between consecutive windows
- **Future:** Multi-window trend analysis for early warning

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**High-Priority Contributions:**
- 🎯 **Intelligent triage agent** - Multi-stage adaptive sampling (see above)
- 📊 Fix Plotly chart rendering in HTML reports (currently deferred)
- 🔍 BEV/camera cross-validation for ground filtering tuning
- 🏃 Visual/LiDAR odometry integration (Phase 2)

**Other Ideas:**
- 📡 Add support for new sensor modalities (GPS, ultrasonic, radar)
- 🤖 Generalize for other robot platforms (drones, warehouse AMRs, cars)
- 🎨 Interactive dashboard for batch analysis visualization
- 📈 Time-series trend analysis across multiple scenarios
- 🧪 LLM-as-judge evaluation benchmarks for agent quality

---

## 🏆 Acknowledgments

Built for the **[Kaggle 5-Day Agents Intensive](https://www.kaggle.com/learn-guide/5-day-agents)** program.

**Powered by:**
- 🧠 **Google Gemini 2.5 Pro & 2.0 Flash** - Multimodal AI models
- 🔧 **Google ADK (Agent Development Kit)** - Agent orchestration framework
- 🤖 **Unitree Go2** - Quadruped robot platform
- 🔗 **ROS2 Humble** - Robotics middleware

---

## 📄 License

MIT License - see [LICENSE](LICENSE)

---

## 📧 Contact

**Author:** Dan Martinez  
**GitHub:** [@danmartinez78](https://github.com/danmartinez78)  
**Issues:** [github.com/danmartinez78/go2-odd-observer/issues](https://github.com/danmartinez78/go2-odd-observer/issues)

---

<div align="center">

**⭐ Star this repo if you find it useful!**

[🏠 Home](https://github.com/danmartinez78/go2-odd-observer) • [📚 Docs](docs/guides/GETTING_STARTED.md) • [🐛 Issues](https://github.com/danmartinez78/go2-odd-observer/issues)

</div>
