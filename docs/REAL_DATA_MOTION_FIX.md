# Real Data Motion Fix: Position-Derived Velocity

**STATUS: ✅ IMPLEMENTED** (December 1, 2025)

## Summary

Real robot rosbag data often has zeros for IMU data because `go2_interfaces` wasn't being sourced during extraction. The fix involves:
1. **Always source ROS2 + go2_ros2_sdk** before extraction
2. **Derive speed from position** as primary measurement (more accurate than odometry velocity)
3. **Derive yaw_rate from orientation** as fallback for angular velocity

## Problem Statement

The real robot rosbag data has **zeros for acceleration and gyro data** (`accel_x`, `accel_y`, `accel_z`, `gyro_x`, `gyro_y`, `gyro_z`), while roll/pitch/yaw orientation data is present and valid.

This causes the motion analysis pipeline to incorrectly report:
- `max_accel_mps2: 0.0`
- `max_angular_velocity_radps: 0.0`
- Robot always classified as "stationary"

**Simulation data works correctly** - has valid IMU acceleration and gyro values.

## Root Cause (IDENTIFIED)

The Go2 robot's IMU data uses a custom message type from `go2_interfaces`. When extracting data without sourcing the workspace, the IMU messages can't be deserialized.

**Solution:** Always source both environments before extraction:
```bash
source /opt/ros/humble/setup.bash
source /workspaces/go2-odd-observer/go2_ros2_sdk/install/setup.bash
```

## Available Data

The real rosbag data has:
- **Position data**: `odom_msg.pose.pose.position` (x, y, z) ✓ (now extracted)
- **Orientation data**: `odom_msg.pose.pose.orientation` → roll, pitch, yaw ✓
- **Timestamps**: accurate relative timestamps ✓
- **IMU data**: Available when `go2_interfaces` is properly sourced ✓

## Implemented Solution

### Derive Speed from Position (Primary)

We derive speed from position differentiation as the **primary** speed measurement because:
- Position data is always available and accurate
- Odometry velocity fields are often zeros
- Position-derived speed matches actual robot motion

### New Motion Data Fields

**Added to motion JSON files:**
```python
{
    # Position from odometry
    "pos_x": [...],
    "pos_y": [...],
    "pos_z": [...],
    
    # Derived fields (computed from position)
    "derived_speed": [...],      # Speed magnitude (m/s)
    "derived_yaw_rate": [...],   # Angular velocity (rad/s)
}
```

**NOT included (intentionally):**
- `derived_vx`, `derived_vy` - intermediate values, not needed
- `derived_accel` - double-differentiation is too noisy, IMU is better when available

### Key Implementation Details

**MIN_DT_THRESHOLD (10ms):**
Real robot odometry sometimes has duplicate timestamps or very small dt values. We filter these to avoid unrealistic speed calculations:
```python
MIN_DT_THRESHOLD = 0.01  # 10ms minimum

# Only compute speed if dt is large enough
if dt >= MIN_DT_THRESHOLD:
    speed = math.sqrt(vx**2 + vy**2)
```

**MAX_PLAUSIBLE_SPEED (5 m/s):**
Go2 robot max speed is ~3.5 m/s. Values above 5 m/s are clipped as noise.

### Motion Tool v10.0.0 (`odd_agents/tools/motion.py`)

**Data source strategy:**
| Metric | Primary Source | Fallback |
|--------|---------------|----------|
| **Speed** | `derived_speed` (always) | N/A |
| **Acceleration** | IMU `accel_x/y` | `None` (unavailable) |
| **Angular velocity** | IMU `gyro_z` | `derived_yaw_rate` |
| **Roll/Pitch** | Orientation | Always available |
| **Stationary** | `derived_speed < 0.05` | N/A |

**Output includes `data_availability` dict:**
```json
{
  "data_availability": {
    "speed": "derived",
    "acceleration": "imu",      // or "unavailable"
    "angular_velocity": "imu",  // or "derived"
    "orientation": "available"
  }
}
```

## Regeneration Command

**IMPORTANT:** Always source ROS2 + go2_ros2_sdk before extraction!

```bash
# Regenerate all production and test data
bash scripts/regenerate_all_data.sh

# Or manually for a single scenario:
source /opt/ros/humble/setup.bash
source /workspaces/go2-odd-observer/go2_ros2_sdk/install/setup.bash

python scripts/extract_windows.py \
  --rosbag data/raw_rosbags/real/collection_20251122_173442 \
  --output data/production/real_173442 \
  --window-length 2.0 \
  --stride 2.0 \
  --run-id real_173442 \
  --data-source real
```

## Backward Compatibility

- New fields are additive - old motion JSON files without them still work
- Motion tool falls back gracefully when derived fields missing
- Simulation data also gets derived fields (for consistency)

## Completed Tasks

- [x] Implement position extraction in extract_windows.py
- [x] Implement `_compute_derived_motion()` function with MIN_DT_THRESHOLD
- [x] Update motion tool v10.0.0 to use derived values
- [x] Create regeneration script (`regenerate_all_data.sh`)
- [x] Add derived_yaw_rate for angular velocity fallback
- [x] Test on sim_2win and real_2win

## Commit Reference

- `6e65df6` - feat(motion): add derived_speed and derived_yaw_rate fields
