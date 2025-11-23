#!/usr/bin/env python3
"""
Create test sets from real robot data.

Select representative windows from each collection to create
small, curated test scenarios for rapid validation.
"""

import json
import shutil
from pathlib import Path
from typing import List, Dict
import pandas as pd


def select_windows(collection_path: Path, num_windows: int = 2) -> List[int]:
    """
    Select representative windows from a collection.

    Strategy:
    - Pick one from early in the run (initial behavior)
    - Pick one from middle (steady state)
    """
    index_file = list(collection_path.glob("index_*.csv"))[0]
    df = pd.read_csv(index_file)

    total = len(df)
    if total < num_windows:
        return list(range(total))

    # Early window (around 20% through)
    early_idx = int(total * 0.2)

    # Middle window (around 50% through)
    middle_idx = int(total * 0.5)

    return [early_idx, middle_idx]


def create_test_set(
    collection_path: Path,
    output_path: Path,
    window_indices: List[int],
    test_name: str
):
    """Create a test set from selected windows."""

    print(f"\nCreating test set: {test_name}")
    print(f"  Source: {collection_path.name}")
    print(f"  Windows: {window_indices}")

    output_path.mkdir(parents=True, exist_ok=True)

    # Get collection info
    index_file = list(collection_path.glob("index_*.csv"))[0]
    df = pd.read_csv(index_file)

    # Select rows
    selected_df = df.iloc[window_indices].reset_index(drop=True)

    # Update window IDs to be sequential
    selected_df['window_id'] = range(len(selected_df))

    # Copy files for selected windows
    copied_files = []
    for idx, row in selected_df.iterrows():
        original_window_id = df.iloc[window_indices[idx]]['window_id']

        # Get original filenames (with original window ID)
        run_id = index_file.stem.replace('index_', '')

        files_to_copy = [
            ('motion_path', f"motion_{run_id}_w{original_window_id:03d}.json"),
            ('cam_image_path', f"cam_{run_id}_w{original_window_id:03d}.png"),
            ('bev_occupancy_path',
             f"bev_occupancy_{run_id}_w{original_window_id:03d}.png"),
            ('bev_height_path',
             f"bev_height_{run_id}_w{original_window_id:03d}.png"),
            ('bev_density_path',
             f"bev_density_{run_id}_w{original_window_id:03d}.png"),
            ('bev_roughness_path',
             f"bev_roughness_{run_id}_w{original_window_id:03d}.png"),
        ]

        # Copy each file with new sequential ID and test set name
        for col_name, original_filename in files_to_copy:
            src = collection_path / original_filename
            if src.exists():
                # Extract file type (motion, cam, bev_occupancy, etc.)
                file_type = original_filename.split('_')[0]
                if original_filename.startswith('bev_'):
                    # Handle bev_occupancy, bev_height, etc.
                    file_type = '_'.join(original_filename.split('_')[:2])

                # Get file extension
                ext = src.suffix

                # New filename with test set name and sequential window ID
                new_filename = f"{file_type}_{test_name}_w{idx:03d}{ext}"
                dst = output_path / new_filename
                shutil.copy2(src, dst)
                copied_files.append(new_filename)

                # Update path in dataframe
                selected_df.at[idx, col_name] = new_filename

    # Save new index
    new_index_file = output_path / f"index_{test_name}.csv"
    selected_df.to_csv(new_index_file, index=False)

    # Create metadata
    metadata = {
        'test_name': test_name,
        'source_collection': collection_path.name,
        'original_windows': window_indices,
        'num_windows': len(selected_df),
        'files_copied': len(copied_files)
    }

    metadata_file = output_path / 'metadata.json'
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"  ✓ Created {len(selected_df)} window test set")
    print(f"  ✓ Copied {len(copied_files)} files")
    print(f"  Output: {output_path}")

    return metadata


def main():
    """Create test sets from all collections."""

    project_root = Path(__file__).parent.parent
    data_dir = project_root / "data" / "processed" / "production"
    test_dir = project_root / "data" / "processed" / "test_data" / "real"

    # Find all collections (only _chunk_01 to get one per collection)
    collections = sorted(data_dir.glob("collection_*_chunk_01"))

    if not collections:
        print("No collections found!")
        return

    print(f"Found {len(collections)} collections")
    print(f"Creating 2-window test sets from each...")

    all_metadata = []

    for i, collection in enumerate(collections):
        # Extract date from collection name
        # collection_20251122_173442_chunk_01 -> 173442
        parts = collection.name.split('_')
        time_id = parts[2]  # The HHMMSS part

        # Create test name
        # real_01_173442, etc.
        test_name = f"real_{i+1:02d}_{time_id}"
        output_path = test_dir / test_name

        # Select windows
        window_indices = select_windows(collection, num_windows=2)

        # Create test set
        metadata = create_test_set(
            collection, output_path, window_indices, test_name)
        all_metadata.append(metadata)

    # Create summary
    summary_file = test_dir / "real_test_sets_summary.json"
    with open(summary_file, 'w') as f:
        json.dump({
            'num_test_sets': len(all_metadata),
            'total_windows': sum(m['num_windows'] for m in all_metadata),
            'test_sets': all_metadata
        }, f, indent=2)

    print(f"\n{'='*60}")
    print(f"✓ Created {len(all_metadata)} test sets")
    print(f"✓ Total windows: {sum(m['num_windows'] for m in all_metadata)}")
    print(f"✓ Summary: {summary_file}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
