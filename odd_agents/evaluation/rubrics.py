"""
Evaluation rubrics for different agent types.

Each rubric defines a specific quality criterion that an LLM judge
will evaluate. Rubrics should be:
- Specific and measurable
- Independent from each other
- Aligned with agent goals

These rubrics are formatted for ADK's rubric_based_final_response_quality_v1
and rubric_based_tool_use_quality_v1 criteria.

ADK Rubric Format:
{
    "rubric_id": "unique_id",
    "rubric_content": {
        "text_property": "Description of what to evaluate"
    }
}
"""


# ============================================================================
# PERCEPTION AGENT RUBRICS
# ============================================================================

PERCEPTION_RUBRICS = [
    {
        "rubric_id": "environment_classification",
        "rubric_content": {
            "text_property": (
                "The agent correctly identifies the environment type (indoor, outdoor, "
                "mixed) based on camera data. The classification should match the "
                "dominant environment characteristics visible in the image analysis."
            )
        }
    },
    {
        "rubric_id": "lighting_assessment",
        "rubric_content": {
            "text_property": (
                "The agent accurately assesses lighting conditions (bright, moderate, dim) "
                "based on camera data. The assessment should reflect actual illumination "
                "levels that would affect robot perception capabilities."
            )
        }
    },
    {
        "rubric_id": "obstacle_detection",
        "rubric_content": {
            "text_property": (
                "The agent identifies the presence and approximate count of obstacles "
                "from camera data. Detection should be reasonably accurate (±20%) and "
                "consistent with LiDAR-derived obstacle density."
            )
        }
    },
    {
        "rubric_id": "terrain_characterization",
        "rubric_content": {
            "text_property": (
                "The agent correctly characterizes terrain type (smooth, rough, mixed) "
                "and clearance_index from BEV occupancy analysis. Clearance index "
                "should align with gap availability in the BEV occupancy map."
            )
        }
    },
    {
        "rubric_id": "multimodal_consistency",
        "rubric_content": {
            "text_property": (
                "The agent's camera-based and BEV-based assessments are consistent "
                "and complementary. For example, high obstacle count from camera should "
                "correlate with lower clearance_index from BEV occupancy analysis."
            )
        }
    },
    {
        "rubric_id": "json_format_compliance",
        "rubric_content": {
            "text_property": (
                "The agent output is valid JSON with all required fields: environment_type, "
                "lighting, obstacles (count, types, density), terrain_type, clearance_index, "
                "and summary. No missing fields or malformed structure."
            )
        }
    },
]


# ============================================================================
# MOTION AGENT RUBRICS
# ============================================================================

MOTION_RUBRICS = [
    {
        "rubric_id": "velocity_extraction",
        "rubric_content": {
            "text_property": (
                "The agent correctly extracts velocity statistics (mean, max, variance) "
                "from IMU acceleration data. Values should be physically plausible "
                "(e.g., max velocity < 5 m/s for quadruped)."
            )
        }
    },
    {
        "rubric_id": "rotation_extraction",
        "rubric_content": {
            "text_property": (
                "The agent correctly extracts rotation statistics (mean, max, variance) "
                "from IMU gyroscope data. Values should be in valid ranges (e.g., "
                "max rotation < 180 deg/s for typical quadruped motion)."
            )
        }
    },
    {
        "rubric_id": "platform_stability",
        "rubric_content": {
            "text_property": (
                "The agent accurately assesses platform stability based on acceleration "
                "variance and angular velocity. High variance or rotation should result "
                "in lower stability scores."
            )
        }
    },
    {
        "rubric_id": "stationary_detection",
        "rubric_content": {
            "text_property": (
                "The agent correctly identifies stationary periods (near-zero velocities "
                "and rotations). This should be flagged explicitly if sustained over "
                "multiple samples."
            )
        }
    },
    {
        "rubric_id": "motion_summary",
        "rubric_content": {
            "text_property": (
                "The agent provides a clear, accurate summary of motion characteristics "
                "that reflects the extracted statistics. Summary should highlight "
                "key patterns (e.g., 'predominantly stationary', 'moderate movement')."
            )
        }
    },
    {
        "rubric_id": "json_format_compliance",
        "rubric_content": {
            "text_property": (
                "The agent output is valid JSON with all required fields: velocity, "
                "rotation, platform_stability, and summary. Statistics include mean, "
                "max, and variance where applicable."
            )
        }
    },
]


# ============================================================================
# COLLISION AGENT RUBRICS
# ============================================================================

COLLISION_RUBRICS = [
    {
        "rubric_id": "risk_score_calibration",
        "rubric_content": {
            "text_property": (
                "The collision risk score (0-1) is well-calibrated based on obstacle "
                "proximity and density. High density or close obstacles should yield "
                "high risk scores. Score should reflect actual danger level."
            )
        }
    },
    {
        "rubric_id": "proximity_analysis",
        "rubric_content": {
            "text_property": (
                "The agent correctly identifies closest obstacles and their distances. "
                "Minimum distance should align with LiDAR point cloud data and be "
                "physically plausible."
            )
        }
    },
    {
        "rubric_id": "multimodal_fusion",
        "rubric_content": {
            "text_property": (
                "The agent effectively fuses perception data (obstacle detection, "
                "clearance_index) and motion data (velocity, stability) to assess "
                "collision risk. Risk should increase with higher velocity or lower "
                "clearance_index."
            )
        }
    },
    {
        "rubric_id": "risk_interpretation",
        "rubric_content": {
            "text_property": (
                "The agent provides clear risk interpretation (low/moderate/high) "
                "consistent with the numerical score. Thresholds should be reasonable "
                "(e.g., >0.7 = high risk)."
            )
        }
    },
    {
        "rubric_id": "actionable_insights",
        "rubric_content": {
            "text_property": (
                "The agent summary includes actionable insights about collision risk "
                "factors and potential mitigations (e.g., 'reduce speed', 'avoid dense "
                "obstacle areas')."
            )
        }
    },
    {
        "rubric_id": "json_format_compliance",
        "rubric_content": {
            "text_property": (
                "The agent output is valid JSON with required fields: collision_risk, "
                "closest_obstacle_distance, risk_factors, and summary."
            )
        }
    },
]


# ============================================================================
# ODD SPEC AGENT RUBRICS
# ============================================================================

ODD_SPEC_RUBRICS = [
    {
        "rubric_id": "conversational_interpretation",
        "rubric_content": {
            "text_property": (
                "The agent correctly interprets conversational/vague ODD descriptions "
                "and converts them to formal specifications. For example, 'walking pace' "
                "→ 0.0-0.5 m/s, 'moderate obstacles' → 0.0-0.6 density."
            )
        }
    },
    {
        "rubric_id": "range_inference",
        "rubric_content": {
            "text_property": (
                "The agent intelligently infers IN_ODD and BOUNDARY ranges when not "
                "explicitly provided. Boundaries should be reasonable extensions (e.g., "
                "+30% for max values, +0.2 for densities)."
            )
        }
    },
    {
        "rubric_id": "axis_completeness",
        "rubric_content": {
            "text_property": (
                "The agent defines all relevant ODD axes (numeric and categorical) "
                "based on the description. Common axes include speed, obstacle_density, "
                "terrain_type, lighting, environment_type."
            )
        }
    },
    {
        "rubric_id": "boundary_consistency",
        "rubric_content": {
            "text_property": (
                "For each numeric axis, IN_ODD and BOUNDARY ranges are consistent "
                "(BOUNDARY extends IN_ODD, no overlaps or gaps). Categorical axes "
                "have clear IN_ODD and OUT_ODD values."
            )
        }
    },
    {
        "rubric_id": "importance_weighting",
        "rubric_content": {
            "text_property": (
                "Importance weights (0-1) reflect the criticality of each axis. "
                "Safety-critical axes (speed, obstacle_density) should have higher "
                "weights than environmental preferences."
            )
        }
    },
    {
        "rubric_id": "json_format_compliance",
        "rubric_content": {
            "text_property": (
                "The agent output is valid JSON with all required fields: axes, "
                "each axis has type, IN_ODD, BOUNDARY (or OUT_ODD for categorical), "
                "unit, and importance."
            )
        }
    },
]


# ============================================================================
# COD CLASSIFIER RUBRICS
# ============================================================================

COD_RUBRICS = [
    {
        "rubric_id": "correct_classification",
        "rubric_content": {
            "text_property": (
                "The COD classification (IN_ODD, BOUNDARY, OUT_ODD) correctly reflects "
                "the number and severity of violations. All IN_ODD → IN_ODD, any "
                "OUT_ODD violation → OUT_ODD, only BOUNDARY violations → BOUNDARY."
            )
        }
    },
    {
        "rubric_id": "violation_identification",
        "rubric_content": {
            "text_property": (
                "The agent correctly identifies which ODD axes are violated and their "
                "severity. Violations should match actual exceedances of IN_ODD or "
                "BOUNDARY thresholds."
            )
        }
    },
    {
        "rubric_id": "confidence_calibration",
        "rubric_content": {
            "text_property": (
                "Confidence scores reflect classification certainty. Clear violations "
                "should have high confidence (>0.9), borderline cases lower confidence. "
                "Confidence should correlate with violation magnitude."
            )
        }
    },
    {
        "rubric_id": "reasoning_quality",
        "rubric_content": {
            "text_property": (
                "The reasoning clearly explains why the classification was chosen, "
                "citing specific axes and values. Reasoning should be traceable to "
                "compliance data."
            )
        }
    },
    {
        "rubric_id": "json_format_compliance",
        "rubric_content": {
            "text_property": (
                "The agent output is valid JSON with required fields: cod_classification, "
                "confidence, reasoning, and contributing_factors."
            )
        }
    },
]


# ============================================================================
# COMPLIANCE AGENT RUBRICS
# ============================================================================

COMPLIANCE_RUBRICS = [
    {
        "rubric_id": "accurate_comparison",
        "rubric_content": {
            "text_property": (
                "The agent accurately compares actual values from perception/motion "
                "analysis against ODD specification ranges. Each axis is evaluated "
                "correctly (IN_ODD, BOUNDARY, OUT_ODD)."
            )
        }
    },
    {
        "rubric_id": "violation_detection",
        "rubric_content": {
            "text_property": (
                "All violations (OUT_ODD) and warnings (BOUNDARY) are correctly "
                "identified. No false positives or missed violations. Thresholds "
                "applied consistently."
            )
        }
    },
    {
        "rubric_id": "importance_weighting",
        "rubric_content": {
            "text_property": (
                "Axis importance from ODD spec is properly considered. High-importance "
                "violations should be weighted more heavily in overall assessment."
            )
        }
    },
    {
        "rubric_id": "summary_quality",
        "rubric_content": {
            "text_property": (
                "Compliance summary clearly communicates overall status and key "
                "violations. Summary should prioritize critical issues and provide "
                "actionable context."
            )
        }
    },
    {
        "rubric_id": "json_format_compliance",
        "rubric_content": {
            "text_property": (
                "The agent output is valid JSON with required fields: overall_compliance, "
                "axis_compliance (per axis with status and actual value), violations, "
                "warnings, and summary."
            )
        }
    },
]


# ============================================================================
# REPORT AGENT RUBRICS
# ============================================================================

REPORT_RUBRICS = [
    {
        "rubric_id": "executive_summary_quality",
        "rubric_content": {
            "text_property": (
                "Executive summary concisely captures scenario, overall compliance, and "
                "key findings. Should be understandable by non-technical stakeholders "
                "and highlight critical issues."
            )
        }
    },
    {
        "rubric_id": "findings_completeness",
        "rubric_content": {
            "text_property": (
                "Key findings section covers all major violations, warnings, and notable "
                "observations from perception/motion/collision analysis. Findings are "
                "specific and evidence-based."
            )
        }
    },
    {
        "rubric_id": "recommendations_actionability",
        "rubric_content": {
            "text_property": (
                "Recommendations are specific, actionable, and prioritized. Each "
                "recommendation addresses a concrete finding and suggests clear next "
                "steps (e.g., 'Reduce max speed to X m/s', 'Improve path planning')."
            )
        }
    },
    {
        "rubric_id": "risk_assessment_accuracy",
        "rubric_content": {
            "text_property": (
                "Risk assessment accurately reflects the severity of compliance "
                "violations and operational risks. Risk level (low/moderate/high) "
                "should align with violation count and importance."
            )
        }
    },
    {
        "rubric_id": "clarity_and_structure",
        "rubric_content": {
            "text_property": (
                "Report is well-structured with clear sections, logical flow, and "
                "appropriate level of detail. Avoids jargon where possible or explains "
                "technical terms."
            )
        }
    },
    {
        "rubric_id": "json_format_compliance",
        "rubric_content": {
            "text_property": (
                "The agent output is valid JSON with required fields: executive_summary, "
                "key_findings, recommendations, risk_assessment, and metadata."
            )
        }
    },
]


# Export all rubrics
__all__ = [
    "PERCEPTION_RUBRICS",
    "MOTION_RUBRICS",
    "COLLISION_RUBRICS",
    "ODD_SPEC_RUBRICS",
    "COD_RUBRICS",
    "COMPLIANCE_RUBRICS",
    "REPORT_RUBRICS",
]
