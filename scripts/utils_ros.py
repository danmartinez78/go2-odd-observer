"""
ROS2 Utility Functions

Helper functions for working with ROS2 messages, time synchronization,
and topic reading.
"""

from typing import List, Dict, Any, Optional, Tuple
import numpy as np


def sync_messages_by_time(
    messages: List[Tuple[float, Any]],
    target_time: float,
    tolerance: float = 0.1,
) -> Optional[Any]:
    """
    Find message closest to target time within tolerance.
    
    Args:
        messages: List of (timestamp, message) tuples
        target_time: Target timestamp in seconds
        tolerance: Maximum allowed time difference in seconds
        
    Returns:
        Message closest to target_time, or None if no match within tolerance
    """
    if not messages:
        return None
    
    # Find closest message
    min_diff = float('inf')
    closest_msg = None
    
    for timestamp, msg in messages:
        diff = abs(timestamp - target_time)
        if diff < min_diff and diff <= tolerance:
            min_diff = diff
            closest_msg = msg
    
    return closest_msg


def interpolate_messages(
    messages: List[Tuple[float, Dict[str, float]]],
    target_time: float,
) -> Optional[Dict[str, float]]:
    """
    Linearly interpolate between messages to estimate values at target time.
    
    Args:
        messages: List of (timestamp, data_dict) tuples
        target_time: Target timestamp in seconds
        
    Returns:
        Interpolated data dictionary, or None if not possible
    """
    if len(messages) < 2:
        return None
    
    # Find bracketing messages
    before = None
    after = None
    
    for i, (t, msg) in enumerate(messages):
        if t <= target_time:
            before = (t, msg)
        if t >= target_time and after is None:
            after = (t, msg)
            break
    
    if before is None or after is None:
        # Target time outside range, return nearest
        if before is None:
            return after[1] if after else None
        if after is None:
            return before[1]
    
    # Interpolate
    t_before, msg_before = before
    t_after, msg_after = after
    
    if t_after == t_before:
        return msg_before
    
    # Linear interpolation weight
    alpha = (target_time - t_before) / (t_after - t_before)
    alpha = np.clip(alpha, 0.0, 1.0)
    
    # Interpolate each field
    result = {}
    for key in msg_before.keys():
        if key in msg_after:
            val_before = msg_before[key]
            val_after = msg_after[key]
            
            if isinstance(val_before, (int, float)) and isinstance(val_after, (int, float)):
                result[key] = val_before * (1 - alpha) + val_after * alpha
            else:
                # Non-numeric, take nearest
                result[key] = msg_before[key] if alpha < 0.5 else msg_after[key]
    
    return result


def ros_time_to_seconds(sec: int, nanosec: int) -> float:
    """
    Convert ROS2 time (sec + nanosec) to float seconds.
    
    Args:
        sec: Seconds component
        nanosec: Nanoseconds component
        
    Returns:
        Time in seconds as float
    """
    return float(sec) + float(nanosec) * 1e-9


def aggregate_motion_window(
    motion_samples: List[Dict[str, Any]],
    window_start: float,
    window_end: float,
) -> Dict[str, List[float]]:
    """
    Aggregate motion samples within a time window.
    
    Args:
        motion_samples: List of dictionaries with motion data and timestamps
        window_start: Window start time in seconds
        window_end: Window end time in seconds
        
    Returns:
        Dictionary with lists of values for each motion field
    """
    # Filter samples in window
    window_samples = [
        s for s in motion_samples
        if window_start <= s.get('timestamp', 0.0) < window_end
    ]
    
    if not window_samples:
        return {}
    
    # Aggregate into lists
    result = {
        "timestamps": [],
        "cmd_vx": [],
        "cmd_wz": [],
        "odom_vx": [],
        "odom_wz": [],
        "roll": [],
        "pitch": [],
        "yaw": [],
        "accel_x": [],
        "accel_y": [],
        "accel_z": [],
    }
    
    for sample in window_samples:
        for key in result.keys():
            if key in sample:
                result[key].append(sample[key])
    
    return result


# TODO: Add actual ROS2 message deserialization utilities
# These would use rclpy.serialization and specific message types:
# - geometry_msgs.msg.Twist
# - nav_msgs.msg.Odometry
# - sensor_msgs.msg.Imu
# - sensor_msgs.msg.JointState
# - sensor_msgs.msg.Image
# - sensor_msgs.msg.PointCloud2


def extract_twist_data(twist_msg) -> Dict[str, float]:
    """
    Extract velocity data from Twist message.
    
    TODO: Implement with actual ROS2 message
    """
    raise NotImplementedError("ROS2 message deserialization not yet implemented")


def extract_odom_data(odom_msg) -> Dict[str, float]:
    """
    Extract odometry data from Odometry message.
    
    TODO: Implement with actual ROS2 message
    """
    raise NotImplementedError("ROS2 message deserialization not yet implemented")


def extract_imu_data(imu_msg) -> Dict[str, float]:
    """
    Extract IMU data from Imu message.
    
    TODO: Implement with actual ROS2 message
    """
    raise NotImplementedError("ROS2 message deserialization not yet implemented")


if __name__ == "__main__":
    # Test time sync
    print("Testing message synchronization...")
    
    test_messages = [
        (0.0, {"value": 0}),
        (1.0, {"value": 10}),
        (2.0, {"value": 20}),
        (3.0, {"value": 30}),
    ]
    
    result = sync_messages_by_time(test_messages, 1.5, tolerance=0.6)
    print(f"Closest to 1.5s: {result}")
    
    # Test interpolation
    result = interpolate_messages(test_messages, 1.5)
    print(f"Interpolated at 1.5s: {result}")
