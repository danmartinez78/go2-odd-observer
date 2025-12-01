#!/bin/bash
#
# Regenerate ALL production and test data with derived motion fields
# Adds: derived_speed, derived_yaw_rate to motion JSON files
#
# IMPORTANT: Run this from workspace root: bash scripts/regenerate_all_data.sh
#

set -e  # Exit on error

echo "================================================================================"
echo "REGENERATING ALL DATA WITH DERIVED MOTION FIELDS"
echo "================================================================================"
echo ""
echo "This will regenerate all rosbag extractions adding:"
echo "  - derived_speed (from position differentiation)"
echo "  - derived_yaw_rate (from yaw differentiation)"
echo ""

# Source ROS2 environment (CRITICAL for go2_interfaces IMU message type)
echo "Sourcing ROS2 environment..."
source /opt/ros/humble/setup.bash
source /workspaces/go2-odd-observer/go2_ros2_sdk/install/setup.bash
echo "✓ ROS2 environment sourced"
echo ""

# Change to workspace root
cd /workspaces/go2-odd-observer

# Extraction parameters (VERIFIED from existing production data)
# Using 2.0s windows with 2.0s stride (no overlap) - matches DATA_VERSIONS.md
WINDOW_LENGTH=2.0
STRIDE=2.0

echo "Parameters:"
echo "  Window length: ${WINDOW_LENGTH}s"
echo "  Stride: ${STRIDE}s (no overlap)"
echo ""

# Backup existing data
BACKUP_DIR="data/production_backup_$(date +%Y%m%d_%H%M%S)"
if [ -d "data/production" ]; then
    echo "Backing up existing production data to ${BACKUP_DIR}..."
    mv data/production "${BACKUP_DIR}"
    echo "✓ Backup complete"
fi
mkdir -p data/production

# Track progress
TOTAL=7
CURRENT=0

#===============================================================================
# SIM DATA (1 collection)
#===============================================================================

echo ""
echo "================================================================================"
echo "PART 1: SIMULATION DATA"
echo "================================================================================"
echo ""

CURRENT=$((CURRENT+1))
echo "[$CURRENT/$TOTAL] Processing sim_1..."
python scripts/extract_windows.py \
  --rosbag data/raw_rosbags/sim/1 \
  --output data/production/sim_1 \
  --window-length $WINDOW_LENGTH \
  --stride $STRIDE \
  --run-id sim_1 \
  --data-source sim
echo "✓ sim_1 complete"
echo ""

#===============================================================================
# REAL ROBOT DATA (6 collections)
#===============================================================================

echo "================================================================================"
echo "PART 2: REAL ROBOT DATA (6 collections)"
echo "================================================================================"
echo ""

# Collection 1: 173442
CURRENT=$((CURRENT+1))
echo "[$CURRENT/$TOTAL] Processing real_173442..."
python scripts/extract_windows.py \
  --rosbag data/raw_rosbags/real/collection_20251122_173442 \
  --output data/production/real_173442 \
  --window-length $WINDOW_LENGTH \
  --stride $STRIDE \
  --run-id real_173442 \
  --data-source real
echo "✓ real_173442 complete"
echo ""

# Collection 2: 173813
CURRENT=$((CURRENT+1))
echo "[$CURRENT/$TOTAL] Processing real_173813..."
python scripts/extract_windows.py \
  --rosbag data/raw_rosbags/real/collection_20251122_173813 \
  --output data/production/real_173813 \
  --window-length $WINDOW_LENGTH \
  --stride $STRIDE \
  --run-id real_173813 \
  --data-source real
echo "✓ real_173813 complete"
echo ""

# Collection 3: 174232
CURRENT=$((CURRENT+1))
echo "[$CURRENT/$TOTAL] Processing real_174232..."
python scripts/extract_windows.py \
  --rosbag data/raw_rosbags/real/collection_20251122_174232 \
  --output data/production/real_174232 \
  --window-length $WINDOW_LENGTH \
  --stride $STRIDE \
  --run-id real_174232 \
  --data-source real
echo "✓ real_174232 complete"
echo ""

# Collection 4: 174321
CURRENT=$((CURRENT+1))
echo "[$CURRENT/$TOTAL] Processing real_174321..."
python scripts/extract_windows.py \
  --rosbag data/raw_rosbags/real/collection_20251122_174321 \
  --output data/production/real_174321 \
  --window-length $WINDOW_LENGTH \
  --stride $STRIDE \
  --run-id real_174321 \
  --data-source real
echo "✓ real_174321 complete"
echo ""

# Collection 5: 174503
CURRENT=$((CURRENT+1))
echo "[$CURRENT/$TOTAL] Processing real_174503..."
python scripts/extract_windows.py \
  --rosbag data/raw_rosbags/real/collection_20251122_174503 \
  --output data/production/real_174503 \
  --window-length $WINDOW_LENGTH \
  --stride $STRIDE \
  --run-id real_174503 \
  --data-source real
echo "✓ real_174503 complete"
echo ""

# Collection 6: 174604
CURRENT=$((CURRENT+1))
echo "[$CURRENT/$TOTAL] Processing real_174604..."
python scripts/extract_windows.py \
  --rosbag data/raw_rosbags/real/collection_20251122_174604 \
  --output data/production/real_174604 \
  --window-length $WINDOW_LENGTH \
  --stride $STRIDE \
  --run-id real_174604 \
  --data-source real
echo "✓ real_174604 complete"
echo ""

#===============================================================================
# REGENERATE MANIFEST
#===============================================================================

echo "================================================================================"
echo "REGENERATING MANIFEST"
echo "================================================================================"
echo ""

cat > data/production/manifest.csv << 'EOF'
scenario_id,data_source,windows,index_csv
EOF

for scenario_dir in data/production/*/; do
    scenario_id=$(basename "$scenario_dir")
    if [[ "$scenario_id" == "chunks" ]] || [[ "$scenario_id" == manifest* ]]; then
        continue
    fi
    
    # Determine data source
    if [[ "$scenario_id" == sim* ]]; then
        data_source="sim"
    else
        data_source="real"
    fi
    
    # Count windows
    windows=$(ls "$scenario_dir"motion_*.json 2>/dev/null | wc -l)
    
    # Index file
    index_csv="index_${scenario_id}.csv"
    
    echo "${scenario_id},${data_source},${windows},${index_csv}" >> data/production/manifest.csv
done

echo "✓ Manifest regenerated"
cat data/production/manifest.csv
echo ""

#===============================================================================
# TEST DATA
#===============================================================================

echo "================================================================================"
echo "REGENERATING TEST DATA"
echo "================================================================================"
echo ""

# Clean existing test data
rm -rf data/test/sim_2win data/test/real_2win

# sim_2win: windows 10-11 from sim_1
echo "Creating sim_2win test set..."
mkdir -p data/test/sim_2win/sim_2win
cp data/production/sim_1/*w010* data/test/sim_2win/sim_2win/
cp data/production/sim_1/*w011* data/test/sim_2win/sim_2win/

cat > data/test/sim_2win/sim_2win/index_sim_2win.csv << 'EOF'
window_id,motion_file,camera_file,bev_occupancy_file,bev_height_file,bev_roughness_file
sim_1_w010,motion_sim_1_w010.json,cam_sim_1_w010.png,bev_occupancy_sim_1_w010.png,bev_height_sim_1_w010.png,bev_roughness_sim_1_w010.png
sim_1_w011,motion_sim_1_w011.json,cam_sim_1_w011.png,bev_occupancy_sim_1_w011.png,bev_height_sim_1_w011.png,bev_roughness_sim_1_w011.png
EOF
echo "✓ sim_2win created"

# real_2win: windows 10-11 from real_173442
echo "Creating real_2win test set..."
mkdir -p data/test/real_2win/real_2win
cp data/production/real_173442/*w010* data/test/real_2win/real_2win/
cp data/production/real_173442/*w011* data/test/real_2win/real_2win/

cat > data/test/real_2win/real_2win/index_real_2win.csv << 'EOF'
window_id,motion_file,camera_file,bev_occupancy_file,bev_height_file,bev_roughness_file
real_173442_w010,motion_real_173442_w010.json,cam_real_173442_w010.png,bev_occupancy_real_173442_w010.png,bev_height_real_173442_w010.png,bev_roughness_real_173442_w010.png
real_173442_w011,motion_real_173442_w011.json,cam_real_173442_w011.png,bev_occupancy_real_173442_w011.png,bev_height_real_173442_w011.png,bev_roughness_real_173442_w011.png
EOF
echo "✓ real_2win created"
echo ""

#===============================================================================
# VERIFICATION
#===============================================================================

echo "================================================================================"
echo "VERIFICATION"
echo "================================================================================"
echo ""

# Check derived fields exist
echo "Checking derived_speed field in motion files..."
python3 -c "
import json
from pathlib import Path

errors = []
for motion_file in Path('data/production').rglob('motion_*.json'):
    with open(motion_file) as f:
        data = json.load(f)
    if 'derived_speed' not in data:
        errors.append(str(motion_file))
    if 'derived_yaw_rate' not in data:
        errors.append(str(motion_file))

if errors:
    print(f'❌ Missing derived fields in {len(errors)} files!')
    for e in errors[:5]:
        print(f'   {e}')
else:
    print('✓ All motion files have derived_speed and derived_yaw_rate')
"

# Check IMU data in real files
echo ""
echo "Checking IMU data in real robot files..."
python3 -c "
import json
from pathlib import Path

real_with_imu = 0
real_without_imu = 0

for motion_file in Path('data/production').glob('real_*/motion_*.json'):
    with open(motion_file) as f:
        data = json.load(f)
    accel_x = data.get('accel_x', [])
    has_imu = any(abs(ax) > 1e-6 for ax in accel_x)
    if has_imu:
        real_with_imu += 1
    else:
        real_without_imu += 1

print(f'Real files with IMU data: {real_with_imu}')
print(f'Real files without IMU data: {real_without_imu}')
if real_with_imu > 0:
    print('✓ IMU data is being extracted (go2_interfaces working)')
else:
    print('❌ No IMU data found - check go2_interfaces is sourced!')
"
echo ""

#===============================================================================
# SUMMARY
#===============================================================================

echo "================================================================================"
echo "REGENERATION COMPLETE!"
echo "================================================================================"
echo ""
echo "Production data:"
find data/production -name "motion_*.json" | wc -l | xargs echo "  Total windows:"
ls -d data/production/*/ 2>/dev/null | wc -l | xargs echo "  Total scenarios:"
echo ""
echo "Test data:"
find data/test -name "motion_*.json" | wc -l | xargs echo "  Total windows:"
echo ""
echo "New fields added to all motion files:"
echo "  ✓ derived_speed (position-based speed in m/s)"
echo "  ✓ derived_yaw_rate (yaw-based angular velocity in rad/s)"
echo ""
echo "Backup location: ${BACKUP_DIR}"
echo ""
