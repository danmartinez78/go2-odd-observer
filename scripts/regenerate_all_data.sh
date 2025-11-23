#!/bin/bash
#
# Regenerate all production data with BEV ground filtering
# Uses 10cm height threshold to filter ground from occupancy maps
#
# IMPORTANT: Run this from workspace root: bash scripts/regenerate_all_data.sh
#

set -e  # Exit on error

echo "================================================================================"
echo "REGENERATING ALL PRODUCTION DATA WITH BEV GROUND FILTERING"
echo "================================================================================"
echo ""
echo "This will regenerate all rosbag extractions with the new BEV ground filtering."
echo "Original data has been backed up to: data/processed/production_pre_bev_filter/"
echo ""

# Source ROS2 environment
source /opt/ros/humble/setup.bash
source /workspaces/go2-odd-observer/go2_ros2_sdk/install/setup.bash

# Change to workspace root
cd /workspaces/go2-odd-observer

# Extraction parameters (VERIFIED from original index files)
WINDOW_LENGTH=2.0
STRIDE=1.0

echo "Parameters:"
echo "  Window length: ${WINDOW_LENGTH}s"
echo "  Stride: ${STRIDE}s"
echo "  (These match the original extraction parameters)"
echo ""

# Track progress
TOTAL=7
CURRENT=0

#===============================================================================
# REAL ROBOT DATA (6 collections)
#===============================================================================

echo "================================================================================"
echo "PART 1: REAL ROBOT DATA (6 collections)"
echo "================================================================================"
echo ""

# Collection 1: 173442
CURRENT=$((CURRENT+1))
echo "[$CURRENT/$TOTAL] Processing collection_20251122_173442..."
rm -rf data/processed/production/collection_20251122_173442_chunk_*
python scripts/extract_windows.py \
  --rosbag data/raw_rosbags/real/collection_20251122_173442 \
  --output data/processed/production \
  --window-length $WINDOW_LENGTH \
  --stride $STRIDE \
  --run-id collection_20251122_173442_chunk \
  --data-source real
echo "✓ Collection 173442 complete"
echo ""

# Collection 2: 173813
CURRENT=$((CURRENT+1))
echo "[$CURRENT/$TOTAL] Processing collection_20251122_173813..."
rm -rf data/processed/production/collection_20251122_173813_chunk_*
python scripts/extract_windows.py \
  --rosbag data/raw_rosbags/real/collection_20251122_173813 \
  --output data/processed/production \
  --window-length $WINDOW_LENGTH \
  --stride $STRIDE \
  --run-id collection_20251122_173813_chunk \
  --data-source real
echo "✓ Collection 173813 complete"
echo ""

# Collection 3: 174232
CURRENT=$((CURRENT+1))
echo "[$CURRENT/$TOTAL] Processing collection_20251122_174232..."
rm -rf data/processed/production/collection_20251122_174232_chunk_*
python scripts/extract_windows.py \
  --rosbag data/raw_rosbags/real/collection_20251122_174232 \
  --output data/processed/production \
  --window-length $WINDOW_LENGTH \
  --stride $STRIDE \
  --run-id collection_20251122_174232_chunk \
  --data-source real
echo "✓ Collection 174232 complete"
echo ""

# Collection 4: 174321
CURRENT=$((CURRENT+1))
echo "[$CURRENT/$TOTAL] Processing collection_20251122_174321..."
rm -rf data/processed/production/collection_20251122_174321_chunk_*
python scripts/extract_windows.py \
  --rosbag data/raw_rosbags/real/collection_20251122_174321 \
  --output data/processed/production \
  --window-length $WINDOW_LENGTH \
  --stride $STRIDE \
  --run-id collection_20251122_174321_chunk \
  --data-source real
echo "✓ Collection 174321 complete"
echo ""

# Collection 5: 174503
CURRENT=$((CURRENT+1))
echo "[$CURRENT/$TOTAL] Processing collection_20251122_174503..."
rm -rf data/processed/production/collection_20251122_174503_chunk_*
python scripts/extract_windows.py \
  --rosbag data/raw_rosbags/real/collection_20251122_174503 \
  --output data/processed/production \
  --window-length $WINDOW_LENGTH \
  --stride $STRIDE \
  --run-id collection_20251122_174503_chunk \
  --data-source real
echo "✓ Collection 174503 complete"
echo ""

# Collection 6: 174604
CURRENT=$((CURRENT+1))
echo "[$CURRENT/$TOTAL] Processing collection_20251122_174604..."
rm -rf data/processed/production/collection_20251122_174604_chunk_*
python scripts/extract_windows.py \
  --rosbag data/raw_rosbags/real/collection_20251122_174604 \
  --output data/processed/production \
  --window-length $WINDOW_LENGTH \
  --stride $STRIDE \
  --run-id collection_20251122_174604_chunk \
  --data-source real
echo "✓ Collection 174604 complete"
echo ""

#===============================================================================
# SIM DATA (1 collection)
#===============================================================================

echo "================================================================================"
echo "PART 2: SIMULATION DATA (1 collection)"
echo "================================================================================"
echo ""

# Sim collection
CURRENT=$((CURRENT+1))
echo "[$CURRENT/$TOTAL] Processing sim_run_new..."
rm -rf data/processed/production/sim_run_new
python scripts/extract_windows.py \
  --rosbag data/raw_rosbags/sim/1 \
  --output data/processed/production \
  --window-length $WINDOW_LENGTH \
  --stride $STRIDE \
  --run-id sim_run_new \
  --data-source sim
echo "✓ Sim run complete"
echo ""

#===============================================================================
# COMPLETION SUMMARY
#===============================================================================

echo "================================================================================"
echo "REGENERATION COMPLETE!"
echo "================================================================================"
echo ""
echo "Summary:"
find data/processed/production -name "motion_*.json" -not -path "*/production_pre_bev_filter/*" | wc -l | xargs echo "  Total windows regenerated:"
echo ""
echo "Backup location: data/processed/production_pre_bev_filter/"
echo ""

#===============================================================================
# POST-PROCESSING: CHUNK LARGE SCENARIOS
#===============================================================================

echo "================================================================================"
echo "CHUNKING LARGE SCENARIOS (>40 windows)"
echo "================================================================================"
echo ""
echo "Splitting scenarios that exceed 40-window agent limit..."
python scripts/split_large_scenarios.py
echo ""
echo "✓ Scenario chunking complete"
echo ""

#===============================================================================
# POST-PROCESSING: REGENERATE TEST SETS
#===============================================================================

echo "================================================================================"
echo "REGENERATING TEST SETS FROM CHUNKED PRODUCTION DATA"
echo "================================================================================"
echo ""
echo "Creating curated test sets (2 windows per collection)..."
python scripts/create_real_test_sets.py
echo ""
echo "✓ Test sets regenerated"
echo ""

#===============================================================================
# FINAL SUMMARY
#===============================================================================

echo "================================================================================"
echo "ALL DATA REGENERATION COMPLETE!"
echo "================================================================================"
echo ""
echo "Production data:"
find data/processed/production -name "motion_*.json" -not -path "*/production_pre_bev_filter/*" | wc -l | xargs echo "  Total windows:"
ls -d data/processed/production/collection_*_chunk_* data/processed/production/sim_* 2>/dev/null | wc -l | xargs echo "  Total scenarios (chunked):"
echo ""
echo "Test data:"
find data/processed/test_data -name "motion_*.json" | wc -l | xargs echo "  Total windows:"
echo ""
echo "Improvements applied:"
echo "  ✓ BEV ground filtering (10cm height threshold)"
echo "  ✓ Correct IMU data extraction (go2_interfaces)"
echo "  ✓ Scenario chunking (≤40 windows per chunk)"
echo ""
echo "Next steps:"
echo "  1. Verify window counts match expectations (332 total)"
echo "  2. Compare BEV occupancy images (old vs new)"
echo "  3. Verify IMU data is non-zero"
echo "  4. Run perception analysis on sample scenarios"
echo "  5. Generate updated statistics and reports"
echo ""
