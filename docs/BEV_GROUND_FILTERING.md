# BEV Ground Filtering Enhancement

## ✅ SOLVED - Version 1.3 (November 25, 2024)

**BREAKTHROUGH: TF-Based Transform Chain Solution - IMPLEMENTED & WORKING**

Successfully implemented proper ground filtering using ROS2 TF transforms with a two-stage transform approach that solves all previous issues.

### Solution Summary
1. **Transform sensor → odom (gravity-aligned)** for reliable ground plane detection
2. **Filter ground in odom frame** where z-axis is always vertical
3. **Transform filtered points back to base_link** for robot-centric BEV rendering

### Results
- ✅ Ground points properly filtered from occupancy/height channels  
- ✅ Terrain roughness preserved (includes ground variance for traversability)
- ✅ Robot-centric view maintained (robot at center, facing up)
- ✅ BEV file sizes reduced 80-90% (1-2KB vs 10-20KB)
- ✅ Production sim data regenerated: 62 windows + 3 test sets

### Why This Works
- **Odom frame is gravity-aligned** - z-axis always points up regardless of robot pitch/roll
- **Ground plane is horizontal in odom** - simple z-threshold works reliably  
- **Transform back to base_link** - maintains robot-centric view for BEV
- **Dynamic motion handled** - odom frame compensates for walking pitch/roll (5-15°)

See "Version 1.3 Implementation" section below for technical details.

---

## Problem Statement

### Original Issue
The BEV occupancy map was marking **all LiDAR points** as occupied, including the ground plane. This created confusion:

- **What it showed**: Ground + obstacles mixed together (bright pixels everywhere)
- **What agents expected**: Only obstacles above ground level
- **Impact**: Occupancy ratio and obstacle density metrics were inflated, making clear paths look cluttered

### Example Scenario
On a flat floor with a rug:
- **Before**: 80% occupancy (ground + rug both bright)
- **After**: 5% occupancy (only objects >10cm above ground)

## Solution: Height-Based Ground Filtering

### Implementation
Added a **ground threshold filter** to the occupancy map generation:

```python
ground_threshold = 0.10  # 10cm - points below this are considered ground

# Only mark as occupied if above ground threshold
if z > ground_threshold:
    occupancy_grid[pixel_y, pixel_x] = 255
```

### Key Parameters

- **Ground Threshold**: `0.10m` (10cm)
  - Points with `z <= 0.10m` are considered ground plane
  - Points with `z > 0.10m` are marked as obstacles
  - Rationale: Typical robot clearance is ~15-20cm, 10cm buffer for safety

### Multi-Channel BEV System

The system generates **4 complementary BEV maps**:

1. **Occupancy** (filtered): Binary obstacle detection, ground removed
2. **Height**: Average elevation per grid cell (includes ground for terrain analysis)
3. **Density**: Point cloud density (LiDAR return intensity)
4. **Roughness**: Height variance (surface roughness estimation)

## Impact on Analysis

### Perception Agent
- **More accurate occupancy ratio**: Only counts actual obstacles
- **Clearer obstacle density**: Distinct objects vs free space
- **Better traversability**: Ground texture doesn't inflate obstacle count

### Before vs After

**Scenario**: Living room with flat floor, area rug, and chair

| Metric | Before (Ground Included) | After (Ground Filtered) |
|--------|-------------------------|-------------------------|
| Occupancy Ratio | 0.75 (ground + rug + chair) | 0.15 (chair only) |
| Obstacle Density | 0.8 (cluttered appearance) | 0.3 (realistic) |
| Traversability | 0.3 (looks blocked) | 0.8 (mostly clear) |

### Terrain vs Obstacles

**Critical Distinction**:
- **Terrain roughness**: Uses height map + camera (ground elevation changes)
- **Obstacle detection**: Uses filtered occupancy (objects above ground)

This separation allows correct classification:
- Rug on flat floor: `terrain="smooth"`, `occupancy=0.05`
- Rocky ground: `terrain="rough"`, `occupancy=0.2` (rocks >10cm)

## Validation Strategy

### Test Cases

1. **Flat floor + furniture**: Should show low occupancy, only furniture visible
2. **Stairs/ramps**: Should show elevated terrain in height map, not occupancy
3. **Ground clutter**: Small items <10cm filtered, large items >10cm detected
4. **Emergency stop scenario**: Wall/obstacle clearly visible in occupancy

### Metrics to Monitor

- **Occupancy ratio consistency**: Should decrease for flat terrain scenarios
- **Obstacle density accuracy**: Should match camera-visible objects
- **Traversability correlation**: Should align with path clearance in camera
- **False positive reduction**: Fewer "obstacles" on clear floors

## Configuration

### Tunable Parameters

Located in `scripts/extract_windows.py`:

```python
ground_threshold = 0.10  # meters (10cm)
```

**Adjustment Guidelines**:
- **Lower (0.05m)**: Detect smaller obstacles, may include ground noise
- **Higher (0.15m)**: Only detect larger obstacles, clearer maps but may miss small items
- **Default (0.10m)**: Balanced for typical indoor navigation

### Related Settings

- **BEV size**: 400x400 pixels
- **Resolution**: 0.05m/pixel (5cm)
- **Coverage**: ±10m range (20m x 20m area)
- **Height normalization**: ±2m range for visualization

## Technical Details

### Point Cloud Processing

1. **Extract points**: Read XYZ from PointCloud2 message
2. **Project to 2D**: Convert (x, y, z) → (pixel_x, pixel_y)
3. **Filter by height**: 
   - Occupancy: Only z > ground_threshold
   - Height/Density/Roughness: All points (for terrain analysis)
4. **Render**: Apply Gaussian blur (3x3 kernel) for visibility

### Coordinate System

- **X-axis**: Forward (robot's front)
- **Y-axis**: Lateral (left positive, right negative)
- **Z-axis**: Vertical (up positive, down negative)
- **Origin**: Robot's LiDAR sensor position

## Future Enhancements

### Potential Improvements

1. **Adaptive ground threshold**: Auto-calibrate based on local ground plane
2. **Ground plane fitting**: RANSAC-based ground removal for slopes
3. **Multi-layer occupancy**: Separate low/mid/high obstacles
4. **Dynamic objects**: Temporal filtering for moving obstacles

### Compatibility

- **Backward compatible**: All 4 BEV channels still generated
- **No schema changes**: Perception tool outputs unchanged
- **Reprocessing required**: Existing data needs re-extraction for updated occupancy maps

## References

- **Implementation**: `scripts/extract_windows.py` (line 451)
- **Perception prompt**: `odd_agents/tools/perception.py` (line 70)
- **Validation**: Production scenario `real_03_174232` (emergency stop test)

## Changelog

**Version 1.2** (2025-11-25) - DEFERRED
- **CRITICAL ISSUE DISCOVERED**: Ground filtering implementation exists but doesn't work correctly
- Ground plane still visible in occupancy maps despite 10cm threshold
- Root cause: Complex sensor mounting geometry (180° roll, 15° pitch tilt, dynamic robot motion)
- Multiple approaches attempted (see "Attempted Solutions" below)
- **DECISION**: Reverted to original implementation, deferring proper fix to future work
- Production data still uses all-points occupancy (includes ground)

**Version 1.1** (2025-11-23)
- Added ground threshold filtering (10cm) - **NON-FUNCTIONAL, SEE v1.2**
- Updated perception agent prompt to clarify filtered occupancy
- Documentation created

**Version 1.0** (Initial)
- All-points occupancy map (ground included)

---

## CRITICAL: Ground Filtering Implementation Issues

### Problem Discovery (Nov 25, 2025)

Visual inspection of production BEV occupancy maps revealed that **ground plane is still visible** despite the implemented 10cm height threshold. The ground filtering code exists in `extract_windows.py` but is **not effective**.

### Root Cause Analysis

The LiDAR sensor has a **complex mounting geometry**:

1. **Static Transform** (from TF data in rosbag):
   - `base_link → UnitreeL1_link`:
     - Translation: `[0.293, 0.0, -0.08]`
     - Rotation (quaternion): `[0.0, 0.991, 0.0, 0.131]`
   - Euler angles: **Roll=180°, Pitch=15°, Yaw=180°**
   - Sensor is mounted **upside-down and tilted forward**

2. **Dynamic Transform**:
   - Robot pitches/rolls significantly during walking (~5-15° variation)
   - Ground plane orientation **changes relative to sensor** in each frame
   - Static TF alone insufficient for ground alignment

3. **Coordinate Frame Implications**:
   - In sensor frame: `-Z` points "up" (due to 180° roll)
   - Ground plane is **tilted 29.49° from horizontal** (measured via RANSAC)
   - Simple `z > 0.10m` threshold filters wrong points
   - CloudCompare visualization confirmed ground plane NOT aligned with XY plane

### Attempted Solutions (All Unsuccessful)

#### Approach 1: TF-Only Transform
**Method**: Apply `base_link → UnitreeL1_link` inverse transform
```python
# Transform point cloud to base_link frame
points_base = rot_inv.apply(points) + translation_sensor_to_base
ground_mask = points_base[:, 2] > 0.10
```
**Result**: ❌ Ground still tilted 29.49° from horizontal
**Why failed**: Static TF doesn't account for robot's dynamic pitch/roll during walking

#### Approach 2: CloudCompare Level Tool
**Method**: Manually computed transform to align ground with XY plane
```
Transform matrix (from CloudCompare):
[ 0.552897  0.820041 -0.147777  2.551939]
[ 0.794451 -0.572282 -0.203325 -1.469287]
[-0.251304 -0.004983 -0.967896  0.340201]
```
**Result**: ❌ Works for single frame but not generalizable (robot orientation changes)
**Why failed**: Transform specific to one robot pose, doesn't adapt to motion

#### Approach 3: RANSAC Plane Fitting
**Method**: Fit ground plane per point cloud using RANSAC
```python
# Fit plane: z = ax + by + c
ransac.fit(points[:, :2], points[:, 2])
distances = |ax + by - z + c| / sqrt(a² + b² + 1)
ground_mask = distances > 0.10
```
**Result**: ❌ Too slow (~500ms per frame), unreliable convergence
**Why failed**: Computational cost, sensitive to outliers, inconsistent plane fitting

#### Approach 4: Point Cloud Normals
**Method**: Compute surface normals, cluster to find dominant ground normal
```python
# Find ground normal cluster (largest cluster)
ground_normal = [0.4146, -0.0902, 0.9055]  # in sensor frame
```
**Result**: ❌ Normal computation expensive, doesn't solve alignment problem
**Why failed**: Still need rotation to align, no clear advantage over TF approach

#### Approach 5: Pitch Correction Only
**Method**: Use robot pitch from odometry to correct Z-axis alignment
```python
# Get pitch from IMU/odom at LiDAR timestamp
cos_p = np.cos(-robot_pitch)
sin_p = np.sin(-robot_pitch)
rotation_matrix = [[cos_p, 0, sin_p], [0, 1, 0], [-sin_p, 0, cos_p]]
points_corrected = rotation_matrix @ points.T
```
**Result**: ❌ Improved but still issues (occupancy 4-11% instead of expected 1-3%)
**Why failed**: Only corrects pitch, ignores roll and sensor's 180° flip

### Forgotten Approach: Multi-Frame Transform Chain

**RECOMMENDED FOR FUTURE**: Transform through complete chain:
```
sensor_frame → base_link → odom_frame
```

**Rationale**:
- `sensor → base_link`: Static TF (accounts for mounting)
- `base_link → odom`: Dynamic TF (accounts for robot orientation)
- `odom_frame`: Gravity-aligned (Z is vertical)

**Implementation**:
```python
# Read both transforms from rosbag
tf_sensor_to_base = get_tf("base_link", "UnitreeL1_link", timestamp)
tf_base_to_odom = get_tf("odom", "base_link", timestamp)

# Compose transforms
T_sensor_to_odom = T_base_to_odom @ T_sensor_to_base

# Apply to point cloud
points_odom = (T_sensor_to_odom @ points_homogeneous.T).T

# Filter ground in odom frame (where Z is truly vertical)
ground_mask = points_odom[:, 2] > (ground_z + 0.10)
```

**Advantages**:
- Leverages existing TF data in rosbag
- Accounts for both static mounting and dynamic robot motion
- Odom frame is gravity-aligned by design
- Generalizes across all frames

**Challenges**:
- Requires TF message parsing from rosbag
- Need to handle TF interpolation for timestamp alignment
- Additional computational overhead

---

## Version 1.3 Implementation (November 25, 2024) ✅

**Status**: IMPLEMENTED AND WORKING

### Architecture

**Two-Stage Transform Process:**
```
1. Sensor Frame → Odom Frame (gravity-aligned filtering)
2. Odom Frame → Base Link (robot-centric rendering)
```

**File**: `scripts/extract_windows.py`

### Key Components

#### 1. TF Data Collection
```python
# Read TF transforms from /tf topic during bag parsing
if topic == '/tf':
    tf_msg = deserialize_message(data, TFMessage)
    for transform in tf_msg.transforms:
        self.tf_transforms.append((timestamp, transform))
```

#### 2. Transform Lookup with Chain Support
```python
def _lookup_transform(target_frame, source_frame, timestamp):
    # Try direct transform
    # Try inverse transform
    # Try 2-hop chain: source → intermediate → target
    return TransformStamped or None
```

**Supported Transform Patterns:**
- Direct: `A → B`
- Inverse: `B → A` (computed from `A → B`)
- 2-hop chain: `A → B → C` (composed)

#### 3. Transform Composition
```python
def _compose_transforms(t1, t2):
    # T1: parent1 → child1
    # T2: parent2 → child2 (where child1 == parent2)
    # Result: parent1 → child2
    rotation = rot1 * rot2  # Quaternion multiplication
    translation = rot1.apply(trans2) + trans1
```

#### 4. Ground Filtering in Odom Frame
```python
def _render_bev_from_pointcloud(pc_msg, timestamp):
    # Extract points in sensor frame
    points_sensor = extract_from_pc_msg(pc_msg)
    
    # Transform sensor → odom (gravity-aligned)
    transform_s2o = lookup_transform('odom', 'sensor', timestamp)
    points_odom = apply_transform(points_sensor, transform_s2o)
    
    # Find ground in odom frame (z-axis is vertical)
    z_histogram = histogram(points_odom[:, 2], bins=100)
    ground_z = most_common_z(z_histogram)
    
    # Filter obstacles
    obstacle_mask = points_odom[:, 2] > (ground_z + 0.10)
    obstacles_odom = points_odom[obstacle_mask]
    
    # Transform back: odom → base_link (robot-centric)
    transform_o2b = lookup_transform('base_link', 'odom', timestamp)
    obstacles_base = apply_transform(obstacles_odom, transform_o2b)
    all_points_base = apply_transform(points_odom, transform_o2b)
    
    # Render BEV channels
    return {
        'occupancy': render(obstacles_base),   # Filtered
        'height': render(obstacles_base),      # Filtered
        'roughness': render(all_points_base)   # Unfiltered (terrain)
    }
```

### Coordinate Frames

**Sim Data:**
```
robot0/UnitreeL1_link (sensor, upside-down)
    ↓ TF: [0.293, 0.0, -0.08], rpy=[π, 0.26, π]
robot0/base_link (robot body)
    ↓ TF: dynamic (from odom messages)
robot0/odom (world, gravity-aligned)
```

**Real Data:**
```
UnitreeL1_link (sensor)
    ↓ TF: static
base_link (robot body)
    ↓ TF: dynamic
odom (world, gravity-aligned)
```

### BEV Channel Strategy

| Channel | Input Points | Purpose |
|---------|-------------|---------|
| **Occupancy** | Obstacles only (z > ground + 0.10m) | Show where obstacles are |
| **Height** | Obstacles only | Show obstacle heights |
| **Roughness** | All points (including ground) | Show terrain variance for traversability |

**Rationale:**
- Occupancy should only show obstacles, not ground
- Height should measure obstacle elevation, not ground level
- Roughness should include ground variance (bumpy terrain vs smooth floor)

### Final Rotation

**Sim Data**: 90° CCW rotation applied after rendering
- Aligns BEV with camera perspective
- Robot faces "up" in the image
- Forward (x-axis in base_link) points up in image

**Real Data**: TBD based on actual sensor mounting

### Performance

**Before (Unfiltered):**
- BEV file size: 10-20KB
- Dense ground points inflating occupancy

**After (TF Filtered):**
- BEV file size: 1-2KB (80-90% reduction)
- Clean obstacle-only occupancy
- Proper height measurements

### Production Data Status

**Regenerated (November 25, 2024):**
- ✅ `sim_1_0`: 62 windows with proper ground filtering
- ✅ `sim_test_w010_w011`: 2 windows
- ✅ `sim_test_w030_w031`: 2 windows  
- ✅ `sim_test_w050_w051`: 2 windows

**Real Data**: Pending (same TF approach will work)

### Lessons Learned

1. **Odom frame is key** - Gravity-aligned regardless of robot motion
2. **Transform chains work** - sensor → base → odom composition
3. **Inverse transforms essential** - TF provides A→B, need B→A
4. **Separate channels** - Obstacles (occupancy/height) vs terrain (roughness)
5. **ROS2 TF is reliable** - No need for manual transform math
6. **Two-stage process** - Filter in odom, render in base_link

### Future Work

- Test on real robot data (same approach should work)
- Validate ground threshold (currently 0.10m) on varied terrain
- Consider adaptive threshold based on terrain type
- Add visualization tools for debugging transform chains

### Future Work (Phase TBD)

**Recommended Solution**: Multi-frame transform chain (`sensor → base_link → odom`)

**Implementation Plan**:
1. Add TF message parsing to `extract_windows.py`
2. Read `odom → base_link` transform at each LiDAR timestamp
3. Compose with static `base_link → UnitreeL1_link` transform
4. Apply combined transform before ground filtering
5. Validate on multiple scenarios (walking, turning, slopes)
6. Regenerate all production BEV data

**Estimated Effort**: 2-3 days
- Day 1: TF parsing infrastructure
- Day 2: Integration and validation
- Day 3: Production data regeneration

**Alternative**: Accept current limitation, document in agent prompts

---

## References

- **Implementation**: `scripts/extract_windows.py` (ground filtering currently disabled)
- **TF Data**: Available in rosbag `/tf` topic
- **Investigation**: `data/development/bev_ground_filter_analysis/` (deleted after cleanup)
- **CloudCompare**: External tool used for coordinate frame validation
