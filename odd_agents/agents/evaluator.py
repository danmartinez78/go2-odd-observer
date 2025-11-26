"""
Evaluator agent - uses Python tools to construct COD and analyze compliance.
"""

from pathlib import Path
from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.adk.tools import FunctionTool
from google.genai import Client


# Agent version
# v2.0.0: Input is ODD + insights only. Tools read blackboard for measurements.
EVALUATOR_AGENT_VERSION = "2.0.0"


def create_evaluator_tools(scenario_path: Path):
    """Create Python tools for Evaluator Agent."""
    from google.adk.tools.tool_context import ToolContext
    import json

    async def construct_cod_tool(odd_spec: dict, tool_context: ToolContext) -> str:
        """
        Construct COD region and compute ODD/COD distance metrics.

        Reads sensor outputs from blackboard and constructs:
        - Overall COD region (envelope of all measurements)
        - Time series: per-window violation distances and margins
        - Region metrics: aggregate distance, fraction-outside per axis, flagged windows

        Returns JSON with cod_region, time_series, and region_metrics.
        """
        # Read sensor outputs from blackboard via tool_context
        perception_output = tool_context.get_value(
            "temp:perception_output") or {}
        motion_output = tool_context.get_value("temp:motion_output") or {}
        collision_output = tool_context.get_value(
            "temp:collision_output") or {}

        # Call the COD construction function directly with the data from blackboard
        from ..tools.cod_construction import (
            _combine_sensor_outputs,
            _build_cod_region,
            _compute_time_series_metrics,
            _compute_region_metrics
        )

        # Combine per-window measurements from all sensors
        combined_windows = _combine_sensor_outputs(
            perception_output,
            motion_output,
            collision_output
        )

        # Build overall COD region
        cod_region = _build_cod_region(combined_windows, odd_spec)

        # Compute time series metrics (per-window)
        time_series = _compute_time_series_metrics(combined_windows, odd_spec)

        # Compute region metrics (aggregate)
        region_metrics = _compute_region_metrics(
            cod_region, odd_spec, combined_windows)

        result = {
            "cod_region": cod_region,
            "time_series": time_series,
            "region_metrics": region_metrics
        }

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
        instruction="""You evaluate ODD compliance using Python tools for COD computation and LLM reasoning for insights.

INPUT (text summaries only - raw window data is in blackboard, accessed by tools):
- ODD Specification: {temp:odd_spec?}
- Perception insights: {temp:perception_output.temporal_analysis?} {temp:perception_output.summary_insights?}
- Motion insights: {temp:motion_output.temporal_analysis?} {temp:motion_output.summary_insights?}
- Collision insights: {temp:collision_output.temporal_analysis?} {temp:collision_output.summary_insights?}

TOOLS (read raw measurements from blackboard):
- construct_cod_tool(odd_spec): Reads per_window measurements from blackboard, computes COD region + metrics

WORKFLOW:
1. Call construct_cod_tool(odd_spec) - this reads sensor measurements from blackboard
2. Analyze tool output: COD region, violation distances, fraction-outside per axis
3. Interpret sensor insights (temporal_analysis, summary_insights) for context
4. Determine compliance verdict with reasoning

OUTPUT (JSON only, no markdown):
{
  "cod_region": {
    // From construct_cod tool - overall measurement envelope
  },
  "region_metrics": {
    // From construct_cod tool - aggregate distance and fractions
  },
  "compliance_verdict": {
    "verdict": "IN_ODD" | "OUT_ODD" | "BOUNDARY",
    "confidence": 0.0-1.0,
    "rationale": "Reasoning combining COD metrics + sensor insights",
    "critical_axes": ["Axes with largest violations"],
    "temporal_stability": "STABLE" | "DEGRADING" | "IMPROVING"
  },
  "key_concerns": [
    "Issues identified from sensor insights + COD analysis"
  ]
}

RULES:
1. Tool computes COD metrics - you interpret them
2. Sensor insights provide context for violations
3. Verdict based on region_distance and fraction_outside metrics
4. IN_ODD: region_distance < 0.1, no critical violations
5. BOUNDARY: region_distance 0.1-0.3, minor excursions
6. OUT_ODD: region_distance > 0.3, significant violations""",
    )
