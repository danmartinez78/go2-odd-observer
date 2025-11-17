# Go2 ODD/COD Observer - Dev Container Guide

## Overview

This dev container provides a complete ROS2 Humble environment with all necessary dependencies for processing Go2 robot data and performing ODD/COD analysis.

## What's Included

### ROS2 Humble Base
- Full ROS2 Humble installation
- rosbag2 tools for bag file processing
- cv_bridge for image conversion
- TF2 for transformations
- All standard message types

### Go2 Robot Interfaces
- Custom message definitions from `go2_ros2_sdk`
- `go2_interfaces` package with:
  - Go2State, IMU, LowState messages
  - WebRtcReq for robot commands
  - VoxelMapCompressed for LiDAR data
  - All standard sensor messages

### Python Environment
- Python 3.10
- NumPy, Pandas, Matplotlib, Seaborn
- OpenCV, Pillow
- Open3D for point cloud processing
- Jupyter for notebooks
- Pytest for testing
- All dependencies from requirements.txt

## Getting Started

### 1. Open in Dev Container

In VS Code:
- Open Command Palette (Ctrl+Shift+P / Cmd+Shift+P)
- Select "Dev Containers: Reopen in Container"
- Wait for container to build and initialize

### 2. Verify Setup

```bash
# Check ROS2 installation
ros2 --version

# Check Go2 interfaces
ros2 interface list | grep go2_interfaces

# Check Python packages
python3 -c "import cv2, numpy, pandas; print('✓ All packages available')"
```

### 3. Run Tests

```bash
cd /workspaces/go2-odd-observer
python -m pytest tests/ -v
```

## Working with ROS Bags

### Expected Topics

The dev container is configured to work with these Go2 topics:

- `/robot0/cmd_vel` - geometry_msgs/Twist
- `/robot0/odom` - nav_msgs/Odometry  
- `/robot0/imu` - sensor_msgs/Imu
- `/robot0/joint_states` - sensor_msgs/JointState
- `/robot0/front_cam/rgb` - sensor_msgs/Image
- `/robot0/point_cloud2_L1` - sensor_msgs/PointCloud2

### Extract Windows from Bags

```bash
python scripts/extract_windows.py \
  --rosbag data/raw_rosbags/my_robot_run.db3 \
  --output data/processed/runs/run_001 \
  --window-length 2.0 \
  --stride 1.0
```

### Inspect Bag Files

```bash
# List topics
ros2 bag info data/raw_rosbags/my_robot_run.db3

# Play back (for testing)
ros2 bag play data/raw_rosbags/my_robot_run.db3
```

## Development Workflow

### 1. Process Data Locally

```bash
# Extract windows from rosbag
python scripts/extract_windows.py --rosbag <path> --output <dir>

# Run local demo pipeline
python scripts/demo_pipeline_local.py
```

### 2. Test Changes

```bash
# Run unit tests
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/test_distance_metrics.py::TestWindowDistance -v
```

### 3. Jupyter Development

```bash
# Start Jupyter
jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser

# Access at http://localhost:8888
```

## Troubleshooting

### ROS2 Not Sourced

If ROS2 commands aren't found:
```bash
source /opt/ros/humble/setup.bash
source /workspace/ros2_ws/install/setup.bash
```

### Go2 Interfaces Not Found

Rebuild the interfaces:
```bash
cd /workspace/ros2_ws
colcon build --packages-select go2_interfaces --symlink-install
source install/setup.bash
```

### Python Import Errors

Ensure PYTHONPATH includes the project:
```bash
export PYTHONPATH=/workspaces/go2-odd-observer:$PYTHONPATH
```

## File Structure

```
/workspaces/go2-odd-observer/     # Your project (mounted)
  ├── odd_cod/                     # Core Python package
  ├── scripts/                     # Processing scripts
  ├── tests/                       # Unit tests
  └── data/                        # Data directory (gitignored)

/workspace/ros2_ws/                # ROS2 workspace
  ├── src/
  │   └── go2_ros2_sdk/           # Go2 message definitions
  └── install/                     # Built packages
```

## Environment Variables

Pre-configured in the container:
- `ROS_DOMAIN_ID=0`
- `PYTHONPATH` includes project root
- ROS2 and workspace auto-sourced in bashrc

## VS Code Extensions

Installed automatically:
- Python + Pylance
- ROS extension
- Jupyter notebooks
- Docker
- GitHub Copilot

## Next Steps

1. **Collect Data**: Place rosbag files in `data/raw_rosbags/`
2. **Process**: Run extraction scripts
3. **Analyze**: Use demo pipeline or create notebooks
4. **Develop**: Modify odd_cod package as needed
5. **Test**: Run pytest suite
6. **Deploy**: Phase 4 - cloud agent integration

## Resources

- [ROS2 Humble Docs](https://docs.ros.org/en/humble/)
- [Go2 ROS2 SDK](https://github.com/danmartinez78/go2_ros2_sdk)
- [Project README](../README.md)
- [Project Plan](../project_plan.md)
