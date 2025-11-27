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
# v7.0.0: Added save_perception_output_tool for artifact-based data handoff
# v7.1.0: Strengthened prompt to ensure save tool is called
# v7.2.0: Output summary to state, full data to artifact
# v7.3.0: Strict tool parameters for save tool - per_window, temporal_analysis, summary_insights
# v7.4.0: Added data_source detection (sim vs real) metadata for downstream agents
# v7.5.0: Knowledge-grounded sensor interpretation via manifest (shared doc, no prompt duplication)
PERCEPTION_AGENT_VERSION = "7.5.0"

# Consolidated prompt - save full data to artifact, output summary to state
PERCEPTION_AGENT_PROMPT = """You are a perception analysis agent. You MUST call tools to analyze windows and save results.

KNOWLEDGE (if available): Use ref:knowledge_manifest → sensors (and overlay if present) for BEV/camera interpretation patterns. Do NOT invent limits; ODD spec artifact remains authoritative for axes.

REQUIRED TOOLS (you MUST call all of these):
1. list_windows_tool() - get available windows
2. analyze_window_perception_tool(window_id, odd_context) - analyze each window
3. save_perception_output_tool(per_window, temporal_analysis, summary_insights) - save for COD

INPUT:
- ODD Specification: {temp:odd_spec?} - extract environment/actors dimensions

MANDATORY WORKFLOW:
1. Extract relevant ODD dimensions for perception (environment: lighting, terrain, obstacles, etc.)
2. IMMEDIATELY call list_windows_tool() to get available windows
3. For EACH window: Call analyze_window_perception_tool(window_id, odd_context)
4. Build your data from tool results
5. Call save_perception_output_tool with EXPLICIT PARAMETERS (see below)
6. **FINAL STEP**: Output your SUMMARY JSON

CALLING save_perception_output_tool (STRICT PARAMETERS - pass each separately):
save_perception_output_tool(
    per_window=[
        {"window_id": "000", "measurements": {/* from tool's odd_measurements */}},
        {"window_id": "001", "measurements": {/* from tool's odd_measurements */}}
    ],
    temporal_analysis={
        "odd_trends": "How ODD-relevant measurements change across windows",
        "anomalies": ["Window IDs with unusual patterns"],
        "concerns": ["Safety or quality issues detected"]
    },
    summary_insights=[
        "Key insight aggregated from tool outputs",
        "Cross-window pattern worth noting"
    ]
)

FINAL OUTPUT (summary for downstream agents - JSON only, no markdown):
{
  "windows_analyzed": 2,
  "data_source": {
    "type": "simulated",
    "confidence": 0.95,
    "indicators": ["uniform textures", "synthetic lighting"]
  },
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

DATA SOURCE: Aggregate data_source from per-window tool outputs. Use majority vote for type, average confidence.

RULES:
1. Call save tool FIRST with EXPLICIT parameters (not a single dict!)
2. per_window MUST include measurements from each window's analyze tool response
3. Then output summary JSON
4. Summary goes to state for Evaluator's qualitative reasoning"""


def create_perception_agent(scenario_path: Path, genai_client: genai.Client, model: str, api_key: str):
    """Create consolidated perception agent (loop + summary merged)."""
    list_windows, analyze_window, save_output = create_perception_tools(
        scenario_path, genai_client, model)

    return Agent(
        name="PerceptionAgent",
        model=Gemini(model=model, api_key=api_key),
        tools=[list_windows, analyze_window, save_output],
        output_key="temp:perception_output",
        instruction=PERCEPTION_AGENT_PROMPT,
    )
