# Bagfile Audit Data

## Purpose
This directory contains extracted metadata from ROS2 bagfiles for Phase 0 data source discovery. Cloud agents can analyze this data to identify integration opportunities without needing ROS2 installed.

## Files
- `real_01_173442_bag_info.txt` - Raw ros2 bag info output from real robot scenario
- `sim_01_bag_info.txt` - Raw ros2 bag info output from simulation scenario
- `bagfile_audit_results.json` - Structured JSON with all topics, types, rates, and counts
- `parse_bag_info.py` - Script that converted text to JSON (for reference)

## Key Findings

### Real Robot Topics
- **IMU**: `/imu` (go2_interfaces/msg/IMU) @ 19.13 Hz - ✅ Currently used
- **Odometry**: `/odom` (nav_msgs/msg/Odometry) @ 18.62 Hz - ⚠️ NOT currently used
- **Joint States**: `/joint_states` (sensor_msgs/msg/JointState) @ 0.92 Hz - ⚠️ NOT currently used
- **Camera**: `/camera/image_raw` @ 12.38 Hz - ✅ Currently used
- **LiDAR**: `/point_cloud2` @ 5.85 Hz - ✅ Currently used
- **Transforms**: `/tf` @ 19.53 Hz - Potentially useful

### Simulation Topics
- **IMU**: `/robot0/imu` (sensor_msgs/msg/Imu) @ 12.41 Hz - Different type than real!
- **Odometry**: `/robot0/odom` @ 12.41 Hz - Available
- **Joint States**: `/robot0/joint_states` @ 12.41 Hz - Available
- **Camera**: `/robot0/front_cam/rgb` @ 12.41 Hz - ✅ Currently used
- **LiDAR**: `/robot0/point_cloud2_L1` @ 12.41 Hz - ✅ Currently used
- **Extra LiDAR**: `/robot0/point_cloud2_extra` @ 12.41 Hz - What is this?
- **Robot State**: `/robot0/go2_states` (go2_interfaces/msg/Go2State) @ 12.41 Hz - What's in here?

## Investigation Tasks for Cloud Agents

### 1. Odometry Data Investigation
**Priority: HIGH**
- Odometry topic exists but we're not using it
- Contains pose (position + orientation) and twist (linear + angular velocity)
- **Questions:**
  - Does `/odom/twist/twist/linear` contain actual velocity data?
  - Is it reliable? (Compare to integrated IMU if possible)
  - Could this replace our missing velocity constraint?
  - Why did we not use this originally?

### 2. Joint States Analysis  
**Priority: MEDIUM**
- Real robot: Only 0.92 Hz (very slow updates)
- Sim robot: 12.41 Hz (much better)
- **Questions:**
  - What joints are reported? (leg positions?)
  - Can we infer motion state from joint velocities?
  - Why such low rate on real robot?
  - Is this worth integrating given low rate?

### 3. Go2State Message Type
**Priority: MEDIUM**
- Sim only: `go2_interfaces/msg/Go2State` @ 12.41 Hz
- **Questions:**
  - What fields does this message contain?
  - Is there equivalent on real robot?
  - Could this provide useful context (battery, mode, etc)?
  - Check `go2_ros2_sdk` package for message definition

### 4. IMU Type Discrepancy
**Priority: LOW**
- Real: `go2_interfaces/msg/IMU`
- Sim: `sensor_msgs/msg/Imu` (standard ROS2)
- **Questions:**
  - What's different between these?
  - Does our code handle both?
  - Check `go2_ros2_sdk/go2_interfaces` for custom IMU definition
  - Any fields we're missing from the custom type?

### 5. Point Cloud Extra
**Priority: LOW**
- Sim only: `/robot0/point_cloud2_extra` @ 12.41 Hz
- **Questions:**
  - What is this second point cloud?
  - Different sensor? Different processing?
  - Could it be useful for obstacle detection?

## Expected Deliverables

Cloud agents should create `BAGFILE_AUDIT_FINDINGS.md` with:

1. **Odometry Investigation Results**
   - Field breakdown of nav_msgs/msg/Odometry
   - Whether velocity data is populated
   - Recommendation on using for velocity constraint

2. **Message Type Documentation**
   - go2_interfaces/msg/IMU vs sensor_msgs/msg/Imu comparison
   - go2_interfaces/msg/Go2State field breakdown
   - sensor_msgs/msg/JointState field breakdown

3. **Integration Opportunities**
   - Prioritized list of topics to integrate
   - Expected benefit for each
   - Implementation complexity estimate

4. **Updated Sensor Documentation**
   - Add newly discovered topics to existing sensor docs
   - Note real vs sim differences
   - Update ARCHITECTURE_REDESIGN.md if needed

## Reference Documentation
- `docs/ARCHITECTURE_REDESIGN.md` - Phase 0 details
- ROS2 message definitions: https://docs.ros2.org/foxy/api/
- Go2 SDK: `/workspaces/go2-odd-observer/go2_ros2_sdk/`

## Notes
- Cloud agents cannot run ROS2 commands - all necessary data is in the JSON
- Focus on **what data is available**, not how to extract it (we'll handle extraction)
- Odometry velocity is the highest priority discovery
- Some topics may exist but contain no useful data - note this
