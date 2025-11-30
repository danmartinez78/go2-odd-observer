"""
Report builder - Post-pipeline report assembly.

This module handles report generation AFTER the ADK pipeline completes.

Architecture (Phase 1.6):
- ARTIFACTS: Full per-window data from tools (odd_spec.json, perception_analysis.json, etc.)
- SESSION STATE: Agent summaries with temporal analysis (perception_summary, etc.)
- REPORT BUILDER: Assembles comprehensive reports from both sources

Data flow:
    Tools → Artifacts (full detail)
    Agents → Session (summaries)
    Report Builder → Executive Summary + Full Technical Report
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from .utils import extract_json_block


# =============================================================================
# ARTIFACT-BASED REPORT GENERATION (Phase 1.6)
# =============================================================================

def generate_reports_from_artifacts(
    artifacts: Dict[str, Any],
    session_state: Dict[str, Any],
    pipeline_metadata: Dict[str, Any],
    output_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Generate reports from artifacts and session state (Phase 1.6 architecture).

    This is the primary entry point for post-pipeline report generation.

    Args:
        artifacts: Dict of artifact filename -> parsed JSON data
                   Expected keys: odd_spec.json, perception_analysis.json,
                   motion_analysis.json, collision_analysis.json, cod_construction.json
        session_state: Dict of session state keys -> values
                      Expected keys: odd_spec, perception_summary,
                      motion_summary, collision_summary, 
                      evaluator_output, report_output
        pipeline_metadata: Metadata from pipeline run (versions, timing, tokens)
        output_dir: Optional directory to save reports

    Returns:
        Dict with 'executive_summary' and 'full_report' keys
    """
    # Build executive summary from session state (agent summaries)
    executive_summary = _build_executive_summary_from_state(
        session_state,
        pipeline_metadata
    )

    # Build full technical report from artifacts (full detail)
    full_report = _build_full_report_from_artifacts(
        artifacts,
        session_state,
        pipeline_metadata
    )

    # Save if output_dir provided
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(output_dir / "executive_summary.json", "w") as f:
            json.dump(executive_summary, f, indent=2)

        with open(output_dir / "full_report.json", "w") as f:
            json.dump(full_report, f, indent=2)

    return {
        "executive_summary": executive_summary,
        "full_report": full_report,
    }


def _build_executive_summary_from_state(
    session_state: Dict[str, Any],
    pipeline_metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Build executive summary from session state (agent summaries).

    Session state contains temporal analysis and key insights from agents,
    not the full per-window data.
    """
    # Parse session state values (they may be JSON strings)
    odd_spec = _parse_state_value(session_state.get("odd_spec", {}))
    perception = _parse_state_value(
        session_state.get("perception_summary", {}))
    motion = _parse_state_value(session_state.get("motion_summary", {}))
    collision = _parse_state_value(
        session_state.get("collision_summary", {}))
    evaluator = _parse_state_value(
        session_state.get("evaluator_output", {}))
    report = _parse_state_value(session_state.get("report_output", {}))

    # Extract compliance info from evaluator or report
    compliance_verdict = evaluator.get("compliance_verdict", {})
    if not compliance_verdict:
        compliance_verdict = report.get("compliance", {})

    # Build data quality from agent summaries
    warnings = []
    anomalies = []

    # Check perception summary for issues
    if perception.get("data_quality_issues"):
        warnings.extend(perception["data_quality_issues"])
    if perception.get("anomalies"):
        anomalies.extend(perception["anomalies"])

    # Check motion summary for issues
    if motion.get("data_quality_issues"):
        warnings.extend(motion["data_quality_issues"])
    if motion.get("anomalies"):
        anomalies.extend(motion["anomalies"])

    # Check collision summary
    if collision.get("collision_events"):
        anomalies.append(
            f"Collisions detected: {len(collision['collision_events'])} events")

    return {
        "report_type": "executive_summary",
        "generated_at": datetime.utcnow().isoformat() + "Z",

        # From Report Agent
        "scenario_overview": report.get("scenario_overview", report.get("executive_summary", "")),
        "key_observations": report.get("key_observations", report.get("key_findings", [])),
        "recommendations": report.get("recommendations", []),

        # From Sensor Agent Summaries
        "temporal_insights": {
            "perception": perception.get("temporal_analysis", perception.get("cross_window_observations", {})),
            "motion": motion.get("temporal_analysis", motion.get("cross_window_observations", {})),
            "collision": collision.get("temporal_analysis", {}),
        },

        # From Evaluator
        "compliance": {
            "verdict": compliance_verdict.get("verdict", "UNKNOWN"),
            "confidence": compliance_verdict.get("confidence", 0),
            "stability": compliance_verdict.get("temporal_stability", "UNKNOWN"),
            "critical_axes": compliance_verdict.get("critical_axes", []),
            "rationale": compliance_verdict.get("rationale", ""),
        },

        "data_quality": {
            "warnings": warnings,
            "anomalies": anomalies,
        },

        # From ODD Spec
        "odd_summary": odd_spec.get("summary", {}),

        # Metadata
        "scenario": {
            "name": pipeline_metadata.get("scenario_info", {}).get("scenario_name", ""),
            "windows_analyzed": perception.get("windows_analyzed", 0),
        },
        "analysis": {
            "duration_seconds": round(pipeline_metadata.get("pipeline_duration_seconds", 0), 2),
            "total_tokens": sum(
                exec.get("token_usage", {}).get("total_tokens", 0)
                for exec in pipeline_metadata.get("agent_executions", {}).values()
            ),
            "pipeline_version": pipeline_metadata.get("pipeline_version", ""),
        }
    }


def _build_full_report_from_artifacts(
    artifacts: Dict[str, Any],
    session_state: Dict[str, Any],
    pipeline_metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Build full technical report from artifacts (complete per-window data).

    Artifacts contain all the detail; session state has summaries.
    """
    # Extract artifacts
    odd_spec_artifact = artifacts.get("odd_spec.json", {})
    perception_artifact = artifacts.get("perception_analysis.json", {})
    motion_artifact = artifacts.get("motion_analysis.json", {})
    collision_artifact = artifacts.get("collision_analysis.json", {})
    cod_artifact = artifacts.get("cod_construction.json", {})

    # Parse session state for summaries
    odd_spec_state = _parse_state_value(session_state.get("odd_spec", {}))
    perception_state = _parse_state_value(
        session_state.get("perception_summary", {}))
    motion_state = _parse_state_value(
        session_state.get("motion_summary", {}))
    collision_state = _parse_state_value(
        session_state.get("collision_summary", {}))
    evaluator_state = _parse_state_value(
        session_state.get("evaluator_output", {}))
    report_state = _parse_state_value(
        session_state.get("report_output", {}))

    # Merge per-window data from artifacts
    per_window_data = _merge_per_window_from_artifacts(
        perception_artifact,
        motion_artifact,
        collision_artifact
    )

    # Compute statistics from artifacts
    stats = _compute_statistics_from_artifacts(
        perception_artifact,
        motion_artifact,
        collision_artifact,
        cod_artifact
    )

    return {
        "report_type": "full_technical",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "pipeline_version": pipeline_metadata.get("pipeline_version", "2.0.0"),

        # =====================================================================
        # SECTION 1: EXECUTIVE SUMMARY (from session state)
        # =====================================================================
        "executive_summary": {
            "scenario_overview": report_state.get("scenario_overview", ""),
            "key_observations": report_state.get("key_observations", []),
            "recommendations": report_state.get("recommendations", []),
        },

        # =====================================================================
        # SECTION 2: COMPLIANCE (from cod_construction artifact + evaluator state)
        # =====================================================================
        "compliance": {
            "verdict": evaluator_state.get("compliance_verdict", cod_artifact.get("compliance_verdict", {})),
            "cod_region": cod_artifact.get("cod_region", {}),
            "region_metrics": cod_artifact.get("region_metrics", {}),
        },

        # =====================================================================
        # SECTION 3: ODD SPECIFICATION (from artifact)
        # =====================================================================
        "odd_specification": odd_spec_artifact.get("odd_specification", odd_spec_state.get("odd_specification", {})),

        # =====================================================================
        # SECTION 4: PER-WINDOW DATA (from artifacts - FULL DETAIL)
        # =====================================================================
        "per_window_data": per_window_data,

        # =====================================================================
        # SECTION 5: TEMPORAL ANALYSIS (from session state - SUMMARIES)
        # =====================================================================
        "temporal_analysis": {
            "perception": perception_state.get("temporal_analysis", {}),
            "motion": motion_state.get("temporal_analysis", {}),
            "collision": collision_state.get("temporal_analysis", {}),
        },

        # =====================================================================
        # SECTION 6: COMPUTED STATISTICS
        # =====================================================================
        "statistics": stats,

        # =====================================================================
        # SECTION 7: PIPELINE METADATA
        # =====================================================================
        "pipeline_metadata": {
            "scenario": pipeline_metadata.get("scenario_info", {}),
            "timing": {
                "start_time": pipeline_metadata.get("pipeline_start_time", ""),
                "duration_seconds": pipeline_metadata.get("pipeline_duration_seconds", 0),
            },
            "agents": _build_agent_summary(pipeline_metadata.get("agent_executions", {})),
            "token_summary": _build_token_summary(pipeline_metadata.get("agent_executions", {})),
        },

        # =====================================================================
        # SECTION 8: RAW ARTIFACTS (for debugging)
        # =====================================================================
        "raw_artifacts": {
            "odd_spec": odd_spec_artifact,
            "perception": perception_artifact,
            "motion": motion_artifact,
            "collision": collision_artifact,
            "cod_construction": cod_artifact,
        },
    }


def _parse_state_value(value: Any) -> Dict[str, Any]:
    """Parse session state value - may be JSON string or dict."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            try:
                return extract_json_block(value)
            except:
                return {}
    elif isinstance(value, dict):
        return value
    return {}


def _merge_per_window_from_artifacts(
    perception: Dict[str, Any],
    motion: Dict[str, Any],
    collision: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Merge per-window data from artifacts into unified structure.
    """
    # Extract per-window arrays from artifacts
    perception_windows = perception.get("per_window", [])
    motion_windows = motion.get("per_window", [])
    collision_windows = collision.get("per_window", [])

    # Index by window_id
    merged = {}

    for pw in perception_windows:
        wid = pw.get("window_id", "")
        if wid not in merged:
            merged[wid] = {"window_id": wid}
        merged[wid]["perception"] = pw

    for mw in motion_windows:
        wid = mw.get("window_id", "")
        if wid not in merged:
            merged[wid] = {"window_id": wid}
        merged[wid]["motion"] = mw

    for cw in collision_windows:
        wid = cw.get("window_id", "")
        if wid not in merged:
            merged[wid] = {"window_id": wid}
        merged[wid]["collision"] = cw

    return sorted(merged.values(), key=lambda x: x.get("window_id", ""))


def _compute_statistics_from_artifacts(
    perception: Dict[str, Any],
    motion: Dict[str, Any],
    collision: Dict[str, Any],
    cod: Dict[str, Any]
) -> Dict[str, Any]:
    """Compute statistics from artifact data."""
    perception_windows = perception.get("per_window", [])
    motion_windows = motion.get("per_window", [])
    collision_windows = collision.get("per_window", [])

    # Window counts
    window_stats = {
        "total_windows": max(len(perception_windows), len(motion_windows), len(collision_windows)),
        "perception_windows": len(perception_windows),
        "motion_windows": len(motion_windows),
        "collision_windows": len(collision_windows),
    }

    # Measurement ranges
    measurement_stats = {}

    # Gather all numeric measurements
    all_measurements = {}
    for windows in [perception_windows, motion_windows, collision_windows]:
        for w in windows:
            measurements = w.get("measurements", w.get("observations", {}))
            if isinstance(measurements, dict):
                for key, value in measurements.items():
                    if isinstance(value, (int, float)):
                        if key not in all_measurements:
                            all_measurements[key] = []
                        all_measurements[key].append(value)

    for key, values in all_measurements.items():
        if values:
            measurement_stats[key] = {
                "min": round(min(values), 4),
                "max": round(max(values), 4),
                "mean": round(sum(values) / len(values), 4),
                "samples": len(values),
            }

    # Compliance from COD artifact
    compliance_stats = {}
    if cod:
        verdict = cod.get("compliance_verdict", {})
        compliance_stats = {
            "verdict": verdict.get("verdict", "UNKNOWN"),
            "confidence": verdict.get("confidence", 0),
            "critical_axes": verdict.get("critical_axes", []),
        }

        # Region metrics
        region_metrics = cod.get("region_metrics", {})
        if region_metrics:
            compliance_stats["fraction_outside_odd"] = region_metrics.get(
                "fraction_outside_odd", 0)
            compliance_stats["windows_violated"] = region_metrics.get(
                "windows_violated", [])

    return {
        "window_stats": window_stats,
        "measurement_stats": measurement_stats,
        "compliance_stats": compliance_stats,
    }


def _build_agent_summary(agent_executions: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build summary of agent executions for report."""
    summary = []

    for agent_name, exec_data in agent_executions.items():
        summary.append({
            "name": agent_name,
            "version": exec_data.get("version", ""),
            "model": exec_data.get("actual_model", exec_data.get("declared_model", "")),
            "tokens": exec_data.get("token_usage", {}).get("total_tokens", 0),
        })

    return summary


def _build_token_summary(agent_executions: Dict[str, Any]) -> Dict[str, Any]:
    """Build token usage summary with accurate cost calculation."""
    from .pricing import calculate_pipeline_cost

    total_prompt = 0
    total_completion = 0
    total = 0

    for exec_data in agent_executions.values():
        usage = exec_data.get("token_usage", {})
        total_prompt += usage.get("prompt_tokens") or 0
        total_completion += usage.get("completion_tokens") or 0
        total += usage.get("total_tokens") or 0

    # Calculate accurate cost based on model pricing
    cost_data = calculate_pipeline_cost(agent_executions)

    return {
        "prompt_tokens": total_prompt,
        "completion_tokens": total_completion,
        "total_tokens": total,
        "estimated_cost_usd": cost_data["total_usd"],
        "cost_breakdown": cost_data["breakdown"],
        "cost_per_agent": cost_data["per_agent"],
    }


# =============================================================================
# LEGACY ENTRY POINT (for backwards compatibility)
# =============================================================================

def extract_all_agent_outputs(events: list) -> Dict[str, Any]:
    """
    Extract outputs from ALL agents in the pipeline (legacy method).

    DEPRECATED: Use artifacts + session state instead.
    This exists for backwards compatibility with event-based extraction.
    """
    outputs = {}

    agent_names = [
        "OddSpecAgent",
        "PerceptionAgent",
        "MotionAgent",
        "CollisionAgent",
        "EvaluatorAgent",
        "ReportAgent"
    ]

    for event in events:
        if event.author in agent_names and event.content and event.content.parts:
            for part in event.content.parts:
                # Check for direct text output (most agents)
                if part.text:
                    try:
                        parsed = extract_json_block(part.text)
                        outputs[event.author] = parsed
                        break
                    except Exception:
                        continue

                # Check for function response (tool returns)
                if hasattr(part, 'function_response') and part.function_response:
                    try:
                        response = part.function_response.response
                        if isinstance(response, str):
                            parsed = extract_json_block(response)
                            outputs[event.author] = parsed
                            break
                        elif isinstance(response, dict):
                            outputs[event.author] = response
                            break
                    except Exception:
                        continue

    return outputs


def generate_reports(
    events: list,
    pipeline_metadata: Dict[str, Any],
    output_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Generate all reports from pipeline events (legacy method).

    DEPRECATED: Use generate_reports_from_artifacts() instead.
    This exists for backwards compatibility.
    """
    # Extract agent outputs from events (legacy approach)
    agent_outputs = extract_all_agent_outputs(events)

    # Convert to session state format for new architecture
    session_state = {
        "odd_spec": agent_outputs.get("OddSpecAgent", {}),
        "perception_summary": agent_outputs.get("PerceptionAgent", {}),
        "motion_summary": agent_outputs.get("MotionAgent", {}),
        "collision_summary": agent_outputs.get("CollisionAgent", {}),
        "evaluator_output": agent_outputs.get("EvaluatorAgent", {}),
        "report_output": agent_outputs.get("ReportAgent", {}),
    }

    # Empty artifacts (legacy mode - no artifacts available)
    artifacts = {}

    return generate_reports_from_artifacts(
        artifacts=artifacts,
        session_state=session_state,
        pipeline_metadata=pipeline_metadata,
        output_dir=output_dir
    )
