# Notebooks

Interactive Jupyter notebooks for ODD/COD analysis and visualization.

## Available Notebooks

### `odd_cod_workflow.ipynb` - **Main Workflow** ⭐

Complete 10-agent ODD/COD analysis workflow with visualizations.

**What it does:**
- Runs the full 10-agent sequential pipeline
- Analyzes multi-modal sensor data (camera + LiDAR + IMU)
- Compares Current Operating Domain (COD) vs Operational Design Domain (ODD)
- Detects ODD violations and safety boundaries
- Generates comprehensive compliance reports

**Key Features:**
- ✅ ODD-first architecture (define constraints before analyzing sensors)
- ✅ IMU-based motion detection (robust to odometry failures)
- ✅ Sim vs real classification
- ✅ Interactive visualizations (collision risk timeline, compliance status)
- ✅ Export to JSON and text formats

**Notebook Structure (10 sections):**
1. **Title & Overview** - ODD/COD concepts and 10-agent pipeline
2. **Setup** - Import libraries, configure API
3. **ODD Definition** - Natural language specification
4. **Scenario Selection** - Choose dataset
5. **Run Workflow** - Execute 10-agent pipeline
6. **Executive Summary** - High-level findings
7. **ODD Compliance** - Violation analysis
8. **Collision Risk Timeline** - Visualization
9. **Motion Detection** - IMU statistics
10. **Export & Next Steps** - Save results, customization guide

**Usage:**
```bash
# 1. Set API key
export GOOGLE_API_KEY="your-api-key-here"

# 2. Launch Jupyter
jupyter notebook

# 3. Open odd_cod_workflow.ipynb
# 4. Update SCENARIO_NAME (cell 6)
# 5. Run all cells
```

**Typical runtime:** 2-3 minutes for 13-window scenario

---

### Archived Notebooks

- `odd_cod_workflow_ARCHIVED.ipynb` - Previous 9-agent version (archived Nov 21, 2025)
- `odd_workflow_interactive.ipynb` - Legacy interactive workflow (needs updates)

---

## Quick Start

```bash
# 1. Ensure API key is configured
export GOOGLE_API_KEY="your-api-key-here"

# 2. Launch Jupyter
jupyter notebook

# 3. Open odd_cod_workflow.ipynb
# 4. Run all cells (Cell → Run All)
```

## Prerequisites

- Python 3.10+
- Google Gemini API key (free at https://aistudio.google.com/app/apikey)
- Preprocessed scenario data in `../data/processed/runs/`
- Required packages: `pandas`, `matplotlib`, `seaborn`, `google-genai`

## Customization Examples

### Outdoor Delivery Robot ODD

```python
nl_odd_description = """
Outdoor delivery robot designed for sidewalk navigation.

OPERATIONAL CONSTRAINTS:
1. Environment: outdoor_sidewalk, outdoor_urban
2. Weather: clear, light_rain (no heavy rain or snow)
3. Terrain: paved_sidewalk, asphalt
4. Speed: 0.0 to 2.0 m/s
5. GPS Quality: HDOP < 2.0
6. Slope: -5° to +5°
"""
```

### Aerial Drone ODD

```python
nl_odd_description = """
Quadcopter drone for outdoor inspection.

OPERATIONAL CONSTRAINTS:
1. Environment: outdoor, open_airspace
2. Altitude: 10 to 100 meters AGL
3. Wind Speed: < 10 m/s
4. GPS Quality: > 8 satellites, HDOP < 1.5
5. Battery: > 30%
6. Visibility: > 1 km
"""
```

## Output Files

After running the notebook:

```
data/processed/runs/<scenario>/
├── odd_analysis_report.json          # Full workflow output (from script)
├── odd_analysis_report_notebook.json # Notebook-generated output
└── odd_analysis_summary.txt          # Human-readable summary
```

## Troubleshooting

**Issue:** `GOOGLE_API_KEY not found`
- **Solution:** `export GOOGLE_API_KEY='your-key'` or create `.env` file

**Issue:** `Scenario not found`
- **Solution:** Run `extract_windows.py` first to preprocess ROS2 bags

**Issue:** `Module 'odd_workflow_full' not found`
- **Solution:** Run from `notebooks/` directory (auto-adds `../scripts` to path)

**Issue:** Rate limit exceeded
- **Solution:** Wait 60s and retry, or use gemini-2.0-flash-lite

## Learn More

- **Getting Started**: `../docs/guides/GETTING_STARTED.md`
- **Workflow Updates**: `../IMU_MOTION_DETECTION_UPDATE.md`
- **Main README**: `../README.md`
