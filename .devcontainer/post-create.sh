#!/bin/bash

# Post-create script for dev container setup
echo "Setting up Go2 ODD/COD Observer development environment..."

# Source ROS2
source /opt/ros/humble/setup.bash

# Navigate to ROS2 workspace
cd /workspace/ros2_ws

# Clone go2_ros2_sdk for message definitions
echo "Cloning Go2 ROS2 SDK for message definitions..."
if [ ! -d "src/go2_ros2_sdk" ]; then
    cd src
    git clone https://github.com/danmartinez78/go2_ros2_sdk.git
    cd ..
fi

# Build only the interfaces package (we don't need the full SDK)
echo "Building go2_interfaces package..."
colcon build --packages-select go2_interfaces --symlink-install

# Source the workspace
source install/setup.bash

# Install Python dependencies for the project
echo "Installing Python dependencies..."
cd /workspaces/go2-odd-observer
pip3 install -r requirements.txt

# Make scripts executable
echo "Making scripts executable..."
chmod +x scripts/*.py

# Set up environment variables
echo "export ROS_DOMAIN_ID=0" >> ~/.bashrc
echo "export PYTHONPATH=/workspaces/go2-odd-observer:\$PYTHONPATH" >> ~/.bashrc

# Create data directories if they don't exist
mkdir -p data/raw_rosbags
mkdir -p data/processed/runs

echo "✓ Development environment setup complete!"
echo ""
echo "To get started:"
echo "  1. Place your rosbag files in data/raw_rosbags/"
echo "  2. Run window extraction: python scripts/extract_windows.py"
echo "  3. Run demo pipeline: python scripts/demo_pipeline_local.py"
echo ""
echo "ROS2 topics available from Go2:"
echo "  /robot0/cmd_vel         - Command velocities"
echo "  /robot0/odom            - Odometry"
echo "  /robot0/imu             - IMU data"
echo "  /robot0/joint_states    - Joint states"
echo "  /robot0/front_cam/rgb   - Front camera RGB"
echo "  /robot0/point_cloud2_L1 - LiDAR point cloud"
