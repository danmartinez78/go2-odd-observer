# Data Generation Guide

This document explains how to extract window data from ROS2 bag files for ODD analysis.

## Quick Start

### Sim Data (Recommended - No Manual Params Needed)

```bash
source /opt/ros/humble/setup.bash
source go2_ros2_sdk/install/setup.bash

python scripts/extract_windows.py \
  --rosbag data/raw_rosbags/sim/1/sim_1_0.db3 \
  --output data/production/my_scenario \
  --window-length 2.0 \
  --stride 2.0 \
  --run-id my_scenario \
  --data-source sim
```

### Real Data (When Available)

```bash
python scripts/extract_windows.py \
  --rosbag data/raw_rosbags/real/collection_YYYYMMDD_HHMMSS/collection_*.db3 \
  --output data/production/real_scenario \
  --window-length 2.0 \
  --stride 2.0 \
  --run-id real_scenario \
  --data-source real
```

---

## The `extract_windows.py` Tool

### Purpose

Extracts time-windowed sensor data from ROS2 bag files into a format ready for ODD analysis:
- **Camera images** (PNG)
- **BEV images** - Bird's Eye View from LiDAR (occupancy, height, roughness channels)
- **Motion JSON** - IMU data with statistics (acceleration, angular velocity, orientation)
- **Index CSV** - Window metadata with file paths and timestamps

### Command Line Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--rosbag` | ✅ | - | Path to ROS2 bag file (.db3) |
| `--output` | ✅ | - | Output directory for extracted windows |
| `--window-length` | ❌ | 2.0 | Window duration in seconds |
| `--stride` | ❌ | 1.0 | Time between window starts (seconds) |
| `--run-id` | ❌ | auto | Scenario identifier (used in filenames) |
| `--data-source` | ❌ | auto | `sim` or `real` (auto-detected from path) |
| `--bev-rotation` | ❌ | 0 | Additional BEV rotation (0, 90, 180, 270°) |
| `--bev-flip-horizontal` | ❌ | false | Additional horizontal flip |

---

## Important: Data Source Auto-Detection

**The tool automatically applies correct transformations based on data source.**

### How Auto-Detection Works

The `--data-source` parameter is auto-detected from the bag file path:
- Path contains `sim` → Uses sim configuration
- Path contains `real` → Uses real configuration

You can override with `--data-source sim` or `--data-source real` if needed.

### Sim Data Transformations (Automatic)

When `data_source == 'sim'`, the tool automatically:

1. **Uses TF transforms** to convert LiDAR points from sensor frame → odom frame → base_link frame
2. **Applies ground filtering** in the gravity-aligned odom frame
3. **Renders robot-centric BEV** with robot at center
4. **Applies 90° CCW rotation** to align BEV with camera view (forward = up)

**⚠️ DO NOT specify `--bev-rotation` or `--bev-flip-horizontal` for sim data!**  
The automatic transformations handle everything. Adding manual rotation/flip will produce incorrect results.

### Real Data Transformations (Automatic)

When `data_source == 'real'`:

1. **Detects point cloud frame** - Real robot publishes LiDAR directly in odom frame (no sensor→odom transform needed)
2. **Uses TF transforms** to convert from odom frame → base_link frame
3. **Applies ground filtering** in the gravity-aligned odom frame
4. **Renders robot-centric BEV** with robot at center
5. **Applies 90° CCW rotation** to align BEV with camera view (forward = up)

Uses different topic names (`/point_cloud2` instead of `/robot0/point_cloud2_L1`) and frame names (`base_link` instead of `robot0/base_link`).

**⚠️ DO NOT specify `--bev-rotation` or `--bev-flip-horizontal` for real data either!**  
Both sim and real use the same final orientation convention.

---

## Window Parameters

### Window Length vs Stride

```
window_length = 2.0s, stride = 2.0s (NO OVERLAP - Recommended)
├── Window 0: [0.0s - 2.0s]
├── Window 1: [2.0s - 4.0s]
├── Window 2: [4.0s - 6.0s]
└── ...

window_length = 2.0s, stride = 1.0s (50% OVERLAP - Legacy)
├── Window 0: [0.0s - 2.0s]
├── Window 1: [1.0s - 3.0s]  ← overlaps with W0
├── Window 2: [2.0s - 4.0s]  ← overlaps with W1
└── ...
```

### Recommended Settings

| Use Case | Window Length | Stride | Notes |
|----------|---------------|--------|-------|
| **Production** | 2.0s | 2.0s | No overlap, no redundancy |
| **High-detail analysis** | 2.0s | 1.0s | 50% overlap, 2x windows |
| **Long-term trends** | 5.0s | 5.0s | Fewer windows, broader view |

**Why no overlap is preferred:**
- 50% fewer API calls (cost savings)
- No redundant analysis (each moment analyzed once)
- LLM cross-window reasoning already sees all windows in a chunk

---

## Output Structure

After extraction, the output directory contains:

```
data/production/my_scenario/
├── index_my_scenario.csv           # Window metadata
├── cam_my_scenario_w000.png        # Camera images
├── cam_my_scenario_w001.png
├── ...
├── bev_occupancy_my_scenario_w000.png  # BEV channels
├── bev_height_my_scenario_w000.png
├── bev_roughness_my_scenario_w000.png
├── ...
├── motion_my_scenario_w000.json    # IMU data
├── motion_my_scenario_w001.json
└── ...
```

### Index CSV Format

```csv
window_id,start_time,end_time,motion_path,cam_image_path,bev_occupancy_path,bev_height_path,bev_roughness_path
0,1763483957.74,1763483959.74,motion_my_scenario_w000.json,cam_my_scenario_w000.png,...
1,1763483959.74,1763483961.74,motion_my_scenario_w001.json,cam_my_scenario_w001.png,...
```

---

## Motion JSON Structure

Motion JSON files contain IMU data and derived motion metrics:

```json
{
    "start_time": 0.0,
    "end_time": 2.0,
    "timestamps": [0.0, 0.02, 0.04, ...],
    
    // IMU measurements
    "accel_x": [...], "accel_y": [...], "accel_z": [...],
    "gyro_x": [...], "gyro_y": [...], "gyro_z": [...],
    "roll": [...], "pitch": [...], "yaw": [...],
    
    // Odometry position (raw)
    "pos_x": [...], "pos_y": [...], "pos_z": [...],
    
    // Derived motion (computed from position)
    "derived_speed": [...],     // Speed magnitude (m/s)
    "derived_yaw_rate": [...]   // Angular velocity (rad/s)
}
```

### Derived Motion Fields

| Field | Source | Description |
|-------|--------|-------------|
| `derived_speed` | Position differentiation | Magnitude of velocity vector |
| `derived_yaw_rate` | Yaw differentiation | Angular velocity from heading change |

**Why derived fields?**
- Real robot odometry velocity is often zeros
- Position-derived speed is more reliable
- Provides consistent measurement across sim and real data

**Implementation details:**
- `MIN_DT_THRESHOLD` (10ms): Filters unrealistic speeds from duplicate timestamps
- `MAX_PLAUSIBLE_SPEED` (5 m/s): Clips values above Go2's max speed (~3.5 m/s)

---

## BEV Channels

The tool generates three BEV channels from LiDAR data:

| Channel | Description | Interpretation |
|---------|-------------|----------------|
| **occupancy** | Binary obstacle presence | White = obstacle, Black = free |
| **height** | Point height above ground | Brighter = taller obstacles |
| **roughness** | Height variance in cell | Brighter = more uneven terrain |

### BEV Orientation

After automatic transformations:
- **Robot position**: Center of image
- **Forward direction**: Up (toward top of image)
- **Right side**: Right side of image
- **Left side**: Left side of image

This matches the camera's perspective for intuitive comparison.

---

## Troubleshooting

### BEV appears mirrored or rotated incorrectly

**For both sim and real data:** Remove any `--bev-rotation` or `--bev-flip-horizontal` flags. The automatic transformation handles alignment for both data sources.

### "No TF transforms available" warning

The tool will fall back to rendering in sensor frame without ground filtering. This may produce different results. Ensure the bag file contains `/tf` messages.

### ROS2 libraries not found

Source the ROS2 workspace before running:
```bash
source /opt/ros/humble/setup.bash
source go2_ros2_sdk/install/setup.bash
```

### Output directory naming

**Critical:** The output directory name MUST match the `run_id`. The workflow uses the directory name to find files. If they don't match, analysis will fail.

---

## Examples

### Generate Sim Production Data (No Overlap)

```bash
python scripts/extract_windows.py \
  --rosbag data/raw_rosbags/sim/1/sim_1_0.db3 \
  --output data/production/sim_2_0_nooverlap \
  --window-length 2.0 \
  --stride 2.0 \
  --run-id sim_2_0_nooverlap \
  --data-source sim
```

### Generate Test Data (Small Sample)

```bash
# Extract just 5 windows for testing
python scripts/extract_windows.py \
  --rosbag data/raw_rosbags/sim/1/sim_1_0.db3 \
  --output data/test/sim/sim_test_5windows \
  --window-length 2.0 \
  --stride 2.0 \
  --run-id sim_test_5windows \
  --data-source sim
# Then manually select windows 0-4
```

---

## Version History

| Date | Change |
|------|--------|
| 2025-12-01 | Added derived motion fields: `derived_speed` and `derived_yaw_rate` |
| 2025-11-28 | Real data BEV fix: unified rotation, auto-detect odom frame point cloud |
| 2025-11-28 | Added no-overlap recommendation, clarified auto-transformation for sim data |
| 2025-11-25 | Initial BEV transformation work, TF integration |

---

**Last Updated:** December 1, 2025
