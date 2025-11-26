"""
Evaluator agent - uses Python tools to construct COD and analyze compliance.
"""

from pathlib import Path
from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.adk.tools import FunctionTool
from google.genai import Client


# Agent version
EVALUATOR_AGENT_VERSION = "1.0.0"


def create_evaluator_tools(scenario_path: Path):
    """Create Python tools for Evaluator Agent."""
    from ..tools.cod_construction import construct_cod_from_sensor_outputs
    import json

    async def construct_cod_tool(odd_spec: dict) -> str:
        """
        Construct COD region and compute ODD/COD distance metrics.

        Reads per-window measurements from sensor agents (perception/motion/collision)
        and constructs:
        - Overall COD region (envelope of all measurements)
        - Time series: per-window violation distances and margins
        - Region metrics: aggregate distance, fraction-outside per axis, flagged windows

        Returns JSON with cod_region, time_series, and region_metrics.
        """
        result = construct_cod_from_sensor_outputs(
            str(scenario_path), odd_spec)
        return json.dumps(result, indent=2)

    async def get_window_details_tool(window_id: str) -> str:
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

    # Return FunctionTool wrappers
    return [
        FunctionTool(func=construct_cod_tool),
        FunctionTool(func=get_window_details_tool)
    ]


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
- Tools: construct_cod_from_sensor_outputs(odd_spec), get_window_details(window_id)

TASKS:
1. Call construct_cod_from_sensor_outputs(odd_spec) with ODD specification
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
