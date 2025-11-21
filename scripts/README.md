# Scripts Directory

This directory contains **all executable scripts** for the Go2 ODD Observer project, including the main workflow, data processing tools, and testing utilities.

---

## 🚀 Main Workflow

### `odd_workflow_full.py` - 9-Agent Sequential Pipeline

**Purpose**: Complete ODD/COD analysis using the proven loop+summary pattern.

**Usage**:
```bash
python scripts/odd_workflow_full.py
```

**What it does**:
- Analyzes multi-modal sensor data (camera, LiDAR, motion)
- Runs 9 specialized AI agents in sequence
- Generates comprehensive ODD compliance report
- Outputs to: `data/processed/runs/{scenario}/odd_analysis_report.json`

**Agents**: Perception Loop/Summary → Motion Loop/Summary → Collision Loop/Summary → ODD Spec → COD → Report

---

### `multi_agent_image_adk_workflow.py` - Reference Pattern

**Purpose**: Proven loop+summary pattern for multimodal vision workflows.

**This is the reference implementation** that demonstrated:
- Hallucination-free vision analysis
- Tools calling Gemini directly with `types.Part.from_bytes`
- Loop agent processing items individually
- Summary agent aggregating results

**Do not modify** - this is the pattern foundation for `odd_workflow_full.py`.

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
- `bev_occupancy_<scenario>_w<NNN>.png` - LiDAR bird's eye view
- `index_<scenario>.csv` - Window metadata

**Dependencies**: ROS2 Humble, sensor_msgs, nav_msgs

---

### `render_bev.py` - LiDAR BEV Renderer

**Purpose**: Convert LiDAR PointCloud2 messages to bird's eye view images.

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
- 10 time windows with realistic motion profiles
- Synthetic camera images (640x480)
- Synthetic LiDAR BEV images
- Complete index CSV and manifest entry
- Intentional ODD violations in windows 7-8 for demo

**Use cases**:
- Test workflow without real robot data
- Validate agent pipeline changes
- Demonstrate ODD violations
- CI/CD testing

---

### `demo_pipeline_local.py` - Mock Agent Testing

**Purpose**: Validate data flow and orchestration without API calls.

**Features**:
- Mock agents that return fake JSON (no Gemini API required)
- Mirrors notebook architecture exactly
- Tests file I/O, schema alignment, and aggregation logic
- Useful for rapid iteration during development

**Usage**:
```bash
python scripts/demo_pipeline_local.py
```

**Output**: Console validation of data processing steps

**When to use**:
- Before running expensive API workflows
- Testing schema changes
- Validating new window extraction logic
- Understanding agent orchestration pattern

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

To extract additional sensor data:

1. Add topic name to `extract_windows.py` (line ~50)
2. Add deserialization logic in `utils_ros.py`
3. Update window output schema
4. Modify agent tools to process new data type

### Customizing Window Parameters

Common adjustments in `extract_windows.py`:

- **Window length**: Duration of each analysis window (default: 2.0s)
- **Stride**: Overlap between windows (default: 1.0s)
- **BEV resolution**: Pixel size (default: 0.05m/pixel)
- **BEV range**: Spatial extent (default: ±10m)

### Testing Data Pipeline

```bash
# 1. Generate demo data
python scripts/generate_demo_data.py

# 2. Validate with mock pipeline
python scripts/demo_pipeline_local.py

# 3. Run real workflow
python odd_workflow_full.py
```

---

## 🚀 Quick Reference

| Task | Script | Key Options |
|------|--------|-------------|
| Extract from ROS bag | `extract_windows.py` | `--rosbag`, `--output`, `--window-length` |
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

**Issue**: "Demo pipeline fails"
- **Solution**: Run `python scripts/generate_demo_data.py` first
- Verify `data/processed/runs/demo_run/` exists
