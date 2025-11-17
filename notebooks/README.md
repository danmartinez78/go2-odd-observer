# ODD/COD Analysis Notebooks

This directory contains Jupyter notebooks demonstrating the complete workflow for ODD/COD analysis of Unitree Go2 robot scenarios.

## Main Notebook

### `odd_cod_workflow.ipynb`

A comprehensive notebook demonstrating the complete analysis workflow:

1. **Setup and Dependencies** - Install and configure Google AI SDK and project packages
2. **ODD Specification** - Define operational design domain with natural language boundaries
3. **Multi-Modal Agents** - Instantiate AI agents for Motion, Image, LiDAR, and Collision analysis
4. **Data Loading** - Load preprocessed window data from ROS2 bag processing
5. **ODD Evaluation** - Analyze compliance and compute distance metrics for each window
6. **Visualization** - Generate timeline plots and distribution charts
7. **Reporting** - Create comprehensive analysis reports with violation details

## Getting Started

### Prerequisites

1. Python 3.10+ with Jupyter installed
2. Google API key for Gemini (optional - notebook works in demo mode without it)
3. Preprocessed window data from ROS2 bags (or use demo data)

### Setup

```bash
# Install dependencies
pip install -r ../requirements.txt

# (Optional) Set up Google API key for AI analysis
export GOOGLE_API_KEY='your-api-key-here'
# Or create a .env file in the project root:
# echo "GOOGLE_API_KEY=your-api-key-here" > ../.env
```

### Running with Demo Data

The repository includes a demo data generator for testing the workflow without real ROS2 bags:

```bash
# Generate demo data
python3 ../scripts/generate_demo_data.py

# Start Jupyter
jupyter notebook

# Open odd_cod_workflow.ipynb and run all cells
```

### Running with Real Data

If you have actual ROS2 bag files:

```bash
# 1. Extract windows from ROS2 bags (requires ROS2 environment)
source /opt/ros/humble/setup.bash
python3 ../scripts/extract_windows.py \
  --rosbag ../data/raw_rosbags/your_bag.db3 \
  --output ../data/processed/runs/run_001 \
  --run-id run_001 \
  --window-length 2.0 \
  --stride 1.0

# 2. Update manifest
# Edit data/processed/manifest.csv to add metadata for your run

# 3. Run the notebook
jupyter notebook odd_cod_workflow.ipynb
```

## Notebook Features

### AI-Powered Analysis (with API Key)

When a Google API key is configured, the notebook uses Gemini 2.5 Flash for:
- Motion pattern analysis from time series data
- Visual scene understanding from camera images
- Terrain classification from multi-channel LiDAR BEV images
- Multi-modal collision detection

### Demo Mode (without API Key)

The notebook works without an API key using heuristic-based fallbacks:
- Simple statistical analysis for motion data
- Default classifications for images and terrain
- Basic collision detection from tracking errors

### Output

The notebook generates:
- **Interactive plots**: Distance timelines, status distributions, feature trends
- **JSON reports**: Detailed analysis results saved to scenario directory
- **Violation summaries**: Lists of ODD exits with context and severity

## Architecture Overview

The workflow follows the architecture described in the [Google Agentic Intensive Course](https://www.kaggle.com/learn-guide/5-day-agents):

```
Multi-Modal Windows (Motion + Camera + LiDAR)
    ↓
Specialized Analysis Agents (Motion, Image, LiDAR)
    ↓
Fusion Agent (Collision Detection)
    ↓
ODD Evaluator (Compliance Checking)
    ↓
Distance Metrics (Quantitative Assessment)
    ↓
Reports & Visualizations
```

## Customization

### Defining Custom ODDs

Create your own ODD specifications by modifying the ODD definition cell:

```python
odd_spec = OddSpec(
    version="2.0",
    description="Custom ODD for your use case",
    axes={
        "speed": AxisSpecNumeric(
            feature="forward_velocity",
            units="m/s",
            in_odd=[min_speed, max_speed],
            near_boundary=[min_boundary, max_boundary],
            hard_limit=[hard_min, hard_max]
        ),
        # Add more axes...
    },
    importance={
        "speed": 1.0,  # Adjust weights
        # ...
    }
)
```

### Agent Prompts

Modify the agent analysis functions to customize how Gemini interprets sensor data:
- `analyze_motion_with_gemini()` - Motion analysis prompts
- `analyze_image_with_gemini()` - Camera image prompts
- `analyze_lidar_with_gemini()` - LiDAR BEV prompts
- `analyze_collision_with_gemini()` - Collision detection prompts

## Examples

See the [Google Agentic Intensive notebooks](https://www.kaggle.com/learn-guide/5-day-agents) for inspiration on:
- Structuring multi-agent workflows
- Prompt engineering for multi-modal analysis
- Combining structured and unstructured data
- Building robust evaluation metrics

## Troubleshooting

### "No processed data found"
- Run `generate_demo_data.py` or process actual ROS2 bags first
- Check that `data/processed/runs/` contains scenario directories

### "Gemini API error"
- Verify your API key is set correctly
- Check you have API quota remaining
- The notebook will fall back to demo mode if API calls fail

### "Import errors"
- Ensure all requirements are installed: `pip install -r ../requirements.txt`
- Check Python version is 3.10 or newer

## Contributing

Improvements to the notebook are welcome! Consider:
- Better visualization styles
- Additional analysis metrics
- Enhanced agent prompts
- Support for more sensor modalities

## License

This notebook is part of the Go2 ODD/COD Observer project, licensed under MIT.
