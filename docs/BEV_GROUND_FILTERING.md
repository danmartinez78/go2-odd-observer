# BEV Ground Filtering Enhancement

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

**Version 1.1** (2025-11-23)
- Added ground threshold filtering (10cm)
- Updated perception agent prompt to clarify filtered occupancy
- Documentation created

**Version 1.0** (Initial)
- All-points occupancy map (ground included)
