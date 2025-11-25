# BEV Transformation Status & Next Steps

**Date:** November 25, 2025  
**Branch:** `feature/phase1.1-bev-enhancement`  
**Status:** ✅ WORKING for sim data | ⚠️ BLOCKED for real data (needs per-scan LiDAR)

## Current Solution (Sim Data)

### Working Configuration
```bash
python scripts/extract_windows.py \
  --rosbag data/raw_rosbags/sim/1/sim_1_0.db3 \
  --output data/production \
  --data-source sim \
  --bev-rotation 90 \
  --bev-flip-horizontal
```

**Transformations Applied (sim only):**
1. **Rotation**: 90° clockwise (fixes orientation)
2. **Flip**: Horizontal flip (fixes left/right mirror)
3. **Auto-crop**: Preserves all obstacles, reduces size 65-72%

**Result:** Clean, correctly oriented BEVs with robot centered and forward=up

### Production Data Generated
- **Sim data**: `data/production/sim_1_0/` (62 windows)
  - Window length: 2.0s, stride: 1.0s
  - BEV channels: **occupancy, height, roughness** (density removed)
  - Transformations: 90° rotation + horizontal flip + auto-crop
  - Status: ✅ Complete

### Test Data Generated
- **Sim test**: `data/test/sim/` (6 windows)
  - Windows: w010-011, w030-031, w050-051 (early/middle/late samples)
  - Same transformations as production
  - For manual agent testing

## Problem Summary (Real Data)

We need robot-centered BEVs for both sim and real robot data, but real robot uses accumulated point clouds which create severe aliasing when transformed.

### Root Cause

**Sim Robot:**
- Point cloud topic: `/robot0/point_cloud2_L1`
- Frame: `base_link` (robot-centered)
- Type: Single LiDAR scan per message
- Result: Clean BEVs with robot at center ✅

**Real Robot:**
- Point cloud topic: `/point_cloud2`
- Frame: `odom` (world frame)
- Type: **Accumulated voxel map** (many scans combined)
- Resolution: Already pixelated at ~5cm
- Problem: Robot position varies within the accumulated cloud ❌

### Attempted Solutions

#### 1. Point Cloud Transformation (FAILED)
**Commits:** `d004b10`, `12e19aa`
- Approach: Transform each point from odom → base_link before rendering
- Result: Severe aliasing artifacts (checkerboard pattern)
- Why it failed: Transforming individual points with rounding creates clustering

#### 2. BEV Image Transformation (FAILED)
**Commits:** `e3445fe`, `c9ccfcb`
- Approach: Render BEV in odom frame, then use `cv2.warpAffine` to rotate/translate
- Tried: `INTER_LINEAR`, `INTER_CUBIC`, `INTER_LANCZOS4`
- Result: Grid aliasing artifacts worse than original
- Why it failed: Input data is already pixelated/voxelized at low resolution. Rotating a 5cm voxel grid creates severe artifacts no matter the interpolation method.

#### 3. What Actually Works ✅
**Auto-crop function** (commits `f267abe`, `93f7db3`)
- Finds robot center position
- Calculates max distance to farthest obstacle
- Crops BEV preserving all obstacles
- **100% obstacle preservation validated**
- 65-72% size reduction
- 13 passing unit tests

## Solution: Per-Scan LiDAR Data

### What We Need
A point cloud topic that publishes **individual LiDAR scans** in `base_link` frame, not accumulated data.

**Potential topics to record:**
- Raw LiDAR driver output (before aggregation)
- `/hesai/pandar` or similar manufacturer topic
- Check `go2_ros2_sdk/lidar_processor/launch/` for available topics
- Any topic published by LiDAR driver before `lidar_to_pointcloud_node`

### Why This Solves Everything
1. **Robot-centered data:** Each scan naturally in base_link frame
2. **No transformation needed:** Robot already at center
3. **No aliasing:** Fresh point data, not pre-pixelated
4. **Sim/real consistency:** Both sources have same structure
5. **Clean BEVs:** Like the original images we had before transformation

## Code Status

### Working Code (Sim Data Ready) ✅
- `odd_agents/utils.py`: `auto_crop_bev()` function
- `tests/test_bev_cropping.py`: Full test suite (13 tests, all passing)
- `scripts/extract_windows.py`: 
  - `--bev-rotation` parameter (0, 90, 180, 270)
  - `--bev-flip-horizontal` flag
  - Auto-crop integration
  - Transformation order: rotation → flip → crop

### Production Data
- **Generated**: `data/production/sim_1_0/` (62 windows)
- **Command used**:
  ```bash
  python scripts/extract_windows.py \
    --rosbag data/raw_rosbags/sim/1/sim_1_0.db3 \
    --output data/production \
    --window-length 2.0 --stride 1.0 \
    --data-source sim \
    --bev-rotation 90 --bev-flip-horizontal
  ```

### Code to Update (When per-scan real data available)
**Lines 70-85:** Update TOPIC_MAPS (when per-scan topic identified)
```python
TOPIC_MAPS = {
    'real': {
        # TODO: Update to per-scan topic once available
        "lidar": "/point_cloud2",  # Currently accumulated - CHANGE THIS
        # Candidate topics:
        # "lidar": "/hesai/pandar",
        # "lidar": "/pointcloud/raw",
        # "lidar": "/livox/lidar",
    },
}
```

**Transformation settings:** Once real per-scan data is available, determine if any rotation/flip is needed via testing, then apply appropriate flags.

## Testing Plan (Once Real Per-Scan Data Available)

1. **Verify per-scan data:**
   ```bash
   ros2 topic echo /NEW_TOPIC --once
   # Check: frame_id should be "base_link"
   ```

2. **Update topic mapping** in `extract_windows.py`

3. **Test extraction:**
   ```bash
   python scripts/extract_windows.py \
     --rosbag data/raw_rosbags/real/NEW_BAG.db3 \
     --output data/test_real_perscan \
     --data-source real
   ```

4. **Check orientation and apply fixes if needed:**
   - Compare camera image vs BEV occupancy
   - If mirrored or rotated wrong, add appropriate flags:
     - `--bev-rotation 90` (or 180, 270)
     - `--bev-flip-horizontal`
   - Re-test until BEV matches camera orientation
5. **Visual inspection:**
   - Check BEV images for aliasing (should be clean with per-scan data)
   - Verify robot centered in images
   - Verify forward=up, not mirrored (compare with camera)
   - Compare with sim BEVs for consistency

6. **Regenerate all data:**
   ```bash
   # Update regenerate script with correct transformation flags
   ./scripts/regenerate_all_data.sh
   ```

## Files Modified on This Branch

### Core Implementation
- `odd_agents/utils.py`: Auto-crop function (+121 lines)
- `scripts/extract_windows.py`: 
  - BEV transformation parameters (rotation, flip)
  - Removed density channel (kept occupancy, height, roughness)
  - Data-source specific transformation pipeline
- `tests/test_bev_cropping.py`: Comprehensive test suite (13 tests, all passing)

### Data Organization
- **Reorganized**: `data/processed/` → `data/production/`
- **Production data**: `data/production/sim_1_0/` (62 windows, 3 BEV channels)
- **Test data**: `data/test/sim/` (6 windows for manual testing)
- **Archived**: Old analysis results moved to `data/archive/`

### Documentation
- `data/README.md`: Updated for new structure
- `data/DATA_VERSIONS.md`: Version tracking schema
- `docs/BEV_TRANSFORMATION_STATUS.md`: This file

## Performance Notes

### Current Accumulated Data
- BEV rendering: ~0.5s per window
- Point cloud size: ~50K-100K points (accumulated)
- File sizes: 6-12KB per BEV channel

### Expected Per-Scan Data
- BEV rendering: ~0.2s per window (fewer points)
- Point cloud size: ~10K-20K points (single scan)
- File sizes: Similar or smaller
- **Quality:** Much better, no aliasing

## Next Actions

### Immediate (Data Collection)
1. [ ] Check available LiDAR topics on real robot
2. [ ] Identify per-scan topic in base_link frame
3. [ ] Re-record test bagfiles with new topic
4. [ ] Verify data structure matches sim data

### Code Updates (After per-scan data ready)
1. [ ] Update TOPIC_MAPS in `extract_windows.py` (change `/point_cloud2` topic)
2. [ ] Test BEV orientation with camera comparison
3. [ ] Apply rotation/flip if needed (may differ from sim)
4. [ ] Test with single bagfile
5. [ ] Run full test suite
6. [ ] Regenerate all real production data

### Future Enhancements (Optional)
- [ ] Add BEV size as configurable parameter
- [ ] Support multiple LiDAR sources simultaneously
- [ ] Add temporal aggregation (2-3 scans) for density
- [ ] Adaptive cropping based on robot velocity

## References

**Related Issues:**
- Aliasing artifacts in transformed BEVs
- Robot not centered in real data BEVs
- Data quality degradation with accumulated clouds

**Git History:**
```bash
git log --oneline feature/phase1.1-bev-enhancement
b3ce805 feat: Add horizontal flip parameter for sim data orientation fix
d5c7ac1 feat: Add configurable BEV rotation for sim data orientation
5bb8ac0 docs: Add comprehensive status doc for BEV transformation work
c9ccfcb wip: Attempted BEV transformations - needs per-scan LiDAR data
e3445fe refactor: Transform BEV images instead of point clouds (FAILED - aliasing)
12e19aa fix: Eliminate BEV aliasing with vectorized transform (FAILED - still aliasing)
d004b10 feat: Add odom->base_link transformation (FAILED - aliasing)
93f7db3 fix: CRITICAL - Preserve ALL obstacles in BEV cropping (WORKING ✅)
f267abe fix: CRITICAL - Preserve robot center position in BEV cropping (WORKING ✅)
```

**Key Learnings:**
- ❌ Transforming accumulated/voxelized point clouds causes severe aliasing
- ❌ Transforming rendered BEV images (even with high-quality interpolation) causes aliasing on sparse data
- ✅ Auto-crop works perfectly, preserves 100% of obstacles
- ✅ Simple rotation + flip on clean single-scan data works well (sim proven)
- ⏳ Need per-scan LiDAR data for real robot to avoid aliasing

**Contact:** Check with robot team for LiDAR configuration and available topics
