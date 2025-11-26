"""
Perception analysis agents.
Factory functions that create agents with specific configuration.
"""

from pathlib import Path
from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google import genai

from ..tools.perception import create_perception_tools


# Agent versions
PERCEPTION_LOOP_VERSION = "3.0.0"  # Breaking: ODD-guided + observations structure
# Breaking: ODD-guided + observations structure
PERCEPTION_SUMMARY_VERSION = "3.0.0"

# Prompt templates
PERCEPTION_LOOP_PROMPT = """You orchestrate perception analysis across all scenario windows.

Steps you MUST follow:
1. Call list_windows_tool() exactly once to get the ordered window_id list.
2. For each window_id returned (in that order), call analyze_window_perception_tool(window_id=...).
3. Collect each tool response exactly as returned.
4. After all windows are processed, respond with JSON:
{
  "windows_analyzed": ["..."],
  "per_window_perception": [<tool_response_objects_in_order>]
}
Do not add commentary. Ensure valid JSON."""

PERCEPTION_SUMMARY_PROMPT = """You finalize the perception report with ODD-guided measurements and general observations.

INPUT DATA:
- ODD Specification: {temp:odd_spec?}
- Per-window perception: {temp:perception_data?}

If no data is provided, respond with:
{"error": "missing_perception_data"}

Otherwise, extract TWO types of information:

**1. ODD-GUIDED MEASUREMENTS** (for compliance checking):
- Read the ODD spec's environment and actors sections
- For each categorical dimension, classify observations using ODD taxonomy where applicable
- For each numeric dimension, calculate metrics as specified in measurement_guidance
- Use dimension names from ODD spec as keys
- If ODD dimension can't be measured from available sensors, note in observations

**2. GENERAL OBSERVATIONS** (for safety/reliability/effectiveness context):
- Sensor quality issues: blur, glare, lens artifacts, data gaps
- Environmental anomalies: sudden lighting changes, unusual patterns
- Data source classification: simulation vs real-world
  * Simulation: Perfect textures, uniform lighting, geometric regularity, synthetic appearance
  * Real-world: Natural variations, sensor noise, organic textures, imperfections
- Any other safety-relevant context not captured in ODD measurements

OUTPUT STRUCTURE:
{
  "windows_analyzed": [...],
  "environment_classification": {
    "primary_class": "indoor_office|indoor_corridor|outdoor_urban|etc",
    "confidence": 0.0-1.0,
    "evidence": ["observations"]
  },
  "odd_measurements": {
    // Use ODD dimension names as keys
    // Categorical dimensions: extract classification
    // Numeric dimensions: calculate value
    // Example: "lighting_conditions": "bright", "obstacle_density": 0.35
  },
  "observations": [
    "Data source: simulation (synthetic textures, perfect lighting)",
    "Camera exposure stable across all windows",
    "BEV coverage consistent, no sensor dropouts"
    // Add any safety/reliability/performance notes
  ],
  "per_window_perception": [...]
}
Only output JSON.

PRIORITY: Capture both ODD-aligned measurements AND broader context. The ODD dimensions guide what to look for, but don't restrict observations."""


def create_perception_loop_agent(scenario_path: Path, genai_client: genai.Client, model: str, api_key: str):
    """
    Factory function to create a new PerceptionLoopAgent instance.

    Args:
        scenario_path: Path to scenario directory
        genai_client: Configured Gemini client
        model: Model name to use
        api_key: Google API key

    Returns:
        Configured PerceptionLoopAgent
    """
    list_windows, analyze_window = create_perception_tools(
        scenario_path, genai_client, model)

    return Agent(
        name="PerceptionLoopAgent",
        model=Gemini(model=model, api_key=api_key),
        tools=[list_windows, analyze_window],
        output_key="temp:perception_data",
        instruction=PERCEPTION_LOOP_PROMPT,
    )


def create_perception_summary_agent(api_key: str, model: str):
    """
    Factory function to create a new PerceptionSummaryAgent instance.

    Args:
        api_key: Google API key
        model: Model name to use

    Returns:
        Configured PerceptionSummaryAgent
    """
    return Agent(
        name="PerceptionSummaryAgent",
        model=Gemini(model=model, api_key=api_key),
        output_key="temp:perception_output",
        instruction=PERCEPTION_SUMMARY_PROMPT,
    )
