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
import math
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import numpy as np
import pandas as pd
from collections import defaultdict
from scipy.spatial.transform import Rotation as R

# Minimum time delta for derived motion calculations (seconds)
# Below this threshold, dt values are unreliable (duplicate timestamps, etc.)
MIN_DT_THRESHOLD = 0.01  # 10ms

# Import BEV utilities
sys.path.insert(0, str(Path(__file__).parent.parent))

# ROS2 libraries
try:
    from rosbag2_py import SequentialReader, StorageOptions, ConverterOptions
    from rclpy.serialization import deserialize_message
    from sensor_msgs.msg import Image, PointCloud2, Imu, JointState
    from nav_msgs.msg import Odometry
    from geometry_msgs.msg import Twist, TransformStamped
    from tf2_msgs.msg import TFMessage
    from tf2_ros import Buffer as TF2Buffer
    from cv_bridge import CvBridge
    import sensor_msgs_py.point_cloud2 as pc2
    from rclpy.time import Time
    from rclpy.duration import Duration
    ROS2_AVAILABLE = True
    TF2_AVAILABLE = True
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
    TF2_AVAILABLE = False
    # Define dummy types to prevent NameError in type hints
    PointCloud2 = None
    Go2IMU = None
    TF2Buffer = None

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
        bev_rotation: int = 0,
        bev_flip_horizontal: bool = False,
        ground_filter_height: float = 0.10,
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
            bev_rotation: Optional rotation to apply to BEVs in degrees (0, 90, 180, 270)
                         Positive = clockwise. Sim-specific workaround.
            bev_flip_horizontal: If True, flip BEV horizontally after rotation.
                                Sim-specific workaround for coordinate frame issues.
            ground_filter_height: Height threshold in meters for ground filtering (default: 0.10m)
                                 Points less than this height above ground plane are filtered from occupancy.

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

        # Store BEV transformation settings (data-source specific workarounds)
        self.bev_rotation = bev_rotation
        self.bev_flip_horizontal = bev_flip_horizontal
        self.ground_filter_height = ground_filter_height

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

        # TF2 buffer for transforms (populated during bag reading)
        # Using tf2_ros.Buffer for proper transform lookups with interpolation
        # Set cache_time to 5 minutes for offline bag processing (bags can be long)
        if TF2_AVAILABLE:
            self.tf_buffer = TF2Buffer(cache_time=Duration(seconds=300))
        else:
            self.tf_buffer = None

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
            # Position data (for deriving velocity/accel when IMU is zeros)
            "pos_x": [],
            "pos_y": [],
            "pos_z": [],
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

            # Extract position for deriving velocity/acceleration
            pos = odom_msg.pose.pose.position
            motion_data["pos_x"].append(pos.x)
            motion_data["pos_y"].append(pos.y)
            motion_data["pos_z"].append(pos.z)

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

        # Compute derived velocity and acceleration from position
        # This provides backup data when IMU values are zeros (common in real robot data)
        self._compute_derived_motion(motion_data)

        # Save to JSON
        motion_path = self.output_dir / \
            f"motion_{self.run_id}_w{window_id:03d}.json"
        with open(motion_path, 'w') as f:
            json.dump(motion_data, f, indent=2)

    def _compute_derived_motion(self, motion_data: dict):
        """
        Compute speed and yaw rate from position/orientation differences.

        This provides motion data derived from odometry position when IMU 
        values are zeros (common in real robot rosbag data).

        Adds to motion_data:
        - derived_speed: Speed magnitude from position differentiation (m/s)
        - derived_yaw_rate: Angular velocity from yaw differentiation (rad/s)

        Note: We intentionally do NOT compute derived_accel because:
        - Double-differentiation of position is very noisy
        - IMU acceleration (when available) is more accurate
        - For real data where IMU is zeros, accel is simply unavailable
        """
        timestamps = motion_data.get("timestamps", [])
        pos_x = motion_data.get("pos_x", [])
        pos_y = motion_data.get("pos_y", [])
        yaw = motion_data.get("yaw", [])  # In degrees

        if len(timestamps) < 2:
            # Not enough data to compute derivatives
            motion_data["derived_speed"] = []
            motion_data["derived_yaw_rate"] = []
            return

        # Maximum plausible speed for Go2 robot (~3.5 m/s max, use 5 for margin)
        MAX_PLAUSIBLE_SPEED = 5.0  # m/s

        # Compute speed by finite differences of position
        derived_speed = []
        last_valid_speed = 0.0
        for i in range(len(timestamps) - 1):
            dt = timestamps[i + 1] - timestamps[i]
            if dt >= MIN_DT_THRESHOLD:
                vx = (pos_x[i + 1] - pos_x[i]) / dt
                vy = (pos_y[i + 1] - pos_y[i]) / dt
                speed = math.sqrt(vx**2 + vy**2)
                # Clamp to plausible range
                if speed > MAX_PLAUSIBLE_SPEED:
                    speed = last_valid_speed  # Use previous valid value
                else:
                    last_valid_speed = speed
            else:
                # dt too small - use last valid speed
                speed = last_valid_speed
            derived_speed.append(speed)

        # Pad last value to match length
        derived_speed.append(derived_speed[-1] if derived_speed else 0.0)

        # Compute yaw rate from yaw differentiation (convert deg to rad/s)
        derived_yaw_rate = []
        last_valid_yaw_rate = 0.0
        for i in range(len(timestamps) - 1):
            dt = timestamps[i + 1] - timestamps[i]
            if dt >= MIN_DT_THRESHOLD and i + 1 < len(yaw):
                # Handle wraparound at ±180°
                dyaw = yaw[i + 1] - yaw[i]
                if dyaw > 180:
                    dyaw -= 360
                elif dyaw < -180:
                    dyaw += 360
                yaw_rate = math.radians(dyaw) / dt  # Convert to rad/s
                last_valid_yaw_rate = yaw_rate
            else:
                yaw_rate = last_valid_yaw_rate  # Use last valid for tiny dt
            derived_yaw_rate.append(yaw_rate)

        # Pad last value

        # Pad last value
        derived_yaw_rate.append(
            derived_yaw_rate[-1] if derived_yaw_rate else 0.0)

        # Store in motion_data (only speed and yaw_rate - simplified)
        motion_data["derived_speed"] = derived_speed
        motion_data["derived_yaw_rate"] = derived_yaw_rate

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
                'roughness': empty.copy(),
            }
        else:
            timestamp, pc_msg = closest
            # Render multi-channel BEV from point cloud
            try:
                bev_features = self._render_bev_from_pointcloud(
                    pc_msg, timestamp)
            except Exception as e:
                print(f"Warning: Failed to render BEV: {e}")
                import traceback
                traceback.print_exc()
                empty = np.zeros((400, 400), dtype=np.uint8)
                bev_features = {
                    'occupancy': empty.copy(),
                    'height': empty.copy(),
                    'roughness': empty.copy(),
                }

        # Apply data-source specific transformations to match expected BEV format:
        # - Robot at center
        # - Forward (x-axis) pointing up in image
        # - Not mirrored (right is right, left is left)

        # Rotation (if specified)
        if self.bev_rotation != 0:
            for feature_name in bev_features:
                if self.bev_rotation == 90:
                    bev_features[feature_name] = cv2.rotate(
                        bev_features[feature_name], cv2.ROTATE_90_CLOCKWISE)
                elif self.bev_rotation == 180:
                    bev_features[feature_name] = cv2.rotate(
                        bev_features[feature_name], cv2.ROTATE_180)
                elif self.bev_rotation == 270:
                    bev_features[feature_name] = cv2.rotate(
                        bev_features[feature_name], cv2.ROTATE_90_COUNTERCLOCKWISE)

        # Horizontal flip (if specified)
        if self.bev_flip_horizontal:
            for feature_name in bev_features:
                bev_features[feature_name] = cv2.flip(
                    bev_features[feature_name], 1)

        # FINAL ROTATION: Align with camera view (robot center, facing up)
        # In base_link frame: X=forward, Y=left. Raw BEV has forward=right.
        # Apply 90° CCW rotation to make forward point up in the image.
        # This applies to both sim and real data since both use ROS standard frames.
        for feature_name in bev_features:
            bev_features[feature_name] = cv2.rotate(
                bev_features[feature_name], cv2.ROTATE_90_COUNTERCLOCKWISE)

        # Apply auto-crop to preserve obstacles while reducing size
        for feature_name in bev_features:
            bev_features[feature_name] = auto_crop_bev(
                bev_features[feature_name])

        # Save each feature as separate PNG
        for feature_name, feature_img in bev_features.items():
            bev_path = self.output_dir / \
                f"bev_{feature_name}_{self.run_id}_w{window_id:03d}.png"
            cv2.imwrite(str(bev_path), feature_img)

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

    def _lookup_transform(self, target_frame: str, source_frame: str, timestamp: float) -> Optional[TransformStamped]:
        """
        Look up transform using tf2_ros.Buffer.

        The tf2 library handles:
        - Transform chain composition (multi-hop lookups)
        - Transform inversion (automatic)
        - Time interpolation (automatic)

        Args:
            target_frame: Target frame (e.g., 'base_link')
            source_frame: Source frame (e.g., 'odom')
            timestamp: Timestamp in seconds

        Returns:
            TransformStamped if found, None otherwise
        """
        if self.tf_buffer is None:
            return None

        try:
            # Convert timestamp to ROS Time
            sec = int(timestamp)
            nanosec = int((timestamp - sec) * 1e9)
            ros_time = Time(seconds=sec, nanoseconds=nanosec)

            # Use tf2 buffer to look up transform
            # This handles chains, inversions, and interpolation automatically
            transform = self.tf_buffer.lookup_transform(
                target_frame,
                source_frame,
                ros_time,
                # No blocking - data should already be in buffer
                timeout=Duration(seconds=0)
            )
            return transform
        except Exception as e:
            # Transform not available at this time
            return None

    # Legacy manual transform methods kept for reference but not used
    def _compose_transforms_legacy(self, t1: TransformStamped, t2: TransformStamped) -> TransformStamped:
        """
        Compose two transforms: result = t1 @ t2
        (t1.parent → t1.child) @ (t2.parent → t2.child) = (t1.parent → t2.child)

        Assumes t1.child == t2.parent
        """
        # Extract first transform
        trans1 = np.array([t1.transform.translation.x,
                          t1.transform.translation.y, t1.transform.translation.z])
        rot1 = R.from_quat([t1.transform.rotation.x, t1.transform.rotation.y,
                           t1.transform.rotation.z, t1.transform.rotation.w])

        # Extract second transform
        trans2 = np.array([t2.transform.translation.x,
                          t2.transform.translation.y, t2.transform.translation.z])
        rot2 = R.from_quat([t2.transform.rotation.x, t2.transform.rotation.y,
                           t2.transform.rotation.z, t2.transform.rotation.w])

        # Compose: T = T1 @ T2
        rot_composed = rot1 * rot2  # Quaternion multiplication
        trans_composed = rot1.apply(trans2) + trans1

        # Create composed transform
        composed = TransformStamped()
        composed.header.frame_id = t1.header.frame_id
        composed.child_frame_id = t2.child_frame_id
        composed.header.stamp = t1.header.stamp
        composed.transform.translation.x = trans_composed[0]
        composed.transform.translation.y = trans_composed[1]
        composed.transform.translation.z = trans_composed[2]
        quat_composed = rot_composed.as_quat()
        composed.transform.rotation.x = quat_composed[0]
        composed.transform.rotation.y = quat_composed[1]
        composed.transform.rotation.z = quat_composed[2]
        composed.transform.rotation.w = quat_composed[3]

        return composed

    def _invert_transform_legacy(self, transform: TransformStamped) -> TransformStamped:
        """
        LEGACY: Invert a transform: if T is parent→child, return child→parent.
        Note: tf2_ros.Buffer handles inversions automatically, so this is unused.
        """
        # Extract transform
        trans = np.array([transform.transform.translation.x,
                         transform.transform.translation.y, transform.transform.translation.z])
        rot = R.from_quat([transform.transform.rotation.x, transform.transform.rotation.y,
                          transform.transform.rotation.z, transform.transform.rotation.w])

        # Invert: R_inv = R^T, t_inv = -R^T * t
        rot_inv = rot.inv()
        trans_inv = -rot_inv.apply(trans)

        # Create inverted transform (swap parent and child)
        inverted = TransformStamped()
        inverted.header.frame_id = transform.child_frame_id
        inverted.child_frame_id = transform.header.frame_id
        inverted.header.stamp = transform.header.stamp
        inverted.transform.translation.x = trans_inv[0]
        inverted.transform.translation.y = trans_inv[1]
        inverted.transform.translation.z = trans_inv[2]
        quat_inv = rot_inv.as_quat()
        inverted.transform.rotation.x = quat_inv[0]
        inverted.transform.rotation.y = quat_inv[1]
        inverted.transform.rotation.z = quat_inv[2]
        inverted.transform.rotation.w = quat_inv[3]

        return inverted

    def _apply_transform(self, points: np.ndarray, transform: TransformStamped) -> np.ndarray:
        """
        Apply TransformStamped to point cloud.

        Args:
            points: Nx3 array of points
            transform: ROS TransformStamped message

        Returns:
            Transformed Nx3 array of points
        """
        if points.shape[0] == 0:
            return points

        # Extract translation
        trans = transform.transform.translation
        translation = np.array([trans.x, trans.y, trans.z])

        # Extract rotation as quaternion and convert to matrix
        rot = transform.transform.rotation
        quat = [rot.x, rot.y, rot.z, rot.w]
        rotation_matrix = R.from_quat(quat).as_matrix()

        # Apply: points_transformed = R @ points + t
        points_transformed = (rotation_matrix @ points.T).T + translation

        return points_transformed

    def _render_bev_from_pointcloud(self, pc_msg: PointCloud2, timestamp: float) -> Dict[str, np.ndarray]:
        """
        Render multi-channel bird's-eye-view images from a point cloud.

        Uses TF transforms to properly filter ground in gravity-aligned odom frame,
        then transforms back to base_link for robot-centric BEV rendering.

        Args:
            pc_msg: PointCloud2 message
            timestamp: Timestamp in seconds for TF lookup

        Returns:
            Dictionary with keys: 'occupancy', 'height', 'roughness'
            Each value is a 400x400 uint8 numpy array
        """
        # Extract points from PointCloud2 message (in sensor frame)
        points = []
        for point in pc2.read_points(pc_msg, field_names=("x", "y", "z"), skip_nans=True):
            points.append([point[0], point[1], point[2]])

        # BEV parameters
        bev_size = 400
        meters_per_pixel = 0.05  # 5cm per pixel
        ground_threshold = self.ground_filter_height  # Use configurable threshold

        if not points:
            # Return empty feature maps
            empty = np.zeros((bev_size, bev_size), dtype=np.uint8)
            return {
                'occupancy': empty.copy(),
                'height': empty.copy(),
                'roughness': empty.copy(),
            }

        points_raw = np.array(points, dtype=np.float32)

        # Determine frame names based on data source
        if self.data_source == 'sim':
            sensor_frame = 'robot0/UnitreeL1_link'
            base_frame = 'robot0/base_link'
            odom_frame = 'robot0/odom'
            # Sim: points are in sensor frame, need transform to odom
            points_already_in_odom = False
        else:  # real
            sensor_frame = 'UnitreeL1_link'  # May not exist - real lidar publishes in odom
            base_frame = 'base_link'
            odom_frame = 'odom'
            # Real: Check the point cloud frame_id to determine if already in odom
            # Real robot lidar driver typically publishes directly in odom frame
            pc_frame = pc_msg.header.frame_id
            points_already_in_odom = (pc_frame == odom_frame)

        # Strategy: Get points into odom frame (gravity-aligned) for ground filtering,
        # then transform filtered points odom → base_link for robot-centric BEV

        # Step 1: Get points into odom frame
        if points_already_in_odom:
            # Real data: Points are already in odom frame (no transform needed)
            points_odom = points_raw
            have_odom_points = True
        else:
            # Sim data: Transform from sensor frame to odom
            transform_sensor_to_odom = self._lookup_transform(
                odom_frame, sensor_frame, timestamp)
            if transform_sensor_to_odom is not None:
                points_odom = self._apply_transform(
                    points_raw, transform_sensor_to_odom)
                have_odom_points = True
            else:
                have_odom_points = False

        if have_odom_points:
            # Ground filtering in odom frame (z-axis is gravity-aligned, up)
            if self.data_source == 'real':
                # For real data: odom frame has ground at Z ≈ 0
                # Use a fixed threshold above ground (more robust than histogram)
                ground_z = 0.0  # Ground is at Z=0 in odom frame
                # Filter points above ground + threshold (e.g., z > 0.15m)
                obstacle_mask = points_odom[:, 2] > (
                    ground_z + ground_threshold)
            else:
                # For sim data: use histogram to find ground (works well)
                z_values = points_odom[:, 2]
                hist, bin_edges = np.histogram(z_values, bins=100)
                ground_bin_idx = np.argmax(hist)
                ground_z = (bin_edges[ground_bin_idx] +
                            bin_edges[ground_bin_idx + 1]) / 2
                obstacle_mask = points_odom[:, 2] > (
                    ground_z + ground_threshold)

            # Create masks for obstacles (above ground) vs all points (for roughness)
            obstacles_odom = points_odom[obstacle_mask]

            # Step 2: Transform back to base_link for robot-centric BEV rendering
            transform_odom_to_base = self._lookup_transform(
                base_frame, odom_frame, timestamp)

            if transform_odom_to_base is not None:
                # Transform obstacles for occupancy & height
                obstacles_base = self._apply_transform(
                    obstacles_odom, transform_odom_to_base)

                # Transform all points for roughness (includes ground variance)
                all_points_base = self._apply_transform(
                    points_odom, transform_odom_to_base)
            else:
                print(
                    f"Warning: No TF transform {odom_frame}→{base_frame}, using odom frame")
                obstacles_base = obstacles_odom
                all_points_base = points_odom
        else:
            # Fallback: Use points in raw frame (old behavior)
            print(
                f"Warning: No TF transforms available, using raw frame without ground filtering")
            obstacles_base = points_raw
            all_points_base = points_raw

        # Create accumulator grids for feature calculation
        occupancy_grid = np.zeros((bev_size, bev_size), dtype=np.float32)
        height_grid = np.full((bev_size, bev_size), np.nan, dtype=np.float32)
        height_sum = np.zeros((bev_size, bev_size), dtype=np.float32)
        height_sq_sum = np.zeros((bev_size, bev_size), dtype=np.float32)
        point_count = np.zeros((bev_size, bev_size), dtype=np.float32)
        height_min = np.full((bev_size, bev_size), np.inf, dtype=np.float32)
        height_max = np.full((bev_size, bev_size), -np.inf, dtype=np.float32)

        # Separate grids for roughness (uses all points including ground)
        roughness_height_sum = np.zeros((bev_size, bev_size), dtype=np.float32)
        roughness_height_sq_sum = np.zeros(
            (bev_size, bev_size), dtype=np.float32)
        roughness_point_count = np.zeros(
            (bev_size, bev_size), dtype=np.float32)

        # Helper function for bilinear splatting (anti-aliased point rendering)
        def splat_point(grid, px, py, value=1.0):
            """Splat a point using bilinear interpolation for anti-aliasing."""
            x0, y0 = int(px), int(py)
            x1, y1 = x0 + 1, y0 + 1

            # Bilinear weights
            wx1 = px - x0
            wx0 = 1.0 - wx1
            wy1 = py - y0
            wy0 = 1.0 - wy1

            # Splat to 4 neighboring pixels
            if 0 <= x0 < bev_size and 0 <= y0 < bev_size:
                grid[y0, x0] += value * wx0 * wy0
            if 0 <= x1 < bev_size and 0 <= y0 < bev_size:
                grid[y0, x1] += value * wx1 * wy0
            if 0 <= x0 < bev_size and 0 <= y1 < bev_size:
                grid[y1, x0] += value * wx0 * wy1
            if 0 <= x1 < bev_size and 0 <= y1 < bev_size:
                grid[y1, x1] += value * wx1 * wy1

        # First pass: OBSTACLES ONLY → occupancy
        for point in obstacles_base:
            x, y, z = point

            # Convert to sub-pixel coordinates (x forward, y left in base_link)
            pixel_x = (x / meters_per_pixel) + bev_size / 2
            pixel_y = (-y / meters_per_pixel) + bev_size / 2

            # Splat occupancy with anti-aliasing
            splat_point(occupancy_grid, pixel_x, pixel_y, 1.0)

            # Track obstacle point count for normalization
            px_int = int(pixel_x)
            py_int = int(pixel_y)
            if 0 <= px_int < bev_size and 0 <= py_int < bev_size:
                point_count[py_int, px_int] += 1

        # Second pass: ALL POINTS → height and roughness (richer terrain signal)
        # Use splatting for smoother coverage
        for point in all_points_base:
            x, y, z = point

            # Convert to sub-pixel coordinates
            pixel_x = (x / meters_per_pixel) + bev_size / 2
            pixel_y = (-y / meters_per_pixel) + bev_size / 2

            # Bilinear splatting for height/roughness accumulation
            x0, y0 = int(pixel_x), int(pixel_y)
            x1, y1 = x0 + 1, y0 + 1

            wx1 = pixel_x - x0
            wx0 = 1.0 - wx1
            wy1 = pixel_y - y0
            wy0 = 1.0 - wy1

            # Splat to 4 neighboring pixels with weighted height values
            for (px, py, w) in [(x0, y0, wx0*wy0), (x1, y0, wx1*wy0),
                                (x0, y1, wx0*wy1), (x1, y1, wx1*wy1)]:
                if 0 <= px < bev_size and 0 <= py < bev_size:
                    # Weighted accumulation for height
                    height_sum[py, px] += z * w
                    height_sq_sum[py, px] += z * z * w

                    # Weighted accumulation for roughness
                    roughness_point_count[py, px] += w
                    roughness_height_sum[py, px] += z * w
                    roughness_height_sq_sum[py, px] += z * z * w

        # Normalize occupancy to 0-255 and apply threshold
        # The splatted values accumulate, so normalize and threshold
        max_occ = occupancy_grid.max()
        if max_occ > 0:
            occupancy_grid = (occupancy_grid / max_occ *
                              255).astype(np.float32)
        # Also set any cell with obstacle points to max for consistency
        occupancy_grid[point_count > 0] = np.maximum(
            occupancy_grid[point_count > 0], 200)

        # Calculate derived features

        # 1. Height map (average elevation of ALL POINTS - full terrain)
        all_points_mask = roughness_point_count > 0
        height_grid[all_points_mask] = height_sum[all_points_mask] / \
            roughness_point_count[all_points_mask]
        # Normalize to 0-255 range (assuming ±2m range)
        height_img = np.zeros((bev_size, bev_size), dtype=np.uint8)
        height_img[all_points_mask] = np.clip(
            (height_grid[all_points_mask] + 2.0) * 63.75, 0, 255).astype(np.uint8)

        # 2. Roughness map (terrain variance - all points including ground)
        roughness_img = np.zeros((bev_size, bev_size), dtype=np.uint8)
        # Calculate variance: Var(X) = E[X²] - E[X]²
        variance = np.zeros((bev_size, bev_size), dtype=np.float32)
        variance[all_points_mask] = (roughness_height_sq_sum[all_points_mask] / roughness_point_count[all_points_mask]) - \
            (roughness_height_sum[all_points_mask] /
             roughness_point_count[all_points_mask]) ** 2
        # Ensure non-negative due to floating point errors
        variance = np.maximum(variance, 0)
        std_dev = np.sqrt(variance)
        # Normalize: 0.5m std = 255 (very rough)
        roughness_img = np.clip(std_dev * 510, 0, 255).astype(np.uint8)

        # Convert occupancy to uint8 for output
        occupancy_grid = np.clip(occupancy_grid, 0, 255).astype(np.uint8)

        # Apply slight blur to make features more visible and reduce aliasing
        occupancy_grid = cv2.GaussianBlur(occupancy_grid, (5, 5), 1.0)
        height_img = cv2.GaussianBlur(height_img, (5, 5), 1.0)
        roughness_img = cv2.GaussianBlur(roughness_img, (5, 5), 1.0)

        return {
            'occupancy': occupancy_grid,
            'height': height_img,
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
            'tf2_msgs/msg/TFMessage': TFMessage,
        }

        # Add Go2 IMU if available
        if GO2_IMU_AVAILABLE:
            msg_type_dict['go2_interfaces/msg/IMU'] = Go2IMU

        # Read all messages
        msg_count = 0
        tf_count = 0
        while reader.has_next():
            (topic, data, t) = reader.read_next()

            # Handle TF messages - add to tf2 buffer
            if topic == '/tf' or topic == '/tf_static':
                try:
                    msg_type = msg_type_dict.get('tf2_msgs/msg/TFMessage')
                    if msg_type and self.tf_buffer is not None:
                        tf_msg = deserialize_message(data, msg_type)
                        # TFMessage contains multiple TransformStamped messages
                        for transform in tf_msg.transforms:
                            # Use appropriate method for static vs dynamic transforms
                            if topic == '/tf_static':
                                self.tf_buffer.set_transform_static(
                                    transform, 'bag_reader')
                            else:
                                self.tf_buffer.set_transform(
                                    transform, 'bag_reader')
                            tf_count += 1
                except Exception as e:
                    print(f"Warning: Failed to parse TF message: {e}")
                continue

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
        print(f"  TF transforms read: {tf_count}")
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
    parser.add_argument(
        "--bev-rotation",
        type=int,
        choices=[0, 90, 180, 270],
        default=0,
        help="Rotation to apply to BEVs in degrees, clockwise (default: 0). Data-source specific."
    )
    parser.add_argument(
        "--bev-flip-horizontal",
        action="store_true",
        help="Flip BEV horizontally after rotation. Data-source specific workaround."
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
        bev_rotation=args.bev_rotation,
        bev_flip_horizontal=args.bev_flip_horizontal,
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
