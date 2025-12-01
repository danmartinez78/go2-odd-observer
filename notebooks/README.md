# ODD Analysis Notebooks

Interactive notebooks for ODD (Operational Design Domain) compliance analysis.

## Quick Start

### `odd_analysis_demo.ipynb`

Demonstrates the 6-agent pipeline for robot safety analysis.

**Requirements:**
- Google Gemini API key ([get free key](https://aistudio.google.com/app/apikey))
- Set key in `.env` file: `GOOGLE_API_KEY=your-key-here`

**Usage:**
1. Open `odd_analysis_demo.ipynb`
2. Run setup cells (1-4)
3. Select scenario (default: `sim_2win`)
4. Run analysis or explore data

**Sections:**
1. Setup & API config
2. ODD/COD concepts
3. Available scenarios
4. Explore window data (camera, BEV, motion)
5. Run analysis pipeline
6. Review results
7. Generate HTML report

## Available Scenarios

| Scenario | Type | Windows | Description |
|----------|------|---------|-------------|
| `sim_2win` | Test | 2 | Simulation quick test |
| `real_2win` | Test | 2 | Real robot quick test |
| `real_173442_2win` | Test | 2 | Real robot (173442) |
| `sim_outdoor_*` | Prod | 16 | Full simulation runs |
| `real_173442_*` | Prod | 16 | Full real robot runs |

## For Developers

- **Pipeline runner**: `scripts/run_odd_analysis.py`
- **Agent implementations**: `odd_agents/agents/`
- **Tools**: `odd_agents/tools/`
- **Architecture**: `docs/index.html`

## Archived

Old notebooks in `.archive/notebooks/` - use `odd_analysis_demo.ipynb` instead.
