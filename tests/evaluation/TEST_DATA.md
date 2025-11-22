# Test Data Documentation

This document describes the test data used for ADK agent evaluation.

---

## 📊 Dataset: `sim_run_test`

**Location**: `data/processed/runs/sim_run_test/`

**Source**: Simulated Unitree Go2 quadruped robot navigation in indoor environment

**Total Windows**: 13 windows (000-012)

**Evaluation Uses**: Windows **006** and **007** (representative samples)

---

## 🎯 Why Windows 006 and 007?

These two windows were selected for evaluation because they:

1. **Representative motion patterns** - Robot actively moving (not stationary)
2. **Complete sensor coverage** - All modalities present (camera, LiDAR BEV, IMU)
3. **Moderate complexity** - Not trivial, not edge cases
4. **Fast evaluation** - 2 windows = ~20-80s test runs vs 13 windows = ~2-5min
5. **Consistent quality** - Clean data, no sensor dropouts

---

## 📁 Files Per Window

Each window contains the following files:

### Visual Data
- **`cam_sim_run_test_w{NNN}.png`** - RGB camera frame (640x480)
  - Window 006: 486KB (detailed scene)
  - Window 007: 319KB (less detail)

### LiDAR Bird's Eye View (BEV) Images
- **`bev_occupancy_sim_run_test_w{NNN}.png`** - Occupancy grid (obstacles vs free space)
- **`bev_height_sim_run_test_w{NNN}.png`** - Height map (elevation data)
- **`bev_density_sim_run_test_w{NNN}.png`** - Point density (LiDAR return intensity)
- **`bev_roughness_sim_run_test_w{NNN}.png`** - Surface roughness estimate

All BEV images: 200x200 pixels, 5cm/pixel resolution, ±10m range

### Motion Data
- **`motion_sim_run_test_w{NNN}.json`** - IMU time series data
  - Timestamps (~24 samples per 2-second window)
  - Gyroscope (angular velocity): `gyro_x`, `gyro_y`, `gyro_z` [rad/s]
  - Accelerometer (linear acceleration): `accel_x`, `accel_y`, `accel_z` [m/s²]
  - Orientation: `roll`, `pitch`, `yaw` [radians]
  - ⚠️ **Odometry stuck at zero** (known sim issue): `odom_vx/vy/vz/wx/wy/wz` all 0.0

### Index
- **`index_sim_run_test.csv`** - Window metadata
  - `window_id`: Window identifier (006, 007, ...)
  - `start_idx`: Start frame index
  - `end_idx`: End frame index

---

## 🔢 Window 006 Data Characteristics

**Duration**: ~2 seconds (24 IMU samples)

### IMU Data Summary
| Sensor | Axis | Min | Max | Mean | Interpretation |
|--------|------|-----|-----|------|----------------|
| **Gyro (rad/s)** | X | -1.409 | 0.710 | -0.037 | Small pitch rotation |
| | Y | -0.386 | 0.863 | 0.131 | Small roll rotation |
| | Z | -0.859 | 0.164 | **-0.187** | **Turning left** |
| **Accel (m/s²)** | X | 0.329 | 0.921 | 0.672 | Forward acceleration |
| | Y | 0.052 | 0.222 | 0.117 | Slight lateral |
| | Z | -0.148 | 0.175 | 0.036 | Near-level platform |

**Motion Interpretation**: Robot rotating left (Z gyro -0.187 rad/s ≈ -10.7°/s) with forward acceleration

### Visual Data
- **Camera**: Indoor environment, moderate lighting, visible obstacles
- **BEV Occupancy**: Obstacle density ~0.45, moderate clutter
- **BEV Height**: Relatively flat terrain with minor variations
- **BEV Roughness**: Smooth surface (indoor floor)

---

## 🔢 Window 007 Data Characteristics

**Duration**: ~2 seconds (24 IMU samples)

### IMU Data Summary
| Sensor | Axis | Min | Max | Mean | Interpretation |
|--------|------|-----|-----|------|----------------|
| **Gyro (rad/s)** | X | -0.852 | 1.238 | 0.039 | Small pitch variation |
| | Y | -0.682 | 1.129 | -0.081 | Small roll variation |
| | Z | -0.044 | 0.133 | 0.036 | Minimal yaw rotation |
| **Accel (m/s²)** | X | 0.808 | 0.975 | **0.907** | **Strong forward accel** |
| | Y | -0.017 | 0.037 | 0.003 | Minimal lateral |
| | Z | -0.099 | 0.205 | 0.023 | Stable platform |

**Motion Interpretation**: Robot moving mostly forward (X accel 0.907 m/s²) with minimal rotation (nearly straight line)

### Visual Data
- **Camera**: Similar indoor environment, good lighting
- **BEV Occupancy**: Obstacle density similar to 006
- **BEV Height**: Flat terrain
- **BEV Roughness**: Smooth surface

---

## ⚠️ Critical Data Issues

### Odometry Stuck at Zero
**Issue**: All odometry fields (`odom_vx`, `odom_vy`, `odom_vz`, `odom_wx`, `odom_wy`, `odom_wz`) are stuck at `0.0` in the simulation data.

**Root Cause**: Known issue with Unitree Go2 simulator odometry publishing

**Impact**: Cannot use odometry for velocity/position estimation

**Mitigation**: **Motion analysis uses IMU data exclusively** (gyro + accel)
- Gyroscope provides angular velocity (rotation rate)
- Accelerometer provides linear acceleration
- This is sufficient for motion classification and stability assessment

**Agent Implications**:
- ✅ **Motion Agent**: Uses IMU only, unaffected by odometry issue
- ✅ **Collision Agent**: Uses perception + motion (IMU-based), unaffected
- ✅ **Compliance Agent**: Uses aggregated statistics, unaffected

**Test Expectations**: Do NOT expect velocity estimates from odometry. Motion should be inferred from IMU signatures (gyro patterns, acceleration profiles).

---

## 📋 Using This Data for Evaluation

### Perception Agent Tests
**Inputs**: Camera image + 4 BEV images (occupancy, height, density, roughness)

**Expected Outputs**:
- Environment classification (indoor/outdoor)
- Lighting assessment (moderate/bright/dim)
- Obstacle detection and density
- Terrain type and traversability score
- Summary description

**Acceptance Criteria**:
- Correctly identifies indoor environment
- Detects moderate obstacle density (~0.45)
- Classifies terrain as smooth
- Provides reasonable traversability score (0.6-0.8 range)

### Motion Agent Tests
**Inputs**: Motion JSON with IMU time series

**Expected Outputs**:
- Motion classification (stationary/moving/turning)
- Gyro statistics (mean, max, variance)
- Accel statistics (mean, max, variance)
- Platform stability assessment
- Summary description

**Acceptance Criteria**:
- **Window 006**: Detects turning motion (Z gyro ~-0.187 rad/s)
- **Window 007**: Detects forward motion (X accel ~0.907 m/s²)
- Does NOT rely on odometry (all zeros)
- Provides physically plausible statistics

### Collision Agent Tests
**Inputs**: Perception output + Motion output + Camera + BEV images

**Expected Outputs**:
- Collision risk score (0.0-1.0)
- Closest obstacle distance
- Risk factors list
- Recommendations

**Acceptance Criteria**:
- Risk score correlates with obstacle density
- Considers motion speed (higher speed = higher risk)
- Identifies specific risk factors
- Provides actionable recommendations

---

## 🎯 Creating New Test Cases

When adding evaluation for new agents, follow this pattern:

1. **Use windows 006 and 007** for consistency across agent tests
2. **Reference this document** for expected data characteristics
3. **Create realistic expectations** based on actual data ranges
4. **Account for odometry issue** - do not expect velocity from odometry
5. **Use IMU data** for any motion-related assertions

### Example Test Case Structure
```json
{
  "name": "Window 006 analysis",
  "user_request": "Analyze window 006",
  "expected_tool_uses": [
    {
      "tool_name": "list_windows_tool",
      "match_type": "EXACT"
    },
    {
      "tool_name": "analyze_motion_tool",
      "args": {
        "window_id": "006"
      }
    }
  ]
}
```

---

## 📚 Related Documentation

- **Agent implementations**: `odd_agents/agents/`
- **Tool implementations**: `odd_agents/tools/`
- **Evaluation framework**: `tests/evaluation/README.md`
- **Perception tests**: `tests/evaluation/perception/README.md`
- **Motion tests**: `tests/evaluation/motion/README.md`
- **Data extraction**: `scripts/extract_windows.py`
- **BEV rendering**: `scripts/render_bev.py`

---

## 🔍 Inspecting Test Data

### View Window Files
```bash
ls -lh data/processed/runs/sim_run_test/ | grep "w006\|w007"
```

### Analyze Motion Data
```python
import json
import statistics

with open('data/processed/runs/sim_run_test/motion_sim_run_test_w006.json') as f:
    motion = json.load(f)

print(f"Gyro Z mean: {statistics.mean(motion['gyro_z']):.3f} rad/s")
print(f"Accel X mean: {statistics.mean(motion['accel_x']):.3f} m/s²")
```

### View Images
```bash
# Open camera image
code data/processed/runs/sim_run_test/cam_sim_run_test_w006.png

# Open BEV occupancy
code data/processed/runs/sim_run_test/bev_occupancy_sim_run_test_w006.png
```

---

**Last Updated**: November 22, 2025  
**Maintainer**: Go2 ODD Observer Team
