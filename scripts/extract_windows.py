"""
Extract time-windowed multi-modal data from ROS2 bag files.

This script processes rosbag2 files from the Unitree Go2 robot and creates
time-windowed snapshots containing:
- Motion data (JSON): velocity, IMU, odometry
- Camera frames (PNG): RGB snapshots
- LiDAR BEV images (PNG): Bird's Eye View projections

Usage:
    python extract_windows.py --rosbag <path> --output <dir> [options]
"""

from odd_agents.utils import auto_crop_bev
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import numpy as np
import pandas as pd
from collections import defaultdict

# Import BEV cropping utility
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

# ROS2 libraries
try:
    from rosbag2_py import SequentialReader, StorageOptions, ConverterOptions
    from rclpy.serialization import deserialize_message
    from sensor_msgs.msg import Image, PointCloud2, Imu, JointState
    from nav_msgs.msg import Odometry
    from geometry_msgs.msg import Twist
    from cv_bridge import CvBridge
    import sensor_msgs_py.point_cloud2 as pc2
    ROS2_AVAILABLE = True
    # Try to import Go2 custom IMU message (optional)
    try:
        from go2_interfaces.msg import IMU as Go2IMU
        GO2_IMU_AVAILABLE = True
    except ImportError:
        GO2_IMU_AVAILABLE = False
        Go2IMU = None
        print(
            "Note: go2_interfaces not available. IMU data from real robot will be skipped.")
except ImportError as e:
    print(f"Warning: ROS2 libraries not fully available: {e}")
    print("Please source ROS2 workspace: source /opt/ros/humble/setup.bash")
    ROS2_AVAILABLE = False
    GO2_IMU_AVAILABLE = False
    # Define dummy types to prevent NameError in type hints
    PointCloud2 = None
    Go2IMU = None

try:
    import cv2
    from PIL import Image as PILImage
    CV2_AVAILABLE = True
except ImportError:
    print("Warning: OpenCV and/or Pillow not installed. Image processing will be limited.")
    CV2_AVAILABLE = False


class WindowExtractor:
    """Extract time-windowed multi-modal data from ROS2 bags."""

    # Topic mapping for different data sources
    TOPIC_MAPS = {
        'sim': {
            "odom": "/robot0/odom",
            "imu": "/robot0/imu",
            "joints": "/robot0/joint_states",
            "camera": "/robot0/front_cam/rgb",
            "lidar": "/robot0/point_cloud2_L1",
        },
        'real': {
            "odom": "/odom",
            "imu": "/imu",
            "joints": "/joint_states",
            "camera": "/camera/image_raw",
            "lidar": "/point_cloud2",
        },
    }

    def __init__(
        self,
        rosbag_path: str,
        output_dir: str,
        window_length: float = 2.0,
        stride: float = 1.0,
        run_id: Optional[str] = None,
        data_source: Optional[str] = None,
    ):
        """
        Initialize window extractor.

        Args:
            rosbag_path: Path to rosbag2 database file (.db3)
            output_dir: Directory to write extracted windows
            window_length: Length of each window in seconds
            stride: Stride between window starts in seconds
            run_id: Optional run identifier (auto-generated if None)
            data_source: 'real' or 'sim' (auto-detected if None)

        IMPORTANT: The output directory name MUST match the run_id.
        Files are created with names like motion_{run_id}_w000.json.
        The workflow tools use the directory name to find these files.
        If they don't match, the workflow will fail.
        """
        self.rosbag_path = Path(rosbag_path)

        # Determine run_id first
        if run_id is None:
            self.run_id = self.rosbag_path.stem
        else:
            self.run_id = run_id

        # CRITICAL: Output directory MUST be named after run_id
        # The workflow uses directory.name to construct filenames
        base_output = Path(output_dir)
        if base_output.name != self.run_id:
            # If output_dir doesn't end with run_id, append it
            self.output_dir = base_output / self.run_id
            print(
                f"⚠️  Directory name adjusted to match run_id: {self.output_dir}")
        else:
            self.output_dir = base_output

        self.window_length = window_length
        self.stride = stride

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Verify directory name matches run_id (safety check)
        if self.output_dir.name != self.run_id:
            raise ValueError(
                f"Output directory name '{self.output_dir.name}' must match run_id '{self.run_id}'. "
                f"This is required for the workflow tools to find window files correctly."
            )

        # Auto-detect data source if not specified
        if data_source is None:
            self.data_source = self._detect_data_source()
        else:
            self.data_source = data_source

        # Set topic names based on data source
        self.topics = self.TOPIC_MAPS.get(
            self.data_source, self.TOPIC_MAPS['sim'])
        print(f"Using topic mapping for data source: {self.data_source}")

        # Data buffers - dict of lists indexed by topic
        self.messages = defaultdict(list)

        # CV Bridge for image conversion
        if ROS2_AVAILABLE:
            self.bridge = CvBridge()

    def _detect_data_source(self) -> str:
        """
        Auto-detect whether data is from real robot or simulator.

        Returns:
            'real' or 'sim'
        """
        # Check if bag path contains 'real' or 'sim'
        path_str = str(self.rosbag_path).lower()
        if 'real' in path_str:
            return 'real'
        elif 'sim' in path_str:
            return 'sim'

        # Default to sim if unclear
        print("Warning: Could not auto-detect data source from path. Defaulting to 'sim'.")
        print("         Use --data-source flag to specify 'real' or 'sim' explicitly.")
        return 'sim'

    def _get_closest_message(self, topic: str, target_time: float) -> Optional[Tuple[float, any]]:
        """Find the message closest to target time for a given topic."""
        if topic not in self.messages or not self.messages[topic]:
            return None

        messages = self.messages[topic]
        # Binary search for closest timestamp
        closest = min(messages, key=lambda x: abs(x[0] - target_time))
        return closest

    def _get_messages_in_window(self, topic: str, start_time: float, end_time: float) -> List[Tuple[float, any]]:
        """Get all messages in a time window for a given topic."""
        if topic not in self.messages:
            return []

        return [(t, msg) for t, msg in self.messages[topic] if start_time <= t <= end_time]

    def extract_all_windows(self) -> pd.DataFrame:
        """
        Extract all windows from the rosbag.

        Returns:
            DataFrame with window metadata (index CSV)
        """
        print(f"Processing rosbag: {self.rosbag_path}")
        print(f"Output directory: {self.output_dir}")
        print(f"Window length: {self.window_length}s, Stride: {self.stride}s")

        # Read all messages from bag
        self._read_rosbag_messages()

        # Determine time range from odometry messages
        odom_msgs = self.messages[self.topics['odom']]
        if not odom_msgs:
            print("ERROR: No odometry messages found in bag!")
            return pd.DataFrame()

        start_time = odom_msgs[0][0]
        end_time = odom_msgs[-1][0]
        duration = end_time - start_time

        print(f"\nBag duration: {duration:.2f}s")
        print(f"Start time: {start_time:.2f}s")
        print(f"End time: {end_time:.2f}s")

        # Create windows
        window_starts = np.arange(
            start_time, end_time - self.window_length, self.stride)
        num_windows = len(window_starts)

        print(f"Creating {num_windows} windows...")

        # Extract each window
        index_data = []
        for i, window_start in enumerate(window_starts):
            window_end = window_start + self.window_length

            window_info = {
                "window_id": i,
                "start_time": window_start,
                "end_time": window_end,
                "motion_path": f"motion_{self.run_id}_w{i:03d}.json",
                "cam_image_path": f"cam_{self.run_id}_w{i:03d}.png",
                "bev_occupancy_path": f"bev_occupancy_{self.run_id}_w{i:03d}.png",
                "bev_height_path": f"bev_height_{self.run_id}_w{i:03d}.png",
                "bev_density_path": f"bev_density_{self.run_id}_w{i:03d}.png",
                "bev_roughness_path": f"bev_roughness_{self.run_id}_w{i:03d}.png",
            }

            index_data.append(window_info)

            # Extract window data
            self._extract_window(i, window_start, window_end)

            if (i + 1) % 10 == 0:
                print(f"  Processed {i + 1}/{num_windows} windows...")

        # Create index DataFrame
        index_df = pd.DataFrame(index_data)
        index_path = self.output_dir / f"index_{self.run_id}.csv"
        index_df.to_csv(index_path, index=False)

        print(f"\nCreated index: {index_path}")
        print(f"Extracted {len(index_df)} windows")

        return index_df

    def _extract_window(self, window_id: int, start_time: float, end_time: float):
        """Extract and save data for a single window."""
        # Extract motion data (odometry + IMU)
        self._extract_motion_data(window_id, start_time, end_time)

        # Extract camera frame (closest to window center)
        self._extract_camera_frame(window_id, (start_time + end_time) / 2)

        # Extract LiDAR BEV (closest to window center)
        self._extract_lidar_bev(window_id, (start_time + end_time) / 2)

    def _extract_motion_data(self, window_id: int, start_time: float, end_time: float):
        """Extract motion data (odometry + IMU) for a window."""
        # Get all odometry and IMU messages in window
        odom_msgs = self._get_messages_in_window(
            self.topics['odom'], start_time, end_time)
        imu_msgs = self._get_messages_in_window(
            self.topics['imu'], start_time, end_time)

        motion_data = {
            "timestamps": [],
            "odom_vx": [],
            "odom_vy": [],
            "odom_vz": [],
            "odom_wx": [],
            "odom_wy": [],
            "odom_wz": [],
            "roll": [],
            "pitch": [],
            "yaw": [],
            "accel_x": [],
            "accel_y": [],
            "accel_z": [],
            "gyro_x": [],
            "gyro_y": [],
            "gyro_z": [],
        }

        # Extract odometry data
        for t, odom_msg in odom_msgs:
            motion_data["timestamps"].append(t - start_time)  # Relative time
            motion_data["odom_vx"].append(odom_msg.twist.twist.linear.x)
            motion_data["odom_vy"].append(odom_msg.twist.twist.linear.y)
            motion_data["odom_vz"].append(odom_msg.twist.twist.linear.z)
            motion_data["odom_wx"].append(odom_msg.twist.twist.angular.x)
            motion_data["odom_wy"].append(odom_msg.twist.twist.angular.y)
            motion_data["odom_wz"].append(odom_msg.twist.twist.angular.z)

            # Convert quaternion to Euler angles
            quat = odom_msg.pose.pose.orientation
            roll, pitch, yaw = self._quaternion_to_euler(
                quat.x, quat.y, quat.z, quat.w)
            motion_data["roll"].append(np.degrees(roll))
            motion_data["pitch"].append(np.degrees(pitch))
            motion_data["yaw"].append(np.degrees(yaw))

        # Extract IMU data (synchronized by timestamp)
        for t, imu_msg in imu_msgs:
            # Find closest timestamp in motion_data
            if not motion_data["timestamps"]:
                continue

            closest_idx = np.argmin([abs(ts - (t - start_time))
                                    for ts in motion_data["timestamps"]])

            # Extend arrays if needed
            while len(motion_data["accel_x"]) < len(motion_data["timestamps"]):
                motion_data["accel_x"].append(0.0)
                motion_data["accel_y"].append(0.0)
                motion_data["accel_z"].append(0.0)
                motion_data["gyro_x"].append(0.0)
                motion_data["gyro_y"].append(0.0)
                motion_data["gyro_z"].append(0.0)

            # Update IMU values at closest index
            # Handle both sensor_msgs/Imu and go2_interfaces/IMU
            if closest_idx < len(motion_data["accel_x"]):
                if hasattr(imu_msg, 'linear_acceleration'):
                    # Standard sensor_msgs/Imu
                    motion_data["accel_x"][closest_idx] = imu_msg.linear_acceleration.x
                    motion_data["accel_y"][closest_idx] = imu_msg.linear_acceleration.y
                    motion_data["accel_z"][closest_idx] = imu_msg.linear_acceleration.z
                    motion_data["gyro_x"][closest_idx] = imu_msg.angular_velocity.x
                    motion_data["gyro_y"][closest_idx] = imu_msg.angular_velocity.y
                    motion_data["gyro_z"][closest_idx] = imu_msg.angular_velocity.z
                elif hasattr(imu_msg, 'accelerometer'):
                    # Go2 custom IMU message (convert numpy float32 to Python float)
                    motion_data["accel_x"][closest_idx] = float(
                        imu_msg.accelerometer[0])
                    motion_data["accel_y"][closest_idx] = float(
                        imu_msg.accelerometer[1])
                    motion_data["accel_z"][closest_idx] = float(
                        imu_msg.accelerometer[2])
                    motion_data["gyro_x"][closest_idx] = float(
                        imu_msg.gyroscope[0])
                    motion_data["gyro_y"][closest_idx] = float(
                        imu_msg.gyroscope[1])
                    motion_data["gyro_z"][closest_idx] = float(
                        imu_msg.gyroscope[2])

        # Ensure all arrays have same length
        target_len = len(motion_data["timestamps"])
        for key in ["accel_x", "accel_y", "accel_z", "gyro_x", "gyro_y", "gyro_z"]:
            while len(motion_data[key]) < target_len:
                motion_data[key].append(0.0)

        # Save to JSON
        motion_path = self.output_dir / \
            f"motion_{self.run_id}_w{window_id:03d}.json"
        with open(motion_path, 'w') as f:
            json.dump(motion_data, f, indent=2)

    def _extract_camera_frame(self, window_id: int, center_time: float):
        """Extract camera frame closest to center time."""
        closest = self._get_closest_message(self.topics['camera'], center_time)

        if closest is None or not CV2_AVAILABLE:
            # Create placeholder gray image
            cam_image = np.ones((100, 100, 3), dtype=np.uint8) * 128
        else:
            _, img_msg = closest
            # Convert ROS Image to OpenCV format
            try:
                cam_image = self.bridge.imgmsg_to_cv2(
                    img_msg, desired_encoding='bgr8')
            except Exception as e:
                print(f"Warning: Failed to convert camera image: {e}")
                cam_image = np.ones((100, 100, 3), dtype=np.uint8) * 128

        # Save as PNG
        cam_path = self.output_dir / f"cam_{self.run_id}_w{window_id:03d}.png"
        cv2.imwrite(str(cam_path), cam_image)

    def _extract_lidar_bev(self, window_id: int, center_time: float):
        """Extract and render multi-channel LiDAR bird's-eye-view images."""
        closest = self._get_closest_message(self.topics['lidar'], center_time)

        if closest is None or not CV2_AVAILABLE:
            # Create placeholder gray images
            empty = np.zeros((400, 400), dtype=np.uint8)
            bev_features = {
                'occupancy': empty.copy(),
                'height': empty.copy(),
                'density': empty.copy(),
                'roughness': empty.copy(),
            }
        else:
            _, pc_msg = closest
            # Get robot pose for transforming point cloud to base_link frame
            robot_pose = self._get_robot_pose(center_time)

            # Render multi-channel BEV from point cloud
            try:
                bev_features = self._render_bev_from_pointcloud(
                    pc_msg, robot_pose)
            except Exception as e:
                print(f"Warning: Failed to render BEV: {e}")
                empty = np.zeros((400, 400), dtype=np.uint8)
                bev_features = {
                    'occupancy': empty.copy(),
                    'height': empty.copy(),
                    'density': empty.copy(),
                    'roughness': empty.copy(),
                }

        # Save each feature as separate PNG (with auto-cropping)
        for feature_name, feature_img in bev_features.items():
            # Crop BEV to remove empty borders while preserving robot center
            cropped_img = auto_crop_bev(feature_img)

            bev_path = self.output_dir / \
                f"bev_{feature_name}_{self.run_id}_w{window_id:03d}.png"
            cv2.imwrite(str(bev_path), cropped_img)

    def _quaternion_to_euler(self, x: float, y: float, z: float, w: float) -> Tuple[float, float, float]:
        """Convert quaternion to Euler angles (roll, pitch, yaw)."""
        # Roll (x-axis rotation)
        sinr_cosp = 2 * (w * x + y * z)
        cosr_cosp = 1 - 2 * (x * x + y * y)
        roll = np.arctan2(sinr_cosp, cosr_cosp)

        # Pitch (y-axis rotation)
        sinp = 2 * (w * y - z * x)
        if abs(sinp) >= 1:
            pitch = np.copysign(np.pi / 2, sinp)
        else:
            pitch = np.arcsin(sinp)

        # Yaw (z-axis rotation)
        siny_cosp = 2 * (w * z + x * y)
        cosy_cosp = 1 - 2 * (y * y + z * z)
        yaw = np.arctan2(siny_cosp, cosy_cosp)

        return roll, pitch, yaw

    def _get_robot_pose(self, timestamp: float) -> Optional[Dict[str, float]]:
        """
        Get robot pose (position + orientation) at given timestamp from odometry.

        Returns:
            Dict with keys: x, y, z, roll, pitch, yaw (None if no odom data)
        """
        odom_msg_tuple = self._get_closest_message(
            self.topics['odom'], timestamp)
        if odom_msg_tuple is None:
            return None

        _, odom_msg = odom_msg_tuple
        pos = odom_msg.pose.pose.position
        ori = odom_msg.pose.pose.orientation

        roll, pitch, yaw = self._quaternion_to_euler(
            ori.x, ori.y, ori.z, ori.w)

        return {
            'x': pos.x,
            'y': pos.y,
            'z': pos.z,
            'roll': roll,
            'pitch': pitch,
            'yaw': yaw
        }

    def _transform_point_odom_to_baselink(self, point: Tuple[float, float, float], robot_pose: Dict[str, float]) -> np.ndarray:
        """
        Transform a point from odom frame to base_link frame.

        Args:
            point: (x, y, z) tuple in odom frame
            robot_pose: Robot pose dict with x, y, z, yaw

        Returns:
            [x, y, z] in base_link frame
        """
        # Convert point to numpy array
        point_arr = np.array([point[0], point[1], point[2]], dtype=np.float64)
        
        # Translation: subtract robot position
        translated = point_arr - \
            np.array([robot_pose['x'], robot_pose['y'], robot_pose['z']])

        # Rotation: rotate by -yaw around z-axis (inverse transform)
        yaw = -robot_pose['yaw']  # Negative for inverse transform
        cos_yaw = np.cos(yaw)
        sin_yaw = np.sin(yaw)

        # 2D rotation in XY plane
        x_base = cos_yaw * translated[0] - sin_yaw * translated[1]
        y_base = sin_yaw * translated[0] + cos_yaw * translated[1]
        z_base = translated[2]

        return np.array([x_base, y_base, z_base])
        if abs(sinp) >= 1:
            pitch = np.copysign(np.pi / 2, sinp)
        else:
            pitch = np.arcsin(sinp)

        # Yaw (z-axis rotation)
        siny_cosp = 2 * (w * z + x * y)
        cosy_cosp = 1 - 2 * (y * y + z * z)
        yaw = np.arctan2(siny_cosp, cosy_cosp)

        return roll, pitch, yaw

    def _render_bev_from_pointcloud(self, pc_msg: PointCloud2, robot_pose: Optional[Dict[str, float]] = None) -> Dict[str, np.ndarray]:
        """
        Render multi-channel bird's-eye-view images from a point cloud.

        Args:
            pc_msg: PointCloud2 message
            robot_pose: Optional robot pose dict (x, y, z, yaw) for odom->base_link transform.
                       If provided, points are transformed from odom frame to base_link frame.
                       If None, points are assumed to already be in base_link frame (sim data).

        Returns:
            Dictionary with keys: 'occupancy', 'height', 'density', 'roughness'
            Each value is a 400x400 uint8 numpy array
        """
        # Extract points from PointCloud2 message
        points = []
        for point in pc2.read_points(pc_msg, field_names=("x", "y", "z"), skip_nans=True):
            points.append(point)

        # BEV parameters
        bev_size = 400
        meters_per_pixel = 0.05  # 5cm per pixel
        ground_threshold = 0.10  # 10cm - points below this are considered ground

        if not points:
            # Return empty feature maps
            empty = np.zeros((bev_size, bev_size), dtype=np.uint8)
            return {
                'occupancy': empty.copy(),
                'height': empty.copy(),
                'density': empty.copy(),
                'roughness': empty.copy(),
            }

        points = np.array(points)

        # Transform points from odom to base_link if robot pose is provided
        if robot_pose is not None:
            transformed_points = []
            for point in points:
                transformed = self._transform_point_odom_to_baselink(
                    point, robot_pose)
                transformed_points.append(transformed)
            points = np.array(transformed_points)

        # Create accumulator grids for feature calculation
        occupancy_grid = np.zeros((bev_size, bev_size), dtype=np.uint8)
        height_grid = np.full((bev_size, bev_size), np.nan, dtype=np.float32)
        height_sum = np.zeros((bev_size, bev_size), dtype=np.float32)
        height_sq_sum = np.zeros((bev_size, bev_size), dtype=np.float32)
        point_count = np.zeros((bev_size, bev_size), dtype=np.int32)
        height_min = np.full((bev_size, bev_size), np.inf, dtype=np.float32)
        height_max = np.full((bev_size, bev_size), -np.inf, dtype=np.float32)

        # Project points to BEV and accumulate statistics
        for point in points:
            x, y, z = point

            # Convert to pixel coordinates (x forward, y left)
            # Robot is at center (bev_size/2, bev_size/2)
            # x-axis (forward) maps to vertical (rows), y-axis (left) maps to horizontal (cols)
            pixel_x = int((x / meters_per_pixel) + bev_size / 2)
            # Fixed: removed negative sign
            pixel_y = int((y / meters_per_pixel) + bev_size / 2)

            # Check bounds
            if 0 <= pixel_x < bev_size and 0 <= pixel_y < bev_size:
                # Occupancy: only mark as occupied if above ground threshold
                # This filters out ground plane and shows only obstacles
                if z > ground_threshold:
                    occupancy_grid[pixel_y, pixel_x] = 255

                # Accumulate for height statistics (includes all points for terrain analysis)
                point_count[pixel_y, pixel_x] += 1
                height_sum[pixel_y, pixel_x] += z
                height_sq_sum[pixel_y, pixel_x] += z * z
                height_min[pixel_y, pixel_x] = min(
                    height_min[pixel_y, pixel_x], z)
                height_max[pixel_y, pixel_x] = max(
                    height_max[pixel_y, pixel_x], z)

        # Calculate derived features

        # 1. Height map (average elevation)
        mask = point_count > 0
        height_grid[mask] = height_sum[mask] / point_count[mask]
        # Normalize to 0-255 range (assuming ±2m range)
        height_img = np.zeros((bev_size, bev_size), dtype=np.uint8)
        height_img[mask] = np.clip(
            (height_grid[mask] + 2.0) * 63.75, 0, 255).astype(np.uint8)

        # 2. Density map (number of points per cell)
        density_img = np.zeros((bev_size, bev_size), dtype=np.uint8)
        max_count = point_count.max() if point_count.max() > 0 else 1
        density_img = np.clip((point_count / max_count)
                              * 255, 0, 255).astype(np.uint8)

        # 3. Roughness map (height variance within cell)
        roughness_img = np.zeros((bev_size, bev_size), dtype=np.uint8)
        # Calculate variance: Var(X) = E[X²] - E[X]²
        variance = np.zeros((bev_size, bev_size), dtype=np.float32)
        variance[mask] = (height_sq_sum[mask] / point_count[mask]) - \
            (height_sum[mask] / point_count[mask]) ** 2
        # Ensure non-negative due to floating point errors
        variance = np.maximum(variance, 0)
        std_dev = np.sqrt(variance)
        # Normalize: 0.5m std = 255 (very rough)
        roughness_img = np.clip(std_dev * 510, 0, 255).astype(np.uint8)

        # Apply slight blur to make features more visible
        occupancy_grid = cv2.GaussianBlur(occupancy_grid, (3, 3), 0)
        height_img = cv2.GaussianBlur(height_img, (3, 3), 0)
        density_img = cv2.GaussianBlur(density_img, (3, 3), 0)
        roughness_img = cv2.GaussianBlur(roughness_img, (3, 3), 0)

        return {
            'occupancy': occupancy_grid,
            'height': height_img,
            'density': density_img,
            'roughness': roughness_img,
        }

    def _create_placeholder_window(
        self,
        window_id: int,
        start_time: float,
        end_time: float,
    ):
        """Create placeholder window files for testing (deprecated - use real extraction)."""
        pass

    def _read_rosbag_messages(self):
        """
        Read and deserialize messages from rosbag.
        """
        if not ROS2_AVAILABLE:
            raise RuntimeError(
                "ROS2 libraries not available. "
                "Please source ROS2: source /opt/ros/humble/setup.bash"
            )

        print("Reading rosbag messages...")

        # Set up storage options - rosbag_path should be the bag directory
        storage_options = StorageOptions(
            uri=str(self.rosbag_path),
            storage_id='sqlite3'
        )
        converter_options = ConverterOptions(
            input_serialization_format='cdr',
            output_serialization_format='cdr'
        )

        # Create reader
        reader = SequentialReader()
        reader.open(storage_options, converter_options)

        # Get type map
        topic_types = reader.get_all_topics_and_types()
        type_map = {t.name: t.type for t in topic_types}

        # Message type mapping
        msg_type_dict = {
            'sensor_msgs/msg/Image': Image,
            'sensor_msgs/msg/PointCloud2': PointCloud2,
            'sensor_msgs/msg/Imu': Imu,
            'sensor_msgs/msg/JointState': JointState,
            'nav_msgs/msg/Odometry': Odometry,
            'geometry_msgs/msg/Twist': Twist,
        }

        # Add Go2 IMU if available
        if GO2_IMU_AVAILABLE:
            msg_type_dict['go2_interfaces/msg/IMU'] = Go2IMU

        # Read all messages
        msg_count = 0
        while reader.has_next():
            (topic, data, t) = reader.read_next()

            # Only process topics we care about
            if topic not in self.topics.values():
                continue

            # Get message type
            msg_type_str = type_map.get(topic)
            if msg_type_str not in msg_type_dict:
                continue

            # Deserialize
            msg_type = msg_type_dict[msg_type_str]
            msg = deserialize_message(data, msg_type)

            # Store with timestamp (convert from nanoseconds to seconds)
            timestamp = t / 1e9
            self.messages[topic].append((timestamp, msg))

            msg_count += 1
            if msg_count % 1000 == 0:
                print(f"  Read {msg_count} messages...")

        print(f"  Total messages read: {msg_count}")
        print(f"  Odom messages: {len(self.messages[self.topics['odom']])}")
        print(f"  IMU messages: {len(self.messages[self.topics['imu']])}")
        print(
            f"  Camera messages: {len(self.messages[self.topics['camera']])}")
        print(f"  LiDAR messages: {len(self.messages[self.topics['lidar']])}")

        del reader


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract time-windowed data from ROS2 bag files"
    )
    parser.add_argument(
        "--rosbag",
        type=str,
        required=True,
        help="Path to rosbag2 database file (.db3)"
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Output directory for extracted windows"
    )
    parser.add_argument(
        "--window-length",
        type=float,
        default=2.0,
        help="Window length in seconds (default: 2.0)"
    )
    parser.add_argument(
        "--stride",
        type=float,
        default=1.0,
        help="Stride between windows in seconds (default: 1.0)"
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Run identifier (default: auto-generate from bag filename)"
    )
    parser.add_argument(
        "--data-source",
        type=str,
        choices=['real', 'sim'],
        default=None,
        help="Data source: 'real' for real robot, 'sim' for simulator (default: auto-detect from path)"
    )

    args = parser.parse_args()

    # Create extractor
    extractor = WindowExtractor(
        rosbag_path=args.rosbag,
        output_dir=args.output,
        window_length=args.window_length,
        stride=args.stride,
        run_id=args.run_id,
        data_source=args.data_source,
    )

    # Extract windows
    try:
        index_df = extractor.extract_all_windows()
        print("\n✓ Window extraction complete!")
        return 0
    except Exception as e:
        print(f"\n✗ Error during extraction: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
