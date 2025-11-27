# Scripts Directory

Executable scripts for the Go2 ODD Observer project.

**Phase 1.4.5 (Nov 27, 2025):** Artifact-based handoff, categorical micro-agent, data source detection.

---

## 🎯 Core Production Scripts

### `run_odd_analysis.py` - **Interactive Analyzer**

**Purpose**: Interactive single-scenario ODD analysis with scenario selection.

**Usage**:
```bash
# Interactive mode
python scripts/run_odd_analysis.py

# Specify scenario directly
python scripts/run_odd_analysis.py --scenario data/test/sim/sim_test_w010_w011
```

**What it does**:
- Scans data/production/ and data/test/ for available scenarios
- Interactive scenario selection with window counts
- Runs complete 6-agent ODD workflow
- Displays executive summary and compliance status
- Saves results to `data/archive/analysis_results/manual/<timestamp>/<scenario>/`

**Model Configuration** (Phase 1.4.5):
```python
MODEL_PERCEPTION = "gemini-2.5-flash"   # Multimodal + data source detection
MODEL_MOTION = "gemini-2.5-flash"       # IMU motion analysis
MODEL_COLLISION = "gemini-2.5-flash"    # Collision detection
MODEL_ODD_SPEC = "gemini-2.5-flash"     # ODD specification parsing
MODEL_EVALUATOR = "gemini-2.5-pro"      # COD + compliance (complex reasoning)
MODEL_REPORT = "gemini-2.5-flash"       # Report generation
```

**Output Example**:
```
╔════════════════════════════════════════════════════════════════╗
║                      ODD ANALYSIS SUMMARY                       ║
╚════════════════════════════════════════════════════════════════╝

┌─ COMPLIANCE ─────────────────────────────────────────────────────┐
│ Verdict: IN_ODD                                                  │
│ Confidence: 0.85                                                 │
│ Region Distance: 0.0                                             │
│ Stability: stable                                                │
└──────────────────────────────────────────────────────────────────┘

┌─ SCENARIO METADATA ──────────────────────────────────────────────┐
│ Data Source: simulated                                           │
│ Windows: 2                                                       │
└──────────────────────────────────────────────────────────────────┘

┌─ ANALYSIS METADATA ──────────────────────────────────────────────┐
│ Duration: 148.3 seconds                                          │
│ Cost: $0.0155                                                    │
└──────────────────────────────────────────────────────────────────┘
```

---

### `chunk_large_scenario.py` - **Scenario Chunker** (NEW)

**Purpose**: Split large scenarios into manageable chunks for processing.

**Usage**:
```bash
# Default 10-window chunks
python scripts/chunk_large_scenario.py data/production/sim_1_0 --chunk-size 10

# Custom chunk size
python scripts/chunk_large_scenario.py data/production/sim_1_0 --chunk-size 5
```

**What it does**:
- Splits large scenarios (e.g., 62 windows) into smaller chunks
- Creates standalone scenarios with their own index CSVs
- Copies all necessary files (motion, camera, BEV)
- Enables processing large datasets in batches

**Output Example** (62 windows → 7 chunks):
```
sim_1_0_chunk_000_009/  (10 windows)
sim_1_0_chunk_010_019/  (10 windows)
sim_1_0_chunk_020_029/  (10 windows)
sim_1_0_chunk_030_039/  (10 windows)
sim_1_0_chunk_040_049/  (10 windows)
sim_1_0_chunk_050_059/  (10 windows)
sim_1_0_chunk_060_061/  (2 windows)
```

---

### `run_odd_batch_analysis.py` - **Batch Processor**

**Purpose**: Process all production scenarios automatically.

**Usage**:
```bash
python scripts/run_odd_batch_analysis.py
```

**What it does**:
- Auto-discovers all scenarios in `data/production/`
- Processes each sequentially
- Generates aggregate report combining all scenarios
- Saves to `data/archive/analysis_results/automated/<timestamp>/`

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

---

## 🧪 Development & Exploration Scripts

These scripts were created during development to explore ADK patterns and validate new features.

### `test_categorical_agent.py` - **Categorical Micro-Agent Tests**

**Purpose**: Validate the categorical micro-agent for semantic ODD matching.

**Usage**:
```bash
python scripts/test_categorical_agent.py
```

**What it tests**:
- Semantic equivalence detection (e.g., "indoor_commercial" ≈ "office")
- Anti-cheat generalization (uses novel examples not in training prompt)
- Edge cases and false positive prevention

**Key Design Principle**: Tests verify GENERALIZATION, not memorization. Every pattern in the prompt has a corresponding anti-cheat test with different examples.

---

### `test_adk_artifacts.py` - **Artifact Pattern Example**

**Purpose**: Toy example demonstrating ADK artifact-based inter-agent communication.

**Usage**:
```bash
python scripts/test_adk_artifacts.py
```

**What it demonstrates**:
- `InMemoryArtifactService` usage
- Producer agent saving artifacts
- Consumer agent loading artifacts
- Reliable data handoff pattern

**Why created**: Explored artifact pattern before implementing in production pipeline (Phase 1.4.5).

---

### `test_adk_blackboard.py` - **Blackboard State Example**

**Purpose**: Toy example demonstrating ADK blackboard state access from tools.

**Usage**:
```bash
python scripts/test_adk_blackboard.py
```

**What it demonstrates**:
- `tool_context.state` access in tools
- `output_key` pattern for agent state
- Producer/consumer agent pattern

**Why created**: Explored blackboard pattern before deciding artifact pattern was more reliable.
