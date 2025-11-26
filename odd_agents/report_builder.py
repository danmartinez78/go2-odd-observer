"""
Report builder - Post-pipeline report assembly.

This module handles report generation AFTER the ADK pipeline completes.
It extracts all agent outputs from events and assembles comprehensive reports.

Architecture:
- ReportAgent (in pipeline): Generates executive summary using statistics tools
- report_builder (post-pipeline): Assembles full technical report from all data

This keeps ReportAgent's token context minimal while capturing all pipeline data.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from .utils import extract_json_block


# =============================================================================
# DATA EXTRACTION FROM PIPELINE EVENTS
# =============================================================================

def extract_all_agent_outputs(events: list) -> Dict[str, Any]:
    """
    Extract outputs from ALL agents in the pipeline.

    Returns dict keyed by agent name with their parsed JSON outputs.
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
        if event.author in agent_names and event.content:
            for part in event.content.parts:
                if part.text:
                    try:
                        parsed = extract_json_block(part.text)
                        outputs[event.author] = parsed
                        break
                    except Exception:
                        continue

    return outputs


def extract_tool_calls(events: list) -> List[Dict[str, Any]]:
    """
    Extract all tool calls made during pipeline execution.

    Useful for debugging and understanding agent behavior.
    """
    tool_calls = []

    for event in events:
        # Check for function call events in ADK format
        if hasattr(event, 'content') and event.content:
            for part in event.content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    tool_calls.append({
                        "agent": event.author,
                        "tool_name": part.function_call.name,
                        "args": dict(part.function_call.args) if part.function_call.args else {},
                    })

    return tool_calls


# =============================================================================
# STATISTICS COMPUTATION (same logic as report tool, for post-processing)
# =============================================================================

def compute_statistics(agent_outputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute comprehensive statistics from agent outputs.

    This mirrors the compute_report_statistics_tool but works on extracted outputs.
    """
    odd_spec = agent_outputs.get("OddSpecAgent", {})
    perception = agent_outputs.get("PerceptionAgent", {})
    motion = agent_outputs.get("MotionAgent", {})
    collision = agent_outputs.get("CollisionAgent", {})
    evaluator = agent_outputs.get("EvaluatorAgent", {})

    # Window stats
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

    # Agent health
    agent_health = {}

    perception_empty = [w["window_id"]
                        for w in perception_windows if not w.get("measurements")]
    agent_health["perception"] = {
        "windows_processed": len(perception_windows),
        "empty_windows": perception_empty,
        "status": "OK" if not perception_empty else f"WARNING: {len(perception_empty)} empty",
    }

    motion_empty = [w["window_id"]
                    for w in motion_windows if not w.get("measurements")]
    zero_accel = [w["window_id"] for w in motion_windows
                  if w.get("measurements", {}).get("max_accel_mps2", 0) == 0]
    agent_health["motion"] = {
        "windows_processed": len(motion_windows),
        "empty_windows": motion_empty,
        "zero_acceleration_windows": zero_accel,
        "status": "OK" if not motion_empty and not zero_accel else "WARNING",
    }

    collision_detected = [w["window_id"] for w in collision_windows
                          if w.get("measurements", {}).get("collision_detected", 0) == 1]
    agent_health["collision"] = {
        "windows_processed": len(collision_windows),
        "collision_detected_windows": collision_detected,
        "collision_count": len(collision_detected),
        "status": "OK",
    }

    # Measurement stats
    measurement_stats = {}
    all_measurements = {}
    for windows in [perception_windows, motion_windows, collision_windows]:
        for w in windows:
            for key, value in w.get("measurements", {}).items():
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

    # Compliance stats
    compliance_verdict = evaluator.get("compliance_verdict", {})
    compliance_stats = {
        "verdict": compliance_verdict.get("verdict", "UNKNOWN"),
        "confidence": compliance_verdict.get("confidence", 0),
        "temporal_stability": compliance_verdict.get("temporal_stability", "UNKNOWN"),
        "critical_axes": compliance_verdict.get("critical_axes", []),
    }

    return {
        "window_stats": window_stats,
        "agent_health": agent_health,
        "measurement_stats": measurement_stats,
        "compliance_stats": compliance_stats,
    }


# =============================================================================
# REPORT ASSEMBLY
# =============================================================================

def build_executive_summary_report(
    agent_outputs: Dict[str, Any],
    pipeline_metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Build a concise executive summary report.

    This is what stakeholders see - high-level compliance status and key findings.
    """
    report_output = agent_outputs.get("ReportAgent", {})
    evaluator_output = agent_outputs.get("EvaluatorAgent", {})
    stats = compute_statistics(agent_outputs)

    return {
        "report_type": "executive_summary",
        "generated_at": datetime.utcnow().isoformat() + "Z",

        # From ReportAgent
        "executive_summary": report_output.get("executive_summary", ""),
        "key_findings": report_output.get("key_findings", []),
        "recommendations": report_output.get("recommendations", []),

        # From statistics
        "compliance": {
            "verdict": stats["compliance_stats"]["verdict"],
            "confidence": stats["compliance_stats"]["confidence"],
            "temporal_stability": stats["compliance_stats"]["temporal_stability"],
            "critical_axes": stats["compliance_stats"]["critical_axes"],
        },

        # Data quality from report
        "data_quality": report_output.get("data_quality", {}),

        # Metadata
        "scenario": {
            "name": pipeline_metadata.get("scenario_info", {}).get("scenario_name", ""),
            "windows_analyzed": stats["window_stats"]["total_windows"],
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


def build_full_technical_report(
    agent_outputs: Dict[str, Any],
    pipeline_metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Build comprehensive technical report with ALL pipeline data.

    This captures everything for debugging, auditing, and detailed analysis.
    No LLM involved - pure data assembly.
    """
    odd_spec = agent_outputs.get("OddSpecAgent", {})
    perception = agent_outputs.get("PerceptionAgent", {})
    motion = agent_outputs.get("MotionAgent", {})
    collision = agent_outputs.get("CollisionAgent", {})
    evaluator = agent_outputs.get("EvaluatorAgent", {})
    report = agent_outputs.get("ReportAgent", {})

    stats = compute_statistics(agent_outputs)

    return {
        "report_type": "full_technical",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "pipeline_version": pipeline_metadata.get("pipeline_version", "2.0.0"),

        # =====================================================================
        # SECTION 1: EXECUTIVE SUMMARY (from report agent)
        # =====================================================================
        "executive_summary": {
            "summary": report.get("executive_summary", ""),
            "key_findings": report.get("key_findings", []),
            "recommendations": report.get("recommendations", []),
            "data_quality": report.get("data_quality", {}),
            "measurement_summary": report.get("measurement_summary", {}),
        },

        # =====================================================================
        # SECTION 2: COMPLIANCE VERDICT
        # =====================================================================
        "compliance": {
            "verdict": evaluator.get("compliance_verdict", {}),
            "cod_region": evaluator.get("cod_region", {}),
            "region_metrics": evaluator.get("region_metrics", {}),
            "key_concerns": evaluator.get("key_concerns", []),
        },

        # =====================================================================
        # SECTION 3: COMPUTED STATISTICS
        # =====================================================================
        "statistics": stats,

        # =====================================================================
        # SECTION 4: ODD SPECIFICATION
        # =====================================================================
        "odd_specification": odd_spec.get("odd_specification", {}),

        # =====================================================================
        # SECTION 5: PER-WINDOW DATA (from sensor agents)
        # =====================================================================
        "per_window_data": _merge_per_window_data(perception, motion, collision),

        # =====================================================================
        # SECTION 6: TEMPORAL ANALYSIS (from sensor agents)
        # =====================================================================
        "temporal_analysis": {
            "perception": perception.get("temporal_analysis", {}),
            "motion": motion.get("temporal_analysis", {}),
            "collision": collision.get("temporal_analysis", {}),
        },

        # =====================================================================
        # SECTION 7: SUMMARY INSIGHTS (from sensor agents)
        # =====================================================================
        "summary_insights": {
            "perception": perception.get("summary_insights", []),
            "motion": motion.get("summary_insights", []),
            "collision": collision.get("summary_insights", []),
        },

        # =====================================================================
        # SECTION 8: PIPELINE METADATA
        # =====================================================================
        "pipeline_metadata": {
            "scenario": pipeline_metadata.get("scenario_info", {}),
            "odd_spec_hash": pipeline_metadata.get("odd_specification", {}).get("hash", ""),
            "timing": {
                "start_time": pipeline_metadata.get("pipeline_start_time", ""),
                "duration_seconds": pipeline_metadata.get("pipeline_duration_seconds", 0),
            },
            "agents": _build_agent_summary(pipeline_metadata.get("agent_executions", {})),
            "token_summary": _build_token_summary(pipeline_metadata.get("agent_executions", {})),
        },

        # =====================================================================
        # SECTION 9: RAW AGENT OUTPUTS (for debugging)
        # =====================================================================
        "raw_agent_outputs": {
            "odd_spec": odd_spec,
            "perception": perception,
            "motion": motion,
            "collision": collision,
            "evaluator": evaluator,
            "report": report,
        },
    }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _count_windows(agent_outputs: Dict[str, Any]) -> int:
    """Count total windows analyzed from perception output."""
    perception = agent_outputs.get("PerceptionAgent", {})
    per_window = perception.get(
        "per_window", perception.get("per_window_measurements", []))
    return len(per_window)


def _merge_per_window_data(
    perception: Dict[str, Any],
    motion: Dict[str, Any],
    collision: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Merge per-window data from all sensor agents into unified structure.

    Output: [
        {
            "window_id": "010",
            "perception": {...},
            "motion": {...},
            "collision": {...}
        },
        ...
    ]
    """
    # Extract per-window data from each agent
    perception_windows = perception.get(
        "per_window", perception.get("per_window_measurements", []))
    motion_windows = motion.get(
        "per_window", motion.get("per_window_measurements", []))
    collision_windows = collision.get(
        "per_window", collision.get("per_window_measurements", []))

    # Index by window_id
    merged = {}

    for pw in perception_windows:
        wid = pw.get("window_id", "")
        if wid not in merged:
            merged[wid] = {"window_id": wid}
        merged[wid]["perception"] = pw.get("measurements", {})

    for mw in motion_windows:
        wid = mw.get("window_id", "")
        if wid not in merged:
            merged[wid] = {"window_id": wid}
        merged[wid]["motion"] = mw.get("measurements", {})

    for cw in collision_windows:
        wid = cw.get("window_id", "")
        if wid not in merged:
            merged[wid] = {"window_id": wid}
        merged[wid]["collision"] = cw.get("measurements", {})

    # Sort by window_id and return as list
    return sorted(merged.values(), key=lambda x: x.get("window_id", ""))


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
    """Build token usage summary."""
    total_prompt = 0
    total_completion = 0
    total = 0

    for exec_data in agent_executions.values():
        usage = exec_data.get("token_usage", {})
        total_prompt += usage.get("prompt_tokens", 0)
        total_completion += usage.get("completion_tokens", 0)
        total += usage.get("total_tokens", 0)

    # Cost estimation (conservative)
    estimated_cost = total * 0.00002

    return {
        "prompt_tokens": total_prompt,
        "completion_tokens": total_completion,
        "total_tokens": total,
        "estimated_cost_usd": round(estimated_cost, 4),
    }


# =============================================================================
# REPORT GENERATION ENTRY POINT
# =============================================================================

def generate_reports(
    events: list,
    pipeline_metadata: Dict[str, Any],
    output_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Generate all reports from pipeline events.

    Args:
        events: List of ADK events from pipeline execution
        pipeline_metadata: Metadata from pipeline run
        output_dir: Optional directory to save reports

    Returns:
        Dict with 'executive_summary' and 'full_report' keys
    """
    # Extract all agent outputs
    agent_outputs = extract_all_agent_outputs(events)

    # Build reports
    executive_summary = build_executive_summary_report(
        agent_outputs, pipeline_metadata)
    full_report = build_full_technical_report(agent_outputs, pipeline_metadata)

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
