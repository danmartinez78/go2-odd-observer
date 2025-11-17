FROM ros:humble-ros-base

# Install dependencies
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-opencv \
    python3-numpy \
    python3-pandas \
    ros-humble-cv-bridge \
    ros-humble-sensor-msgs-py \
    ros-humble-rosbag2-py \
    ros-humble-rclpy \
    ros-humble-geometry-msgs \
    ros-humble-nav-msgs \
    ros-humble-sensor-msgs \
    ros-humble-tf2-ros \
    ros-humble-tf2-geometry-msgs \
    ros-humble-image-transport \
    git \
    vim \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create workspace
RUN mkdir -p /workspace/ros2_ws/src

# Set up ROS2 workspace
WORKDIR /workspace/ros2_ws

# Source ROS2 in bashrc
RUN echo "source /opt/ros/humble/setup.bash" >> /etc/bash.bashrc
RUN echo "if [ -f /workspace/ros2_ws/install/setup.bash ]; then source /workspace/ros2_ws/install/setup.bash; fi" >> /etc/bash.bashrc

# Install Python packages for ODD/COD analysis
RUN pip3 install --no-cache-dir \
    matplotlib \
    seaborn \
    scipy \
    pydantic \
    pytest \
    pytest-cov \
    jupyter \
    ipykernel \
    ipywidgets \
    tqdm \
    python-dotenv \
    open3d \
    pillow

# Set default shell
SHELL ["/bin/bash", "-c"]

CMD ["/bin/bash"]
