# IMU-Based Motion Detection Update

## Summary
Refactored motion agent to use IMU accelerometer/gyroscope data instead of broken odometry for motion detection.

## Changes Made

### 1. Test Script (`tests/test_motion_agent.py`)
- **Tool redesign**: `analyze_motion_tool()` now uses direct Gemini API call
- **Raw sensor analysis**: Calculates horizontal acceleration magnitude from IMU data
- **Motion classification**: stationary/rotation/translation/complex based on thresholds
- **Platform stability**: Detects unstable conditions from roll/pitch angles
- **Follows perception agent pattern**: Proven reliable multi-agent workflow

### 2. Full Workflow (`scripts/odd_workflow_full.py`)
- Updated `analyze_motion_tool()` to match test pattern
- Updated collision tool to compute motion metrics from raw IMU arrays
- Updated motion summary agent instructions for new data structure
- Updated ODD spec agent to use `motion_detection_rate` and `peak_horizontal_accel` fields

### 3. Extraction Pipeline (`scripts/extract_windows.py`)
- **No changes needed** - already extracts all required IMU data

## Motion Detection Strategy

### Primary: IMU Accelerometer
- Horizontal acceleration (√(accel_x² + accel_y²)) indicates translation
- Threshold: >0.05 m/s² suggests motion (gravity-compensated IMU)
- Threshold: >0.5 m/s² indicates strong acceleration

### Secondary: IMU Gyroscope
- gyro_z indicates yaw rotation (turning)
- Threshold: >0.1 rad/s is significant rotation

### Stability: Orientation
- Roll/pitch changes detect platform tilt/instability
- Threshold: >15° indicates unstable platform

## Test Results (sim_run_test)

```json
{
  "overall_stats": {
    "motion_detected_count": 2,
    "motion_detection_rate": 1.0,
    "motion_type_distribution": {"complex": 2},
    "max_horizontal_accel_mps2": 0.9755,
    "max_angular_velocity_radps": 0.8592,
    "overall_assessment": "high_activity"
  }
}
```

**Window 006**: 0.925 m/s² peak accel, 0.859 rad/s rotation → complex motion  
**Window 007**: 0.976 m/s² peak accel, 0.133 rad/s rotation → complex motion

## Why This Works

1. **Odometry was broken**: Showed zero velocities despite robot movement
2. **IMU showed truth**: Clear acceleration signatures (0.93-0.98 m/s²)
3. **Agent analyzes raw data**: Gemini directly interprets sensor arrays
4. **Reliable pattern**: Follows proven perception agent design

## Next Steps

- [ ] Test on full scenario (13 windows)
- [ ] Update notebook with same pattern
- [ ] Test on real robot data
- [ ] Document in TODO Priority 0
