#!/usr/bin/env python3
"""
Parse ros2 bag info output files and create structured JSON for cloud agent analysis.
"""
import json
import re
from pathlib import Path


def parse_bag_info(filepath):
    """Parse a ros2 bag info text file into structured data."""
    with open(filepath, 'r') as f:
        content = f.read()

    data = {
        'source_file': str(filepath),
        'metadata': {},
        'topics': []
    }

    # Parse metadata
    for line in content.split('\n'):
        if line.startswith('Files:'):
            data['metadata']['files'] = line.split('Files:')[1].strip()
        elif line.startswith('Bag size:'):
            data['metadata']['bag_size'] = line.split('Bag size:')[1].strip()
        elif line.startswith('Storage id:'):
            data['metadata']['storage_id'] = line.split('Storage id:')[
                1].strip()
        elif line.startswith('Duration:'):
            duration_str = line.split('Duration:')[1].strip()
            data['metadata']['duration_seconds'] = float(
                duration_str.replace('s', ''))
        elif line.startswith('Start:'):
            data['metadata']['start_time'] = line.split('Start:')[1].strip()
        elif line.startswith('End:'):
            data['metadata']['end_time'] = line.split('End:')[1].strip()
        elif line.startswith('Messages:'):
            data['metadata']['total_messages'] = int(
                line.split('Messages:')[1].strip())

    # Parse topics
    topic_pattern = r'Topic: (\S+) \| Type: (\S+) \| Count: (\d+) \| Serialization Format: (\S+)'
    for match in re.finditer(topic_pattern, content):
        topic_name, msg_type, count, serialization = match.groups()

        # Calculate message rate
        duration = data['metadata'].get('duration_seconds', 1)
        msg_rate = int(count) / duration if duration > 0 else 0

        topic_data = {
            'topic': topic_name,
            'type': msg_type,
            'message_count': int(count),
            'message_rate_hz': round(msg_rate, 2),
            'serialization': serialization
        }
        data['topics'].append(topic_data)

    # Sort topics by message count (descending)
    data['topics'].sort(key=lambda x: x['message_count'], reverse=True)

    return data


def main():
    audit_dir = Path(__file__).parent

    # Parse all bag info files
    results = {}
    for info_file in audit_dir.glob('*_bag_info.txt'):
        scenario_name = info_file.stem.replace('_bag_info', '')
        print(f"Parsing {scenario_name}...")
        results[scenario_name] = parse_bag_info(info_file)

    # Save combined results
    output_file = audit_dir / 'bagfile_audit_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✓ Saved results to {output_file}")

    # Print summary
    print("\n=== BAGFILE AUDIT SUMMARY ===\n")
    for scenario, data in results.items():
        print(f"{scenario}:")
        print(
            f"  Duration: {data['metadata'].get('duration_seconds', 0):.1f}s")
        print(f"  Total Messages: {data['metadata'].get('total_messages', 0)}")
        print(f"  Topics: {len(data['topics'])}")
        print(f"  Key topics:")
        for topic in data['topics'][:8]:  # Top 8 topics
            print(
                f"    - {topic['topic']}: {topic['message_rate_hz']} Hz ({topic['message_count']} msgs)")
        print()


if __name__ == '__main__':
    main()
