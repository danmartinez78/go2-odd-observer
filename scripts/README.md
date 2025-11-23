# Scripts Directory

Executable scripts for the Go2 ODD Observer project.

---

## 🎯 Core Production Scripts

### `run_analysis.py` - **Interactive Analysis Runner**

**Purpose**: User-friendly interface to select and analyze a single production dataset.

**Usage**:
```bash
# Interactive mode (prompts for dataset selection)
python scripts/run_analysis.py
```

**What it does**:
- Lists all production datasets with window counts
- Prompts user to select dataset
- Prompts for model configuration (or uses defaults)
- Runs complete 10-agent ODD workflow
- Displays comprehensive results summary
- Saves analysis report + executive summary
- Runtime: 2-5 minutes per dataset

**Features**:
- ✅ Environment variables loaded from .env automatically
- 📊 Visual dataset selection menu
- 🤖 Configurable model selection (or use defaults)
- 📝 Comprehensive console output with summary
- 💾 Automatic result saving to `data/analysis_results/real_robot/`

**Example session**:
```
AVAILABLE PRODUCTION DATASETS
 1. collection_173442_chunk_01    ( 25 windows)
 2. collection_173442_chunk_02    ( 25 windows)
 ...
14. office_navigation              ( 13 windows)

Select dataset number: 14

Use default models? [Y/n]: y
✅ Model configuration set

⏳ This may take 2-5 minutes...
✅ ANALYSIS COMPLETE

📊 Summary:
   • Windows analyzed: 13
   • ODD compliance: IN_ODD
   • Violations: 0
   • Warnings: 2
```

---

### `batch_analysis.py` - **Batch Production Processor**

**Purpose**: Process all production datasets and generate aggregate meta-analysis.

**Usage**:
```bash
# Process all datasets
python scripts/batch_analysis.py

# Preview what would be processed (no actual analysis)
python scripts/batch_analysis.py --dry-run

# Skip datasets with existing recent results
python scripts/batch_analysis.py --skip-existing
```

**What it does**:
- Scans all datasets in `data/processed/production/`
- Processes each dataset with full ODD workflow
- Saves individual analysis reports
- Generates aggregate meta-analysis report
- Displays comprehensive summary statistics
- Runtime: ~1 hour for 14 datasets (283 windows total)

**Features**:
- 🔄 Batch processing of all production data
- 📊 Aggregate statistics across all datasets
- 🏆 Compliance summary (compliant/non-compliant/partial)
- ⚠️ Common violations and warnings analysis
- 💾 Individual + aggregate report generation
- ⏭️ Skip previously analyzed datasets (--skip-existing)
- 🔍 Dry-run mode for preview

**Output structure**:
```
data/analysis_results/real_robot/
├── collection_173442_chunk_01_analysis_20241123_143022.json
├── collection_173442_chunk_02_analysis_20241123_144530.json
├── ...
├── office_navigation_analysis_20241123_150142.json
└── aggregate_analysis_20241123_151200.json  # Meta-analysis
```

**Aggregate report includes**:
- Total datasets/windows analyzed
- Overall compliance distribution
- Most common violations (frequency-ranked)
- Most common warnings (frequency-ranked)
- Per-dataset summary breakdown

---

## 🚀 Legacy Workflow Scripts

### `odd_workflow.py` - Original Production Script

**Purpose**: Run complete ODD/COD analysis using the parameterized `odd_agents` module.

**Usage**:
```bash
# Set up API key in .env file (one time)
echo "GOOGLE_API_KEY=your-key-here" > .env

# Run analysis
python scripts/odd_workflow.py
```

**What it does**:
- Analyzes multi-modal sensor data (camera, LiDAR, IMU)
- Runs 10-agent sequential pipeline with parameterized workflow
- No global state - fully isolated execution
- Defaults to `gemini-2.0-flash-lite` for all agents
- Generates comprehensive ODD compliance report
- Outputs to: `data/processed/runs/{scenario}/odd_analysis_report.json`

**Source code**: Clean ~50 lines - imports from `odd_agents` module (single source of truth)

**Configuration**:
```python
# Edit odd_workflow.py to customize:
SCENARIO_PATH = DATA_DIR / "sim_run_test"  # Change scenario
nl_odd_description = "..."  # Custom ODD specification

# Use default models (flash-lite) or override:
result = await run_odd_workflow(
    scenario_path=SCENARIO_PATH,
    genai_client=client,
    api_key=api_key,
    model_perception="gemini-2.5-pro",  # Override specific agents
    # ... other model_* parameters
)
```

**Agents**: ODD Spec → Perception Loop/Summary → Motion Loop/Summary → Collision Loop/Summary → COD Classifier → ODD Compliance → Report

---

### `validate_data_structure.py` - Data Structure Validator

**Purpose**: Validate that directory names match file naming conventions (required for workflow).

**Usage**:
```bash
# Validate all processed data
python scripts/validate_data_structure.py

# Validate specific directory
python scripts/validate_data_structure.py data/processed/production

# Only check immediate children (not recursive)
python scripts/validate_data_structure.py data/processed/production --no-recursive
```

**What it checks**:
- ✅ Directory name matches index file name
- ✅ Directory name matches scenario name in filenames
- ✅ Index file exists
- ⚠️ Motion, camera, and BEV files are present

**Why needed**: The workflow tools use `directory.name` to construct expected filenames. If directory name doesn't match the `run_id` embedded in files, agents will fail to find windows.

**Example output**:
```
Found 14 scenarios to validate

✅ collection_20251122_173442_chunk_01
✅ collection_20251122_173813_chunk_01
❌ office_navigation
   ❌ NAMING MISMATCH: Directory 'office_navigation' but files use 'sim_run_new'

Validation FAILED - please fix naming mismatches above
```

---

## 📊 Data Processing Scripts

### `split_scenario.py` - Scenario Chunking for Large Datasets

**Purpose**: Split large scenarios into manageable chunks to avoid LLM context/output limits.

**Usage**:
```bash
# Split with default chunk size (25 windows)
python scripts/split_scenario.py data/processed/runs/collection_20251122_173442

# Custom chunk size
python scripts/split_scenario.py data/processed/runs/collection_20251122_173442 --chunk-size 30

# Custom output directory
python scripts/split_scenario.py data/processed/runs/collection_20251122_173442 --output data/processed/chunks
```

**What it does**:
- Splits scenarios exceeding ~20 windows into sequential chunks
- Creates new sub-scenario directories with renamed files
- Generates index files for each chunk
- Maintains manifest showing chunk-to-original mapping
- Preserves all metadata and file types

**Why needed**: Motion/Perception/Collision agents can fail on large datasets (>25 windows) due to LLM response truncation. Chunking ensures reliable processing.

**Output structure**:
```
data/processed/runs/
├── collection_20251122_173442/              # Original (62 windows)
├── collection_20251122_173442_chunk_01/     # Chunk 1 (windows 000-024)
├── collection_20251122_173442_chunk_02/     # Chunk 2 (windows 025-049)
├── collection_20251122_173442_chunk_03/     # Chunk 3 (windows 050-061)
└── collection_20251122_173442_chunks_manifest.json  # Mapping manifest
```

---

### `split_all_scenarios.py` - Batch Scenario Splitting

**Purpose**: Automatically split all large scenarios in one command.

**Usage**:
```bash
# Split all scenarios >15 windows into 25-window chunks
python scripts/split_all_scenarios.py --threshold 15 --chunk-size 25

# Dry run to see what would be split
python scripts/split_all_scenarios.py --dry-run

# Custom parameters
python scripts/split_all_scenarios.py --threshold 20 --chunk-size 30
```

**What it does**:
- Scans `data/processed/runs/` for scenarios exceeding threshold
- Automatically splits each into chunks
- Creates overall summary of splitting operation
- Skips already-chunked scenarios (with `_chunk_` in name)

**Example output**:
```
Found 7 scenarios to split:
  collection_20251122_173442    62 windows → 3 chunks
  collection_20251122_173813    60 windows → 3 chunks
  ...

✓ Split 7 scenarios
✓ Created 16 total chunks  
✓ Distributed 332 windows
```

---

### `extract_windows.py` - ROS2 Bag Window Extractor

**Purpose**: Extract time-windowed multi-modal snapshots from ROS2 bag files.

**Usage**:
```bash
# IMPORTANT: Output directory will be automatically created to match run-id
# This ensures workflow tools can find the files correctly

python scripts/extract_windows.py \
  --rosbag data/raw_rosbags/real/my_bag.db3 \
  --output data/processed/production \
  --run-id my_scenario \
  --window-length 2.0 \
  --stride 1.0

# Creates: data/processed/production/my_scenario/
#   with files: motion_my_scenario_w000.json, etc.

# For real robot data with date-stamped collections:
python scripts/extract_windows.py \
  --rosbag data/raw_rosbags/real/collection_20251122_173442.db3 \
  --output data/processed/production \
  --run-id collection_20251122_173442_chunk_01 \
  --window-length 2.0 \
  --stride 1.0

# Creates: data/processed/production/collection_20251122_173442_chunk_01/
#   with files: motion_collection_20251122_173442_chunk_01_w000.json, etc.
```

**CRITICAL NAMING REQUIREMENT**:
- ⚠️ The output directory name MUST match the run-id
- Files are created as `motion_{run_id}_w000.json`
- Workflow tools use directory name to find files
- Script will automatically append run-id to output path if needed

**Outputs per window**:
- `motion_<scenario>_w<NNN>.json` - Velocity, IMU, odometry time series
- `cam_<scenario>_w<NNN>.png` - RGB camera frame
- `bev_occupancy_<scenario>_w<NNN>.png` - LiDAR BEV (occupancy)
- `bev_height_<scenario>_w<NNN>.png` - LiDAR BEV (height map)
- `bev_density_<scenario>_w<NNN>.png` - LiDAR BEV (point density)
- `bev_roughness_<scenario>_w<NNN>.png` - LiDAR BEV (surface roughness)
- `index_<scenario>.csv` - Window metadata

**Dependencies**: ROS2 Humble, sensor_msgs, nav_msgs

---

### `render_bev.py` - LiDAR BEV Renderer

**Multi-channel BEV rendering (occupancy, height, density, roughness)
**Features**:
- Occupancy grid generation
- Height mapping
- Configurable resolution (default: 5cm/pixel)
- Customizable range (default: ±10m)

**Usage**: Called internally by `extract_windows.py` or standalone for debugging.

---

### `utils_ros.py` - ROS2 Utilities

**Purpose**: Helper functions for ROS2 message parsing and time synchronization.

**Key functions**:
- Message deserialization (Image, PointCloud2, Odometry, IMU)
- Timestamp alignment across topics
- Topic filtering and validation

---

## 🧪 Manual Testing & Development Scripts

### `generate_demo_results.py` - Manual Workflow Test

**Purpose**: Run complete ODD workflow on `sim_run_new` dataset and generate demonstration results.

**Usage**:
```bash
python scripts/generate_demo_results.py
```

**What it does**:
- Runs full 10-agent ODD analysis pipeline
- Uses sim_run_new dataset (13 windows)
- Generates comprehensive analysis report
- Saves executive summary
- Runtime: ~3-5 minutes

**Use cases**:
- Manual verification of workflow changes
- Generate demo outputs for documentation
- Test model configurations
- Validate end-to-end pipeline

**Note**: This is for MANUAL TESTING. For automated evaluation, see `tests/evaluation/README.md`.

---

### `generate_demo_data.py` - Synthetic Data Generator

**Purpose**: Create synthetic window data for testing without ROS2 bags.

**Usage**:
```bash
python scripts/generate_demo_data.py
```

**Generates**:
- Synthetic time windows with realistic motion profiles
- Synthetic camera images (640x480)
- Synthetic LiDAR BEV images (all 4 channels)
- Complete index CSV
- Intentional ODD violations for demo

**Use cases**:
- Test workflow without real robot data
- Validate agent pipeline changes
- Demonstrate ODD violations
- CI/CD testing

---

## 📁 Directory Structure After Processing

```
data/processed/
├── production/                          # Production datasets
│   ├── collection_20251122_173442_chunk_01/
│   │   ├── index_collection_20251122_173442_chunk_01.csv
│   │   ├── motion_collection_20251122_173442_chunk_01_w000.json
│   │   ├── cam_collection_20251122_173442_chunk_01_w000.png
│   │   ├── bev_occupancy_collection_20251122_173442_chunk_01_w000.png
│   │   └── ...
│   └── collection_20251122_173813_chunk_01/
│       └── ...
├── test_data/                           # Curated test sets
│   ├── real/                            # Real robot test sets
│   │   ├── real_01_173442/
│   │   │   ├── index_real_01_173442.csv
│   │   │   ├── motion_real_01_173442_w000.json
│   │   │   └── ...
│   │   └── real_02_173813/
│   │       └── ...
│   └── sim/                             # Simulation test sets
│       └── sim_run_test/
│           ├── index_sim_run_test.csv
│           ├── motion_sim_run_test_w000.json
│           └── ...
└── runs/                                # Legacy/development runs (deprecated)
    └── ...

CRITICAL: Directory names MUST match the scenario name embedded in filenames!
Example: Directory "real_01_173442" contains files "motion_real_01_173442_w000.json"
```

---

## 🔧 Development Notes

### Adding New Sensors
rchitecture

The current architecture uses a **shared module pattern**:

- **`odd_agents/`** - Source of truth for all agent definitions and workflow
- **`scripts/odd_workflow.py`** - Production entry point (imports from module)
- **`notebooks/odd_analysis_demo.ipynb`** - Interactive analysis (imports from module)
- **`tests/test_*.py`** - Individual agent tests (imports from module)

**No code duplication** - everything imports from `odd_agents` module.

### Adding New Sensors

To extract additional sensor data:

1. Add topic name to `extract_windows.py` configuration
2. Add deserialization logic in `utils_ros.py`
---

## � Archived Scripts

Superseded implementations moved to [`../.archive/scripts/`](../.archive/scripts/):

- `odd_workflow_full.py` - Original monolithic workflow (857 lines, pre-parameterization)
- `odd_workflow_full.py.backup` - Golden reference backup
- `multi_agent_image_adk_workflow.py` - Original loop+summary pattern reference

**Note**: Archived for historical reference. Use current `odd_workflow.py` and the `odd_agents` module instead.

---

## 🚀 Quick Reference

| Task | Script | Key Options |
|------|--------|-------------|
| Run ODD analysis | `odd_workflow.py` | None (uses config in script) |
| Extract from ROS bag | `extract_windows.py` | `--rosbag`, `--output`, `--window-length` |
| Generate test data | `generate_demo_data.py` | None (uses defaults) |
| Debug BEV rendering | `render_bev.py` | Standalone usage with point cloud file |

---

## 📚 Related Documentation

- **Module architecture**: `../docs/MODEL_SELECTION_GUIDE.md`
- **Module API**: `../odd_agents/README.md`
- **Agent implementations**: `../odd_agents/agents/`
- **Workflow orchestration**: `../odd_agents/workflow.py`
- **Interactive analysis**: `../notebooks/odd_analysis_demo.ipynb`
- **Getting started**: `../docs/guides/GETTING_STARTED.md`

---

## 🐛 Troubleshooting

**Issue**: "ROS2 topics not found"
- **Solution**: Check topic names with `ros2 bag info your_bag.db3`
- Update topic names in `extract_windows.py` if needed

**Issue**: "Window extraction incomplete"
- **Solution**: Verify bag duration > window_length
- Check for missing messages in problematic topics

**Issue**: "BEV images blank"
- **Solution**: Verify LiDAR data exists in bag
- Check point cloud coordinate frames
- Adjust BEV range parameters

**Issue**: "Workflow fails"
- **Solution**: Check .env file: `cat .env` (should have GOOGLE_API_KEY)
- Or set environment variable: `export GOOGLE_API_KEY="your-key"`
- Verify scenario data exists: `ls data/processed/runs/sim_run_test/`
- Check for errors in agent outputs (review terminal output)
