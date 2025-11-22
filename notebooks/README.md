# ODD Analysis Notebooks

This directory contains Jupyter notebooks for interactive ODD (Operational Design Domain) compliance analysis.

## Current Notebooks

### `odd_analysis_demo.ipynb` - **RECOMMENDED**

**Clean, well-documented notebook for running ODD analysis.**

Features:
- ✅ Uses shared `odd_agents` module (single source of truth)
- ✅ Clear step-by-step instructions
- ✅ Customizable ODD specifications
- ✅ Built-in visualizations
- ✅ Suitable for learning and experimentation

**What you need:**
- Google Gemini API key (free at https://aistudio.google.com/app/apikey)
- Preprocessed scenario data (run `scripts/extract_windows.py`)

**Quick start:**
1. Open `odd_analysis_demo.ipynb`
2. Set API key in cell 2
3. Run all cells

## Archived Notebooks

The `archive/` directory contains older notebooks that have been superseded:

- `odd_workflow_minimal.ipynb` - Minimal version (replaced by demo)
- `odd_workflow_educational.ipynb` - Extended educational version (replaced by demo)
- `odd_cod_misc.ipynb` - Miscellaneous experiments
- `odd_cod_workflow_ARCHIVED.ipynb` - Original archived workflow

**Note:** Archived notebooks are kept for reference but are no longer maintained. Use `odd_analysis_demo.ipynb` instead.

## For Developers

If you want to understand how the agents work:
- **Agent implementations**: `../odd_agents/agents/`
- **Workflow orchestration**: `../odd_agents/workflow.py`
- **Factory pattern docs**: `../docs/FACTORY_PATTERN.md`
- **Production script**: `../scripts/odd_workflow.py`

All use the same `odd_agents` module - single source of truth!
