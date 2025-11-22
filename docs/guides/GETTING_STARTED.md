# 🚀 Getting Started with Go2 ODD Observer

This guide walks you through setting up and running the ODD/COD analysis system, from installation to analyzing your first robot scenario.

---

## 📋 Prerequisites

### Required
- **Python 3.10+** (tested on Python 3.10 with Ubuntu 22.04)
- **Google Gemini API Key** - Get yours at [Google AI Studio](https://aistudio.google.com/app/apikey)
  - Free tier includes 15 requests/minute
  - 1,500 free requests per day
  - More than enough for development and testing

### Optional (for ROS2 data processing)
- **ROS2 Humble** - Required only if processing new rosbag files
- **Unitree Go2 Robot** - For collecting real-world data (use provided datasets otherwise)

---

## 🔧 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/danmartinez78/go2-odd-observer.git
cd go2-odd-observer
```

### 2. Install Python Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

**Core dependencies installed:**
- `google-genai` (Google ADK for AI agents)
- `python-dotenv` (environment variable management)
- `pandas`, `numpy` (data processing)
- `matplotlib`, `seaborn` (visualization)
- `Pillow` (image handling)

### 3. Configure API Key

**Option A: Environment Variable (Recommended)**
```bash
export GOOGLE_API_KEY="your-api-key-here"
```

**Option B: .env File**
```bash
echo "GOOGLE_API_KEY=your-api-key-here" > .env
```

**Option C: Direct in Code**
```python
import os
os.environ["GOOGLE_API_KEY"] = "your-api-key-here"
```

---

## 🎯 Quick Start: Run Your First Analysis

### Option 1: Full Pipeline (Command Line)

```bash
# Set up API key in .env file (one time setup)
echo "GOOGLE_API_KEY=your-api-key-here" > .env

# Run the complete 10-agent workflow on the test dataset
python scripts/odd_workflow.py

# Output: data/processed/runs/sim_run_test/odd_analysis_report.json
```

**What this does:**
- Analyzes 2 time windows (demo dataset for fast execution)
- Runs 10 agents: ODD spec → perception → motion → collision → COD → compliance → report
- Uses parameterized architecture with no global state
- Generates comprehensive JSON report with findings

**Expected runtime:** 30-60 seconds (depends on API rate limits)

**For larger dataset:**
```python
# Edit scripts/odd_workflow.py, change:
SCENARIO_PATH = DATA_DIR / "sim_run_new"  # 13 windows, ~3 minutes
```

### Option 2: Interactive Notebook

```bash
# Launch Jupyter
jupyter notebook notebooks/odd_analysis_demo.ipynb
```

**Notebook features:**
- Complete workflow with model configuration
- Step-by-step walkthrough with visualizations
- Per-agent model selection for cost optimization
- Real-time result inspection
- Export capabilities for reports

---

## 📊 Understanding the Output

### Generated Report Structure

```json
{
  "report": {
    "executive_summary": "2-3 sentence scenario overview",
    "scenario_metadata": {
      "total_windows_analyzed": 13,
      "scenario_path": "data/processed/runs/sim_run_new"
    },
    "key_findings": [
      "Robot remained stationary due to obstacles",
      "8 windows with alert-level collision risk",
      "Obstacle density exceeded ODD limits"
    ],
    "recommendations": [
      "Review obstacle detection thresholds",
      "Consider expanding ODD for cluttered environments"
    ]
  },
  "full_analysis": {
    "perception": { /* environment classification data */ },
    "motion": { /* speed and orientation data */ },
    "collision": { /* risk assessment data */ },
    "odd_spec": { /* domain classification */ },
    "odd_compliance": {
      "odd_compliance": {
        "categorical_compliance": {
          "environment_type": "IN_ODD",
          "lighting_conditions": "OUT_ODD",
          "terrain_type": "IN_ODD"
        },
        "numeric_compliance": {
          "speed_range": "IN_ODD",
          "obstacle_density": "OUT_ODD",
          "traversability": "OUT_ODD",
          "collision_risk": "OUT_ODD"
        },
        "overall_compliance": "OUT_ODD",
        "violations": [
          "lighting_conditions",
          "obstacle_density",
          "traversability",
          "collision_risk"
        ]
      }
    }
  }
}
```

### Key Metrics Explained

**Compliance States:**
- `IN_ODD`: Conditions within design parameters ✅
- `ODD_BOUNDARY`: Near safety limits ⚠️
- `OUT_ODD`: Exceeds operational envelope ❌

**Risk Levels (Collision):**
- `safe`: Low collision likelihood (score < 0.3)
- `caution`: Moderate risk (score 0.3-0.7)
- `alert`: High risk requiring intervention (score > 0.7)

---

## 🔍 Example Use Cases

### Use Case 1: Validate New Deployment Environment

```bash
# Process your rosbag data
python scripts/extract_windows.py \
  --rosbag data/raw_rosbags/real/new_office.db3 \
  --output data/processed/runs/office_test \
  --run-id office_test \
  --window-length 2.0

# Run analysis
# Edit scripts/odd_workflow.py first: SCENARIO_PATH = DATA_DIR / "office_test"
python scripts/odd_workflow.py

# Review compliance in report
jq '.full_analysis.odd_compliance.odd_compliance' data/processed/runs/office_test/odd_analysis_report.json
```

**Outcome:** Know immediately if the new environment is safe for deployment.

### Use Case 2: Compare Sim vs Real Performance

```bash
# Analyze simulation run
# Edit scripts/odd_workflow.py: SCENARIO_PATH = DATA_DIR / "sim_run_new"
python scripts/odd_workflow.py
cp data/processed/runs/sim_run_new/odd_analysis_report.json reports/sim_baseline.json

# Analyze real-world run
# Edit scripts/odd_workflow.py: SCENARIO_PATH = DATA_DIR / "real_run_001"
python scripts/odd_workflow.py
cp data/processed/runs/real_run_001/odd_analysis_report.json reports/real_deployment.json

# Compare compliance
diff <(jq '.full_analysis.odd_compliance' reports/sim_baseline.json) \
     <(jq '.full_analysis.odd_compliance' reports/real_deployment.json)
```

**Outcome:** Identify sim-to-real transfer gaps.

### Use Case 3: Post-Incident Analysis

```bash
# Extract windows around incident timestamp
python scripts/extract_windows.py \
  --rosbag data/raw_rosbags/real/incident_2025_11_21.db3 \
  --output data/processed/runs/incident_analysis \
  --run-id incident_analysis

# Run analysis (edit scripts/odd_workflow.py: SCENARIO_PATH = DATA_DIR / "incident_analysis")
python scripts/odd_workflow.py

# Examine collision events
jq '.full_analysis.collision.collision_events[] | select(.risk_level == "alert")' \
   data/processed/runs/incident_analysis/odd_analysis_report.json
```

**Outcome:** Root cause analysis with multi-modal evidence.

---

## 🛠️ Processing Your Own Data

### Step 1: Prepare ROS2 Bag Files

Ensure your rosbag contains these topics:

| Topic | Type | Purpose |
|-------|------|---------|
| `/robot0/cmd_vel` | `geometry_msgs/Twist` | Command velocities |
| `/robot0/odom` | `nav_msgs/Odometry` | Wheel odometry |
| `/robot0/imu` | `sensor_msgs/Imu` | Inertial measurements |
| `/robot0/front_cam/rgb` | `sensor_msgs/Image` | RGB camera |
| `/robot0/point_cloud2_L1` | `sensor_msgs/PointCloud2` | LiDAR scan |

### Step 2: Extract Windows

```bash
# Source ROS2 environment
source /opt/ros/humble/setup.bash

# Extract with default parameters (2-second windows, 1-second stride)
python3 scripts/extract_windows.py \
  --rosbag /path/to/your/bag.db3 \
  --output data/processed/runs/my_scenario \
  --run-id my_scenario

# Custom parameters for different analysis granularity
python3 scripts/extract_windows.py \
  --rosbag /path/to/your/bag.db3 \
  --output data/processed/runs/my_scenario \
  --run-id my_scenario \
  --window-length 5.0 \     # Longer windows for smoother metrics
  --stride 2.5              # Less overlap = faster processing
```

**Output structure:**
```
data/processed/runs/my_scenario/
├── index_my_scenario.csv             # Window metadata
├── motion_my_scenario_w000.json      # Motion data window 0
├── motion_my_scenario_w001.json
├── cam_my_scenario_w000.png          # Camera frame window 0
├── cam_my_scenario_w001.png
├── bev_occupancy_my_scenario_w000.png  # LiDAR BEV window 0
├── bev_occupancy_my_scenario_w001.png
└── ...
```

### Step 3: Update Manifest

Edit `data/processed/manifest.csv`:
```csv
scenario_id,is_sim,notes,timestamp
my_scenario,false,"Office deployment test",2025-11-21T10:30:00
```

### Step 4: Run Analysis

Edit `scripts/odd_workflow.py`:
```python
# Change this line (around line 17)
SCENARIO_PATH = DATA_DIR / "my_scenario"  # Your scenario name
```

Then run:
```bash
python scripts/odd_workflow.py
```

---

## 📈 Monitoring and Debugging

### Check Agent Progress

The workflow prints detailed status:
```
================================================================================
ODD WORKFLOW - FULL PIPELINE
Scenario: sim_run_new
================================================================================

=== PerceptionLoopAgent ===
Processing window 000... ✓
Processing window 001... ✓
...

=== PerceptionSummaryAgent ===
Environment classified: indoor_office (95% confidence) ✓

=== MotionLoopAgent ===
...
```

### Validate Data Quality

```bash
# Check window extraction completeness
python -c "
import pandas as pd
df = pd.read_csv('data/processed/runs/my_scenario/index_my_scenario.csv')
print(f'Total windows: {len(df)}')
print(f'Time span: {df.end_time.max():.1f} seconds')
"

# Verify image files exist
ls -lh data/processed/runs/my_scenario/*.png | wc -l
```

### Common Issues

**Issue: "No module named 'google.genai'"**
```bash
# Solution: Install ADK
pip install google-genai
```

**Issue: "API key not found"**
```bash
# Solution: Create .env file
echo "GOOGLE_API_KEY=your-key" > .env
# Or set environment variable
export GOOGLE_API_KEY="your-key"
# Verify
echo $GOOGLE_API_KEY
```

**Issue: "Rate limit exceeded"**
```bash
# Solution: Add delays between windows
# Edit odd_agents/tools/perception.py (or motion.py, collision.py)
import asyncio
await asyncio.sleep(1.0)  # Add before Gemini API call in tool function
```

**Issue: "Motion data incomplete"**
```bash
# Check ROS2 topic availability
ros2 bag info your_bag.db3 | grep -E 'cmd_vel|odom|imu'

# Solution: Adjust topic names in extract_windows.py if needed
```

---

## 🎓 Next Steps

### Learn the Codebase

1. **Read the architecture docs**: `docs/MODEL_SELECTION_GUIDE.md`
2. **Study the module structure**: `odd_agents/` (tools, agents, workflow)
3. **Understand individual agents**: `tests/test_*_agent.py`
4. **Review the workflow**: `scripts/odd_workflow.py` and `odd_agents/workflow.py`
5. **Explore visualizations**: `notebooks/odd_analysis_demo.ipynb`

### Customize for Your Robot

1. **Adjust ODD specification**: Pass custom `nl_odd_description` to `run_odd_workflow()`
2. **Add new axes**: Extend agents in `odd_agents/agents/` for custom metrics
3. **Tune thresholds**: Modify compliance logic in `odd_agents/agents/compliance.py`
4. **Add visualizations**: Extend `odd_analysis_demo.ipynb` with domain-specific plots
5. **Optimize costs**: Configure per-agent models in workflow call (see MODEL_SELECTION_GUIDE.md)

### Contribute

- Star the repo: [github.com/danmartinez78/go2-odd-observer](https://github.com/danmartinez78/go2-odd-observer)
- Report issues: [Open an issue](https://github.com/danmartinez78/go2-odd-observer/issues)
- Submit improvements: [Create a pull request](https://github.com/danmartinez78/go2-odd-observer/pulls)

---

## 📚 Additional Resources

- **Google ADK Docs**: [google.github.io/generative-ai-python](https://google.github.io/generative-ai-python)
- **Kaggle Agents Course**: [kaggle.com/learn-guide/5-day-agents](https://www.kaggle.com/learn-guide/5-day-agents)
- **ROS2 Humble**: [docs.ros.org/en/humble](https://docs.ros.org/en/humble)
- **Unitree Go2**: [unitree.com/go2](https://www.unitree.com/go2)

---

## 💬 Getting Help

**Questions?** Open an issue on GitHub with:
- Your Python version: `python --version`
- Installed packages: `pip freeze`
- Error messages (full traceback)
- Steps to reproduce

**Collaborations?** Reach out via GitHub discussions or email (see main README).

---

**Happy Analyzing! 🤖**
