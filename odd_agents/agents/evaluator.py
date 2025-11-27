"""
Evaluator agent - uses Python tools to construct COD and analyze compliance.

Data flow:
- Loads ODD spec from artifact: odd_spec.json
- Loads sensor outputs from artifacts: perception_output.json, motion_output.json, collision_output.json
- Outputs verdict to state for Report agent
"""

from pathlib import Path
from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.adk.tools import FunctionTool
from google.genai import Client


# Agent version
# v2.1.0: Added try/catch for robust error handling in tools
# v2.2.0: Strengthened prompt with explicit tool calling instructions for 2.5-pro
# v3.0.0: Load sensor outputs from artifacts instead of state (fixes data handoff)
# v4.0.0: Tool takes no parameters - loads ODD spec from state automatically
# v5.0.0: Load ODD spec from artifact (consistent artifact pattern)
# v5.1.0: Knowledge grounding hook via manifest (fundamentals/overlays), artifacts remain authority
EVALUATOR_AGENT_VERSION = "5.1.0"


def _load_artifact_json(artifact) -> dict:
    """Helper to extract JSON from artifact."""
    import json
    if artifact and hasattr(artifact, 'inline_data') and artifact.inline_data:
        raw_data = artifact.inline_data.data
        if isinstance(raw_data, bytes):
            return json.loads(raw_data.decode('utf-8'))
        return json.loads(raw_data)
    return {}


def create_evaluator_tools(scenario_path: Path):
    """Create Python tools for Evaluator Agent."""
    from google.adk.tools.tool_context import ToolContext
    import json

    async def construct_cod_tool(tool_context: ToolContext) -> str:
        """
        Construct COD region and compute ODD/COD distance metrics.

        Loads ALL data from ARTIFACTS (ODD spec + sensor outputs), then constructs:
        - Overall COD region (envelope of all measurements)
        - Time series: per-window violation distances and margins
        - Region metrics: aggregate distance, fraction-outside per axis, flagged windows

        Returns JSON with cod_region, time_series, and region_metrics.
        """
        print("\n🟣 [CONSTRUCT_COD_TOOL] Called - loading 4 artifacts...")

        try:
            # === Load ODD spec from ARTIFACT ===
            odd_spec = {}
            try:
                odd_artifact = await tool_context.load_artifact(filename="odd_spec.json")
                odd_spec = _load_artifact_json(odd_artifact)
                domains = list(odd_spec.get('odd_specification', {}).keys())
                print(f"🟣 [CONSTRUCT_COD_TOOL] Loaded ODD spec: {domains}")
            except Exception as e:
                print(f"🟣 [CONSTRUCT_COD_TOOL] Could not load ODD spec: {e}")

            # === Load sensor outputs from ARTIFACTS ===
            perception_output = {}
            motion_output = {}
            collision_output = {}

            try:
                p_artifact = await tool_context.load_artifact(filename="perception_output.json")
                perception_output = _load_artifact_json(p_artifact)
                print(
                    f"🟣 [CONSTRUCT_COD_TOOL] Loaded perception: {len(perception_output.get('per_window', []))} windows")
            except Exception as e:
                print(f"🟣 [CONSTRUCT_COD_TOOL] Could not load perception: {e}")

            try:
                m_artifact = await tool_context.load_artifact(filename="motion_output.json")
                motion_output = _load_artifact_json(m_artifact)
                print(
                    f"🟣 [CONSTRUCT_COD_TOOL] Loaded motion: {len(motion_output.get('per_window', []))} windows")
            except Exception as e:
                print(f"🟣 [CONSTRUCT_COD_TOOL] Could not load motion: {e}")

            try:
                c_artifact = await tool_context.load_artifact(filename="collision_output.json")
                collision_output = _load_artifact_json(c_artifact)
                print(
                    f"🟣 [CONSTRUCT_COD_TOOL] Loaded collision: {len(collision_output.get('per_window', []))} windows")
            except Exception as e:
                print(f"🟣 [CONSTRUCT_COD_TOOL] Could not load collision: {e}")

            # === Construct COD ===
            from ..tools.cod_construction import (
                _combine_sensor_outputs,
                _build_cod_region,
                _compute_time_series_metrics,
                _compute_region_metrics,
                _flatten_odd_spec
            )

            # Flatten nested ODD spec to flat axis dictionary
            flat_odd_spec = _flatten_odd_spec(odd_spec)
            print(
                f"🟣 [CONSTRUCT_COD_TOOL] Flat ODD spec: {len(flat_odd_spec)} axes")

            # Default weights (equal weight for all axes)
            weights = {k: 1.0 for k in flat_odd_spec.keys()}

            # Combine per-window measurements from all sensors
            combined_windows = _combine_sensor_outputs(
                perception_output,
                motion_output,
                collision_output
            )
            print(
                f"🟣 [CONSTRUCT_COD_TOOL] Combined: {len(combined_windows)} windows")

            # Build overall COD region
            cod_region = _build_cod_region(combined_windows, flat_odd_spec)

            # Compute time series metrics (per-window)
            time_series = _compute_time_series_metrics(
                combined_windows, flat_odd_spec, weights)

            # Compute region metrics (aggregate)
            region_metrics = _compute_region_metrics(
                cod_region, flat_odd_spec, time_series, weights)

            result = {
                "cod_region": cod_region,
                "time_series": time_series,
                "region_metrics": region_metrics,
                "artifacts_loaded": {
                    "odd_spec": bool(odd_spec),
                    "perception": bool(perception_output),
                    "motion": bool(motion_output),
                    "collision": bool(collision_output),
                }
            }

            print(f"🟣 [CONSTRUCT_COD_TOOL] COD region: {len(cod_region)} axes")
            print(
                f"🟣 [CONSTRUCT_COD_TOOL] Region distance: {region_metrics.get('region_distance', 'N/A')}")

            return json.dumps(result, indent=2)

        except Exception as e:
            import traceback
            print(f"🟣 [CONSTRUCT_COD_TOOL] Error: {e}")
            print(
                f"🟣 [CONSTRUCT_COD_TOOL] Traceback: {traceback.format_exc()}")

            return json.dumps({
                "status": "error",
                "error": str(e),
                "cod_region": {},
                "time_series": {},
                "region_metrics": {},
                "message": "COD construction failed - proceed with qualitative assessment only"
            }, indent=2)

    async def get_window_details_tool(window_id: str) -> str:
        """
        Get detailed measurements for a specific window.

        Useful for investigating violations or boundary cases.
        Returns per-window measurements from all sensor agents.
        """
        import json

        scenario = Path(scenario_path)

        # Read sensor outputs from files (fallback for debugging)
        outputs = {}
        for agent in ["perception", "motion", "collision"]:
            output_file = scenario / f"{agent}_output.json"
            if output_file.exists():
                with open(output_file, 'r') as f:
                    data = json.load(f)
                    for window in data.get("per_window", []):
                        if window["window_id"] == window_id:
                            outputs[agent] = window
                            break

        return json.dumps({
            "window_id": window_id,
            "sensor_measurements": outputs
        }, indent=2)

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
        instruction="""You are the ODD Compliance Evaluator. Your job is to construct the COD (Current Operating Domain) and determine compliance.

KNOWLEDGE (if available): Use ref:knowledge_manifest to consult fundamentals (ODD/COD definitions, verdict rules) and any robot/app overlays for terminology alignment. Artifacts (ODD spec + sensor outputs) remain the source of truth for constraints and measurements.

**TERMINOLOGY:**
- ODD = Operational Design Domain (the safe operating envelope)
- COD = Current Operating Domain (what was actually observed)

**CRITICAL: You MUST call construct_cod_tool() before producing any output.**

## STEP 1: CALL THE TOOL (MANDATORY)

Call construct_cod_tool() with NO PARAMETERS - it loads everything from artifacts automatically.

The tool will return:
- cod_region: Envelope of all measurements across windows
- time_series: Per-window violation distances
- region_metrics: Aggregate distance scores and fractions outside ODD

## STEP 2: INTERPRET RESULTS

After receiving tool output, analyze:
1. region_metrics.region_distance: Overall COD distance from ODD boundary
2. region_metrics.fraction_outside_per_axis: Which axes have violations
3. region_metrics.windows_violated: Which windows exceeded ODD limits
4. time_series: Temporal pattern of violations

Also consider sensor insights from the pipeline for context.

## STEP 3: OUTPUT JSON (MANDATORY FORMAT)

After tool call completes, output this EXACT JSON structure:

{
  "cod_region": <COPY FROM TOOL OUTPUT>,
  "region_metrics": <COPY FROM TOOL OUTPUT>,
  "compliance_verdict": {
    "verdict": "IN_ODD" or "OUT_ODD" or "BOUNDARY",
    "confidence": <0.0 to 1.0>,
    "rationale": "<Your reasoning combining metrics + insights>",
    "critical_axes": ["<axis names with violations>"],
    "temporal_stability": "STABLE" or "DEGRADING" or "IMPROVING"
  },
  "key_concerns": [
    "<Concern 1 from analysis>",
    "<Concern 2 if any>"
  ]
}

## VERDICT THRESHOLDS

- IN_ODD: region_distance < 0.1, COD comfortably within ODD
- BOUNDARY: region_distance 0.1-0.3, COD at or near edge of ODD limits
- OUT_ODD: region_distance > 0.3, COD exceeds ODD limits

## RULES

1. **ALWAYS call construct_cod_tool() first** - no parameters needed
2. Copy cod_region and region_metrics directly from tool output
3. Provide clear rationale explaining your verdict (use "Current Operating Domain" not "Conditions of Operation Domain")
4. Output pure JSON only - no markdown code blocks""",
    )
