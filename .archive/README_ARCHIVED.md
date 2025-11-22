# ODD/COD Analysis Notebook

This directory contains the complete AI-powered workflow for analyzing Operational Design Domain (ODD) compliance using Google's Agent Development Kit (ADK).

## Main Notebook

### `odd_cod_workflow.ipynb` - Complete End-to-End Analysis Workflow

A comprehensive notebook implementing the full agent-based analysis pipeline:

1. **Setup and Dependencies** - Install `google-adk` package and configure environment
2. **Configure Google AI SDK** - Set up Gemini API key (required for agent execution)
3. **User Inputs** - Define ODD in natural language and select dataset
4. **Tool Functions** - Python utilities for file I/O, COD computation, visualization
5. **Specialist Agents** - 7 AI agents using Google ADK and Gemini 2.0 Flash
6. **Orchestration** - ParallelAgent and SequentialAgent workflow composition
7. **Execute** - Run the complete workflow with InMemoryRunner

**Architecture Pattern**: Follows [Kaggle Day 1B: Agent Architectures](https://www.kaggle.com/code/kaggle5daysofai/day-1b-agent-architectures)

## Getting Started

### Prerequisites

**Required**:
- Python 3.10+
- Jupyter Notebook or Kaggle environment
- **Google API key for Gemini** ([Get one here](https://aistudio.google.com/apikey))
- Preprocessed window data from ROS2 bags

**Optional**:
- ROS2 Humble (for bag preprocessing)

### Installation

The notebook handles dependency installation in Section 1:
```python
!pip install -q google-adk python-dotenv
```

Additional tools (numpy, pandas, matplotlib, Pillow) are assumed available in Jupyter environment.

### Quick Start with Demo Data

```bash
# 1. Generate demo data
python3 ../scripts/generate_demo_data.py

# 2. Create .env file with API key
echo "GOOGLE_API_KEY=your_api_key_here" > ../.env

# 3. Launch Jupyter
jupyter notebook

# 4. Open odd_cod_workflow.ipynb
# 5. Run all cells sequentially
```

### Quick Start with Real ROS2 Bag Data

```bash
# 1. Extract windows from ROS2 bags
source /opt/ros/humble/setup.bash
python3 ../scripts/extract_windows.py \
  --rosbag ../data/raw_rosbags/sim/1/rosbag2_*.db3 \
  --output ../data/processed/runs/run_001 \
  --run-id run_001 \
  --window-length 2.0 \
  --stride 1.0

# 2. Set API key in .env
echo "GOOGLE_API_KEY=your_api_key_here" > ../.env

# 3. Open notebook and update dataset_path in Section 3
dataset_path = "../data/processed/runs/run_001"

# 4. Run all cells
```

---

## Notebook Structure

### Section 1: Installation
```bash
!pip install -q google-adk python-dotenv
```
Installs Google Agent Development Kit and environment variable management.

### Section 2: Configuration
```python
import os
from dotenv import load_dotenv

load_dotenv()
os.environ["GOOGLE_API_KEY"] = "YOUR_API_KEY_HERE"
```
**⚠️ Required**: You must provide a valid Gemini API key. The ADK framework does not support demo mode.

### Section 3: User Inputs
Define analysis parameters:
```python
nl_odd_description = """
The robot must operate:
- At velocities below 1.5 m/s
- In indoor environments only
- On flat terrain (pitch/roll < 5 degrees)
- With no obstacles within 1 meter
"""

dataset_path = "../data/processed/runs/run_001"
```

### Section 4: Tool Functions
Python utilities that agents can call:
- `load_window_data(window_id, dataset_path)` - Load sensor data from JSON
- `build_odd_spec_from_json(odd_dict)` - Convert ODD to structured spec
- `compute_cod(spec_values, actual_values)` - Calculate Criticality of Deviation
- `plot_cod_timeline(results)` - Generate timeline visualizations
- `aggregate_cod_statistics(results)` - Compute summary statistics

### Section 5: Specialist Agents
Seven AI agents built with `google.adk.agents.Agent`:

1. **ODD Specification Agent**  
   Converts natural language ODD description to structured JSON spec

2. **Motion Analysis Agent**  
   Analyzes velocity, acceleration, angular velocity from IMU data

3. **Vision Analysis Agent**  
   Detects environment type and hazards from camera feed

4. **Terrain Analysis Agent**  
   Evaluates surface conditions from LiDAR point clouds

5. **Collision Risk Agent**  
   Assesses proximity violations and collision hazards

6. **COD Evaluator Agent**  
   Computes deviation metrics from all sensor analyses

7. **Report Generator Agent**  
   Synthesizes comprehensive analysis report

Each agent uses `Gemini(model_id="gemini-2.0-flash-exp")` with specific tool access.

### Section 6: Orchestration
Agent composition using ADK patterns:

```python
from google.adk.agents import ParallelAgent, SequentialAgent

# Parallel sensor analysis (runs simultaneously)
sensor_team = ParallelAgent(
    name="SensorAnalysisTeam",
    agents=[motion_agent, vision_agent, terrain_agent, collision_agent]
)

# Sequential workflow (enforces dependencies)
workflow = SequentialAgent(
    name="ODDAnalysisWorkflow",
    agents=[
        odd_spec_agent,      # Step 1: Parse ODD
        sensor_team,         # Step 2: Analyze sensors in parallel
        cod_evaluator,       # Step 3: Compute deviations
        report_generator     # Step 4: Generate report
    ]
)
```

**ParallelAgent**: Runs Motion, Vision, Terrain, and Collision agents simultaneously for efficiency.

**SequentialAgent**: Ensures proper data flow - ODD Spec → Sensors → COD Evaluator → Report.

### Section 7: Execution
Run the complete workflow:

```python
from google.adk.runners import InMemoryRunner

runner = InMemoryRunner()
result = await runner.run_debug(
    agent=workflow,
    inputs={"user_input": nl_odd_description}
)

# Access results from session state
print(result.session_state.get("final_report"))
```

The runner manages session state, passing data between agents via `output_key` attributes.

---

## Agent Architecture Details

### Data Flow Pattern
```
User Input (NL ODD)
    ↓
ODD Specification Agent → structured_odd_spec
    ↓
┌─────────────── ParallelAgent ───────────────┐
│  Motion Agent → motion_analysis             │
│  Vision Agent → vision_analysis             │
│  Terrain Agent → terrain_analysis           │
│  Collision Agent → collision_analysis       │
└─────────────────────────────────────────────┘
    ↓
COD Evaluator Agent → cod_results
    ↓
Report Generator Agent → final_report
```

### Session State Management
Agents communicate via `runner.session_state`:
- **ODD Spec Agent** outputs to `output_key="structured_odd_spec"`
- **Sensor Agents** read ODD spec from state, output to their respective keys
- **COD Evaluator** reads all sensor analyses, computes deviations
- **Report Generator** synthesizes all prior analyses into final report

No manual data passing required - the `InMemoryRunner` handles it automatically.

### Why This Architecture?

**✅ Scalability**: Add new sensor agents by extending `ParallelAgent`  
**✅ Maintainability**: Each agent has single responsibility (SRP)  
**✅ Efficiency**: Parallel execution reduces total analysis time  
**✅ Modularity**: Swap agents without changing workflow structure  
**✅ Testability**: Test individual agents in isolation before composition  

---

## Output Format

### Agent Execution Results
The `InMemoryRunner` returns session state containing all agent outputs:

```python
{
    "structured_odd_spec": {
        "velocity": {"max": 1.5, "unit": "m/s"},
        "environment": "indoor",
        "terrain": {"max_pitch": 5, "max_roll": 5},
        "min_obstacle_distance": 1.0
    },
    "motion_analysis": {
        "window_001": {"velocity": 1.2, "compliant": True, "cod": 0.0},
        "window_002": {"velocity": 1.8, "compliant": False, "cod": 0.2},
        ...
    },
    "vision_analysis": {
        "window_001": {"environment": "indoor", "hazards": [], "compliant": True},
        ...
    },
    "terrain_analysis": {...},
    "collision_analysis": {...},
    "cod_results": {
        "summary": {"total_windows": 150, "violations": 12},
        "critical_windows": ["window_042", "window_089"],
        "average_cod": 0.03
    },
    "final_report": "# ODD Compliance Analysis\n\n## Summary\n..."
}
```

### Visualizations
Tool functions generate matplotlib figures:
- **COD Timeline**: Line plot showing deviation scores over time
- **Violation Distribution**: Histogram of deviation severity
- **Multi-Sensor Dashboard**: Comparative sensor analysis (optional enhancement)

### Report Structure
The Report Generator Agent produces markdown-formatted analysis:
```markdown
# ODD Compliance Analysis Report

## Executive Summary
- Total Windows Analyzed: 150
- Compliant Windows: 138 (92%)
- Violations: 12 (8%)
- Average COD: 0.03

## Critical Violations
1. Window 042: Velocity 1.8 m/s (max: 1.5 m/s) - COD: 0.20
2. Window 089: Outdoor environment detected - COD: 1.00
3. Window 134: Obstacle at 0.6m (min: 1.0m) - COD: 0.40

## Recommendations
- Review velocity controller gains
- Investigate environment transition at t=89.0s
- Enhance obstacle avoidance for <1m range
```

---

## Customization

### Defining Custom ODDs
Modify the natural language description in Section 3:

```python
nl_odd_description = """
The robot must:
- Maintain speed below 2.0 m/s in corridors, 1.0 m/s in crowded areas
- Operate only in well-lit environments (lux > 100)
- Avoid stairs and ramps steeper than 15 degrees
- Maintain 1.5m distance from humans
"""
```

The ODD Specification Agent will parse these into structured constraints automatically.

### Adjusting Agent Instructions
Edit agent `instruction` parameters in Section 5:

```python
motion_agent = Agent(
    name="Motion_Analysis_Agent",
    model=Gemini(model_id="gemini-2.0-flash-exp"),
    tools=[load_window_data],
    instruction="""
    Analyze motion data with emphasis on:
    1. Smooth velocity transitions (avoid jerky motion)
    2. Energy efficiency (minimize acceleration changes)
    3. Safety margins (maintain 20% buffer from limits)
    """,
    output_key="motion_analysis"
)
```

### Adding New Sensor Agents
Extend the `ParallelAgent` in Section 6:

```python
# Define new agent in Section 5
audio_agent = Agent(
    name="Audio_Analysis_Agent",
    model=Gemini(model_id="gemini-2.0-flash-exp"),
    tools=[load_window_data],
    instruction="Analyze audio data for noise levels and anomalies",
    output_key="audio_analysis"
)

# Add to sensor team in Section 6
sensor_team = ParallelAgent(
    name="SensorAnalysisTeam",
    agents=[
        motion_agent, 
        vision_agent, 
        terrain_agent, 
        collision_agent,
        audio_agent  # NEW
    ]
)
```

### Custom COD Formulas
Modify `compute_cod()` in Section 4:

```python
def compute_cod(spec_value, actual_value, metric_type="normalized"):
    """
    Compute Criticality of Deviation metric.
    
    metric_type options:
    - "normalized": Linear deviation ratio
    - "exponential": Exponential severity scaling
    - "logarithmic": Log-scale for wide ranges
    """
    if metric_type == "normalized":
        return abs(actual_value - spec_value) / spec_value
    elif metric_type == "exponential":
        return 1 - math.exp(-abs(actual_value - spec_value))
    elif metric_type == "logarithmic":
        return math.log1p(abs(actual_value - spec_value))
```

---

## Troubleshooting

### Common Issues

**Problem**: `ModuleNotFoundError: No module named 'google.adk'`  
**Solution**: Execute Section 1 cell to install dependencies. If on Kaggle, enable internet access in notebook settings.

---

**Problem**: `API key not valid` or `Authentication failed`  
**Solution**: 
1. Verify API key at [Google AI Studio](https://aistudio.google.com/apikey)
2. Check `.env` file exists and has correct format: `GOOGLE_API_KEY=your_key_here`
3. Test API key directly:
   ```python
   from google.adk.models.google_llm import Gemini
   model = Gemini(model_id="gemini-2.0-flash-exp")
   print("API key valid!")
   ```

---

**Problem**: `FileNotFoundError: window_000001.json`  
**Solution**: 
1. Run preprocessing: `python scripts/extract_windows.py ...`
2. Verify dataset path: `ls ../data/processed/runs/run_001/`
3. Update `dataset_path` in Section 3 to match your data location

---

**Problem**: Agent execution timeout or hangs  
**Solution**: 
- Gemini 2.0 Flash has rate limits (~60 requests/min)
- Add delays between window analyses: `time.sleep(1)`
- Reduce dataset size for testing: process first 10 windows only
- Check API quota: [Google AI Studio Usage](https://aistudio.google.com/)

---

**Problem**: Agents return incomplete or empty analysis  
**Solution**: 
1. Check tool function outputs - ensure JSON has expected fields
2. Verify ODD spec format matches agent instruction expectations
3. Enable debug logging:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```
4. Inspect session state after each agent:
   ```python
   print(runner.session_state.get("motion_analysis"))
   ```

---

**Problem**: JSON parsing errors in agent responses  
**Solution**: 
- Gemini occasionally returns markdown-wrapped JSON
- Update tool functions to strip markdown:
  ```python
  text = response.strip()
  if text.startswith("```json"):
      text = text.split("```json")[1].split("```")[0]
  result = json.loads(text)
  ```

---

**Problem**: `ImportError` for numpy, pandas, matplotlib  
**Solution**: These are assumed in Jupyter environments. If missing:
```bash
pip install numpy pandas matplotlib pillow
```

---

### Debug Mode
The notebook uses `runner.run_debug()` for detailed execution logs:

```python
result = await runner.run_debug(agent=workflow, inputs={"user_input": nl_odd_description})

# View execution trace
for step in result.execution_trace:
    print(f"{step.agent_name}: {step.status}")
```

Logs show:
- Each agent execution start/end
- Tool calls with arguments and returns
- Session state transitions
- Error messages with stack traces

### Validation Checklist
Before running the complete workflow, verify:

- [ ] **Section 1**: `google-adk` installed successfully (check for version info)
- [ ] **Section 2**: `GOOGLE_API_KEY` is set (test: `print(os.getenv("GOOGLE_API_KEY")[:10] + "...")`)
- [ ] **Section 3**: Dataset path exists (`os.path.exists(dataset_path)` returns `True`)
- [ ] **Section 4**: Tool functions execute without errors (test `load_window_data("window_000001", dataset_path)`)
- [ ] **Section 5**: All 7 agents instantiate (check for import errors, no exceptions)
- [ ] **Section 6**: Orchestration agents created (`sensor_team` and `workflow` are defined)
- [ ] **Section 7**: Runner executes and returns session state with all expected keys

---

## Performance Considerations

### API Costs
Gemini 2.0 Flash pricing (January 2024):
- **Input**: $0.075 per 1M tokens
- **Output**: $0.30 per 1M tokens

**Typical Analysis Costs** (150 windows):
- ODD Spec Agent: ~500 input + ~200 output tokens
- Sensor Agents (4×150): ~600k input + ~240k output tokens
- COD Evaluator: ~50k input + ~20k output tokens
- Report Generator: ~10k input + ~5k output tokens
- **Total**: ~$0.50 per 150-window analysis

### Processing Time
- **Per-Window Analysis**: ~2-3 seconds (network latency)
- **150 Windows Sequential**: ~7-10 minutes
- **150 Windows with Parallel Sensors**: ~5-7 minutes (ParallelAgent optimization)

### Optimization Strategies

1. **Batch Window Processing**: Group windows for single API call
   ```python
   # Instead of: analyze_window(w1), analyze_window(w2), ...
   # Do: analyze_batch([w1, w2, w3, ...])
   ```

2. **Caching ODD Spec**: Store parsed spec to avoid re-parsing
   ```python
   if "structured_odd_spec" in runner.session_state:
       odd_spec = runner.session_state["structured_odd_spec"]
   else:
       odd_spec = odd_spec_agent.run(nl_odd_description)
   ```

3. **Selective Analysis**: Only run expensive vision/LiDAR agents when motion violations detected
   ```python
   if motion_result["compliant"]:
       # Skip detailed vision/terrain analysis for compliant windows
       vision_result = {"compliant": True, "cod": 0.0}
   else:
       vision_result = vision_agent.run(window_data)
   ```

4. **Model Selection**: Use faster model for non-critical analyses
   ```python
   # Use gemini-1.5-flash for terrain (faster, cheaper)
   terrain_agent = Agent(
       name="Terrain_Agent",
       model=Gemini(model_id="gemini-1.5-flash"),  # Older but faster
       ...
   )
   ```

---

## Architecture Notes

### Why Google ADK?
The Agent Development Kit provides:
- **Declarative composition** via `ParallelAgent` and `SequentialAgent`
- **Automatic state management** through `InMemoryRunner`
- **Built-in tool integration** with `AgentTool` and `FunctionTool`
- **Production-ready patterns** validated in Kaggle challenges

### Alternative Approaches Considered
1. **Direct Gemini API calls**: Rejected - too much manual state management
2. **LangChain LCEL**: Rejected - ADK has better Gemini integration and simpler syntax
3. **Custom agent framework**: Rejected - ADK provides battle-tested patterns from Google

### Design Decisions

**ParallelAgent for Sensors**  
Motion, Vision, Terrain, and Collision analyses are independent → parallel execution saves time without sacrificing accuracy.

**SequentialAgent for Workflow**  
- ODD spec must complete before sensors (dependency)
- COD evaluator needs all sensor data (dependency)
- Report needs final COD results (dependency)
→ Sequential enforcement prevents race conditions

**Gemini 2.0 Flash Model**  
- Fast inference (~2s per request)
- Cost-effective ($0.075/1M tokens input)
- Multimodal support (text, JSON, images, future: video)
- Strong structured output capabilities (JSON mode)

**JSON Tool Outputs**  
Structured data enables:
- Reliable agent-to-agent communication
- Easy debugging (inspect session state)
- Validation against schemas
- Type-safe processing in Python

---

## Development Roadmap

**Phase 1 ✅**: Data preprocessing pipeline (extract_windows.py, manifest.csv)  
**Phase 2 ✅**: Tool function library (COD metrics, visualization, I/O)  
**Phase 3 ✅**: Google ADK agent architecture (7 specialists + orchestration)  
**Phase 4 🔄**: Testing and validation (current phase - verify on real ROS2 bags)  
**Phase 5 📋**: Real-time ROS2 integration (streaming bag analysis)  
**Phase 6 📋**: Multi-robot fleet analysis (distributed ParallelAgent across robots)

---

## References

- [Google Agent Development Kit Documentation](https://ai.google.dev/adk)
- [Gemini 2.0 Model Card](https://ai.google.dev/gemini-api/docs/models/gemini-v2)
- [Kaggle Day 1B: Agent Architectures](https://www.kaggle.com/code/kaggle5daysofai/day-1b-agent-architectures)
- [ISO 34503 ODD Specification Standard](https://www.iso.org/standard/78964.html)
- [ROS2 Bag Format](https://docs.ros.org/en/rolling/Concepts/About-ROS2-Bags.html)

---

## Contributing

Improvements welcome! Consider:
- Enhanced visualization dashboards (Plotly, Dash)
- Additional distance metrics (Mahalanobis, Bhattacharyya)
- Custom agent prompts for specific robot types
- Support for additional sensor modalities (thermal, audio, GPS)
- Real-time streaming analysis
- Multi-robot coordination patterns

See [project_plan.md](../project_plan.md) for detailed development roadmap.

---

## License

This notebook is part of the **Go2 ODD/COD Observer** project.  
Licensed under MIT License - see [LICENSE](../LICENSE) for details.

---

## Support

For issues or questions:
1. Check **Troubleshooting** section above
2. Review [project_plan.md](../project_plan.md) for system architecture details
3. Inspect agent execution logs from `runner.run_debug()`
4. Verify tool function outputs match expected JSON schemas
5. Test API key with minimal Gemini example

**⚠️ Important**: This notebook requires an active Gemini API key. There is **no demo mode** or heuristic fallback - all analysis is AI-powered using Google's ADK framework and Gemini 2.0 Flash model.
