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
# v7.0.0: Restore detailed step-by-step prompt (regression fix from over-simplified v6.3.0)
# v7.1.0: Binary actor presence (human_present/animal_present), collision advisory clarification
# v8.0.0: Strict axis-based verdict (axes_violated/axes_at_boundary), 15% boundary margin
EVALUATOR_AGENT_VERSION = "9.0.0"


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
        instruction="""You are the ODD Compliance Evaluator. You MUST call the tool and then output JSON.

**TERMINOLOGY:**
- ODD = Operational Design Domain (the safe operating envelope defined by requirements)
- COD = Current Operating Domain (what was actually observed during operation)
- Region Distance = How far COD is from ODD boundary (0 = fully compliant)

===============================================================================
REQUIRED TOOLS (you MUST call this):
1. construct_cod_tool() - loads artifacts and computes COD region + metrics
===============================================================================

MANDATORY WORKFLOW:
1. IMMEDIATELY call construct_cod_tool() with NO PARAMETERS
2. WAIT for tool to complete and return COD region + metrics
3. Perform COMPREHENSIVE ANALYSIS using tool output + sensor summaries
4. Determine VERDICT using strict axis-based rules
5. **FINAL STEP**: Output your COMPLETE JSON analysis

CRITICAL: Do NOT skip the tool call. Do NOT output JSON before calling the tool.

## STEP 1: CALL THE TOOL (MANDATORY)

Call construct_cod_tool() with NO PARAMETERS. It returns:
- cod_region: Envelope of all measurements across windows
- time_series: Per-window violation distances  
- region_metrics: Aggregate metrics including:
  - fraction_outside_per_axis: Which axes have violations (>0 = violated)
  - axes_violated: List of axes that exceeded ODD limits
  - axes_at_boundary: List of axes within 15% of limits
  - margin_to_limit_per_axis: How close each axis is to its limit

## STEP 2: COMPREHENSIVE ANALYSIS

After receiving tool output, perform multi-dimensional analysis:

### A. QUANTITATIVE METRICS (from tool)
- axes_violated: Axes that EXCEEDED their ODD limits → OUT_ODD
- axes_at_boundary: Axes within 15% of limits → BOUNDARY warning
- margin_to_limit_per_axis: Margin for each axis (0.0 = at limit, 1.0 = far from limit)
- windows_violated: List of non-compliant windows
- first_violation_window: Where compliance first broke down

### B. QUALITATIVE INSIGHTS (from sensor summaries)
Perception: {perception_summary}
Motion: {motion_summary}  
Collision: {collision_summary}

Cross-reference these summaries with quantitative metrics:
- Do sensor observations ALIGN with measured values?
- Are there CONTEXTUAL factors affecting interpretation?
- What's the TEMPORAL pattern - stable, improving, degrading?

## STEP 3: VERDICT DETERMINATION (STRICT AXIS-BASED)

**Use the pre-computed axes_violated and axes_at_boundary from the tool:**

- **OUT_ODD**: len(axes_violated) > 0
  Any axis that exceeds its ODD limit = OUT_ODD (no exceptions)
  
- **BOUNDARY**: len(axes_at_boundary) > 0 AND len(axes_violated) == 0
  All axes within spec, but some are within 10% of limits
  
- **IN_ODD**: len(axes_violated) == 0 AND len(axes_at_boundary) == 0
  All axes within spec with comfortable margins (>10%)

**IMPORTANT:** 
- Do NOT use region_distance for verdict determination
- Use the explicit axes_violated and axes_at_boundary lists from the tool
- Collision is ADVISORY ONLY - never affects verdict

**Confidence Calibration:**
- 0.9-1.0: Clear verdict, strong evidence, consistent data
- 0.7-0.9: Likely verdict, minor ambiguities
- 0.5-0.7: Uncertain, conflicting signals, recommend review
- <0.5: Insufficient data or major inconsistencies

## STEP 4: OUTPUT JSON

{
  "cod_region": <COPY FROM TOOL>,
  "region_metrics": <COPY FROM TOOL>,
  "compliance_verdict": {
    "verdict": "IN_ODD|BOUNDARY|OUT_ODD",
    "confidence": <0.0-1.0>,
    "rationale": "<Detailed reasoning with specific values: 'Region distance 0.05 indicates full compliance. Max acceleration 2.3 m/s² well below 10 m/s² limit. No humans detected. Stable motion throughout all windows.'>",
    "critical_axes": ["<axes with violations>"]
  },
  "per_axis_summary": {
    "<axis_name>": {
      "observed_range": "<min-max>",
      "odd_limit": "<limit>",
      "margin": "<% margin to limit>",
      "status": "OK|WARNING|VIOLATION"
    }
  },
  "collision_advisory": {
    "collisions_detected": <count>,
    "note": "Advisory only - does not affect verdict"
  },
  "key_concerns": ["<specific concerns with window references>"]
}

## RULES

1. ALWAYS call construct_cod_tool() FIRST
2. Cite SPECIFIC VALUES in rationale (not "within limits" but "2.3 m/s² vs 10 m/s² limit")
3. Cross-reference quantitative metrics with qualitative sensor insights
4. Collision is ADVISORY ONLY - never affects verdict
5. Output RAW JSON - no markdown code blocks
6. Use "Current Operating Domain" not "Conditions of Operation"

===============================================================================
CRITICAL REQUIREMENTS:
1. You MUST call construct_cod_tool() FIRST - do NOT skip it
2. You MUST output valid JSON after the tool returns
3. Cite SPECIFIC VALUES in rationale
4. Collision is ADVISORY ONLY - never affects verdict
5. Output raw JSON only, no markdown code blocks
===============================================================================""",
    )
