"""
Evaluator agent - uses Python tools to construct COD and analyze compliance.

Data flow:
- Loads ODD spec from artifact: odd_spec.json
- Loads sensor outputs from artifacts: perception_output.json, motion_output.json, collision_output.json
- Outputs verdict to state for Report agent
"""

from pathlib import Path
from typing import List
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
# v6.0.0: Verbose output, cross-agent consistency check, collision as advisory only, human/animal proximity
# v6.1.0: Added state refs for cross-window insights (temporal_analysis, summary_insights from sensor agents)
# v6.2.0: Updated state refs to _summary keys, construct_cod_tool saves artifact
# v6.3.0: Explicit "output JSON after tools" instruction for output_key capture
EVALUATOR_AGENT_VERSION = "6.3.0"


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

    def _load_local_json(filename: str) -> dict:
        """Fallback loader for tests or offline runs when artifacts are missing."""
        for candidate in [
            scenario_path / filename,
            scenario_path / "artifacts" / filename,
        ]:
            if candidate.exists():
                try:
                    return json.loads(candidate.read_text())
                except Exception:
                    continue
        return {}

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

            # Fallback to scenario fixture files if artifacts are unavailable
            if not odd_spec:
                odd_spec = _load_local_json("odd_spec.json")
            if not perception_output:
                perception_output = _load_local_json("perception_output.json")
            if not motion_output:
                motion_output = _load_local_json("motion_output.json")
            if not collision_output:
                collision_output = _load_local_json("collision_output.json")

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

            # Save COD construction artifact for post-processing
            try:
                import google.genai.types as gtypes
                json_bytes = json.dumps(result, indent=2).encode('utf-8')
                artifact = gtypes.Part.from_bytes(
                    data=json_bytes, mime_type="application/json")
                version = await tool_context.save_artifact(
                    filename="cod_construction.json", artifact=artifact)
                print(f"🟣 [CONSTRUCT_COD_TOOL] Saved COD artifact v{version}")
            except Exception as e:
                print(f"🟣 [CONSTRUCT_COD_TOOL] Artifact save failed: {e}")

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

    async def save_evaluator_output_tool(
        cod_region: dict,
        region_metrics: dict,
        compliance_verdict: dict,
        per_axis_analysis: dict,
        key_concerns: List[str],
        tool_context
    ) -> dict:
        """Save evaluator output as artifact for archival and Report agent.

        Args:
            cod_region: COD envelope from construct_cod_tool
            region_metrics: Distance metrics from construct_cod_tool
            compliance_verdict: {verdict, confidence, rationale, critical_axes}
            per_axis_analysis: Per-axis analysis dict
            key_concerns: List of key concerns
            tool_context: ADK tool context

        Call this AFTER your analysis to persist results.
        """
        import google.genai.types as gtypes

        print(f"\n🟣 [SAVE_EVALUATOR_OUTPUT] Saving evaluator artifact...")

        try:
            output_data = {
                "cod_region": cod_region,
                "region_metrics": region_metrics,
                "compliance_verdict": compliance_verdict,
                "per_axis_analysis": per_axis_analysis,
                "key_concerns": key_concerns
            }

            json_bytes = json.dumps(output_data, indent=2).encode('utf-8')
            artifact = gtypes.Part.from_bytes(
                data=json_bytes, mime_type="application/json")

            version = await tool_context.save_artifact(
                filename="evaluator_output.json",
                artifact=artifact
            )

            print(f"🟣 [SAVE_EVALUATOR_OUTPUT] Saved artifact v{version}")

            # Return full data so it gets captured in agent output
            return output_data
        except Exception as e:
            print(f"🟣 [SAVE_EVALUATOR_OUTPUT] Error: {e}")
            return {"status": "error", "message": str(e)}

    # Only return construct_cod_tool - keep it simple
    # Model must output JSON text for output_key to capture it
    return [
        FunctionTool(func=construct_cod_tool),
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
        output_key="evaluator_output",
        instruction="""ODD Compliance Evaluator - Analyze COD vs ODD and output verdict.

## MANDATORY WORKFLOW

1. Call construct_cod_tool() (no parameters)
2. Analyze the results  
3. **OUTPUT JSON TEXT** (REQUIRED - pipeline fails without text output)

## INPUT
- Perception: {perception_summary}
- Motion: {motion_summary}
- Collision: {collision_summary}

## AFTER TOOL CALL - OUTPUT THIS JSON:

{
  "cod_region": <from tool>,
  "region_metrics": <from tool>,
  "compliance_verdict": {
    "verdict": "IN_ODD|BOUNDARY|OUT_ODD",
    "confidence": 0.0-1.0,
    "rationale": "specific values + reasoning",
    "critical_axes": []
  },
  "collision_advisory": {
    "collisions_detected": 0,
    "note": "Advisory only"
  },
  "key_concerns": []
}

## VERDICT RULES
- IN_ODD: region_distance < 0.1
- BOUNDARY: 0.1-0.3
- OUT_ODD: > 0.3
- Human proximity <1m → OUT_ODD
- Collision is ADVISORY ONLY (doesn't affect verdict)

CRITICAL: Output RAW JSON only. Do NOT wrap in ```json``` markdown blocks.""",
    )
