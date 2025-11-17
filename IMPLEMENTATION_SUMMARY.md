# ODD/COD Workflow Notebook - Implementation Summary

## Overview

This implementation adds a comprehensive Jupyter notebook that demonstrates the complete ODD/COD analysis workflow for Unitree Go2 robot scenarios, following the architecture and style of the [Google Agentic Intensive Course](https://www.kaggle.com/learn-guide/5-day-agents).

## What Was Created

### 1. Main Workflow Notebook (`notebooks/odd_cod_workflow.ipynb`)

A well-documented, production-ready Jupyter notebook with 33 cells covering:

#### Section 1: Setup and Dependencies
- Installation of Google Generative AI SDK
- Import of all required packages (numpy, pandas, matplotlib, PIL, etc.)
- Configuration of plotting styles

#### Section 2: Google AI SDK Configuration
- API key setup with multiple options (environment variable, .env file, direct)
- Graceful fallback to demo mode if no API key is available

#### Section 3: ODD Specification Definition
- Example ODD creation for indoor robot operation
- Natural language boundary definitions (speed, roll/pitch, terrain, lighting, humans, collisions)
- Importance weighting for safety-critical axes

#### Section 4: Multi-Modal AI Agents
- **Motion Agent**: Analyzes time-series motion data (velocity, IMU, odometry)
- **Image Agent**: Visual scene understanding from camera images
- **LiDAR Agent**: Terrain classification from multi-channel BEV images
- **Collision Agent**: Multi-modal fusion for collision detection
- **Data Source Agent**: Sim vs real classification

Each agent includes:
- Gemini API integration with structured prompts
- Heuristic fallback for demo mode
- JSON-structured output parsing
- Error handling and graceful degradation

#### Section 5: Scenario Data Loading
- Directory discovery and listing
- Window index loading from CSV
- Data validation

#### Section 6: Window Processing
- Complete analysis pipeline per window
- Multi-modal data fusion
- COD vector construction
- Distance metric computation
- ODD status classification

#### Section 7: Scenario-Level Metrics
- Aggregation of window results
- Scenario distance calculation
- Time fraction computation
- Scenario classification (IN_ODD, BOUNDARY_HEAVY, ODD_EXIT)

#### Section 8: Visualization
- Distance timeline plot with ODD boundaries
- Status distribution bar chart
- Speed over time with ODD limits
- Roll/Pitch over time with boundaries
- All using matplotlib and seaborn

#### Section 9: Report Generation
- Comprehensive JSON report generation
- Violation listing with context
- Operational statistics summary
- Report saved to scenario directory

#### Section 10: Summary and Next Steps
- Workflow recap
- Suggestions for customization
- Links to resources

### 2. Demo Data Generator (`scripts/generate_demo_data.py`)

A complete synthetic data generator that creates:

- **10 time windows** with realistic motion data
- **Camera images** (640x480 RGB with synthetic indoor scenes)
- **Multi-channel BEV images** (4 channels per window: occupancy, height, density, roughness)
- **Index CSV** with proper metadata
- **Manifest CSV** with scenario information
- **Intentional ODD violations** in windows 7 and 8 for demonstration

Benefits:
- Test workflow without requiring ROS2 bags
- Demonstrate ODD violations and boundary cases
- Fast iteration during development
- Reproducible results

### 3. Documentation

#### `notebooks/README.md`
Comprehensive guide covering:
- Prerequisites and setup
- Running with demo data
- Running with real ROS2 data
- Notebook features (AI-powered vs demo mode)
- Architecture overview
- Customization instructions
- Troubleshooting guide

#### Updated Main README
- Quick start section added
- Repository structure updated
- Links to notebook documentation

### 4. Updated .gitignore
- Excludes executed notebooks (`*_executed.ipynb`)
- Maintains existing data exclusions
- Allows manifest.csv for demo data

## Key Features

### Multi-Modal AI Analysis
The notebook uses Google Gemini 2.5 Flash for:
- Natural language processing of motion patterns
- Vision-based scene understanding
- Multi-image terrain classification (4-channel BEV)
- Multi-modal sensor fusion for collision detection

### Flexible Operation Modes

**AI-Powered Mode** (with Google API key):
- Advanced analysis using Gemini models
- Structured JSON output from prompts
- Multi-modal reasoning capabilities

**Demo Mode** (without API key):
- Statistical heuristics for motion analysis
- Default classifications for images
- Basic collision detection
- Allows testing without API access

### Production-Ready Features
- Error handling and graceful degradation
- Progress indicators and status messages
- Configurable ODD specifications
- Extensible agent architecture
- Comprehensive output (plots + JSON reports)
- Clean, well-documented code

## Testing

The implementation was tested:

1. ✓ Notebook validates as proper JSON structure
2. ✓ All Python imports resolve correctly
3. ✓ Demo data generator creates complete datasets
4. ✓ Notebook executes end-to-end without errors (using nbconvert)
5. ✓ Demo pipeline script works with generated data
6. ✓ CodeQL security scan passes with 0 alerts
7. ✓ Existing unit tests still pass (21/21)

## Usage Examples

### Quick Start (Demo Mode)
```bash
# Generate demo data
python3 scripts/generate_demo_data.py

# Launch notebook
jupyter notebook notebooks/odd_cod_workflow.ipynb

# Run all cells - works without API key using heuristics
```

### With Google Gemini API
```bash
# Set API key
export GOOGLE_API_KEY='your-api-key-here'

# Generate demo data
python3 scripts/generate_demo_data.py

# Launch and run notebook - uses AI for analysis
jupyter notebook notebooks/odd_cod_workflow.ipynb
```

### With Real ROS2 Data
```bash
# Extract windows from ROS bag
source /opt/ros/humble/setup.bash
python3 scripts/extract_windows.py \
  --rosbag data/raw_rosbags/your_bag.db3 \
  --output data/processed/runs/my_run \
  --run-id my_run

# Update manifest.csv with metadata

# Run notebook
jupyter notebook notebooks/odd_cod_workflow.ipynb
```

## Architecture Alignment

The implementation follows the Google Agentic Intensive course principles:

1. **Multi-Agent Architecture**: Specialized agents for different modalities
2. **Structured Outputs**: JSON-formatted agent responses
3. **Prompt Engineering**: Clear, task-specific prompts for each agent
4. **Multi-Modal Analysis**: Combining text, images, and structured data
5. **Evaluation Metrics**: Quantitative distance metrics for compliance
6. **Human-Readable Reports**: Natural language summaries with visualizations

## File Structure

```
go2-odd-observer/
├── notebooks/
│   ├── odd_cod_workflow.ipynb       # Main workflow notebook (42KB)
│   └── README.md                    # Notebook documentation (5.4KB)
├── scripts/
│   ├── generate_demo_data.py        # Demo data generator (7.2KB)
│   └── ... (existing scripts)
├── data/
│   └── processed/
│       ├── manifest.csv             # Updated with demo run
│       └── runs/
│           └── demo_run/            # Generated demo data (gitignored)
├── README.md                        # Updated with quick start
└── .gitignore                       # Updated to exclude executed notebooks
```

## Next Steps

Users can:

1. **Run the notebook immediately** using demo data
2. **Add Google API key** for AI-powered analysis
3. **Process their own ROS2 bags** and analyze real scenarios
4. **Customize ODD specifications** for their use case
5. **Enhance agent prompts** for better analysis
6. **Add more visualization types** to the notebook
7. **Extend to additional sensor modalities** as needed

## Comparison to Google Agentic Course

The notebook follows similar patterns to the course examples:

- **Clear cell organization**: Markdown explanations followed by code
- **Progressive complexity**: Start simple, build up to full pipeline
- **Practical examples**: Real-world robot scenario analysis
- **Multi-modal integration**: Combining different data types
- **Structured prompts**: JSON output for reliable parsing
- **Graceful fallbacks**: Works without API in demo mode
- **Comprehensive documentation**: Inline comments and markdown
- **Reproducible results**: Demo data for consistent testing

## Conclusion

This implementation provides a complete, production-ready Jupyter notebook that demonstrates the full ODD/COD analysis workflow. It's well-documented, thoroughly tested, and ready for both demonstration and real-world use. The notebook can be run immediately with demo data or configured for AI-powered analysis with real ROS2 bag data.
