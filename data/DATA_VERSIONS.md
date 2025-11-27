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

| Version | Date | Windows | BEV Settings | Notes |
|---------|------|---------|--------------|-------|
| `sim_1_v0` | TBD | TBD | rotation=90°, flip=horizontal, auto-crop | Initial with BEV transformations |

### Real Data

| Version | Date | Windows | BEV Settings | Notes |
|---------|------|---------|--------------|-------|
| N/A | - | - | - | Awaiting per-scan LiDAR data |

## Test Data Versions

### Sim Test Data

| Location | Source | Windows | Version | Notes |
|----------|--------|---------|---------|-------|
| `data/test/sim/` | `sim_1_v0` | 6 (w010-011, w030-031, w050-051) | v0 | Early/middle/late samples |

### Real Test Data

| Location | Source | Windows | Version | Notes |
|----------|--------|---------|---------|-------|
| `data/test/real_01_173442/` | collection_20251122_173442 | 2 | v0 | Placeholder (no BEV data yet) |
| `data/test/real_02_173813/` | collection_20251122_173813 | 2 | v0 | Placeholder (no BEV data yet) |

## Version Changelog

### v1 (Planned)
**Target Date**: TBD  
**Changes**:
- Update BEV density normalization (log scale or percentile-based)
- Apply ground filtering (10cm height threshold)
- Regenerate all sim production data

**Command**:
```bash
python scripts/extract_windows.py \
  --rosbag data/raw_rosbags/sim/1/sim_1_0.db3 \
  --output data/production \
  --window-length 2.0 --stride 1.0 \
  --data-source sim \
  --bev-rotation 90 --bev-flip-horizontal \
  --data-version v1
```

### v0 (Current)
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

**Last Updated**: November 25, 2025  
**Maintainer**: Check git log for contributors
