#!/usr/bin/env python3
"""
Split large scenarios into chunks for agent processing.

The agent workflow has a limit of ~40 windows per scenario.
This script splits scenarios exceeding this threshold into manageable chunks.
"""

import json
import shutil
from pathlib import Path
from typing import List, Dict
import pandas as pd


def split_scenario(
    scenario_path: Path,
    chunk_size: int = 25,
    threshold: int = 40
) -> List[Dict]:
    """
    Split a scenario into chunks if it exceeds the threshold.

    Args:
        scenario_path: Path to scenario directory
        chunk_size: Maximum windows per chunk (default: 25)
        threshold: Only split if scenario has more than this many windows

    Returns:
        List of chunk metadata dictionaries
    """
    # Get index file
    index_files = list(scenario_path.glob("index_*.csv"))
    if not index_files:
        print(f"No index file found in {scenario_path}")
        return []

    index_df = pd.read_csv(index_files[0])
    total_windows = len(index_df)

    scenario_name = scenario_path.name

    # Check if splitting is needed
    if total_windows <= threshold:
        print(f"✓ {scenario_name}: {total_windows} windows (no split needed)")
        return []

    print(f"\n📦 Splitting {scenario_name}: {total_windows} windows")

    # Calculate number of chunks
    num_chunks = (total_windows + chunk_size - 1) // chunk_size

    chunks_created = []

    for chunk_idx in range(num_chunks):
        start_window = chunk_idx * chunk_size
        end_window = min(start_window + chunk_size, total_windows)

        chunk_name = f"{scenario_name}_{chunk_idx + 1:02d}"
        chunk_dir = scenario_path.parent / chunk_name
        chunk_dir.mkdir(exist_ok=True)

        print(
            f"  Chunk {chunk_idx + 1}/{num_chunks}: windows {start_window}-{end_window-1} → {chunk_name}")

        # Select windows for this chunk
        chunk_df = index_df.iloc[start_window:end_window].copy()

        # Update window IDs to be sequential within chunk
        chunk_df['window_id'] = range(len(chunk_df))

        # Copy files
        files_copied = 0
        for new_idx, orig_idx in enumerate(range(start_window, end_window)):
            for file_type in ['motion', 'cam', 'bev_occupancy', 'bev_height', 'bev_density', 'bev_roughness']:
                src_pattern = f"{file_type}_{scenario_name}_w{orig_idx:03d}.*"
                src_files = list(scenario_path.glob(src_pattern))

                for src in src_files:
                    dst = chunk_dir / \
                        f"{file_type}_{chunk_name}_w{new_idx:03d}{src.suffix}"
                    shutil.copy2(src, dst)
                    files_copied += 1

        # Update index paths
        for col in chunk_df.columns:
            if col.endswith('_path'):
                chunk_df[col] = chunk_df[col].str.replace(
                    scenario_name, chunk_name)
                # Update window IDs in paths
                for new_idx in range(len(chunk_df)):
                    old_window_id = start_window + new_idx
                    chunk_df.loc[chunk_df.index[new_idx], col] = \
                        chunk_df.loc[chunk_df.index[new_idx], col].replace(
                            f"_w{old_window_id:03d}", f"_w{new_idx:03d}"
                    )

        # Save chunk index
        chunk_df.to_csv(chunk_dir / f"index_{chunk_name}.csv", index=False)

        chunks_created.append({
            "chunk_id": chunk_idx + 1,
            "chunk_name": chunk_name,
            "source_scenario": scenario_name,
            "window_range": [start_window, end_window - 1],
            "num_windows": end_window - start_window,
            "files_copied": files_copied,
            "output_path": str(chunk_dir.relative_to(scenario_path.parent.parent))
        })

    # Create manifest
    manifest = {
        "source_scenario": scenario_name,
        "source_path": str(scenario_path),
        "total_windows": total_windows,
        "chunk_size": chunk_size,
        "num_chunks": num_chunks,
        "chunks": chunks_created
    }

    manifest_path = scenario_path.parent / \
        f"{scenario_name}_chunks_manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f"  ✓ Created {num_chunks} chunks, manifest: {manifest_path.name}")

    return chunks_created


def main():
    """Split all large scenarios in production directory."""
    production_dir = Path("data/processed/production")

    if not production_dir.exists():
        print(f"Production directory not found: {production_dir}")
        return

    print("="*80)
    print("SPLITTING LARGE SCENARIOS")
    print("="*80)
    print()
    print("Threshold: 40 windows")
    print("Chunk size: 25 windows")
    print()

    # Find all scenario directories (exclude manifests, backups, etc.)
    scenarios = [
        d for d in production_dir.iterdir()
        if d.is_dir()
        and not d.name.endswith('_pre_bev_filter')
        and not d.name.endswith('_OLD')
        and not '_manifest' in d.name
    ]

    total_chunks_created = 0
    scenarios_split = 0

    for scenario in sorted(scenarios):
        chunks = split_scenario(scenario, chunk_size=25, threshold=40)
        if chunks:
            total_chunks_created += len(chunks)
            scenarios_split += 1

    print()
    print("="*80)
    print("SPLITTING COMPLETE")
    print("="*80)
    print(f"Scenarios split: {scenarios_split}")
    print(f"Total chunks created: {total_chunks_created}")
    print()
    print("Note: Original unsplit directories are preserved.")
    print("You may want to remove them after verifying chunks are correct.")
    print()


if __name__ == "__main__":
    main()
