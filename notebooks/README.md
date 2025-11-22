# ODD Analysis Notebooks

This directory contains Jupyter notebooks for interactive ODD (Operational Design Domain) compliance analysis.

## Current Notebook

### `odd_analysis_demo.ipynb` - **RECOMMENDED**

**Clean, parameterized notebook for running ODD analysis with model configuration.**

Features:
- ✅ Uses parameterized `odd_agents` module (no global state)
- ✅ Per-agent model selection for cost optimization
- ✅ Clear step-by-step instructions with configuration cells
- ✅ Customizable ODD specifications via natural language
- ✅ Built-in visualizations (collision risk, motion detection)
- ✅ Complete workflow demonstration

**What you need:**
- Google Gemini API key (free at https://aistudio.google.com/app/apikey)
- Preprocessed scenario data (included: `sim_run_test` with 2 windows)

**Quick start:**
1. Open `odd_analysis_demo.ipynb`
2. Set API key in cell 2: `GOOGLE_API_KEY = "your-key-here"`
3. Configure models in cell 5 (optional - defaults to flash-lite)
4. Run all cells

**Model Configuration:**
```python
# Configure per-agent models for cost/quality tradeoff
MODEL_PERCEPTION = "gemini-2.5-pro"      # High-quality vision
MODEL_MOTION = "gemini-2.0-flash-lite"   # Default (cost-effective)
MODEL_COLLISION = "gemini-2.5-pro"       # Critical safety analysis
# ... etc
```

See [`../docs/MODEL_SELECTION_GUIDE.md`](../docs/MODEL_SELECTION_GUIDE.md) for recommendations.

## Archived Notebooks

Historical notebooks moved to [`../.archive/notebooks/`](../.archive/notebooks/):

- `odd_workflow_minimal.ipynb` - Minimal version (superseded)
- `odd_workflow_educational.ipynb` - Extended educational version (superseded)
- `odd_cod_misc.ipynb` - Miscellaneous experiments
- `odd_cod_workflow_ARCHIVED.ipynb` - Original workflow

**Note:** Archived notebooks use old architecture (config.py, non-parameterized) and are not maintained. Use `odd_analysis_demo.ipynb` instead.

## For Developers

To understand the implementation:
- **Module structure**: `../odd_agents/` (tools, agents, workflow)
- **Agent implementations**: `../odd_agents/agents/`
- **Workflow orchestration**: `../odd_agents/workflow.py`
- **Production script**: `../scripts/odd_workflow.py` (same API as notebook)
- **Architecture guide**: `../docs/MODEL_SELECTION_GUIDE.md`

Everything uses the same parameterized `odd_agents` module - single source of truth!
