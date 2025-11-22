"""
Perception analysis agents.
Factory functions that create agents with specific configuration.
"""

from pathlib import Path
from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google import genai

from ..tools.perception import create_perception_tools


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
        instruction="""You orchestrate perception analysis across all scenario windows.

Steps you MUST follow:
1. Call list_windows_tool() exactly once to get the ordered window_id list.
2. For each window_id returned (in that order), call analyze_window_perception_tool(window_id=...).
3. Collect each tool response exactly as returned.
4. After all windows are processed, respond with JSON:
{
  "windows_analyzed": ["..."],
  "per_window_perception": [<tool_response_objects_in_order>]
}
Do not add commentary. Ensure valid JSON.""",
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
        instruction="""You finalize the ODD perception report.

Input data from the previous agent:
{temp:perception_data?}

If no data is provided, respond with:
{"error": "missing_perception_data"}

Otherwise:
1. Read the JSON string carefully.
2. Determine overall environment class (choose from: indoor_office, indoor_corridor, indoor, outdoor_urban, outdoor_natural, open_space).
3. **CLASSIFY DATA SOURCE**: Analyze image and sensor characteristics to determine if data is from simulation or real-world:
   - Simulation indicators: Perfect textures, uniform lighting, geometric regularity, lack of noise, synthetic appearance
   - Real-world indicators: Natural lighting variations, sensor noise, organic textures, imperfections
4. Produce final JSON:
{
  "windows_analyzed": [...],
  "environment_classification": {
    "primary_class": "one_of_allowed_values",
    "confidence": 0.0-1.0,
    "evidence": ["short", "observations"]
  },
  "data_source_classification": {
    "source": "simulation|real_world",
    "confidence": 0.0-1.0,
    "evidence": ["indicators", "observed"]
  },
  "per_window_perception": [...]
}
Only output JSON.

NOTE: This data source classification will flow through the entire pipeline to the final report.""",
    )
