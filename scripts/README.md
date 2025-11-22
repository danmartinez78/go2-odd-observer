# Scripts Directory

Executable scripts for the Go2 ODD Observer project.

---

## 🚀 Main Workflow

### `odd_workflow.py` - **CURRENT** Production Script

**Purpose**: Run complete ODD/COD analysis using the shared `odd_agents` module.

**Usage**:
```bash
python scripts/odd_workflow.py
```

**What it does**:
- Analyzes multi-modal sensor data (camera, LiDAR, IMU)
- Runs 10-agent sequential pipeline
- Generates comprehensive ODD compliance report
- Outputs to: `data/processed/runs/{scenario}/odd_analysis_report.json`

**Source code**: Only 40 lines - imports from `odd_agents` module (single source of truth)

**Agents**: ODD Spec → Perception Loop/Summary → Motion Loop/Summary → Collision Loop/Summary → COD Classifier → ODD Compliance → Report

---

## 📊 Data Processing Scripts

### `extract_windows.py` - ROS2 Bag Window Extractor

**Purpose**: Extract time-windowed multi-modal snapshots from ROS2 bag files.

**Usage**:
```bash
python scripts/extract_windows.py \
  --rosbag data/raw_rosbags/real/my_bag.db3 \
  --output data/processed/runs/my_scenario \
  --run-id my_scenario \
  --window-length 2.0 \
  --stride 1.0
```

**Outputs per window**:
- `motion_<scenario>_w<NNN>.json` - Velocity, IMU, odometry time series
- `cam_<scenario>_w<NNN>.png` - RGB camera frame
- `bev_occupancy_<scenario>_w<NNN>.png` - LiDAR BEV (occupancy)
- `bev_height_<scenario>_w<NNN>.png` - LiDAR BEV (height map)
- `bev_density_<scenario>_w<NNN>.png` - LiDAR BEV (point density)
- `bev_roughness_<scenario>_w<NNN>.png` - LiDAR BEV (surface roughness)
- `index_<scenario>.csv` - Window metadata

**Dependencies**: ROS2 Humble, sensor_msgs, nav_msgs

---

### `render_bev.py` - LiDAR BEV Renderer

**Multi-channel BEV rendering (occupancy, height, density, roughness)
**Features**:
- Occupancy grid generation
- Height mapping
- Configurable resolution (default: 5cm/pixel)
- Customizable range (default: ±10m)

**Usage**: Called internally by `extract_windows.py` or standalone for debugging.

---

### `utils_ros.py` - ROS2 Utilities

**Purpose**: Helper functions for ROS2 message parsing and time synchronization.

**Key functions**:
- Message deserialization (Image, PointCloud2, Odometry, IMU)
- Timestamp alignment across topics
- Topic filtering and validation

---

## 🧪 Testing & Development Scripts

### `generate_demo_data.py` - Synthetic Data Generator

**Purpose**: Create synthetic window data for testing without ROS2 bags.

**Usage**:
```bash
python scripts/generate_demo_data.py
```

**Generates**:
- Synthetic time windows with realistic motion profiles
- Synthetic camera images (640x480)
- Synthetic LiDAR BEV images (all 4 channels)
- Complete index CSV
- Intentional ODD violations for demo

**Use cases**:
- Test workflow without real robot data
- Validate agent pipeline changes
- Demonstrate ODD violations
- CI/CD testing

---

## 📁 Directory Structure After Processing

```
data/processed/runs/
└── my_scenario/
    ├── index_my_scenario.csv
    ├── motion_my_scenario_w000.json
    ├── motion_my_scenario_w001.json
    ├── ...
    ├── cam_my_scenario_w000.png
    ├── cam_my_scenario_w001.png
    ├── ...
    ├── bev_occupancy_my_scenario_w000.png
    ├── bev_occupancy_my_scenario_w001.png
    └── ...
```

---

## 🔧 Development Notes

### Adding New Sensors
rchitecture

The current architecture uses a **shared module pattern**:

- **`odd_agents/`** - Source of truth for all agent definitions and workflow
- **`scripts/odd_workflow.py`** - Production entry point (imports from module)
- **`notebooks/odd_analysis_demo.ipynb`** - Interactive analysis (imports from module)
- **`tests/test_*.py`** - Individual agent tests (imports from module)

**No code duplication** - everything imports from `odd_agents` module.

### Adding New Sensors

To extract additional sensor data:

1. Add topic name to `extract_windows.py` configuration
2. Add deserialization logic in `utils_ros.py`
---

## 📦 Archived Scripts

The `archive/` directory contains superseded implementations:

- `odd_workflow_full.py` - Original monolithic workflow (857 lines)
- `odd_workflow_full.py.backup` - Golden reference backup
- `multi_agent_image_adk_workflow.py` - Original loop+summary pattern reference

**Note**: Archived for reference only. Use `odd_workflow.py` and the `odd_agents` module instead.

---

## 🚀 Quick Reference

| Task | Script | Key Options |
|------|--------|-------------|
| Run ODD analysis | `odd_workflow.py` | None (uses config in script) |
| Extract from ROS bag | `extract_windows.py` | `--rosbag`, `--output`, `--window-length` |
| Generate test data | `generate_demo_data.py` | None (uses defaults) |
| Debug BEV rendering | `render_bev.py` | Standalone usage with point cloud file |

---

## 📚 Related Documentation

- **Module architecture**: `../docs/FACTORY_PATTERN.md`
- **Agent implementations**: `../odd_agents/agents/`
- **Workflow orchestration**: `../odd_agents/workflow.py`
- **Interactive analysis**: `../notebooks/odd_analysis_demo.ipynb`
- **Getting started**: `../docs/guides/xtract_windows.py` | `--rosbag`, `--output`, `--window-length` |
| Generate test data | `generate_demo_data.py` | None (uses defaults) |
| Validate pipeline | `demo_pipeline_local.py` | None (auto-detects demo data) |
| Debug BEV rendering | `render_bev.py` | Standalone usage with point cloud file |

---

## 📚 Related Documentation

- **Data format specs**: See `docs/examples/README.md`
- **Agent workflow**: See `odd_workflow_full.py` and `agent_tests/`
- **Interactive analysis**: See `notebooks/odd_workflow_interactive.ipynb`
- **Complete setup**: See `GETTING_STARTED.md`

---

## 🐛 Troubleshooting

**Issue**: "ROS2 topics not found"
- **Solution**: Check topic names with `ros2 bag info your_bag.db3`
- Update topic names in `extract_windows.py` if needed

**Issue**: "Window extraction incomplete"
- **Solution**: Verify bag duration > window_length
- Check for missing messages in problematic topics

**Issue**: "BEV images blank"
- **Solution**: Verify LiDAR data exists in bag
- Check point cloud coordinate frames
- Adjust BEV range parameters

**Issue**: "Workflow fails"
- **Solution**: Check API key: `echo $GOOGLE_API_KEY`
- Verify scenario data exists: `ls data/processed/runs/`
- Check for errors in agent outputs
