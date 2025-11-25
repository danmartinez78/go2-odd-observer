# BEV Transformation Status & Next Steps

**Date:** November 24, 2025  
**Branch:** `feature/phase1.1-bev-enhancement`  
**Status:** ⚠️ BLOCKED - Waiting for per-scan LiDAR data

## Problem Summary

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

### Working Code (Keep)
- `odd_agents/utils.py`: `auto_crop_bev()` function
- `tests/test_bev_cropping.py`: Full test suite (13 tests, all passing)
- `scripts/extract_windows.py`: Auto-crop integration (lines 432-435)

### Code to Update (When per-scan data available)
**File:** `scripts/extract_windows.py`

**Lines 70-85:** Update TOPIC_MAPS
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

**Lines 530-650:** Remove transformation code
- Delete `_get_robot_pose()` method (lines 463-487)
- Delete `_transform_point_odom_to_baselink()` method (lines 489-513)
- In `_render_bev_from_pointcloud()`:
  - Remove `robot_pose` parameter
  - Remove transformation block (lines 630-664)
  - Keep simple rendering as-is

**Line 469:** Update extraction call
```python
# Current (with transformation):
robot_pose = self._get_robot_pose(center_time)
bev_features = self._render_bev_from_pointcloud(pc_msg, robot_pose)

# Change to (no transformation needed):
bev_features = self._render_bev_from_pointcloud(pc_msg)
```

## Testing Plan (Once Fixed)

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
     --output data/test_perscan \
     --data-source real
   ```

4. **Visual inspection:**
   - Check BEV height images for aliasing
   - Verify robot centered in images
   - Compare with original clean sim BEVs

5. **Regenerate all data:**
   ```bash
   ./scripts/regenerate_all_data.sh
   ```

## Files Modified on This Branch

### Core Implementation
- `odd_agents/utils.py`: Auto-crop function (+121 lines)
- `scripts/extract_windows.py`: Transformation attempts (+130 lines to remove)
- `tests/test_bev_cropping.py`: Comprehensive test suite (new file, 171 lines)

### Test Data
- `tests/fixtures/bev_samples/`: 4 real robot BEV samples
- `data/test_crop_fix/`: Validation images (BEV_Test_1/2)
- `data/test_transform/`: Latest transformation test output (has aliasing)

### Documentation
- This file

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

### Code Updates (After data ready)
1. [ ] Update TOPIC_MAPS in `extract_windows.py`
2. [ ] Remove transformation code (3 blocks)
3. [ ] Test with single bagfile
4. [ ] Run full test suite
5. [ ] Regenerate all production data
6. [ ] Merge to dev

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
c9ccfcb wip: Attempted BEV transformations - needs per-scan LiDAR data
e3445fe refactor: Transform BEV images instead of point clouds to eliminate aliasing
12e19aa fix: Eliminate BEV aliasing artifacts with vectorized transform and proper rounding
d004b10 feat: Add odom->base_link transformation for real robot accumulated point clouds
93f7db3 fix: CRITICAL - Preserve ALL obstacles in BEV cropping
f267abe fix: CRITICAL - Preserve robot center position in BEV cropping
```

**Contact:** Check with robot team for LiDAR configuration and available topics
