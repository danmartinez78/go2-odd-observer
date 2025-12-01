# Data Versioning

This document tracks versions of processed data and the processing parameters used to generate them.

## Version Naming Convention

**Format**: `{source}_{id}_v{version}`

- **source**: `sim` or `real`
- **id**: Scenario identifier (e.g., `1`, `01_173442`)
- **version**: Incrementing version number starting at 0

**Examples**:
- `sim_1_v0` - Sim scenario 1, version 0 (initial)
- `sim_1_v1` - Sim scenario 1, version 1 (with updated BEV processing)
- `real_01_v0` - Real scenario 01, version 0 (initial)

## Current Production Data Versions

### Sim Data

| Version | Date | Windows | Window Settings | BEV Settings | Motion Fields | Notes |
|---------|------|---------|-----------------|--------------|---------------|-------|
| `sim_1` | Nov 28 | 31 | 2.0s window, 2.0s stride | auto (sim default) | derived_speed, derived_yaw_rate | Production: with derived motion |

**Note:** Sim data uses automatic BEV transformations (TF + 90° CCW rotation hardcoded in `extract_windows.py`). Do NOT specify `--bev-rotation` or `--bev-flip-horizontal` for sim data.

### Real Data

| Version | Date | Windows | BEV Settings | Motion Fields | Notes |
|---------|------|---------|--------------|---------------|-------|
| `real_173442` | Dec 1 | 31 | auto (real default) | derived_speed, derived_yaw_rate | Office environment, full traversal |
| `real_173813` | Dec 1 | 30 | auto (real default) | derived_speed, derived_yaw_rate | Office environment |
| `real_174232` | Dec 1 | 11 | auto (real default) | derived_speed, derived_yaw_rate | Shorter sequence |
| `real_174321` | Dec 1 | 29 | auto (real default) | derived_speed, derived_yaw_rate | Office environment |
| `real_174503` | Dec 1 | 11 | auto (real default) | derived_speed, derived_yaw_rate | Shorter sequence |
| `real_174604` | Dec 1 | 24 | auto (real default) | derived_speed, derived_yaw_rate | Office environment |

**Total production windows:** 167 (31 sim + 136 real)

**Note:** Real data uses odom-frame detection (point cloud already in odom frame on real robot). Ground filtering uses fixed `ground_z = 0.0m` for real data.

### Window Strategy Rationale

**Why no overlap is preferred for ODD analysis:**

1. **No redundant analysis** - Each moment analyzed exactly once
2. **50% fewer windows** - Half the API calls and cost
3. **LLM cross-window reasoning** - Agents already see all windows in a chunk, so overlap doesn't add value
4. **Pattern detection** - Looking for trends, not precise event timestamps

**When overlap might help:**
- Event detection where boundary timing matters
- Very short windows (<1s) where context is limited
- Real-time streaming analysis (not our use case)

## Test Data Versions

### Sim Test Data

| Location | Source | Windows | Version | Notes |
|----------|--------|---------|---------|-------|
| `data/test/sim_2win/` | `sim_1` | 2 (w010-011) | v1 | Quick validation |

### Real Test Data

| Location | Source | Windows | Version | Notes |
|----------|--------|---------|---------|-------|
| `data/test/real_2win/` | `real_173442` | 2 (w010-011) | v1 | Quick validation |

## Version Changelog

### v1 (Current)
**Date**: December 1, 2025  
**Changes**:
- Added derived motion fields: `derived_speed`, `derived_yaw_rate`
- Added position fields: `pos_x`, `pos_y`, `pos_z`
- Real data motion fix: source go2_ros2_sdk for IMU types
- MIN_DT_THRESHOLD (10ms) to filter unrealistic speeds
- Standardized stride to 2.0s (no overlap)

**Command**:
```bash
source /opt/ros/humble/setup.bash
source /workspaces/go2-odd-observer/go2_ros2_sdk/install/setup.bash

python scripts/extract_windows.py \
  --rosbag data/raw_rosbags/sim/1/sim_1_0.db3 \
  --output data/production/sim_1 \
  --window-length 2.0 --stride 2.0 \
  --run-id sim_1 \
  --data-source sim
```

**Motion JSON Fields (new)**:
```json
{
  "pos_x": [...], "pos_y": [...], "pos_z": [...],
  "derived_speed": [...],
  "derived_yaw_rate": [...]
}
```

### v0 (Legacy)
**Date**: November 25, 2025  
**Changes**:
- Initial BEV auto-crop implementation (65-72% size reduction)
- Sim data: 90° rotation + horizontal flip
- 4 BEV channels: occupancy, height, density, roughness
- Density: Linear normalization (max value = 255)

**Processing Parameters**:
```python
{
  "bev_rotation": 90,
  "bev_flip_horizontal": True,
  "bev_auto_crop": True,
  "bev_size": 200,  # Pre-crop size
  "bev_resolution": 0.05,  # 5cm per pixel
  "density_normalization": "linear",  # point_count / max_count
  "ground_filter": False  # Not yet implemented
}
```

**Known Issues**:
- Density images show concentration at robot's immediate vicinity (sim single-scan characteristic)
- Real robot data blocked (needs per-scan LiDAR)

## Regeneration Scripts

### Full Production Data
```bash
# Regenerate all sim production data
./scripts/regenerate_production_data.sh --source sim --version v1

# Regenerate all real production data (when available)
./scripts/regenerate_production_data.sh --source real --version v1
```

### Test Data Only
```bash
# Regenerate test data (small sample sets)
./scripts/regenerate_test_data.sh
```

## Data Version Metadata

Each processed scenario directory should include a `metadata.json` file:

```json
{
  "data_version": "v0",
  "source_bagfile": "data/raw_rosbags/sim/1/sim_1_0.db3",
  "generation_date": "2025-11-25T03:42:00Z",
  "script_version": "extract_windows.py v1.2.0",
  "parameters": {
    "window_length": 2.0,
    "stride": 1.0,
    "bev_rotation": 90,
    "bev_flip_horizontal": true,
    "bev_auto_crop": true
  }
}
```

## Guidelines

### When to Increment Version

**Major changes** (increment version number):
- BEV processing algorithm changes (normalization, filtering)
- Coordinate transformations added/removed
- Window extraction parameters changed
- Any change that affects analysis results

**Minor changes** (keep version, document):
- Bug fixes that don't change outputs
- Performance optimizations
- Code refactoring

### Data Retention

- **Keep**: At least the latest version for each scenario
- **Archive**: Previous versions if they're referenced in published results
- **Delete**: Intermediate test/debug versions after validation

### Version Control

- This file (`DATA_VERSIONS.md`) is version controlled
- Data files are gitignored
- Regeneration scripts are version controlled
- Processing parameters are documented here

---

**Last Updated**: December 1, 2025  
**Maintainer**: Check git log for contributors
