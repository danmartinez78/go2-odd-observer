# Scripts Directory

Executable scripts for the Go2 ODD Observer project.

---

## 🎯 Core Production Scripts

### `run_odd_analysis.py` - **Manual Interactive Runner**

**Purpose**: Interactive single-scenario ODD analysis with scenario selection.

**Usage**:
```bash
python scripts/run_odd_analysis.py
```

**What it does**:
- Scans data/production/ and data/test/ for available scenarios
- Interactive scenario selection with window counts
- Runs complete ODD workflow
- Displays executive summary and compliance status
- Saves results to `data/archive/analysis_results/manual/<timestamp>/<scenario>/`
  - `full_result.json` - Complete analysis data
  - `executive_summary.json` - Key findings and recommendations

**Model Configuration** (edit at top of script):
```python
MODEL_PERCEPTION = "gemini-2.5-pro"       # Camera + LiDAR analysis
MODEL_MOTION = "gemini-2.5-flash"         # IMU motion detection
MODEL_COLLISION = "gemini-2.5-pro"        # Collision risk assessment
MODEL_ODD_SPEC = "gemini-2.5-pro"         # ODD specification parsing
MODEL_COD = "gemini-2.5-flash"            # COD classification
MODEL_REPORT = "gemini-2.5-flash"         # Report generation
```

**Output Example**:
```
SCENARIO METADATA
  • Windows analyzed: 2
  • Data source: simulation (confidence: 0.98)
  • Environment: indoor_office

ANALYSIS METADATA
  • Pipeline version: 2.0.0
  • Analysis duration: 214.3s
  • Agents executed: 10
  • Total tokens: 62,860
  • Estimated cost: $1.26

ODD COMPLIANCE
  • Overall: ODD_BOUNDARY
  • Violations: 0
  • Warnings: 1

⚠️  WARNINGS:
    • collision_risk (0.3) is at the ODD boundary
```

**New in v2.0.0 - Metadata Tracking:**

All analysis results now include comprehensive metadata for reproducibility:

**`analysis_metadata`** (lightweight summary):
```json
{
  "pipeline_version": "2.0.0",
  "analysis_timestamp": "2025-11-25T18:13:42",
  "analysis_duration_seconds": 214.3,
  "total_agents_executed": 10,
  "total_tokens_used": 62860,
  "estimated_cost_usd": 1.26
}
```

**`pipeline_metadata`** (detailed execution tracking):
```json
{
  "pipeline_version": "2.0.0",
  "pipeline_start_time": "2025-11-25T18:13:42",
  "pipeline_duration_seconds": 214.3,
  "odd_spec_hash": "a3f8d9e2",
  "scenario_path": "/path/to/scenario",
  "agent_executions": {
    "OddSpecAgent": {
      "version": "2.0.0",
      "model_declared": "gemini-2.0-flash-lite",
      "model_actual": "gemini-2.0-flash-lite",
      "prompt_hash": "a3f8d9e2b1c4",
      "execution_order": 1,
      "timestamp": "2025-11-25T18:13:45",
      "token_usage": {
        "prompt_tokens": 2100,
        "completion_tokens": 2100,
        "total_tokens": 4200
      }
    }
  },
  "workflow_summary": {
    "total_agents": 10,
    "total_tokens": 62860,
    "total_duration_seconds": 214.3,
    "agents_executed": ["OddSpecAgent", "PerceptionLoopAgent", ...]
  }
}
```

**Benefits:**
- **Reproducibility**: Exact prompt versions and model configurations tracked
- **Debugging**: Per-agent execution details with timing and token usage
- **Cost tracking**: Estimated costs based on token usage
- **Drift detection**: Prompt hash changes trigger version updates
- **Audit trail**: Complete record of analysis pipeline execution

**HTML Report Enhancements:**

Reports now include a metadata footer with:
- Pipeline version and analysis timestamp
- Collapsible accordion showing per-agent details:
  - Agent name, version, model used
  - Prompt hash (for drift detection)
  - Expandable table for all 10 agents

**Accessing Metadata:**

```python
# Load analysis result
with open('full_result.json') as f:
    result = json.load(f)

# Lightweight metadata (always present)
meta = result['analysis_metadata']
print(f"Analysis took {meta['analysis_duration_seconds']}s")
print(f"Used {meta['total_tokens_used']} tokens")
print(f"Cost: ${meta['estimated_cost_usd']}")

# Detailed pipeline metadata
pipeline = result['pipeline_metadata']
for agent, details in pipeline['agent_executions'].items():
    print(f"{agent}: {details['token_usage']['total_tokens']} tokens")
```

---

### `run_odd_batch_analysis.py` - **Automated Batch Processor**

**Purpose**: Process all production scenarios and generate aggregate report.

**Usage**:
```bash
python scripts/run_odd_batch_analysis.py
```

**What it does**:
- Auto-discovers all scenarios in `data/production/`
- Processes each sequentially with progress bars
- Exits on first error (saves API costs)
- Saves individual results to `data/archive/analysis_results/automated/<timestamp>/<scenario>/`
- Generates aggregate report combining all scenarios

**Features**:
- 📊 Progress tracking with tqdm
- 🛑 Fail-fast on errors
- 📈 Aggregate statistics across all scenarios
- 💾 Individual + combined reports

**Output Structure**:
```
data/archive/analysis_results/automated/20251123_150000/
├── sim_1_0/
│   ├── full_result.json
│   └── executive_summary.json
├── real_01_173442/
│   ├── full_result.json
│   └── executive_summary.json
├── ...
└── aggregate_report.json              # Combined analysis
```

**Aggregate Report Includes**:
- Batch metadata (timestamp, scenario counts)
- Compliance distribution (IN_ODD, BOUNDARY, VIOLATION)
- Violation type frequencies
- Environment distribution
- Data source distribution
- Per-scenario summaries

---

## 📊 Data Processing Scripts

### `create_test_sets.py` - **Test Set Generator**

**Purpose**: Extract 2-window subsets from production data to create small test datasets.

**Usage**:
```bash
# Interactive mode (recommended)
python scripts/create_test_sets.py

# Command-line mode
python scripts/create_test_sets.py --source data/production/sim_1_0 --windows 10,11 --output data/test/sim_test_w010_w011
python scripts/create_test_sets.py --source data/production/sim_1_0 --windows 30-31 --output data/test/sim_test_w030_w031
```

**What it does**:
- Extracts specified windows from production scenarios
- Copies all necessary files (motion JSON, camera, BEV channels)
- Creates proper CSV index for the test set
- Useful for creating small, focused test datasets

**Interactive Mode**:
1. Lists available production scenarios
2. Select source scenario
3. Choose window IDs (e.g., "10,11" or "10-31")
4. Specify output directory
5. Confirms before overwriting existing test sets

**Output Structure**:
```
data/test/sim_test_w010_w011/
├── index_sim_test_w010_w011.csv
├── motion_sim_1_0_w010.json
├── motion_sim_1_0_w011.json
├── cam_sim_1_0_w010.png
├── cam_sim_1_0_w011.png
├── bev_occupancy_sim_1_0_w010.png
├── bev_occupancy_sim_1_0_w011.png
├── bev_height_sim_1_0_w010.png
├── bev_height_sim_1_0_w011.png
├── bev_roughness_sim_1_0_w010.png
└── bev_roughness_sim_1_0_w011.png
```

---

### `extract_windows.py` - **ROS2 Bag Window Extractor**

**Purpose**: Extract time-windowed multi-modal snapshots from ROS2 bag files.

**Usage**:
```bash
python scripts/extract_windows.py \
  --rosbag data/raw_rosbags/real/my_collection.db3 \
  --output data/processed/production \
  --run-id my_scenario \
  --window-length 2.0 \
  --stride 1.0
```

**⚠️ CRITICAL NAMING REQUIREMENT**:
- Output directory name MUST match run-id
- Files are created as `motion_{run_id}_w000.json`
- Workflow tools use directory name to find files
- Script automatically creates `output/run_id/` directory

**Outputs per window**:
- `motion_<scenario>_w<NNN>.json` - Velocity, IMU, odometry
- `cam_<scenario>_w<NNN>.png` - RGB camera frame
- `bev_occupancy_<scenario>_w<NNN>.png` - LiDAR BEV (occupancy)
- `bev_height_<scenario>_w<NNN>.png` - LiDAR BEV (height)
- `bev_density_<scenario>_w<NNN>.png` - LiDAR BEV (density)
- `bev_roughness_<scenario>_w<NNN>.png` - LiDAR BEV (roughness)
- `index_<scenario>.csv` - Window metadata

**Dependencies**: ROS2 Humble, sensor_msgs, nav_msgs

---

### `validate_data_structure.py` - **Data Structure Validator**

**Purpose**: Validate directory/file naming consistency (required for workflow).

**Usage**:
```bash
# Validate all processed data
python scripts/validate_data_structure.py

# Validate specific directory
python scripts/validate_data_structure.py data/processed/production
```

**What it checks**:
- ✅ Directory name matches index file name
- ✅ Directory name matches scenario name in filenames
- ✅ Index file exists
- ⚠️ Motion, camera, and BEV files present

**Why needed**: Workflow tools use `directory.name` to construct filenames. Mismatches cause silent failures.

**Example output**:
```
✅ real_01_173442
✅ sim_run_test
❌ office_navigation
   ❌ Directory 'office_navigation' but files use 'sim_run_new'
```

---

### `create_real_test_sets.py` - **Test Set Creator**

**Purpose**: Create curated test sets from production data for validation.

**Usage**:
```bash
python scripts/create_real_test_sets.py
```

**What it does**:
- Scans production data for diverse scenarios
- Creates small test sets (2 windows each)
- Copies to `data/processed/test_data/real/`
- Renames files to match test set directory names
- Generates summary JSON with metadata

---

### `render_bev.py` - **LiDAR BEV Renderer**

**Purpose**: Generate multi-channel bird's-eye view images from LiDAR point clouds.

**Features**:
- Occupancy grid generation
- Height mapping
- Point density visualization
- Surface roughness estimation
- Configurable resolution (default: 5cm/pixel)
- Customizable range (default: ±10m)

**Usage**: Called internally by `extract_windows.py` or standalone for debugging.

---

### `utils_ros.py` - **ROS2 Utilities**

**Purpose**: Helper functions for ROS2 message parsing and time synchronization.

**Key functions**:
- Message deserialization (Image, PointCloud2, Odometry, IMU)
- Timestamp alignment across topics
- Topic filtering and validation

---

## 📁 Directory Structure

```
data/
├── production/                        # Production datasets
│   └── sim_1_0/                      # 62 windows
│       ├── index_sim_1_0.csv
│       ├── motion_sim_1_0_w000.json
│       ├── cam_sim_1_0_w000.png
│       └── bev_*_sim_1_0_w000.png
│
├── test/                              # Test datasets
│   ├── sim_test_w010_w011/           # 2 windows
│   ├── sim_test_w030_w031/           # 2 windows
│   └── sim_test_w050_w051/           # 2 windows
│
├── archive/
│   └── analysis_results/
│       ├── manual/                    # From run_odd_analysis.py
│       │   └── 20251125_150000/
│       │       └── sim_test_w010_w011/
│       │           ├── full_result.json
│       │           └── executive_summary.json
│       └── automated/                 # From run_odd_batch_analysis.py
│           └── 20251125_150000/
│               ├── sim_1_0/
│               └── aggregate_report.json
│
└── raw_rosbags/
    ├── real/                          # Real robot bags
    └── sim/                           # Simulation bags
```

---

## 🚀 Quick Reference

| Task | Script | Notes |
|------|--------|-------|
| Analyze single scenario | `run_odd_analysis.py` | Interactive, test + production data |
| Batch process all data | `run_odd_batch_analysis.py` | Automated, production only |
| Extract from ROS bag | `extract_windows.py` | Creates time-windowed snapshots |
| Validate data naming | `validate_data_structure.py` | Prevents workflow failures |
| Create test sets | `create_real_test_sets.py` | Curate validation data |

---

## 📚 Related Documentation

- **Workflow module**: `../odd_agents/README.md`
- **Model selection**: `../docs/MODEL_SELECTION_GUIDE.md`
- **Getting started**: `../docs/guides/GETTING_STARTED.md`
- **Data naming**: `../docs/DATA_NAMING_CONVENTION.md`
- **Interactive demo**: `../notebooks/odd_analysis_demo.ipynb`

---

## 📦 Archived Scripts

Superseded scripts moved to [`.archive/scripts/`](../.archive/scripts/):
- `odd_workflow.py` - Old single-run script (replaced by `run_odd_analysis.py`)
- `analyze_real_data.py` - Old batch script (replaced by `run_odd_batch_analysis.py`)
- `generate_demo_results.py` - Old demo script (replaced by new runners)
- `generate_demo_data.py` - Synthetic data generator (replaced by real test sets)

---

## 🐛 Troubleshooting

**Issue**: "No scenarios found"
- **Solution**: Run `extract_windows.py` to process ROS bags first

**Issue**: "Directory/file naming mismatch"
- **Solution**: Run `validate_data_structure.py` to identify issues
- See `../docs/DATA_NAMING_CONVENTION.md` for naming rules

**Issue**: "Workflow fails to find windows"
- **Solution**: Ensure directory name matches scenario name in filenames
- Script automatically creates correct structure now

**Issue**: "GOOGLE_API_KEY not set"
- **Solution**: Create `.env` file with `GOOGLE_API_KEY=your-key`
- Or: `export GOOGLE_API_KEY="your-key"`

**Issue**: "Rate limit errors"
- **Solution**: Switch to `gemini-2.5-flash` (more quota)
- Edit model configuration at top of script
