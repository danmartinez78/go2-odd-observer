# Bagfile Audit Findings - Phase 0 Data Investigation

## Executive Summary
**CRITICAL FINDING**: Neither `/odom` nor `/go2_states` topics contain velocity data, despite both having velocity fields in their message definitions. The robot is clearly moving (odometry position changes), but velocity fields remain at 0.0 throughout entire recordings.

## Topics Analysis

### Real Robot (`collection_20251122_173442`)

#### Available Topics
| Topic | Type | Rate | Messages | Status |
|-------|------|------|----------|--------|
| `/imu` | go2_interfaces/msg/IMU | 19.13 Hz | 1148 | ✅ Currently used |
| `/odom` | nav_msgs/msg/Odometry | 18.62 Hz | 1117 | ⚠️ Velocity not populated |
| `/camera/image_raw` | sensor_msgs/msg/Image | 12.38 Hz | 743 | ✅ Currently used |
| `/point_cloud2` | sensor_msgs/msg/PointCloud2 | 5.85 Hz | 351 | ✅ Currently used |
| `/tf` | tf2_msgs/msg/TFMessage | 19.53 Hz | 1172 | ❌ Not used |
| `/joint_states` | sensor_msgs/msg/JointState | 0.92 Hz | 55 | ⚠️ Very low rate, no velocities |
| `/tf_static` | tf2_msgs/msg/TFMessage | 0.02 Hz | 1 | ❌ Not used |

#### Detailed Findings

**`/odom` (Odometry)**
- **Position**: ✅ Populated and changing (e.g., [0.68, 0.42] → [1.77, 0.43])
- **Orientation**: ✅ Populated (quaternion)
- **Twist Linear (velocity)**: ❌ Always [0.0, 0.0, 0.0] throughout entire bag
- **Twist Angular**: ❌ Always [0.0, 0.0, 0.0]
- **Covariance**: All zeros
- **Conclusion**: Odometry position is from some source (likely visual odometry or EKF) but velocity not computed/published. Would need to run localization node to get velocity estimates.

**`/imu` (Custom go2_interfaces/msg/IMU)**
- Fields: `quaternion`, `gyroscope`, `accelerometer`, `rpy`, `temperature`
- ✅ All populated with real data
- Contains roll-pitch-yaw euler angles (not in standard sensor_msgs/msg/Imu)
- Custom message type specific to Go2 robot
- **Gyroscope**: Angular velocity in rad/s (e.g., [-0.008, 0.013, 0.002])
- **Accelerometer**: Linear acceleration in m/s² (e.g., [-0.116, -0.316, 9.658])

**`/joint_states` (Robot Leg Joints)**
- **Rate**: Only 0.92 Hz (very slow - updated ~every second)
- **Joints**: 12 joints (FL/FR/RL/RR × hip/thigh/calf)
- **Position**: ✅ Populated (e.g., [-0.034, 0.786, -1.555, ...])
- **Velocity**: ❌ Empty array
- **Effort**: ❌ Empty array
- **Conclusion**: Only useful for pose estimation, not motion analysis. Too slow for real-time velocity estimation.

**`/go2_states`**
- ❌ **NOT PUBLISHED ON REAL ROBOT**
- Only available in simulation

### Simulation (`sim/1`)

#### Available Topics (11 total)
Key differences from real robot:
- Topic names prefixed with `/robot0/`
- `/robot0/go2_states` exists (not on real robot)
- Standard `sensor_msgs/msg/Imu` (not custom go2_interfaces/msg/IMU)
- Two point clouds: `/robot0/point_cloud2_L1` and `/robot0/point_cloud2_extra`

#### Detailed Findings

**`/robot0/go2_states` (go2_interfaces/msg/Go2State)**
- **Rate**: 12.41 Hz
- **Fields**:
  - `mode`, `progress`, `gait_type`: All 0 throughout
  - `foot_raise_height`, `body_height`: 0.0
  - `position`: [0.0, 0.0, 0.0] - not populated
  - `velocity`: ❌ [0.0, 0.0, 0.0] - not populated despite field existing
  - `range_obstacle`: [0.0, 0.0, 0.0, 0.0]
  - `foot_force`: ✅ Changing values! (e.g., [51, 45, 24, 24] → [43, 50, 21, 28])
  - `foot_position_body`, `foot_speed_body`: All zeros
- **Conclusion**: Only foot_force field has useful data. Velocity field exists but not populated.

**`/robot0/odom` (Simulation Odometry)**
- Same as real robot: position populated, velocity = 0.0
- Sim likely populating position directly from ground truth, no velocity computation

**`/robot0/imu` (Standard ROS2 IMU)**
- Uses standard `sensor_msgs/msg/Imu` (not custom)
- Fields: `orientation`, `angular_velocity`, `linear_acceleration` (all with covariance)
- ✅ All populated
- Different structure than real robot's custom IMU message

**`/robot0/joint_states`**
- **Rate**: 12.41 Hz (much better than real robot's 0.92 Hz!)
- **Velocity/Effort**: Still not checked, but higher rate makes it more usable

**`/robot0/point_cloud2_extra`**
- Unknown what this second point cloud represents
- Same rate as L1 (12.41 Hz)
- Need to investigate if it's a different sensor or processing

## Key Insights for Architecture Redesign

### 1. Velocity Constraint is Impossible
- Neither `/odom` nor `/go2_states` provides velocity data
- Only option: **Differentiate odometry position** or **integrate IMU acceleration**
- Both approaches have significant error accumulation
- **Recommendation**: Remove velocity constraint from ODD, focus on acceleration limits from IMU

### 2. IMU is Primary Motion Sensor
- Most reliable high-rate data (19 Hz real, 12 Hz sim)
- Real robot has custom message with RPY (useful!)
- Can detect:
  - ✅ Acceleration spikes (collision detection)
  - ✅ Angular velocity changes (turning, spinning)
  - ✅ Orientation changes (tipping, unstable)
- **Cannot directly measure**: Linear velocity, distance traveled

### 3. Joint States Not Useful for Motion Analysis
- Real robot: Too slow (0.92 Hz), no velocities/efforts
- Could theoretically derive foot speed from position changes, but unreliable at 0.92 Hz
- Only useful for static pose estimation

### 4. Odometry Position Available
- Can compute velocity by differentiation: `v = Δpos / Δt`
- Error accumulates, but might be "good enough" for ODD compliance
- Rate: 18.62 Hz (real), 12.41 Hz (sim) - sufficient for differentiation
- **Recommendation**: Add odometry-derived velocity as "low confidence" metric

### 5. Real vs Sim Differences Matter
- go2_states not available on real robot (can't rely on it)
- IMU message types different (code must handle both)
- Joint state rates very different (0.92 Hz vs 12.41 Hz)
- **Must design for real robot constraints, sim is easier**

## Integration Recommendations

### HIGH PRIORITY
1. **Use Odometry Position for Velocity Estimation**
   - Differentiate position between consecutive messages
   - Calculate: `velocity = (pos_t - pos_t-1) / (time_t - time_t-1)`
   - Mark as "estimated velocity" in reports
   - Use for rough motion classification (stationary vs moving)

2. **Enhance IMU Collision Detection**
   - Already using IMU for collision
   - Add gyroscope analysis for spinning/tipping detection
   - Use RPY from custom message (real robot only)

### MEDIUM PRIORITY
3. **Add Foot Force Analysis (Sim Only)**
   - go2_states.foot_force shows real variation
   - Could detect: foot contact loss, uneven terrain, instability
   - Sim only - don't rely on it for production

4. **Investigate point_cloud2_extra (Sim)**
   - Determine what this second cloud represents
   - Might provide better obstacle detection

### LOW PRIORITY / FUTURE
5. **Transform (TF) Tree Usage**
   - Currently not using /tf topic
   - Could provide robot frame transformations
   - Useful for coordinate system conversions
   - Not critical for current ODD analysis

## Data Source Availability Matrix

| Data Type | Real Robot | Simulation | Reliability | Use Case |
|-----------|------------|------------|-------------|----------|
| IMU (accel, gyro) | ✅ 19 Hz | ✅ 12 Hz | HIGH | Collision, orientation |
| Camera | ✅ 12 Hz | ✅ 12 Hz | HIGH | Perception, environment |
| LiDAR | ✅ 5.8 Hz | ✅ 12 Hz | HIGH | Obstacles, terrain |
| Odometry position | ✅ 18 Hz | ✅ 12 Hz | MEDIUM | Position tracking |
| Odometry velocity | ❌ | ❌ | N/A | Not available |
| Joint positions | ✅ 0.92 Hz | ✅ 12 Hz | LOW (real) | Static pose only |
| Joint velocities | ❌ | ? | N/A | Not populated |
| Go2 states | ❌ | ⚠️ Partial | N/A | Foot force only (sim) |
| Derived velocity | ✅ Possible | ✅ Possible | MEDIUM | From position diff |

## Updated Phase 1 Recommendations

### Remove from Redesign
- ❌ Velocity-based ODD constraints (data not available)
- ❌ Joint velocity analysis (not populated)
- ❌ Go2_states integration (not on real robot)

### Add to Redesign
- ✅ Odometry-derived velocity (with "estimated" caveat)
- ✅ Position-based motion detection (stationary vs moving)
- ✅ Enhanced IMU analysis (gyroscope, RPY angles)
- ✅ Real vs Sim compatibility layer for IMU message types

### Keep as Designed
- ✅ IMU-based collision detection (primary signal)
- ✅ Camera-based perception
- ✅ LiDAR-based obstacles
- ✅ Per-window analysis approach

## Action Items

1. **Update ARCHITECTURE_REDESIGN.md**
   - Remove velocity constraint from ODD spec
   - Add "estimated velocity" from odometry differentiation
   - Add IMU gyroscope analysis
   - Note real vs sim IMU message type difference

2. **Update ODD Specification**
   - Change velocity constraints to acceleration constraints (measurable via IMU)
   - Add "motion state" binary (stationary vs moving) from position changes
   - Remove any references to joint velocities

3. **Code Changes for Phase 1**
   - Add odometry position differentiation utility
   - Handle both go2_interfaces/msg/IMU and sensor_msgs/msg/Imu
   - Extract gyroscope data for enhanced collision detection
   - Add RPY analysis (real robot custom IMU)

4. **Future Investigation**
   - Test velocity estimation accuracy (compare to ground truth if available)
   - Evaluate if running localization node is worth it for better velocity
   - Determine if low joint_states rate (0.92 Hz) can provide any useful signals

## Conclusion

**The most critical finding is the absence of direct velocity measurements.** This fundamentally changes the ODD design - we cannot specify velocity constraints when we cannot measure velocity reliably. 

The redesign should:
1. Focus on **acceleration-based constraints** (directly measurable via IMU)
2. Add **estimated velocity** from position differentiation (marked as low confidence)
3. Use **motion state classification** (stationary/moving) rather than precise velocity thresholds
4. Enhance **IMU analysis** with gyroscope and RPY data for richer motion understanding

This aligns well with the collision detection improvements already planned - IMU is our most reliable high-rate motion sensor.
