"""
Render Bird's Eye View (BEV) images from LiDAR point clouds.

Converts sensor_msgs/PointCloud2 data into 2D overhead view images
for visual analysis and agent processing.
"""

import numpy as np
from typing import Tuple, Optional
import sys

try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False
    print("Warning: OpenCV not installed. BEV rendering will be limited.")


def pointcloud_to_bev(
    points: np.ndarray,
    x_range: Tuple[float, float] = (0.0, 4.0),
    y_range: Tuple[float, float] = (-2.0, 2.0),
    z_range: Tuple[float, float] = (-0.5, 1.5),
    resolution: float = 0.05,
    height_encoding: bool = True,
) -> np.ndarray:
    """
    Convert 3D point cloud to 2D Bird's Eye View image.
    
    Args:
        points: Nx3 or Nx4 array (x, y, z, [intensity])
        x_range: (min, max) range in meters (forward direction)
        y_range: (min, max) range in meters (lateral direction)
        z_range: (min, max) range for filtering points
        resolution: Meters per pixel
        height_encoding: If True, encode height as intensity; else use occupancy
        
    Returns:
        2D numpy array (grayscale image, uint8)
    """
    # Validate input
    if points.shape[0] == 0:
        # Empty point cloud, return blank image
        height = int((x_range[1] - x_range[0]) / resolution)
        width = int((y_range[1] - y_range[0]) / resolution)
        return np.zeros((height, width), dtype=np.uint8)
    
    if points.shape[1] < 3:
        raise ValueError(f"Points must have at least 3 columns (x,y,z), got {points.shape[1]}")
    
    # Extract coordinates
    x = points[:, 0]
    y = points[:, 1]
    z = points[:, 2]
    
    # Filter by z range
    z_mask = (z >= z_range[0]) & (z <= z_range[1])
    x = x[z_mask]
    y = y[z_mask]
    z = z[z_mask]
    
    # Filter by x and y range
    xy_mask = (
        (x >= x_range[0]) & (x < x_range[1]) &
        (y >= y_range[0]) & (y < y_range[1])
    )
    x = x[xy_mask]
    y = y[xy_mask]
    z = z[xy_mask]
    
    if len(x) == 0:
        # No points in range
        height = int((x_range[1] - x_range[0]) / resolution)
        width = int((y_range[1] - y_range[0]) / resolution)
        return np.zeros((height, width), dtype=np.uint8)
    
    # Compute image dimensions
    height = int((x_range[1] - x_range[0]) / resolution)
    width = int((y_range[1] - y_range[0]) / resolution)
    
    # Convert to pixel coordinates
    # X -> rows (image height), Y -> columns (image width)
    pixel_x = ((x - x_range[0]) / resolution).astype(np.int32)
    pixel_y = ((y - y_range[0]) / resolution).astype(np.int32)
    
    # Clip to valid range
    pixel_x = np.clip(pixel_x, 0, height - 1)
    pixel_y = np.clip(pixel_y, 0, width - 1)
    
    # Create BEV image
    bev_image = np.zeros((height, width), dtype=np.float32)
    
    if height_encoding:
        # Encode height as intensity
        # Normalize z to [0, 1] range
        z_normalized = (z - z_range[0]) / (z_range[1] - z_range[0])
        z_normalized = np.clip(z_normalized, 0.0, 1.0)
        
        # For each pixel, take maximum height (top surface)
        for i in range(len(pixel_x)):
            current_val = bev_image[pixel_x[i], pixel_y[i]]
            bev_image[pixel_x[i], pixel_y[i]] = max(current_val, z_normalized[i])
    else:
        # Simple occupancy (binary or count)
        for i in range(len(pixel_x)):
            bev_image[pixel_x[i], pixel_y[i]] = 1.0
    
    # Convert to uint8
    bev_image_uint8 = (bev_image * 255).astype(np.uint8)
    
    return bev_image_uint8


def render_bev_from_ros_pointcloud(
    pointcloud_msg,
    x_range: Tuple[float, float] = (0.0, 4.0),
    y_range: Tuple[float, float] = (-2.0, 2.0),
    z_range: Tuple[float, float] = (-0.5, 1.5),
    resolution: float = 0.05,
) -> np.ndarray:
    """
    Render BEV from ROS sensor_msgs/PointCloud2 message.
    
    Args:
        pointcloud_msg: ROS PointCloud2 message
        x_range: Forward range in meters
        y_range: Lateral range in meters
        z_range: Height range in meters
        resolution: Meters per pixel
        
    Returns:
        BEV image as numpy array
    """
    # TODO: Implement PointCloud2 deserialization
    # This requires ROS2 sensor_msgs and point_cloud2 utilities
    
    raise NotImplementedError(
        "ROS PointCloud2 rendering not yet implemented. "
        "Install ROS2 sensor_msgs and use point_cloud2 utilities."
    )
    
    # Example implementation outline:
    # from sensor_msgs_py import point_cloud2
    # points_generator = point_cloud2.read_points(pointcloud_msg, field_names=("x", "y", "z"))
    # points = np.array(list(points_generator))
    # return pointcloud_to_bev(points, x_range, y_range, z_range, resolution)


def save_bev_image(bev_array: np.ndarray, filepath: str) -> bool:
    """
    Save BEV array as PNG image.
    
    Args:
        bev_array: 2D numpy array (uint8)
        filepath: Output file path
        
    Returns:
        True if successful
    """
    if not HAS_OPENCV:
        print("Error: OpenCV not installed, cannot save image")
        return False
    
    try:
        cv2.imwrite(filepath, bev_array)
        return True
    except Exception as e:
        print(f"Error saving BEV image: {e}")
        return False


def demo_bev_rendering():
    """
    Demonstrate BEV rendering with synthetic data.
    """
    print("Generating synthetic point cloud...")
    
    # Create synthetic point cloud (flat ground + some obstacles)
    num_points = 10000
    
    # Ground plane
    ground_x = np.random.uniform(0.0, 4.0, num_points // 2)
    ground_y = np.random.uniform(-2.0, 2.0, num_points // 2)
    ground_z = np.random.normal(0.0, 0.05, num_points // 2)
    
    # Some obstacles
    obstacle_x = np.random.uniform(1.5, 2.5, num_points // 4)
    obstacle_y = np.random.uniform(-0.5, 0.5, num_points // 4)
    obstacle_z = np.random.uniform(0.0, 1.0, num_points // 4)
    
    # Wall on the right
    wall_x = np.random.uniform(0.0, 4.0, num_points // 4)
    wall_y = np.ones(num_points // 4) * 1.8
    wall_z = np.random.uniform(0.0, 1.2, num_points // 4)
    
    # Combine
    x = np.concatenate([ground_x, obstacle_x, wall_x])
    y = np.concatenate([ground_y, obstacle_y, wall_y])
    z = np.concatenate([ground_z, obstacle_z, wall_z])
    
    points = np.stack([x, y, z], axis=1)
    
    print(f"Point cloud: {points.shape[0]} points")
    
    # Render BEV
    print("Rendering BEV...")
    bev_image = pointcloud_to_bev(
        points,
        x_range=(0.0, 4.0),
        y_range=(-2.0, 2.0),
        z_range=(-0.5, 1.5),
        resolution=0.02,
        height_encoding=True,
    )
    
    print(f"BEV image shape: {bev_image.shape}")
    
    # Save demo image
    if HAS_OPENCV:
        demo_path = "demo_bev.png"
        if save_bev_image(bev_image, demo_path):
            print(f"Saved demo BEV to: {demo_path}")
    
    return bev_image


if __name__ == "__main__":
    print("BEV Rendering Demo")
    print("=" * 50)
    demo_bev_rendering()
