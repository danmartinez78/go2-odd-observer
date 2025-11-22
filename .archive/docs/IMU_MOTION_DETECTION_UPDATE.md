# ODD/COD Workflow Updates

## Summary
Major restructuring of the ODD (Operational Design Domain) and COD (Current Operating Domain) workflow with IMU-based motion detection and proper terminology.

## Key Terminology

- **ODD (Operational Design Domain)**: The environment the robot is **designed** to work in (specification)
- **COD (Current Operating Domain)**: The environment the robot is **actually** in (measured from sensors)
- **ODD Compliance**: Comparison of COD against ODD to detect violations

## Workflow Structure

### 1. ODD Specification Agent
- **Input**: Natural language ODD description (user-provided or default)
- **Output**: Formal ODD specification with categorical constraints and numeric thresholds
- **Runs**: First in pipeline (no sensor data needed)
- **Purpose**: Define allowed/prohibited values and in_odd/boundary/out_odd zones

### 2. Sensor Analysis Agents (COD Measurement)
- **Perception Loop + Summary**: Analyze camera + LiDAR BEV images
  - Environment classification (indoor_office, outdoor, etc.)
  - Lighting, terrain, obstacle analysis
  - **NEW**: Sim vs real classification based on image characteristics
- **Motion Loop + Summary**: Analyze IMU sensor data
  - IMU-based motion detection (replaces broken odometry)
  - Motion type classification (stationary/rotation/translation/complex)
  - Platform stability assessment
- **Collision Loop + Summary**: Multimodal risk assessment
  - Fuses motion + camera + LiDAR data
  - Risk levels and likelihood scores

### 3. COD Classifier Agent
- **Input**: Aggregated sensor analysis (perception + motion + collision)
- **Output**: Current Operating Domain classification
- **Purpose**: Synthesize what environment the robot is currently in

### 4. ODD Compliance Agent
- **Input**: ODD specification + COD classification
- **Output**: Compliance report (IN_ODD / ODD_BOUNDARY / OUT_ODD)
- **Purpose**: Detect violations and warnings

### 5. Report Agent
- **Input**: All previous outputs
- **Output**: Comprehensive human-readable report
- **Includes**: Data source (sim vs real), compliance summary, recommendations

## IMU-Based Motion Detection

### Changes Made
1. **Test Script** (`tests/test_motion_agent.py`)
   - Direct Gemini API call with raw sensor data
   - Follows proven perception agent pattern
   
2. **Full Workflow** (`scripts/odd_workflow_full.py`)
   - Motion tool analyzes IMU accelerometer/gyroscope
   - Collision tool computes motion from raw IMU arrays
   - Summary agent calculates motion detection rate
   
3. **Extraction Pipeline** (`scripts/extract_windows.py`)
   - No changes needed - already extracts IMU data

### Motion Detection Strategy
- **Primary**: IMU Accelerometer (horizontal acceleration √(accel_x² + accel_y²))
  - >0.05 m/s² indicates motion
  - >0.5 m/s² indicates strong acceleration
- **Secondary**: IMU Gyroscope (yaw rotation)
  - >0.1 rad/s indicates significant rotation
- **Stability**: Roll/Pitch orientation
  - >15° indicates unstable platform

### Why IMU Over Odometry
- Odometry showed zero velocities (broken in simulation)
- IMU showed clear acceleration signatures (0.93-0.98 m/s²)
- Agent directly interprets sensor arrays for better accuracy

## Sim vs Real Classification

### Implementation
- Added to **perception_summary_agent**
- Analyzes image characteristics:
  - **Simulation indicators**: Perfect textures, uniform lighting, geometric regularity, lack of noise
  - **Real-world indicators**: Natural lighting variations, sensor noise, organic textures
- Classification flows through to final report metadata
- Includes confidence score

### TODO
Consider extracting into dedicated agent that runs early in pipeline to provide context to all downstream agents.

## Test Results (sim_run_test - 2 windows)

```json
{
  "motion_stats": {
    "motion_detected_count": 2,
    "motion_detection_rate": 1.0,
    "motion_type_distribution": {"complex": 2},
    "max_horizontal_accel_mps2": 0.9755,
    "max_angular_velocity_radps": 0.8592,
    "overall_assessment": "high_activity"
  },
  "data_source": "simulation",
  "data_source_confidence": 0.95
}
```

## Usage

```python
# Default ODD
result = await run_odd_workflow(scenario_name="sim_run_test")

# Custom ODD
custom_odd = "A robot designed for outdoor environments..."
result = await run_odd_workflow(
    scenario_name="sim_run_test",
    nl_odd_description=custom_odd
)
```

## Next Steps

- [x] IMU-based motion detection
- [x] ODD/COD restructuring with correct terminology
- [x] NL ODD description as input parameter
- [x] Sim vs real classification
- [ ] Test on full scenario (13 windows)
- [ ] Update notebook with same patterns
- [ ] Test on real robot data
- [ ] Validate ODD compliance detection
- [ ] Consider dedicated data source classifier agent
