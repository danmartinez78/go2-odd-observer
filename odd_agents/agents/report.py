"""
Report generation agent.
Hybrid approach: Python tool computes statistics, LLM synthesizes insights.
"""

from pathlib import Path
from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.adk.tools import FunctionTool
import json


# Agent version
# v5.0.0: Hybrid approach - Python statistics tool + LLM synthesis
# v6.0.0: Synthesis-focused - LLM interprets/synthesizes, no copying data
REPORT_AGENT_VERSION = "6.0.0"


def create_report_tools(scenario_path: Path):
    """Create report tools: statistics computation + data reading."""
    from google.adk.tools.tool_context import ToolContext
    import json

    async def compute_report_statistics_tool(tool_context: ToolContext) -> str:
        """
        Compute comprehensive statistics from all pipeline outputs.

        This Python tool deterministically computes:
        - Window counts and coverage
        - Per-agent health metrics (empty data, missing fields)
        - Measurement statistics (min/max/mean for numeric axes)
        - Compliance summary statistics
        - Data quality flags

        Returns JSON with statistics for LLM to interpret.
        """
        # Read all agent outputs from blackboard
        odd_spec = tool_context.get_value("temp:odd_spec") or {}
        perception = tool_context.get_value("temp:perception_output") or {}
        motion = tool_context.get_value("temp:motion_output") or {}
        collision = tool_context.get_value("temp:collision_output") or {}
        evaluator = tool_context.get_value("temp:evaluator_output") or {}

        # =====================================================================
        # SECTION 1: Window Statistics
        # =====================================================================
        perception_windows = perception.get(
            "per_window", perception.get("per_window_measurements", []))
        motion_windows = motion.get(
            "per_window", motion.get("per_window_measurements", []))
        collision_windows = collision.get(
            "per_window", collision.get("per_window_measurements", []))

        window_stats = {
            "total_windows": len(perception_windows),
            "perception_windows": len(perception_windows),
            "motion_windows": len(motion_windows),
            "collision_windows": len(collision_windows),
            "window_ids": [w.get("window_id", "") for w in perception_windows],
        }

        # =====================================================================
        # SECTION 2: Per-Agent Health Metrics
        # =====================================================================
        agent_health = {}

        # Perception health
        perception_empty = [w["window_id"] for w in perception_windows
                            if not w.get("measurements")]
        agent_health["perception"] = {
            "windows_processed": len(perception_windows),
            "empty_windows": perception_empty,
            "has_temporal_analysis": bool(perception.get("temporal_analysis")),
            "has_summary_insights": bool(perception.get("summary_insights")),
            "status": "OK" if not perception_empty else f"WARNING: {len(perception_empty)} empty windows",
        }

        # Motion health
        motion_empty = [w["window_id"] for w in motion_windows
                        if not w.get("measurements")]
        zero_accel_windows = [w["window_id"] for w in motion_windows
                              if w.get("measurements", {}).get("max_accel_mps2", 0) == 0]
        agent_health["motion"] = {
            "windows_processed": len(motion_windows),
            "empty_windows": motion_empty,
            "zero_acceleration_windows": zero_accel_windows,
            "has_temporal_analysis": bool(motion.get("temporal_analysis")),
            "status": "OK" if not motion_empty and not zero_accel_windows
            else f"WARNING: {len(motion_empty)} empty, {len(zero_accel_windows)} zero-accel",
        }

        # Collision health
        collision_empty = [w["window_id"] for w in collision_windows
                           if not w.get("measurements")]
        collision_detected_windows = [w["window_id"] for w in collision_windows
                                      if w.get("measurements", {}).get("collision_detected", 0) == 1]
        agent_health["collision"] = {
            "windows_processed": len(collision_windows),
            "empty_windows": collision_empty,
            "collision_detected_windows": collision_detected_windows,
            "collision_count": len(collision_detected_windows),
            "status": "OK" if not collision_empty else f"WARNING: {len(collision_empty)} empty windows",
        }

        # Evaluator health
        agent_health["evaluator"] = {
            "has_cod_region": bool(evaluator.get("cod_region")),
            "has_compliance_verdict": bool(evaluator.get("compliance_verdict")),
            "verdict": evaluator.get("compliance_verdict", {}).get("verdict", "UNKNOWN"),
            "confidence": evaluator.get("compliance_verdict", {}).get("confidence", 0),
            "status": "OK" if evaluator.get("compliance_verdict") else "ERROR: No verdict",
        }

        # =====================================================================
        # SECTION 3: Measurement Statistics (numeric axes)
        # =====================================================================
        measurement_stats = {}

        # Collect all numeric measurements across windows
        all_measurements = {}
        for windows in [perception_windows, motion_windows, collision_windows]:
            for w in windows:
                for key, value in w.get("measurements", {}).items():
                    if isinstance(value, (int, float)):
                        if key not in all_measurements:
                            all_measurements[key] = []
                        all_measurements[key].append(value)

        # Compute stats for each measurement
        for key, values in all_measurements.items():
            if values:
                measurement_stats[key] = {
                    "min": round(min(values), 4),
                    "max": round(max(values), 4),
                    "mean": round(sum(values) / len(values), 4),
                    "samples": len(values),
                }

        # =====================================================================
        # SECTION 4: Compliance Summary
        # =====================================================================
        compliance_verdict = evaluator.get("compliance_verdict", {})
        region_metrics = evaluator.get("region_metrics", {})

        compliance_stats = {
            "verdict": compliance_verdict.get("verdict", "UNKNOWN"),
            "confidence": compliance_verdict.get("confidence", 0),
            "temporal_stability": compliance_verdict.get("temporal_stability", "UNKNOWN"),
            "critical_axes": compliance_verdict.get("critical_axes", []),
            "critical_axes_count": len(compliance_verdict.get("critical_axes", [])),
            "region_distance": region_metrics.get("region_distance"),
            "windows_violated": region_metrics.get("windows_violated", []),
            "violation_count": len(region_metrics.get("windows_violated", [])),
        }

        # =====================================================================
        # SECTION 5: Data Quality Flags
        # =====================================================================
        data_quality = {
            "all_agents_healthy": all(
                h.get("status", "").startswith("OK")
                for h in agent_health.values()
            ),
            "missing_data_warnings": [],
            "anomalies": [],
        }

        # Check for missing data
        if not perception_windows:
            data_quality["missing_data_warnings"].append("No perception data")
        if not motion_windows:
            data_quality["missing_data_warnings"].append("No motion data")
        if not collision_windows:
            data_quality["missing_data_warnings"].append("No collision data")
        if not evaluator.get("compliance_verdict"):
            data_quality["missing_data_warnings"].append(
                "No compliance verdict")

        # Check for anomalies
        if collision_detected_windows:
            data_quality["anomalies"].append(
                f"Collisions detected in windows: {collision_detected_windows}"
            )
        if zero_accel_windows and len(zero_accel_windows) == len(motion_windows):
            data_quality["anomalies"].append(
                "All windows show zero acceleration - possible sensor issue"
            )

        # =====================================================================
        # SECTION 6: ODD Specification Summary
        # =====================================================================
        odd_summary = {
            "has_environment": bool(odd_spec.get("odd_specification", {}).get("environment")),
            "has_ego": bool(odd_spec.get("odd_specification", {}).get("ego")),
            "has_actors": bool(odd_spec.get("odd_specification", {}).get("actors")),
        }

        # Count axes by type
        axis_counts = {"range": 0, "enum": 0, "bool": 0}
        for domain in ["environment", "actors", "ego"]:
            domain_spec = odd_spec.get("odd_specification", {}).get(domain, {})
            for category in ["numeric", "categorical", "boolean"]:
                for axis_name, axis_spec in domain_spec.get(category, {}).items():
                    axis_type = axis_spec.get("type", "unknown")
                    if axis_type in axis_counts:
                        axis_counts[axis_type] += 1
        odd_summary["axis_counts"] = axis_counts
        odd_summary["total_axes"] = sum(axis_counts.values())

        # =====================================================================
        # SECTION 7: Temporal Insights Summary
        # =====================================================================
        temporal_summary = {
            "perception_trends": perception.get("temporal_analysis", {}).get("odd_trends", ""),
            "motion_trends": motion.get("temporal_analysis", {}).get("odd_trends", ""),
            "collision_trends": collision.get("temporal_analysis", {}).get("odd_trends", ""),
            "perception_concerns": perception.get("temporal_analysis", {}).get("concerns", []),
            "motion_concerns": motion.get("temporal_analysis", {}).get("concerns", []),
            "collision_concerns": collision.get("temporal_analysis", {}).get("concerns", []),
        }

        # Aggregate all concerns
        all_concerns = (
            temporal_summary["perception_concerns"] +
            temporal_summary["motion_concerns"] +
            temporal_summary["collision_concerns"]
        )
        temporal_summary["total_concerns"] = len(all_concerns)
        temporal_summary["all_concerns"] = all_concerns

        # =====================================================================
        # ASSEMBLE FINAL STATISTICS
        # =====================================================================
        statistics = {
            "window_stats": window_stats,
            "agent_health": agent_health,
            "measurement_stats": measurement_stats,
            "compliance_stats": compliance_stats,
            "data_quality": data_quality,
            "odd_summary": odd_summary,
            "temporal_summary": temporal_summary,
        }

        return json.dumps(statistics, indent=2)

    async def get_sensor_insights_tool(tool_context: ToolContext) -> str:
        """
        Get high-level insights from sensor agents (not raw data).

        Returns summary_insights and key concerns - minimal token footprint.
        """
        perception = tool_context.get_value("temp:perception_output") or {}
        motion = tool_context.get_value("temp:motion_output") or {}
        collision = tool_context.get_value("temp:collision_output") or {}
        evaluator = tool_context.get_value("temp:evaluator_output") or {}

        insights = {
            "perception_insights": perception.get("summary_insights", []),
            "motion_insights": motion.get("summary_insights", []),
            "collision_insights": collision.get("summary_insights", []),
            "evaluator_concerns": evaluator.get("key_concerns", []),
            "evaluator_rationale": evaluator.get("compliance_verdict", {}).get("rationale", ""),
        }

        return json.dumps(insights, indent=2)

    # Return FunctionTool wrappers
    return [
        FunctionTool(func=compute_report_statistics_tool),
        FunctionTool(func=get_sensor_insights_tool),
    ]


def create_report_agent(scenario_path: Path, api_key: str, model: str) -> Agent:
    """Create a new ReportAgent instance with statistics tool."""
    tools = create_report_tools(scenario_path)

    return Agent(
        name="ReportAgent",
        model=Gemini(model=model, api_key=api_key),
        tools=tools,
        instruction="""You generate executive summary reports by SYNTHESIZING insights from computed statistics.

YOUR ROLE: Interpret and synthesize - DO NOT copy raw data fields.

TOOLS:
1. compute_report_statistics_tool() - Returns:
   - window_stats: how many windows analyzed
   - agent_health: per-agent status (OK/WARNING), empty windows, issues
   - measurement_stats: min/max/mean for numeric measurements
   - compliance_stats: verdict, confidence, stability
   - data_quality: flags for missing data, anomalies
   - temporal_summary: trends and concerns

2. get_sensor_insights_tool() - Returns qualitative insights from each sensor agent

WORKFLOW:
1. Call compute_report_statistics_tool() first
2. Call get_sensor_insights_tool() for qualitative context
3. SYNTHESIZE (don't copy) the information into your output

OUTPUT (JSON only, no markdown):
{
  "scenario_overview": "<1-2 sentences describing what the robot was doing and where>",
  
  "compliance_verdict": "<IN_ODD | OUT_OF_ODD | BORDERLINE>",
  "confidence": "<HIGH | MEDIUM | LOW based on confidence value: >0.8=HIGH, 0.5-0.8=MEDIUM, <0.5=LOW>",
  "stability": "<STABLE | UNSTABLE | TRANSITIONING based on temporal_stability>",
  
  "key_observations": [
    "<Most significant finding from perception - synthesize, include relevant numbers>",
    "<Most significant finding from motion - synthesize, include relevant numbers>",
    "<Most significant finding from collision/safety - synthesize, include relevant numbers>"
  ],
  
  "recommendations": [
    "<Action item if issues found, OR 'No action required - operation within ODD' if compliant>",
    "<Additional recommendation if warranted>"
  ],
  
  "pipeline_quality_assessment": "<1 sentence summarizing agent health and data quality. Examples: 'All agents executed successfully with complete data across N windows.' OR 'Motion agent reported N windows with zero acceleration - potential sensor issue.'>"
}

SYNTHESIS RULES:
1. scenario_overview: Describe the scene and robot behavior in plain English
2. key_observations: Interpret the data - what does it MEAN? Include specific numbers for context
3. recommendations: What should the operator DO based on findings?
4. pipeline_quality_assessment: Summarize agent_health and data_quality in one sentence
5. DO NOT include raw data structures - Python post-processing adds those
6. Keep total output concise - this is an EXECUTIVE summary""",
    )
