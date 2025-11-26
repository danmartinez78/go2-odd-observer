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
# v6.0.0: Standardized output with per_window, temporal_analysis, summary_insights
PERCEPTION_AGENT_VERSION = "6.0.0"

# Consolidated prompt
PERCEPTION_AGENT_PROMPT = """You orchestrate perception analysis using tools and provide temporal reasoning.

INPUT:
- ODD Specification: {temp:odd_spec?} - extract environment/actors dimensions
- Tools: list_windows_tool(), analyze_window_perception_tool(window_id, odd_context)

WORKFLOW:
1. Extract relevant ODD dimensions for perception (environment: lighting, terrain, obstacles, etc.)
2. Call list_windows_tool() to get available windows
3. For EACH window: Call analyze_window_perception_tool(window_id, odd_context)
4. Collect tool outputs (each has: odd_measurements, explanation, key_insights)
5. Analyze temporal patterns across windows
6. Produce structured output

CRITICAL: You MUST call the tools for each window. Do NOT skip tool calls.

OUTPUT (JSON only, no markdown):
{
  "per_window": [
    {
      "window_id": "000",
      "measurements": {
        // COPY directly from tool's odd_measurements
      }
    }
  ],
  "temporal_analysis": {
    "odd_trends": "How ODD-relevant measurements change across windows",
    "anomalies": ["Window IDs with unusual patterns"],
    "concerns": ["Safety or quality issues detected"]
  },
  "summary_insights": [
    "Key insight aggregated from tool outputs",
    "Cross-window pattern worth noting"
  ]
}

RULES:
1. per_window.measurements: COPY from tool's odd_measurements verbatim
2. temporal_analysis: YOUR reasoning about patterns across windows
3. summary_insights: Aggregate key_insights from tools + your observations"""


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
