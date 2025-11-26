"""
Evaluator agent - uses Python tools to construct COD and analyze compliance.
"""

from pathlib import Path
from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.genai import Client
from pydantic import BaseModel, Field


# Agent version
EVALUATOR_AGENT_VERSION = "1.0.0"


class ConstructCODInput(BaseModel):
    """Input for construct_cod_from_sensor_outputs tool."""
    scenario_path: str = Field(
        description="Absolute path to scenario directory")
    odd_spec: dict = Field(
        description="Full ODD specification with type definitions")


class GetWindowInput(BaseModel):
    """Input for get_window_details tool."""
    scenario_path: str = Field(
        description="Absolute path to scenario directory")
    window_id: str = Field(description="Window ID to inspect (e.g., '007')")


def create_evaluator_tools(scenario_path: Path):
    """Create Python tools for Evaluator Agent."""
    from ..tools.cod_construction import construct_cod_from_sensor_outputs
    import json

    def construct_cod_tool(scenario_path: str, odd_spec: dict) -> str:
        """
        Construct COD region and compute ODD/COD distance metrics.

        Reads per-window measurements from sensor agents (perception/motion/collision)
        and constructs:
        - Overall COD region (envelope of all measurements)
        - Time series: per-window violation distances and margins
        - Region metrics: aggregate distance, fraction-outside per axis, flagged windows

        Returns JSON with cod_region, time_series, and region_metrics.
        """
        result = construct_cod_from_sensor_outputs(scenario_path, odd_spec)
        return json.dumps(result, indent=2)

    def get_window_details_tool(scenario_path: str, window_id: str) -> str:
        """
        Get detailed measurements for a specific window.

        Useful for investigating violations or boundary cases.
        Returns per-window measurements from all sensor agents.
        """
        from pathlib import Path
        import json

        scenario = Path(scenario_path)

        # Read sensor outputs
        outputs = {}
        for agent in ["perception", "motion", "collision"]:
            output_file = scenario / f"{agent}_output.json"
            if output_file.exists():
                with open(output_file, 'r') as f:
                    data = json.load(f)
                    # Find measurements for this window
                    for window in data.get("per_window_measurements", []):
                        if window["window_id"] == window_id:
                            outputs[agent] = window
                            break

        return json.dumps({
            "window_id": window_id,
            "sensor_measurements": outputs
        }, indent=2)

    # Create ADK tools with Pydantic models
    from google.adk.tools import Tool

    construct_cod = Tool(
        name="construct_cod_from_sensor_outputs",
        description="Construct COD region and compute ODD/COD distance metrics from sensor outputs",
        parameters=ConstructCODInput,
        callable=construct_cod_tool
    )

    get_window = Tool(
        name="get_window_details",
        description="Get detailed measurements for a specific window to investigate violations",
        parameters=GetWindowInput,
        callable=get_window_details_tool
    )

    return [construct_cod, get_window]


def create_evaluator_agent(
    scenario_path: Path, genai_client: Client, model: str, api_key: str
) -> Agent:
    """Create Evaluator Agent with COD construction tools."""
    tools = create_evaluator_tools(scenario_path)

    return Agent(
        name="EvaluatorAgent",
        model=Gemini(model=model, api_key=api_key),
        tools=tools,
        output_key="temp:evaluator_output",
        instruction="""You analyze ODD compliance using Python tools for COD construction.

INPUT:
- ODD Specification (v5.0.0): {temp:odd_spec?} - includes type definitions (range/bool/enum)
- Sensor outputs: Perception, Motion, Collision per-window measurements (in files)
- Tools: construct_cod_from_sensor_outputs, get_window_details

TASKS:
1. Call construct_cod_from_sensor_outputs(scenario_path, odd_spec)
2. Analyze COD construction results:
   - Overall COD region vs ODD specification
   - Region distance (how far COD diverges from ODD)
   - Per-axis fraction-outside (which dimensions violate most)
   - Time series: when violations occur, margins over time
3. Investigate violations:
   - Identify flagged windows from region_metrics
   - Use get_window_details(window_id) to inspect specific violations
   - Analyze temporal patterns (do violations cluster? trend worse?)
4. Compliance assessment:
   - Overall verdict: IN_ODD, OUT_ODD, or BOUNDARY
   - Critical violations vs minor excursions
   - Temporal stability of compliance

OUTPUT (JSON only, no markdown):
{
  "cod_region": {
    // From construct_cod tool - overall envelope
  },
  "region_metrics": {
    // From construct_cod tool - aggregate distance and fractions
  },
  "time_series_analysis": {
    "violation_patterns": "<temporal clustering, trends, stability>",
    "critical_windows": ["<window_ids with significant violations>"],
    "margin_trends": "<how close to boundary over time>"
  },
  "compliance_verdict": {
    "overall": "IN_ODD" | "OUT_ODD" | "BOUNDARY",
    "rationale": "<reasoning based on region distance and violations>",
    "critical_axes": ["<axes with largest fraction-outside>"],
    "temporal_stability": "STABLE" | "DEGRADING" | "IMPROVING"
  }
}

Use Python tools for computation. Focus on interpreting results and providing actionable insights.""",
    )
