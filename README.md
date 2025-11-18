# Go2 ODD/COD Observer

> **Operational Design Domain (ODD) and Condition of Deployment (COD) Analysis for Unitree Go2 Robot**

**Kaggle 5-Day Agents Intensive - Capstone Project**  
🏆 [Competition Details](https://www.kaggle.com/competitions/agents-intensive-capstone-project) | 📚 [Learning Path](https://www.kaggle.com/learn-guide/5-day-agents)

An AI-powered multi-modal system for analyzing Go2 robot behavior in both real and simulated environments. This project uses embodied AI agents to evaluate whether deployment scenarios align with operational design constraints, detect collisions, and measure the distance between actual operating conditions and design boundaries.

---

## Project Context

This project is developed as a capstone for the **[Kaggle 5-Day Agents Intensive](https://www.kaggle.com/learn-guide/5-day-agents)**, demonstrating practical application of AI agents to real-world robotics challenges. The focus is on building multi-modal agents that can:

1. **Process heterogeneous sensor data** (motion, camera, LiDAR) from physical robots
2. **Reason about operational safety constraints** using structured domain knowledge
3. **Provide quantitative assessments** of deployment risk through distance metrics
4. **Bridge simulation and reality** by detecting and adapting to different data sources

---

## Overview

This project implements a comprehensive framework for:

- **Defining Operational Design Domains (ODD)** in natural language
- **Analyzing real-world and simulated deployment conditions (COD)** using multi-modal AI agents
- **Computing continuous COD–ODD distance metrics** to quantify operational safety margins
- **Detecting collisions** using motion, camera, and LiDAR fusion
- **Classifying scenarios** as compliant, boundary-heavy, or ODD-violating

### Key Features

- 🤖 **Multi-Modal Agent Architecture**: Motion, Camera, LiDAR, and Collision analysis agents
- 📊 **Quantitative ODD Compliance**: Continuous distance metrics per scenario
- 🔍 **Sim vs Real Detection**: Automatic classification of data sources
- 💥 **Collision Detection**: Multi-sensor fusion for impact identification
- 📈 **Visual Analytics**: Timeline plots, distributions, and scenario reports
- 🌐 **Natural Language ODD Specification**: Convert human-readable constraints into machine specs

---

## Architecture

### Agent Workflow (Google ADK Pattern)

The system uses the **Google Agent Development Kit (ADK)** with a hierarchical agent architecture following the [Kaggle Day 1B pattern](https://www.kaggle.com/code/kaggle5daysofai/day-1b-agent-architectures):

```
┌─────────────────────────────────────────────────────────────┐
│                  Natural Language ODD Input                  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    ODD Spec Agent                           │
│              (NL → Structured JSON ODD)                     │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  ParallelAgent: Sensor Analysis Team        │
│  ┌──────────────┬──────────────┬──────────────┬─────────┐  │
│  │Motion Agent  │Vision Agent  │Terrain Agent │Collision│  │
│  │(Motion JSON) │(Camera PNG)  │(LiDAR BEV)   │Agent    │  │
│  └──────────────┴──────────────┴──────────────┴─────────┘  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  COD Evaluator Agent                         │
│        (Aggregates features + computes distances)           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   Report Generation Agent                    │
│          (Markdown report + visualization tools)            │
└─────────────────────────────────────────────────────────────┘
                              ↓
                    Final Analysis Report
```

**Key Components:**
- **SequentialAgent**: Orchestrates the overall workflow (ODD Spec → Parallel Analysis → Evaluation → Report)
- **ParallelAgent**: Runs sensor analysis agents simultaneously for each window
- **InMemoryRunner**: Executes the agent workflow with session state management
- **Tool Functions**: Python utilities for file I/O, COD math, and visualizations

### Data Flow

```
ROS2 Bag Files (Go2 Robot)
         ↓
   Window Extraction (Local Script)
    ├─ Motion JSON (velocity, IMU, odometry)
    ├─ Camera PNG (RGB snapshot)
    └─ LiDAR BEV PNGs (4-channel: occupancy, height, density, roughness)
         ↓
   Upload to Kaggle Dataset
         ↓
   ADK Agent Workflow (Jupyter Notebook)
    ├─ ODD Spec Agent (NL → JSON)
    ├─ ParallelAgent (Motion + Vision + Terrain + Collision)
    ├─ COD Evaluator Agent (feature aggregation + distance computation)
    └─ Report Agent (markdown + visualizations)
         ↓
   Analysis Results
    ├─ Per-window ODD compliance status
    ├─ Scenario-level COD distance metrics
    ├─ Collision detection reports
    └─ Visual timelines and distributions
```

### ODD Axes

The system evaluates scenarios across multiple dimensions:

- **Speed**: Forward velocity (m/s)
- **Roll/Pitch**: Vehicle orientation (degrees)
- **Terrain**: Surface classification (smooth/moderate/rough/very_rough)
- **Lighting**: Visual conditions (bright/dim/dark)
- **Human Proximity**: Distance to people (none/visible_far/very_close)
- **Collisions**: Impact detection (yes/no)
- **Domain**: Sim vs Real (metadata tag)

---

## Repository Structure

```
go2-odd-observer/
├── .devcontainer/             # ROS2 Humble dev container config
│   ├── devcontainer.json
│   ├── Dockerfile
│   ├── post-create.sh
│   └── README.md
├── data/
│   ├── raw_rosbags/           # ROS2 bag files (gitignored)
│   └── processed/
│       ├── runs/              # Per-run window data
│       │   ├── run_001/
│       │   │   ├── motion_run_001_w000.json
│       │   │   ├── cam_run_001_w000.png
│       │   │   ├── bev_occupancy_run_001_w000.png
│       │   │   ├── bev_height_run_001_w000.png
│       │   │   ├── bev_density_run_001_w000.png
│       │   │   ├── bev_roughness_run_001_w000.png
│       │   │   └── index_run_001.csv
│       │   └── run_002/
│       └── manifest.csv       # Run metadata (sim/real tags)
├── docs/
│   └── images/                # Example outputs for documentation
├── scripts/
│   ├── extract_windows.py     # ROS2 bag → multi-modal time windows
│   ├── generate_demo_data.py  # Generate synthetic demo data
│   ├── demo_pipeline_local.py # Local testing with fake agents
│   ├── render_bev.py          # Standalone BEV renderer (deprecated)
│   └── utils_ros.py           # ROS2 utilities
├── notebooks/
│   ├── odd_cod_workflow.ipynb # Complete analysis workflow notebook
│   └── README.md              # Notebook documentation
├── odd_cod/
│   ├── __init__.py
│   ├── odd_spec_schema.py     # ODD schema definitions
│   ├── cod_features.py        # COD numeric mappings
│   ├── distance_metrics.py    # Distance computation
│   └── config_example.py      # Example ODD specifications
├── tests/
│   └── test_distance_metrics.py
├── LICENSE
├── README.md
├── requirements.txt
├── project_plan.md
└── .gitignore
```

---

## Getting Started

### Prerequisites

- Docker and VS Code with Dev Containers extension
- ROS2 bag files from Unitree Go2 robot (sim or real)
- Google Gemini API key (get free at https://aistudio.google.com/app/apikey)
- Kaggle account for running the agent workflow notebook

### Installation

```bash
# Clone the repository
git clone https://github.com/danmartinez78/go2-odd-observer.git
cd go2-odd-observer

# Open in VS Code Dev Container
# VS Code will automatically build the ROS2 Humble container
# All dependencies (ROS2, Python packages) are pre-configured
```

### Quick Start with Jupyter Notebook

The complete AI-powered workflow is in the interactive Jupyter notebook using Google ADK agents.

**⚠️ Prerequisites**: 
- Google Gemini API key (get free at https://aistudio.google.com/apikey)
- Jupyter notebook environment (or Kaggle)

#### Using Demo Data (No ROS2 bags required)

```bash
# 1. Generate synthetic demo data
python3 scripts/generate_demo_data.py

# 2. Set your API key
echo "GOOGLE_API_KEY=your_api_key_here" > .env

# 3. Open the agent workflow notebook
jupyter notebook notebooks/odd_cod_workflow.ipynb

# 4. Follow the notebook sections:
# - Section 1: Install google-adk package
# - Section 2: Load API key from .env
# - Section 3: Define your ODD in natural language
# - Section 4-7: Run the complete ADK agent workflow
```

#### Using Your Own ROS2 Bag Data

```bash
# 1. Extract windows from your ROS bag
python3 scripts/extract_windows.py \
  --rosbag data/raw_rosbags/your_run.db3 \
  --output data/processed/runs/run_001 \
  --run-id run_001

# 2. Open the notebook and point to your data
jupyter notebook notebooks/odd_cod_workflow.ipynb
```

See [notebooks/README.md](notebooks/README.md) for detailed instructions.

### Basic Workflow

#### 1. Extract Windows from ROS Bags

Process ROS2 bag files into time-windowed multi-modal snapshots:

```bash
# Source ROS2 environment (required in dev container)
source /opt/ros/humble/setup.bash

# Extract windows with multi-channel BEV rendering
python3 scripts/extract_windows.py \
  --rosbag data/raw_rosbags/sim/1/sim_data_0.db3 \
  --output data/processed/runs/run_001 \
  --run-id run_001 \
  --window-length 2.0 \
  --stride 1.0
```

This generates:
- **Motion data (JSON)**: Velocity, IMU (roll/pitch/yaw), odometry, accelerations
- **Camera frames (PNG)**: RGB snapshots at 1280x720
- **Multi-channel LiDAR BEV (4 PNGs per window)**:
  - `bev_occupancy_*.png`: Binary presence grid
  - `bev_height_*.png`: Elevation map (±2m range)
  - `bev_density_*.png`: Measurement density/confidence
  - `bev_roughness_*.png`: Terrain roughness (height variance)
- **Index CSV**: Window metadata with paths to all modalities

#### 2. Define Your ODD

Create a natural language ODD specification using the Python library:

```python
from odd_cod.odd_spec_schema import OddSpec, AxisSpecNumeric, AxisSpecCategorical

odd_spec = OddSpec(
    version="1.0",
    axes={
        "speed": AxisSpecNumeric(
            feature="forward_velocity",
            units="m/s",
            in_odd=[0.0, 1.5],
            near_boundary=[0.0, 1.8],
            hard_limit=[0.0, 2.0]
        ),
        "terrain": AxisSpecCategorical(
            feature="terrain_type",
            allowed_in_odd=["smooth", "moderate"],
            allowed_all=["smooth", "moderate", "rough", "very_rough"]
        )
    },
    importance={"speed": 1.0, "terrain": 0.8}
)
```

#### 3. Run Agent Workflow (Kaggle/Jupyter)

Execute the complete ADK agent workflow in the Jupyter notebook:

```python
from google.adk.runners import InMemoryRunner

# The notebook orchestrates:
# 1. ODD Spec Agent: Convert NL ODD → structured JSON
# 2. ParallelAgent: Run Motion + Vision + Terrain + Collision simultaneously
# 3. COD Evaluator: Aggregate features + compute distances (Python tools)
# 4. Report Agent: Generate markdown report with visualizations

runner = InMemoryRunner()
result = await runner.run_debug(
    agent=workflow,  # SequentialAgent defined in Section 6
    inputs={"user_input": nl_odd_description}
)

# Access results from session state
final_report = result.session_state.get("final_report")
print(final_report)
```

See [notebooks/odd_cod_workflow.ipynb](notebooks/odd_cod_workflow.ipynb) for the complete interactive workflow.

**⚠️ Required**: Set `GOOGLE_API_KEY` environment variable before running (no demo mode available).

#### 4. Review Results

The system produces:
- **Per-window classifications**: `in-ODD`, `near-boundary`, `ODD-exit`
- **Scenario distance scores**: Quantified compliance (0 = perfect, 1 = maximum violation)
- **COD profiles**: Statistical distributions across all axes
- **Visual timelines**: Status changes and critical events
- **Collision reports**: Detected impacts with context

---

## Window Structure

Each time window captures a multi-modal snapshot:

### Motion JSON (`motion_run_XXX_wNNN.json`)
```json
{
  "timestamps": [0.0, 0.1, 0.2, ...],
  "cmd_vx": [0.5, 0.52, 0.48, ...],
  "cmd_wz": [0.0, 0.1, 0.0, ...],
  "odom_vx": [0.48, 0.51, 0.47, ...],
  "odom_wz": [0.02, 0.11, 0.01, ...],
  "roll": [0.1, 0.2, 0.15, ...],
  "pitch": [1.2, 1.3, 1.25, ...],
  "yaw": [45.0, 45.2, 45.1, ...],
  "accel_x": [0.1, 0.12, 0.08, ...],
  "accel_y": [0.02, 0.01, 0.03, ...],
  "accel_z": [9.81, 9.82, 9.80, ...]
}
```

### Camera Image (`cam_run_XXX_wNNN.png`)
RGB snapshot from `/robot0/front_cam/rgb` at 1280x720 resolution.

![Example Camera Frame](docs/images/example_camera.png)

*Note: Simulation rosbags may contain placeholder camera data. Real robot deployments capture actual RGB frames.*

### Multi-Channel LiDAR BEV Images

The system generates **4 separate Bird's Eye View (BEV) feature images** per window, each encoding different terrain characteristics from the LiDAR point cloud:

#### 1. Occupancy (`bev_occupancy_run_XXX_wNNN.png`)
Binary presence grid showing where measurements exist (400x400, 5cm/pixel, ±10m range).

![BEV Occupancy](docs/images/example_bev_occupancy.png)

#### 2. Height (`bev_height_run_XXX_wNNN.png`)
Average elevation per cell, normalized from ±2m range to 0-255 grayscale values.

![BEV Height](docs/images/example_bev_height.png)

#### 3. Density (`bev_density_run_XXX_wNNN.png`)
Point cloud measurement density per cell, indicating measurement confidence/concentration.

![BEV Density](docs/images/example_bev_density.png)

#### 4. Roughness (`bev_roughness_run_XXX_wNNN.png`)
Terrain roughness computed from height variance (std dev) within each cell.

![BEV Roughness](docs/images/example_bev_roughness.png)

**Multi-Channel BEV Design**: Separate feature images enable multi-modal vision models (e.g., Google Gemini 2.5 Flash) to independently reason about different terrain characteristics through multi-image prompting, improving terrain classification accuracy over single-channel encodings.

---

## Distance Metrics

### Window-Level Distance

For each window, the distance from ODD is computed as:

```python
distance = Σ(w_i * d_i) / Σ(w_i)
```

Where:
- `w_i` = importance weight for axis `i`
- `d_i` = normalized distance from ODD center/bounds for axis `i`

### Scenario-Level Distance

Aggregates window distances with:
- Mean window distance
- Fraction of ODD-exit windows
- Weighted penalties for violations

### Interpretation

- **0.0**: Perfect ODD compliance
- **0.0-0.3**: Within ODD
- **0.3-0.7**: Near boundary
- **0.7-1.0**: ODD violation

---

## Collision Detection

### Pre-Filtering

Candidate windows identified by:
- Large deceleration/jerk
- IMU acceleration spikes
- Command-odometry tracking failures

### Multi-Modal Analysis

The Collision Agent evaluates:
- **Motion**: Sudden velocity changes, impact signatures
- **Camera**: Visual obstacles, contact points
- **LiDAR**: Geometric proximity, surface interactions

### Output
```json
{
  "collision_suspected": true,
  "collision_confidence": 0.87,
  "collision_type": "front_bump",
  "notes": "Rapid deceleration and IMU spike with visible wall contact"
}
```

---

## Sim vs Real Detection

### Data Source Agent

Automatically classifies scenarios using:

1. **Ground Truth**: `manifest.csv` annotations
2. **Heuristics**:
   - Perfect tracking (cmd_vel ≈ odom_vel) → sim
   - Low sensor noise → sim
   - Sim-specific topic names/frame_ids

### Usage

This enables:
- Comparing ODD compliance across environments
- Identifying sim-to-real transfer gaps
- Validating simulation fidelity

---

## Example ODD Specification

```python
from odd_cod.odd_spec_schema import OddSpec, AxisSpecNumeric, AxisSpecCategorical

odd_spec = OddSpec(
    version="1.0",
    axes={
        "speed": AxisSpecNumeric(
            feature="forward_velocity",
            units="m/s",
            in_odd=[0.0, 1.5],
            near_boundary=[0.0, 1.8],
            hard_limit=[0.0, 2.0]
        ),
        "terrain": AxisSpecCategorical(
            feature="terrain_type",
            allowed_in_odd=["smooth", "moderate"],
            allowed_all=["smooth", "moderate", "rough", "very_rough"]
        ),
        "lighting": AxisSpecCategorical(
            feature="lighting_condition",
            allowed_in_odd=["bright", "dim"],
            allowed_all=["bright", "dim", "dark"]
        )
    },
    importance={
        "speed": 1.0,
        "terrain": 0.8,
        "lighting": 0.5
    }
)
```

---

## Agent Architecture Details

### Specialist Agents (Google ADK)

Each agent is an instance of `google.adk.agents.Agent` with a specific role:

1. **ODD Spec Agent**
   - **Input**: Natural language ODD description
   - **Output**: Structured JSON matching `OddSpec` schema
   - **Model**: Gemini 2.0 Flash with JSON mode

2. **Motion Analysis Agent**
   - **Input**: Motion JSON (velocity, IMU, odometry time series)
   - **Output**: `{avg_forward_speed, max_forward_speed, max_abs_roll_pitch_deg, tracking_error, motion_label}`
   - **Purpose**: Extract motion features for ODD compliance checking

3. **Vision Analysis Agent**
   - **Input**: Camera PNG image
   - **Output**: `{lighting_class, humans_visible, humans_very_close, environment_type}`
   - **Purpose**: Classify environmental conditions from visual data

4. **Terrain Analysis Agent**
   - **Input**: LiDAR BEV PNG images (4 channels)
   - **Output**: `{terrain_roughness_class, terrain_roughness_score, obstacle_density}`
   - **Purpose**: Analyze terrain from multi-channel Bird's Eye View

5. **Collision Detection Agent**
   - **Input**: Motion features + Camera PNG + LiDAR BEV PNGs (multi-modal fusion)
   - **Output**: `{collision_suspected, collision_confidence, collision_type}`
   - **Purpose**: Detect collision events using sensor fusion

6. **COD Evaluator Agent**
   - **Input**: Merged features from sensor agents + ODD spec JSON
   - **Output**: `{merged_features, odd_violations, overall_status}`
   - **Purpose**: Aggregate results and identify ODD violations
   - **Tools**: Uses Python functions for COD vector building and distance computation

7. **Report Generation Agent**
   - **Input**: ODD spec + COD evaluation results + window analyses
   - **Output**: Markdown report with findings and recommendations
   - **Tools**: Uses Python visualization functions (distance plots, status distributions)

### Orchestration Pattern

The workflow uses **hierarchical agent composition** from the ADK:

```python
# Parallel sensor analysis team
sensor_team = ParallelAgent(
    name="SensorAnalysisTeam",
    agents=[motion_agent, vision_agent, terrain_agent, collision_agent]
)

# Sequential workflow orchestration
workflow = SequentialAgent(
    name="ODDAnalysisWorkflow",
    agents=[
        odd_spec_agent,      # Step 1: Parse ODD
        sensor_team,         # Step 2: Analyze sensors (parallel)
        cod_evaluator,       # Step 3: Evaluate compliance
        report_generator     # Step 4: Generate report
    ]
)

# Execute with InMemoryRunner
runner = InMemoryRunner()
result = await runner.run_debug(
    agent=workflow,
    inputs={"user_input": nl_odd_description}
)
```

**Key Benefits:**
- Agents pass data via `output_key` session state (no manual orchestration code)
- Parallel execution for independent sensor analyses
- Sequential composition ensures proper data dependencies
- Clean separation of AI reasoning (agents) and math/tools (Python functions)

---

## Development Roadmap

### Phase 1: Local Preprocessing ✅
- [x] Window extraction from ROS bags
- [x] Multi-channel BEV rendering (occupancy, height, density, roughness)
- [x] ROS2 message deserialization (Image, PointCloud2, Odometry, IMU)
- [x] Time-synchronized multi-modal data extraction
- [x] Manifest management
- [x] Demo data generator

### Phase 2: Core Python Library ✅
- [x] ODD schema
- [x] COD feature mappings
- [x] Distance metrics
- [x] Unit tests

### Phase 3: Agent Architecture ✅
- [x] Google ADK integration
- [x] Specialist agent definitions (ODD Spec, Motion, Vision, Terrain, Collision, COD Evaluator, Report)
- [x] ParallelAgent for sensor analysis team
- [x] SequentialAgent for workflow orchestration
- [x] InMemoryRunner execution pattern
- [x] Tool functions (file I/O, COD computation, visualization)
- [x] Complete Jupyter notebook workflow

### Phase 4: Testing & Validation (In Progress)
- [ ] End-to-end testing with demo data
- [ ] Validation with real ROS2 bag data
- [ ] Agent prompt optimization
- [ ] Error handling and edge cases

### Phase 5: Analytics & Visualization (Planned)
- [ ] Enhanced timeline visualizations
- [ ] Interactive dashboards
- [ ] Scenario comparison tools
- [ ] Real vs sim transfer analysis
- [ ] Automated report generation improvements

### Phase 6: Production Deployment (Planned)
- [ ] Kaggle dataset publishing
- [ ] Batch processing pipeline
- [ ] Results caching and incremental updates
- [ ] Multi-run comparative analysis

---

## ROS2 Topics

The system expects the following topics in your rosbag files:

| Topic | Type | Usage |
|-------|------|-------|
| `/robot0/cmd_vel` | `geometry_msgs/Twist` | Command velocities |
| `/robot0/odom` | `nav_msgs/Odometry` | Wheel odometry |
| `/robot0/imu` | `sensor_msgs/Imu` | Inertial measurements |
| `/robot0/joint_states` | `sensor_msgs/JointState` | Joint positions |
| `/robot0/front_cam/rgb` | `sensor_msgs/Image` | RGB camera |
| `/robot0/point_cloud2_L1` | `sensor_msgs/PointCloud2` | LiDAR scan |

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Citation

If you use this work in your research, please cite:

```bibtex
@software{go2_odd_observer,
  author = {Martinez, Dan},
  title = {Go2 ODD/COD Observer: Multi-Modal Operational Domain Analysis for Embodied AI},
  year = {2025},
  url = {https://github.com/danmartinez78/go2-odd-observer}
}
```

---

## Acknowledgments

- **Kaggle 5-Day Agents Intensive Program** for inspiring this capstone project
- Unitree Go2 robot platform
- Google Gemini AI for multi-modal analysis
- ROS2 ecosystem

---

## Contact

**Dan Martinez**  
GitHub: [@danmartinez78](https://github.com/danmartinez78)

For questions, issues, or collaboration opportunities, please open an issue on GitHub.
