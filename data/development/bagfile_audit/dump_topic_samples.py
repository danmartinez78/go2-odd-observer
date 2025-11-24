#!/usr/bin/env python3
"""
Dump sample messages from all topics in a bagfile for cloud agent analysis.
Based on extract_windows.py pattern but dumps ALL topics (not just ones we use).
"""
import json
import sys
from pathlib import Path
from collections import defaultdict

from rosbag2_py import SequentialReader, StorageOptions, ConverterOptions
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message


def ns_to_sec(timestamp_ns):
    """Convert nanosecond timestamp to seconds."""
    return timestamp_ns / 1e9


def message_to_dict(msg):
    """Convert ROS2 message to dictionary for JSON serialization."""
    result = {}

    # Get all slots (fields) of the message
    if hasattr(msg, 'get_fields_and_field_types'):
        fields = msg.get_fields_and_field_types().keys()
    elif hasattr(msg, '__slots__'):
        fields = msg.__slots__
    else:
        return str(msg)

    for field in fields:
        try:
            value = getattr(msg, field)

            # Handle nested messages recursively
            if hasattr(value, '__slots__') or hasattr(value, 'get_fields_and_field_types'):
                result[field] = message_to_dict(value)
            # Handle arrays/lists
            elif isinstance(value, (list, tuple)):
                if len(value) > 0 and (hasattr(value[0], '__slots__') or hasattr(value[0], 'get_fields_and_field_types')):
                    result[field] = [message_to_dict(
                        item) for item in value[:5]]  # Limit to 5 items
                else:
                    result[field] = list(value[:10]) if len(
                        value) > 10 else list(value)
            # Handle numpy arrays
            elif hasattr(value, 'tolist'):
                arr = value.tolist()
                result[field] = arr[:10] if len(arr) > 10 else arr
            # Handle bytes
            elif isinstance(value, bytes):
                result[field] = f"<bytes: {len(value)} bytes>"
            else:
                result[field] = value
        except Exception as e:
            result[field] = f"<error: {str(e)}>"

    return result


def dump_topic_samples(bagfile_path, output_dir, num_samples=3):
    """
    Read bagfile and dump sample messages from each topic.

    Args:
        bagfile_path: Path to .db3 file
        output_dir: Where to save JSON samples
        num_samples: Number of sample messages per topic
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Setup bag reader
    storage_options = StorageOptions(
        uri=str(bagfile_path), storage_id='sqlite3')
    converter_options = ConverterOptions(
        input_serialization_format='cdr',
        output_serialization_format='cdr'
    )

    reader = SequentialReader()
    reader.open(storage_options, converter_options)

    # Get topic metadata
    topic_types = reader.get_all_topics_and_types()
    topic_type_map = {t.name: t.type for t in topic_types}

    print(f"Found {len(topic_types)} topics in bagfile")

    # Collect samples from each topic
    topic_samples = defaultdict(list)
    topic_counts = defaultdict(int)

    while reader.has_next():
        topic, data, timestamp = reader.read_next()
        topic_counts[topic] += 1

        # Only collect samples if we haven't reached the limit
        if len(topic_samples[topic]) < num_samples:
            try:
                msg_type = get_message(topic_type_map[topic])
                msg = deserialize_message(data, msg_type)

                sample = {
                    'timestamp_ns': timestamp,
                    'timestamp_sec': ns_to_sec(timestamp),
                    'message': message_to_dict(msg)
                }
                topic_samples[topic].append(sample)

            except Exception as e:
                print(f"Warning: Could not deserialize {topic}: {e}")

    # Save samples for each topic
    results = {}
    for topic, samples in topic_samples.items():
        topic_name = topic.replace('/', '_').lstrip('_')
        output_file = output_dir / f"{topic_name}_samples.json"

        topic_data = {
            'topic': topic,
            'type': topic_type_map[topic],
            'total_messages': topic_counts[topic],
            'samples': samples
        }

        with open(output_file, 'w') as f:
            json.dump(topic_data, f, indent=2, default=str)

        results[topic] = {
            'type': topic_type_map[topic],
            'total_messages': topic_counts[topic],
            'samples_collected': len(samples),
            'output_file': str(output_file)
        }

        print(
            f"✓ {topic}: {topic_counts[topic]} messages, saved {len(samples)} samples")

    # Save summary
    summary_file = output_dir / 'topic_samples_summary.json'
    with open(summary_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✓ Saved summary to {summary_file}")
    return results


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(
            "Usage: python dump_topic_samples.py <bagfile.db3> <output_dir> [num_samples]")
        sys.exit(1)

    bagfile = sys.argv[1]
    output_dir = sys.argv[2]
    num_samples = int(sys.argv[3]) if len(sys.argv) > 3 else 3

    dump_topic_samples(bagfile, output_dir, num_samples)
