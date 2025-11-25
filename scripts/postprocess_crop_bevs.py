#!/usr/bin/env python3
"""
Postprocess existing BEV images by applying auto-crop.

This script batch-processes all BEV images in existing scenario directories,
cropping them to remove empty borders while preserving occupied regions with margin.

Usage:
    # Crop all BEVs in production data (in-place)
    python postprocess_crop_bevs.py data/processed/production

    # Crop test data
    python postprocess_crop_bevs.py data/test

    # Dry run (show what would be cropped without modifying files)
    python postprocess_crop_bevs.py data/processed/production --dry-run
"""

from odd_agents.utils import auto_crop_bev
import argparse
import cv2
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def crop_bevs_in_scenario(scenario_dir: Path, dry_run: bool = False) -> dict:
    """
    Crop all BEV images in a single scenario directory.

    Args:
        scenario_dir: Path to scenario directory
        dry_run: If True, don't modify files, just report sizes

    Returns:
        Dictionary with statistics (files_processed, total_before, total_after)
    """
    bev_types = ['occupancy', 'height', 'density', 'roughness']
    stats = {
        'files_processed': 0,
        'files_skipped': 0,
        'total_pixels_before': 0,
        'total_pixels_after': 0,
    }

    # Find all BEV files
    for bev_type in bev_types:
        bev_files = sorted(scenario_dir.glob(f"bev_{bev_type}_*.png"))

        for bev_path in bev_files:
            # Load image
            img = cv2.imread(str(bev_path))
            if img is None:
                print(f"  ⚠️  Could not load {bev_path.name}, skipping")
                stats['files_skipped'] += 1
                continue

            original_pixels = img.shape[0] * img.shape[1]

            # Crop
            cropped = auto_crop_bev(img)
            cropped_pixels = cropped.shape[0] * cropped.shape[1]

            # Calculate reduction
            reduction_pct = (1 - cropped_pixels / original_pixels) * 100

            # Update stats
            stats['total_pixels_before'] += original_pixels
            stats['total_pixels_after'] += cropped_pixels

            # Save or report
            if not dry_run:
                cv2.imwrite(str(bev_path), cropped)
                print(
                    f"  ✓ {bev_path.name}: {img.shape[:2]} → {cropped.shape[:2]} ({reduction_pct:.1f}% smaller)")
            else:
                print(
                    f"  [DRY RUN] {bev_path.name}: {img.shape[:2]} → {cropped.shape[:2]} ({reduction_pct:.1f}% smaller)")

            stats['files_processed'] += 1

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Postprocess BEV images by applying auto-crop",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "data_dir",
        type=Path,
        help="Directory containing scenario subdirectories with BEV images"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be cropped without modifying files"
    )

    args = parser.parse_args()

    if not args.data_dir.exists():
        print(f"Error: Directory not found: {args.data_dir}")
        sys.exit(1)

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Cropping BEVs in: {args.data_dir}")
    print()

    # Find all scenario directories or if data_dir itself has BEVs, process it
    if any(args.data_dir.glob("bev_*.png")):
        # data_dir itself is a scenario directory
        scenario_dirs = [args.data_dir]
    else:
        # Find scenario subdirectories
        # Scenarios typically have format: collection_YYYYMMDD_HHMMSS_chunk_NN
        # or test format: real_NN_HHMMSS, sim_run_new_NN
        scenario_dirs = [
            d for d in args.data_dir.rglob("*")
            if d.is_dir() and d != args.data_dir and any(d.glob("bev_*.png"))
        ]

    if not scenario_dirs:
        print(
            f"No scenario directories with BEV images found in {args.data_dir}")
        sys.exit(0)

    print(f"Found {len(scenario_dirs)} scenario directories")
    print()

    # Process each scenario
    total_stats = {
        'scenarios': 0,
        'files_processed': 0,
        'files_skipped': 0,
        'total_pixels_before': 0,
        'total_pixels_after': 0,
    }

    for scenario_dir in sorted(scenario_dirs):
        print(f"Processing: {scenario_dir.name}")
        stats = crop_bevs_in_scenario(scenario_dir, dry_run=args.dry_run)

        # Accumulate stats
        total_stats['scenarios'] += 1
        total_stats['files_processed'] += stats['files_processed']
        total_stats['files_skipped'] += stats['files_skipped']
        total_stats['total_pixels_before'] += stats['total_pixels_before']
        total_stats['total_pixels_after'] += stats['total_pixels_after']

        print()

    # Print summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Scenarios processed: {total_stats['scenarios']}")
    print(f"Files processed: {total_stats['files_processed']}")
    print(f"Files skipped: {total_stats['files_skipped']}")

    if total_stats['total_pixels_before'] > 0:
        overall_reduction = (
            1 - total_stats['total_pixels_after'] / total_stats['total_pixels_before']) * 100
        print(f"Overall size reduction: {overall_reduction:.1f}%")
        print(f"  Before: {total_stats['total_pixels_before']:,} total pixels")
        print(f"  After:  {total_stats['total_pixels_after']:,} total pixels")

    if args.dry_run:
        print()
        print("This was a dry run. No files were modified.")
        print("Run without --dry-run to apply changes.")


if __name__ == "__main__":
    main()
