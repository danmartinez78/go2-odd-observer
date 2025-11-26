#!/usr/bin/env python3
"""
Split large scenarios into smaller chunks for manageable processing.

Usage:
    python scripts/chunk_large_scenario.py <scenario_path> --chunk-size 10

Example:
    python scripts/chunk_large_scenario.py data/production/sim_1_0 --chunk-size 10
    
This will create:
    data/production/sim_1_0_chunk_000_009/  (windows 0-9)
    data/production/sim_1_0_chunk_010_019/  (windows 10-19)
    etc.
"""

import argparse
import shutil
from pathlib import Path
import pandas as pd


def chunk_scenario(scenario_path: Path, chunk_size: int, output_base: Path = None):
    """
    Split a large scenario into smaller chunks.

    Args:
        scenario_path: Path to the scenario directory
        chunk_size: Number of windows per chunk
        output_base: Base directory for output chunks (default: same parent as scenario)
    """
    if not scenario_path.exists():
        raise FileNotFoundError(f"Scenario not found: {scenario_path}")

    # Find the index CSV
    index_files = sorted(scenario_path.glob("index_*.csv"))
    if not index_files:
        raise FileNotFoundError(f"No index CSV found in {scenario_path}")

    index_df = pd.read_csv(index_files[0])
    total_windows = len(index_df)

    print(f"📊 Scenario: {scenario_path.name}")
    print(f"   Total windows: {total_windows}")
    print(f"   Chunk size: {chunk_size}")
    print(
        f"   Chunks needed: {(total_windows + chunk_size - 1) // chunk_size}")

    if output_base is None:
        output_base = scenario_path.parent

    # Group windows into chunks
    for chunk_idx in range(0, total_windows, chunk_size):
        chunk_end = min(chunk_idx + chunk_size, total_windows)
        chunk_df = index_df.iloc[chunk_idx:chunk_end]

        # Create chunk directory
        chunk_name = f"{scenario_path.name}_chunk_{chunk_idx:03d}_{chunk_end-1:03d}"
        chunk_dir = output_base / chunk_name
        chunk_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n📦 Creating chunk: {chunk_name}")
        print(
            f"   Windows: {chunk_idx} to {chunk_end-1} ({len(chunk_df)} windows)")

        # Copy files for this chunk
        files_copied = 0
        for _, row in chunk_df.iterrows():
            # Copy motion file
            if pd.notna(row.get("motion_path")):
                src = scenario_path / row["motion_path"]
                if src.exists():
                    shutil.copy2(src, chunk_dir / src.name)
                    files_copied += 1

            # Copy camera image
            if pd.notna(row.get("cam_image_path")):
                src = scenario_path / row["cam_image_path"]
                if src.exists():
                    shutil.copy2(src, chunk_dir / src.name)
                    files_copied += 1

            # Copy BEV images
            for bev_col in ["bev_occupancy_path", "bev_height_path", "bev_roughness_path"]:
                if pd.notna(row.get(bev_col)):
                    src = scenario_path / row[bev_col]
                    if src.exists():
                        shutil.copy2(src, chunk_dir / src.name)
                        files_copied += 1

        # Write chunk index CSV
        chunk_index_name = f"index_{chunk_name}.csv"
        chunk_df.to_csv(chunk_dir / chunk_index_name, index=False)

        print(f"   ✅ Copied {files_copied} files")
        print(f"   📄 Created index: {chunk_index_name}")

    print(f"\n✅ Chunking complete!")


def main():
    parser = argparse.ArgumentParser(
        description="Split large scenarios into smaller chunks"
    )
    parser.add_argument(
        "scenario_path",
        type=Path,
        help="Path to the scenario directory to chunk"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=10,
        help="Number of windows per chunk (default: 10)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory for chunks (default: same parent as scenario)"
    )

    args = parser.parse_args()

    chunk_scenario(
        scenario_path=args.scenario_path,
        chunk_size=args.chunk_size,
        output_base=args.output_dir
    )


if __name__ == "__main__":
    main()
