#!/usr/bin/env python3
"""
Sample messages from beginning, middle, and end of bagfile to check if velocity is ever populated.
"""
import json
import sys
from pathlib import Path

from rosbag2_py import SequentialReader, StorageOptions, ConverterOptions
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message


def message_to_dict(msg):
    """Convert ROS2 message to dictionary."""
    result = {}
    fields = msg.get_fields_and_field_types().keys() if hasattr(
        msg, 'get_fields_and_field_types') else msg.__slots__

    for field in fields:
        try:
            value = getattr(msg, field)
            if hasattr(value, '__slots__') or hasattr(value, 'get_fields_and_field_types'):
                result[field] = message_to_dict(value)
            elif isinstance(value, (list, tuple)):
                if len(value) > 0 and (hasattr(value[0], '__slots__') or hasattr(value[0], 'get_fields_and_field_types')):
                    result[field] = [message_to_dict(item) for item in value]
                else:
                    result[field] = list(value)
            elif hasattr(value, 'tolist'):
                result[field] = value.tolist()
            elif isinstance(value, bytes):
                result[field] = f"<bytes: {len(value)} bytes>"
            else:
                result[field] = value
        except Exception as e:
            result[field] = f"<error: {str(e)}>"
    return result


def sample_topic_throughout(bagfile_path, topic_name, num_samples=5):
    """Sample a topic from evenly distributed points throughout the bag."""
    storage_options = StorageOptions(
        uri=str(bagfile_path), storage_id='sqlite3')
    converter_options = ConverterOptions(
        input_serialization_format='cdr', output_serialization_format='cdr')

    reader = SequentialReader()
    reader.open(storage_options, converter_options)

    # Get topic type
    topic_types = reader.get_all_topics_and_types()
    topic_type_map = {t.name: t.type for t in topic_types}

    if topic_name not in topic_type_map:
        print(f"Topic {topic_name} not found!")
        return None

    msg_type = get_message(topic_type_map[topic_name])

    # First pass: count messages for this topic
    messages = []
    while reader.has_next():
        topic, data, timestamp = reader.read_next()
        if topic == topic_name:
            messages.append((data, timestamp))

    total = len(messages)
    if total == 0:
        print(f"No messages found for {topic_name}")
        return None

    print(f"Found {total} messages for {topic_name}")

    # Sample evenly distributed
    indices = [int(i * (total - 1) / (num_samples - 1))
               for i in range(num_samples)]
    samples = []

    for idx in indices:
        data, timestamp = messages[idx]
        msg = deserialize_message(data, msg_type)
        samples.append({
            'index': idx,
            'total_messages': total,
            'percentage': f"{idx/total*100:.1f}%",
            'timestamp_ns': timestamp,
            'message': message_to_dict(msg)
        })

    return samples


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(
            "Usage: python sample_throughout_bag.py <bagfile.db3> <topic_name> [num_samples]")
        sys.exit(1)

    bagfile = sys.argv[1]
    topic = sys.argv[2]
    num_samples = int(sys.argv[3]) if len(sys.argv) > 3 else 5

    samples = sample_topic_throughout(bagfile, topic, num_samples)

    if samples:
        print(f"\n=== SAMPLES FROM {topic} ===\n")
        for s in samples:
            print(
                f"Message {s['index']}/{s['total_messages']} ({s['percentage']} through bag):")
            print(json.dumps(s['message'], indent=2))
            print()
