# Real Data Motion Fix: Position-Derived Velocity & Acceleration

## Problem Statement

The real robot rosbag data has **zeros for acceleration and gyro data** (`accel_x`, `accel_y`, `accel_z`, `gyro_x`, `gyro_y`, `gyro_z`), while roll/pitch/yaw orientation data is present and valid.

This causes the motion analysis pipeline to incorrectly report:
- `max_accel_mps2: 0.0`
- `max_angular_velocity_radps: 0.0`
- Robot always classified as "stationary"

**Simulation data works correctly** - has valid IMU acceleration and gyro values.

## Root Cause

The Go2 robot's IMU data is either:
1. Not being published on the expected topic
2. Using a different message format than expected
3. Actually zeros in the source rosbag (sensor issue during recording)

The odometry velocities (`odom_vx`, `odom_vy`, etc.) are also zeros.

## Available Data

The real rosbag data DOES have:
- **Position data**: `odom_msg.pose.pose.position` (x, y, z) - currently NOT extracted
- **Orientation data**: `odom_msg.pose.pose.orientation` → roll, pitch, yaw ✓
- **Timestamps**: accurate relative timestamps ✓

## Proposed Solution

### Option A: Derive Motion from Position (Recommended)

Extract position from odometry and compute velocity/acceleration by differentiation.

**Changes to `scripts/extract_windows.py`:**

1. **Add position fields to motion_data:**
```python
motion_data = {
    # ... existing fields ...
    "pos_x": [],
    "pos_y": [],
    "pos_z": [],
    # New derived fields (computed at end)
    "derived_vx": [],
    "derived_vy": [],
    "derived_speed": [],
    "derived_accel": [],
}
```

2. **Extract position in odometry loop:**
```python
for t, odom_msg in odom_msgs:
    # ... existing extraction ...
    
    # Add position extraction
    pos = odom_msg.pose.pose.position
    motion_data["pos_x"].append(pos.x)
    motion_data["pos_y"].append(pos.y)
    motion_data["pos_z"].append(pos.z)
```

3. **Compute derived velocity and acceleration:**
```python
def _compute_derived_motion(motion_data):
    """Compute velocity and acceleration from position differences."""
    timestamps = motion_data["timestamps"]
    pos_x = motion_data["pos_x"]
    pos_y = motion_data["pos_y"]
    
    if len(timestamps) < 2:
        return
    
    # Compute velocity by finite differences
    derived_vx = []
    derived_vy = []
    for i in range(len(timestamps) - 1):
        dt = timestamps[i+1] - timestamps[i]
        if dt > 1e-6:
            vx = (pos_x[i+1] - pos_x[i]) / dt
            vy = (pos_y[i+1] - pos_y[i]) / dt
        else:
            vx, vy = 0.0, 0.0
        derived_vx.append(vx)
        derived_vy.append(vy)
    derived_vx.append(derived_vx[-1] if derived_vx else 0.0)  # Pad last
    derived_vy.append(derived_vy[-1] if derived_vy else 0.0)
    
    # Compute speed magnitude
    derived_speed = [math.sqrt(vx**2 + vy**2) for vx, vy in zip(derived_vx, derived_vy)]
    
    # Compute acceleration by differentiating velocity
    derived_accel = []
    for i in range(len(timestamps) - 1):
        dt = timestamps[i+1] - timestamps[i]
        if dt > 1e-6:
            ax = (derived_vx[i+1] - derived_vx[i]) / dt if i+1 < len(derived_vx) else 0.0
            ay = (derived_vy[i+1] - derived_vy[i]) / dt if i+1 < len(derived_vy) else 0.0
            accel_mag = math.sqrt(ax**2 + ay**2)
        else:
            accel_mag = 0.0
        derived_accel.append(accel_mag)
    derived_accel.append(derived_accel[-1] if derived_accel else 0.0)  # Pad last
    
    motion_data["derived_vx"] = derived_vx
    motion_data["derived_vy"] = derived_vy
    motion_data["derived_speed"] = derived_speed
    motion_data["derived_accel"] = derived_accel
```

4. **Apply smoothing (optional):**
Position differentiation is noisy. Consider:
- Moving average filter on position before differentiation
- Low-pass filter on derived velocity
- Savitzky-Golay filter for smoother derivatives

### Changes to Motion Tool (`odd_agents/tools/motion.py`)

Update the motion tool to use derived values when IMU values are zero:

```python
# Check if IMU data is valid or all zeros
imu_valid = any(abs(ax) > 1e-6 for ax in accel_x) or any(abs(ay) > 1e-6 for ay in accel_y)

if imu_valid:
    # Use IMU data (existing logic)
    horiz_accel = [math.sqrt(ax**2 + ay**2) for ax, ay in zip(accel_x, accel_y)
                   if abs(ax) > 1e-6 or abs(ay) > 1e-6]
    peak_horiz_accel = max(horiz_accel) if horiz_accel else 0.0
else:
    # Fall back to position-derived acceleration
    derived_accel = motion_data.get("derived_accel", [])
    peak_horiz_accel = max(derived_accel) if derived_accel else 0.0
    
    # Also get derived speed
    derived_speed = motion_data.get("derived_speed", [])
    peak_speed = max(derived_speed) if derived_speed else 0.0
```

## Implementation Steps

1. **Phase 1: Extraction Update** (scripts/extract_windows.py)
   - Add position extraction from odom pose
   - Implement `_compute_derived_motion()` function
   - Call after IMU extraction to populate derived fields
   - All motion JSON files will have new fields

2. **Phase 2: Motion Tool Update** (odd_agents/tools/motion.py)
   - Check if IMU data is valid (non-zero)
   - Fall back to derived fields when IMU is zeros
   - Update `max_speed_mps` to use derived speed when available

3. **Phase 3: Re-extract Real Data**
   - Re-run extraction on real rosbags
   - Verify derived values are populated
   - Test pipeline on real_2win

4. **Phase 4: Validation**
   - Compare derived motion metrics to expected behavior
   - Verify stationary detection works correctly
   - Check that moving windows show non-zero velocity/acceleration

## Backward Compatibility

- New fields are additive - old motion JSON files without them still work
- Motion tool falls back gracefully when derived fields missing
- Simulation data continues to use IMU values (preferred)

## Testing

```bash
# Re-extract real test data with new fields
python scripts/extract_windows.py --rosbag data/raw_rosbags/real/173442.db3 \
    --output data/test/real_2win_fixed --run-id real_173442_fixed

# Verify derived fields present
python -c "import json; d=json.load(open('data/test/real_2win_fixed/motion_*.json')); print(d.get('derived_speed', 'MISSING'))"

# Run pipeline
python scripts/run_odd_analysis.py --scenario real_2win_fixed
```

## TODO

- [ ] Implement position extraction in extract_windows.py
- [ ] Implement _compute_derived_motion() function
- [ ] Update motion tool to use derived values
- [ ] Re-extract real production data
- [ ] Validate on real_2win test set
- [ ] Consider adding angular velocity from yaw differentiation
