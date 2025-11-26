"""
Perception analysis agent (consolidated loop + summary).
Single agent that orchestrates tools AND produces final ODD-aligned output.
"""

from pathlib import Path
from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google import genai

from ..tools.perception import create_perception_tools


# Agent version
# Breaking: merged loop + summary into single agent
PERCEPTION_AGENT_VERSION = "4.0.0"

# Consolidated prompt
PERCEPTION_AGENT_PROMPT = """You orchestrate perception analysis with ODD-guided measurements.

INPUT:
- ODD Specification: {temp:odd_spec?}
- Tools: list_windows_tool, analyze_window_perception_tool

TASKS:
1. Filter ODD: Extract environment/actors dimensions observable from camera + LiDAR BEV
2. Call tools: list_windows_tool() then analyze_window_perception_tool(window_id, odd_context) for each
3. Cross-window reasoning: Analyze temporal patterns, transitions, anomalies
4. ODD measurements: Map observations to ODD dimensions with quantitative values
5. General observations: Sensor quality, anomalies, safety notes

OUTPUT (JSON only, no markdown):
{
  "windows_analyzed": [...],
  "odd_measurements": {
    // Use ODD dimension names as keys from environment/actors sections
    // Examples: "lighting_conditions": "bright", "obstacle_density": 0.35
  },
  "observations": [
    "Cross-window: <temporal patterns, stability, transitions>",
    "Sensor quality: <issues if any>",
    "Safety: <concerns if any>",
    "Data source: <simulation vs real>"
  ],
  "per_window_perception": [...]
}

Be concise. Provide quantitative metrics where possible."""


def create_perception_agent(scenario_path: Path, genai_client: genai.Client, model: str, api_key: str):
    """Create consolidated perception agent (loop + summary merged)."""
    list_windows, analyze_window = create_perception_tools(
        scenario_path, genai_client, model)

    return Agent(
        name="PerceptionAgent",
        model=Gemini(model=model, api_key=api_key),
        tools=[list_windows, analyze_window],
        output_key="temp:perception_output",
        instruction=PERCEPTION_AGENT_PROMPT,
    )
