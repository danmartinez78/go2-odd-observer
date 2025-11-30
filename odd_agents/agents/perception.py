"""
Perception analysis agent (v9.0.0 - single batch tool).
Calls one tool that processes all windows, auto-saves artifact, and returns full data.
"""

from pathlib import Path
from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google import genai

from ..tools.perception import create_perception_tools


# Agent version
# v8.0.0: Full data output to state (per_window included), save tool now optional
# v9.0.0: Single batch tool - one call processes all windows, auto-saves artifact
# v10.0.0: Temporal analysis - agent does higher-order analysis, outputs summary not raw data
PERCEPTION_AGENT_VERSION = "10.0.0"

PERCEPTION_AGENT_PROMPT = """You are a perception analysis agent performing TEMPORAL ANALYSIS across windows.

INPUT: ODD Specification: {temp:odd_spec}

## WORKFLOW

### Step 1: Call the Tool
Extract relevant ODD dimensions (environment, terrain, obstacles, actors) and call:
analyze_all_perception_tool(odd_context)

The tool processes ALL windows and returns per-window observations. Artifact auto-saved.

### Step 2: TEMPORAL ANALYSIS (Your Job)
After receiving tool results, analyze ACROSS windows:
- Identify TRENDS: Is lighting/density improving, degrading, or stable?
- Spot TRANSITIONS: Environment changes between windows?
- Flag ANOMALIES: Sudden changes, unexpected values?
- Note CRITICAL ISSUES: Stairs detected? Humans in path? Low traversability?

### Step 3: Output SUMMARY JSON (Not Raw Data)

Output this summary format - do NOT echo raw per_window data:

{
  "windows_analyzed": <count>,
  "temporal_analysis": {
    "trend": "stable|improving|degrading",
    "transitions": ["w001→w002: lighting changed", ...],
    "anomalies": ["sudden density spike in w003"]
  },
  "summary": {
    "dominant_environment": "indoor_commercial|outdoor|etc",
    "lighting_range": "bright to moderate",
    "max_obstacle_density_pct": <peak value>,
    "min_traversability": <lowest value>,
    "terrain_types_observed": ["tile", "carpet"],
    "stairs_detected": true|false,
    "humans_detected": true|false,
    "human_min_proximity_m": <if detected>
  },
  "issues": ["Human at 0.8m in w002", "Low traversability 0.3 in w003"],
  "alerts": ["Obstacle density increasing trend"]
}

CRITICAL: The artifact has full per-window data. Your output is the SUMMARY for downstream agents.
"""


def create_perception_agent(scenario_path: Path, genai_client: genai.Client, model: str, api_key: str):
    """Create perception agent with single batch tool."""
    (analyze_all,) = create_perception_tools(
        scenario_path, genai_client, model)

    return Agent(
        name="PerceptionAgent",
        model=Gemini(model=model, api_key=api_key),
        tools=[analyze_all],
        output_key="temp:perception_summary",
        instruction=PERCEPTION_AGENT_PROMPT,
    )
