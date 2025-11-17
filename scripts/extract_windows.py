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

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import numpy as np
import pandas as pd
from collections import defaultdict

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
except ImportError as e:
    print(f"Warning: ROS2 libraries not fully available: {e}")
    print("Please source ROS2 workspace: source /opt/ros/humble/setup.bash")
    ROS2_AVAILABLE = False

try:
    import cv2
    from PIL import Image as PILImage
    CV2_AVAILABLE = True
except ImportError:
    print("Warning: OpenCV and/or Pillow not installed. Image processing will be limited.")
    CV2_AVAILABLE = False


class WindowExtractor:
    """Extract time-windowed multi-modal data from ROS2 bags."""

    def __init__(
        self,
        rosbag_path: str,
        output_dir: str,
        window_length: float = 2.0,
        stride: float = 1.0,
        run_id: Optional[str] = None,
    ):
        """
        Initialize window extractor.

        Args:
            rosbag_path: Path to rosbag2 database file (.db3)
            output_dir: Directory to write extracted windows
            window_length: Length of each window in seconds
            stride: Stride between window starts in seconds
            run_id: Optional run identifier (auto-generated if None)
        """
        self.rosbag_path = Path(rosbag_path)
        self.output_dir = Path(output_dir)
        self.window_length = window_length
        self.stride = stride

        if run_id is None:
            self.run_id = self.rosbag_path.stem.replace('_', '-')
        else:
            self.run_id = run_id

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Topic names
        self.topics = {
            "odom": "/robot0/odom",
            "imu": "/robot0/imu",
            "joints": "/robot0/joint_states",
            "camera": "/robot0/front_cam/rgb",
            "lidar": "/robot0/point_cloud2_L1",
        }

        # Data buffers - dict of lists indexed by topic
        self.messages = defaultdict(list)

        # CV Bridge for image conversion
        if ROS2_AVAILABLE:
            self.bridge = CvBridge()

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
                "bev_image_path": f"bev_{self.run_id}_w{i:03d}.png",
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
            if closest_idx < len(motion_data["accel_x"]):
                motion_data["accel_x"][closest_idx] = imu_msg.linear_acceleration.x
                motion_data["accel_y"][closest_idx] = imu_msg.linear_acceleration.y
                motion_data["accel_z"][closest_idx] = imu_msg.linear_acceleration.z
                motion_data["gyro_x"][closest_idx] = imu_msg.angular_velocity.x
                motion_data["gyro_y"][closest_idx] = imu_msg.angular_velocity.y
                motion_data["gyro_z"][closest_idx] = imu_msg.angular_velocity.z

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
        """Extract and render LiDAR bird's-eye-view image."""
        closest = self._get_closest_message(self.topics['lidar'], center_time)

        if closest is None or not CV2_AVAILABLE:
            # Create placeholder gray image
            bev_image = np.ones((100, 100), dtype=np.uint8) * 200
        else:
            _, pc_msg = closest
            # Render BEV from point cloud
            try:
                bev_image = self._render_bev_from_pointcloud(pc_msg)
            except Exception as e:
                print(f"Warning: Failed to render BEV: {e}")
                bev_image = np.ones((100, 100), dtype=np.uint8) * 200

        # Save as PNG
        bev_path = self.output_dir / f"bev_{self.run_id}_w{window_id:03d}.png"
        cv2.imwrite(str(bev_path), bev_image)

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

    def _render_bev_from_pointcloud(self, pc_msg: PointCloud2) -> np.ndarray:
        """Render a bird's-eye-view image from a point cloud."""
        # Extract points from PointCloud2 message
        points = []
        for point in pc2.read_points(pc_msg, field_names=("x", "y", "z"), skip_nans=True):
            points.append(point)

        if not points:
            return np.ones((400, 400), dtype=np.uint8) * 200

        points = np.array(points)

        # BEV parameters
        bev_size = 400
        meters_per_pixel = 0.05  # 5cm per pixel
        bev_range = (bev_size * meters_per_pixel) / 2  # Range in meters

        # Create empty BEV image
        bev = np.zeros((bev_size, bev_size), dtype=np.uint8)

        # Project points to BEV
        for point in points:
            x, y, z = point

            # Filter by height (only ground plane ±1m)
            if abs(z) > 1.0:
                continue

            # Convert to pixel coordinates (x forward, y left)
            pixel_x = int((x / meters_per_pixel) + bev_size / 2)
            pixel_y = int((-y / meters_per_pixel) + bev_size / 2)

            # Check bounds
            if 0 <= pixel_x < bev_size and 0 <= pixel_y < bev_size:
                bev[pixel_y, pixel_x] = 255

        # Apply slight blur to make points more visible
        bev = cv2.GaussianBlur(bev, (3, 3), 0)

        return bev

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

        # Set up storage options
        storage_options = StorageOptions(
            uri=str(self.rosbag_path.parent),
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

    args = parser.parse_args()

    # Create extractor
    extractor = WindowExtractor(
        rosbag_path=args.rosbag,
        output_dir=args.output,
        window_length=args.window_length,
        stride=args.stride,
        run_id=args.run_id,
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
