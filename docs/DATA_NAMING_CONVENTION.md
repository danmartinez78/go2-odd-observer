# Data Naming Convention

## Critical Requirement

**Directory names MUST match the scenario name embedded in filenames.**

This is required because the workflow tools use `directory.name` to construct expected filenames:

```python
# In odd_agents/tools/perception.py and motion.py
scenario_name = scenario_path.name
motion_file = f"motion_{scenario_name}_w{window_id}.json"
```

If the directory name doesn't match the filename prefix, the workflow will **fail silently** (agents return empty results).

---

## Correct Structure

### Production Data

```
data/processed/production/
├── collection_20251122_173442_chunk_01/
│   ├── index_collection_20251122_173442_chunk_01.csv
│   ├── motion_collection_20251122_173442_chunk_01_w000.json
│   ├── cam_collection_20251122_173442_chunk_01_w000.png
│   └── bev_occupancy_collection_20251122_173442_chunk_01_w000.png
└── sim_run_new/
    ├── index_sim_run_new.csv
    ├── motion_sim_run_new_w000.json
    └── ...
```

✅ **Correct**: Directory `collection_20251122_173442_chunk_01` matches files `motion_collection_20251122_173442_chunk_01_w000.json`

❌ **Wrong**: Directory `collection_173442` with files `motion_collection_20251122_173442_chunk_01_w000.json`

### Test Data

```
data/processed/test_data/
├── real/
│   ├── real_01_173442/
│   │   ├── index_real_01_173442.csv
│   │   ├── motion_real_01_173442_w000.json
│   │   └── ...
│   └── real_02_173813/
│       └── ...
└── sim/
    └── sim_run_test/
        ├── index_sim_run_test.csv
        ├── motion_sim_run_test_w000.json
        └── ...
```

✅ **Correct**: Directory `real_01_173442` matches files `motion_real_01_173442_w000.json`

❌ **Wrong**: Directory `sample_173442_01` with files `motion_real_01_173442_w000.json`

---

## Naming Patterns

### Real Robot Collections (Production)

**Format**: `collection_YYYYMMDD_HHMMSS_chunk_NN`

- Date: `20251122` (Nov 22, 2025)
- Time: `173442` (17:34:42 = 5:34:42 PM)
- Chunk: `01`, `02`, `03` (for split scenarios)

**Examples**:
- `collection_20251122_173442_chunk_01` (25 windows)
- `collection_20251122_173813_chunk_02` (25 windows)

### Real Robot Test Sets

**Format**: `real_NN_HHMMSS`

- Number: `01`, `02`, ... `06` (test set number)
- Time: `173442` (from original collection)

**Examples**:
- `real_01_173442` (2 windows from collection_20251122_173442)
- `real_02_173813` (2 windows from collection_20251122_173813)

### Simulation Data

**Format**: `sim_{description}`

**Examples**:
- `sim_run_test` (test set)
- `sim_run_new` (office navigation scenario)

---

## Data Preparation Scripts

### `extract_windows.py` - Enforced Naming

The script **automatically enforces** correct naming:

```bash
# Correct usage - script appends run_id to output path
python scripts/extract_windows.py \
  --rosbag data/raw_rosbags/real/mybag.db3 \
  --output data/processed/production \
  --run-id collection_20251122_173442_chunk_01

# Creates: data/processed/production/collection_20251122_173442_chunk_01/
# With files: motion_collection_20251122_173442_chunk_01_w000.json
```

**Behavior**:
- If `--output` doesn't end with `--run-id`, script appends it automatically
- Script validates directory name matches run_id before proceeding
- Fails early with clear error if mismatch detected

### `create_real_test_sets.py` - Maintains Convention

Creates test sets with matching names:

```bash
python scripts/create_real_test_sets.py
```

**Behavior**:
- Extracts windows from production collections
- Creates directories: `real_01_173442`, `real_02_173813`, etc.
- Renames files to match: `motion_real_01_173442_w000.json`
- All names stay consistent

---

## Validation

### `validate_data_structure.py` - Check Your Data

Validate all data before running workflows:

```bash
# Validate everything
python scripts/validate_data_structure.py

# Validate specific directory
python scripts/validate_data_structure.py data/processed/production

# Example output
Found 14 scenarios to validate

✅ collection_20251122_173442_chunk_01
✅ sim_run_new
❌ office_navigation
   ❌ NAMING MISMATCH: Directory 'office_navigation' but files use 'sim_run_new'
```

**Always validate** before:
- Running ODD workflows
- Committing new data
- Sharing datasets

---

## Historical Context

### What Went Wrong (Nov 2024)

During data reorganization, directories were renamed but filenames weren't updated:

```
❌ BROKEN:
data/processed/production/
└── collection_173442_chunk_01/              # Missing date!
    ├── motion_collection_20251122_173442_chunk_01_w000.json
    └── ...
```

**Result**: Workflow tools looked for `motion_collection_173442_chunk_01_w000.json` but files were `motion_collection_20251122_173442_chunk_01_w000.json`. Agents failed silently with empty results.

### The Fix (Nov 2024)

1. **Renamed directories** to match files (20 directories)
2. **Updated scripts** to enforce naming
3. **Created validation tool** to prevent future issues

---

## Quick Reference

| Data Type | Directory Pattern | File Pattern | Location |
|-----------|------------------|--------------|----------|
| Production Real | `collection_YYYYMMDD_HHMMSS_chunk_NN` | `motion_collection_YYYYMMDD_HHMMSS_chunk_NN_w000.json` | `production/` |
| Production Sim | `sim_{name}` | `motion_sim_{name}_w000.json` | `production/` |
| Test Real | `real_NN_HHMMSS` | `motion_real_NN_HHMMSS_w000.json` | `test_data/real/` |
| Test Sim | `sim_{name}` | `motion_sim_{name}_w000.json` | `test_data/sim/` |

---

## Best Practices

1. **Always use `--run-id`** when running `extract_windows.py`
2. **Run validation** after creating new datasets
3. **Never manually rename** directories without updating filenames
4. **Use underscore notation** (not hyphens) in names
5. **Include dates** in production data names
6. **Keep names concise** but descriptive

---

## Troubleshooting

### Problem: Agents return empty windows

**Symptom**: 
```
✅ Perception found 25 windows
❌ Motion analyzed: []
❌ Collision analyzed: []
```

**Diagnosis**:
```bash
python scripts/validate_data_structure.py data/processed/production/your_scenario
```

**Fix**:
1. Check validation output for naming mismatches
2. Rename directory to match files OR regenerate data with correct `--run-id`

### Problem: "No such file or directory"

**Symptom**: Workflow fails with file not found errors

**Diagnosis**: Directory name doesn't match expected scenario name

**Fix**: Ensure directory name matches the scenario name embedded in filenames

---

## Migration Guide

### Fixing Existing Data

If you have existing data with naming mismatches:

```bash
# 1. Validate to find issues
python scripts/validate_data_structure.py data/processed/production

# 2. Option A: Rename directories (if safe)
mv data/processed/production/old_name data/processed/production/correct_name

# 3. Option B: Regenerate data with correct --run-id
python scripts/extract_windows.py --run-id correct_name ...

# 4. Re-validate
python scripts/validate_data_structure.py data/processed/production
```

### New Data

For all new data extraction:

```bash
# Specify run-id to match desired directory name
python scripts/extract_windows.py \
  --rosbag path/to/bag.db3 \
  --output data/processed/production \
  --run-id collection_YYYYMMDD_HHMMSS_chunk_01
  
# Script will create: data/processed/production/collection_YYYYMMDD_HHMMSS_chunk_01/
# With files: motion_collection_YYYYMMDD_HHMMSS_chunk_01_w000.json
```

---

**Last Updated**: November 23, 2024  
**Status**: All 21 scenarios validated ✅
