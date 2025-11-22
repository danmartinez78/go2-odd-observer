"""
Evaluation rubrics for different agent types.

Each rubric defines a specific quality criterion that an LLM judge
will evaluate. Rubrics should be:
- Specific and measurable
- Independent from each other
- Aligned with agent goals
"""

from .base import Rubric


# ============================================================================
# PERCEPTION AGENT RUBRICS
# ============================================================================

PERCEPTION_RUBRICS = [
    Rubric(
        rubric_id="environment_classification",
        description=(
            "The agent correctly identifies the environment type (indoor, outdoor, "
            "mixed) based on camera data. The classification should match the "
            "dominant environment characteristics visible in the image analysis."
        ),
        importance=1.0,
    ),
    Rubric(
        rubric_id="lighting_assessment",
        description=(
            "The agent accurately assesses lighting conditions (bright, moderate, dim) "
            "based on camera data. The assessment should reflect actual illumination "
            "levels that would affect robot perception capabilities."
        ),
        importance=0.8,
    ),
    Rubric(
        rubric_id="obstacle_detection",
        description=(
            "The agent identifies the presence and approximate count of obstacles "
            "from camera data. Detection should be reasonably accurate (±20%) and "
            "consistent with LiDAR-derived obstacle density."
        ),
        importance=1.0,
    ),
    Rubric(
        rubric_id="terrain_characterization",
        description=(
            "The agent correctly characterizes terrain type (smooth, rough, mixed) "
            "and traversability from LiDAR point cloud analysis. Traversability "
            "score should align with terrain roughness metrics."
        ),
        importance=1.0,
    ),
    Rubric(
        rubric_id="multimodal_consistency",
        description=(
            "The agent's camera-based and LiDAR-based assessments are consistent "
            "and complementary. For example, high obstacle count from camera should "
            "correlate with low traversability from LiDAR."
        ),
        importance=0.9,
    ),
    Rubric(
        rubric_id="json_format_compliance",
        description=(
            "The agent output is valid JSON with all required fields: environment_type, "
            "lighting, obstacles (count, types, density), terrain_type, traversability_score, "
            "and summary. No missing fields or malformed structure."
        ),
        importance=0.7,
    ),
]


# ============================================================================
# MOTION AGENT RUBRICS
# ============================================================================

MOTION_RUBRICS = [
    Rubric(
        rubric_id="velocity_extraction",
        description=(
            "The agent correctly extracts velocity statistics (mean, max, variance) "
            "from IMU acceleration data. Values should be physically plausible "
            "(e.g., max velocity < 5 m/s for quadruped)."
        ),
        importance=1.0,
    ),
    Rubric(
        rubric_id="rotation_extraction",
        description=(
            "The agent correctly extracts rotation statistics (mean, max, variance) "
            "from IMU gyroscope data. Values should be in valid ranges (e.g., "
            "max rotation < 180 deg/s for typical quadruped motion)."
        ),
        importance=1.0,
    ),
    Rubric(
        rubric_id="platform_stability",
        description=(
            "The agent accurately assesses platform stability based on acceleration "
            "variance and angular velocity. High variance or rotation should result "
            "in lower stability scores."
        ),
        importance=0.9,
    ),
    Rubric(
        rubric_id="stationary_detection",
        description=(
            "The agent correctly identifies stationary periods (near-zero velocities "
            "and rotations). This should be flagged explicitly if sustained over "
            "multiple samples."
        ),
        importance=0.8,
    ),
    Rubric(
        rubric_id="motion_summary",
        description=(
            "The agent provides a clear, accurate summary of motion characteristics "
            "that reflects the extracted statistics. Summary should highlight "
            "key patterns (e.g., 'predominantly stationary', 'moderate movement')."
        ),
        importance=0.7,
    ),
    Rubric(
        rubric_id="json_format_compliance",
        description=(
            "The agent output is valid JSON with all required fields: velocity, "
            "rotation, platform_stability, and summary. Statistics include mean, "
            "max, and variance where applicable."
        ),
        importance=0.7,
    ),
]


# ============================================================================
# COLLISION AGENT RUBRICS
# ============================================================================

COLLISION_RUBRICS = [
    Rubric(
        rubric_id="risk_score_calibration",
        description=(
            "The collision risk score (0-1) is well-calibrated based on obstacle "
            "proximity and density. High density or close obstacles should yield "
            "high risk scores. Score should reflect actual danger level."
        ),
        importance=1.0,
    ),
    Rubric(
        rubric_id="proximity_analysis",
        description=(
            "The agent correctly identifies closest obstacles and their distances. "
            "Minimum distance should align with LiDAR point cloud data and be "
            "physically plausible."
        ),
        importance=1.0,
    ),
    Rubric(
        rubric_id="multimodal_fusion",
        description=(
            "The agent effectively fuses perception data (obstacle detection, "
            "traversability) and motion data (velocity, stability) to assess "
            "collision risk. Risk should increase with higher velocity or lower "
            "traversability."
        ),
        importance=0.9,
    ),
    Rubric(
        rubric_id="risk_interpretation",
        description=(
            "The agent provides clear risk interpretation (low/moderate/high) "
            "consistent with the numerical score. Thresholds should be reasonable "
            "(e.g., >0.7 = high risk)."
        ),
        importance=0.8,
    ),
    Rubric(
        rubric_id="actionable_insights",
        description=(
            "The agent summary includes actionable insights about collision risk "
            "factors and potential mitigations (e.g., 'reduce speed', 'avoid dense "
            "obstacle areas')."
        ),
        importance=0.7,
    ),
    Rubric(
        rubric_id="json_format_compliance",
        description=(
            "The agent output is valid JSON with required fields: collision_risk, "
            "closest_obstacle_distance, risk_factors, and summary."
        ),
        importance=0.7,
    ),
]


# ============================================================================
# ODD SPEC AGENT RUBRICS
# ============================================================================

ODD_SPEC_RUBRICS = [
    Rubric(
        rubric_id="conversational_interpretation",
        description=(
            "The agent correctly interprets conversational/vague ODD descriptions "
            "and converts them to formal specifications. For example, 'walking pace' "
            "→ 0.0-0.5 m/s, 'moderate obstacles' → 0.0-0.6 density."
        ),
        importance=1.0,
    ),
    Rubric(
        rubric_id="range_inference",
        description=(
            "The agent intelligently infers IN_ODD and BOUNDARY ranges when not "
            "explicitly provided. Boundaries should be reasonable extensions (e.g., "
            "+30% for max values, +0.2 for densities)."
        ),
        importance=1.0,
    ),
    Rubric(
        rubric_id="axis_completeness",
        description=(
            "The agent defines all relevant ODD axes (numeric and categorical) "
            "based on the description. Common axes include speed, obstacle_density, "
            "terrain_type, lighting, environment_type."
        ),
        importance=0.9,
    ),
    Rubric(
        rubric_id="boundary_consistency",
        description=(
            "For each numeric axis, IN_ODD and BOUNDARY ranges are consistent "
            "(BOUNDARY extends IN_ODD, no overlaps or gaps). Categorical axes "
            "have clear IN_ODD and OUT_ODD values."
        ),
        importance=1.0,
    ),
    Rubric(
        rubric_id="importance_weighting",
        description=(
            "Importance weights (0-1) reflect the criticality of each axis. "
            "Safety-critical axes (speed, obstacle_density) should have higher "
            "weights than environmental preferences."
        ),
        importance=0.7,
    ),
    Rubric(
        rubric_id="json_format_compliance",
        description=(
            "The agent output is valid JSON with all required fields: axes, "
            "each axis has type, IN_ODD, BOUNDARY (or OUT_ODD for categorical), "
            "unit, and importance."
        ),
        importance=0.8,
    ),
]


# ============================================================================
# COD CLASSIFIER RUBRICS
# ============================================================================

COD_RUBRICS = [
    Rubric(
        rubric_id="correct_classification",
        description=(
            "The COD classification (IN_ODD, BOUNDARY, OUT_ODD) correctly reflects "
            "the number and severity of violations. All IN_ODD → IN_ODD, any "
            "OUT_ODD violation → OUT_ODD, only BOUNDARY violations → BOUNDARY."
        ),
        importance=1.0,
    ),
    Rubric(
        rubric_id="violation_identification",
        description=(
            "The agent correctly identifies which ODD axes are violated and their "
            "severity. Violations should match actual exceedances of IN_ODD or "
            "BOUNDARY thresholds."
        ),
        importance=1.0,
    ),
    Rubric(
        rubric_id="confidence_calibration",
        description=(
            "Confidence scores reflect classification certainty. Clear violations "
            "should have high confidence (>0.9), borderline cases lower confidence. "
            "Confidence should correlate with violation magnitude."
        ),
        importance=0.8,
    ),
    Rubric(
        rubric_id="reasoning_quality",
        description=(
            "The reasoning clearly explains why the classification was chosen, "
            "citing specific axes and values. Reasoning should be traceable to "
            "compliance data."
        ),
        importance=0.7,
    ),
    Rubric(
        rubric_id="json_format_compliance",
        description=(
            "The agent output is valid JSON with required fields: cod_classification, "
            "confidence, reasoning, and contributing_factors."
        ),
        importance=0.7,
    ),
]


# ============================================================================
# COMPLIANCE AGENT RUBRICS
# ============================================================================

COMPLIANCE_RUBRICS = [
    Rubric(
        rubric_id="accurate_comparison",
        description=(
            "The agent accurately compares actual values from perception/motion "
            "analysis against ODD specification ranges. Each axis is evaluated "
            "correctly (IN_ODD, BOUNDARY, OUT_ODD)."
        ),
        importance=1.0,
    ),
    Rubric(
        rubric_id="violation_detection",
        description=(
            "All violations (OUT_ODD) and warnings (BOUNDARY) are correctly "
            "identified. No false positives or missed violations. Thresholds "
            "applied consistently."
        ),
        importance=1.0,
    ),
    Rubric(
        rubric_id="importance_weighting",
        description=(
            "Axis importance from ODD spec is properly considered. High-importance "
            "violations should be weighted more heavily in overall assessment."
        ),
        importance=0.8,
    ),
    Rubric(
        rubric_id="summary_quality",
        description=(
            "Compliance summary clearly communicates overall status and key "
            "violations. Summary should prioritize critical issues and provide "
            "actionable context."
        ),
        importance=0.7,
    ),
    Rubric(
        rubric_id="json_format_compliance",
        description=(
            "The agent output is valid JSON with required fields: overall_compliance, "
            "axis_compliance (per axis with status and actual value), violations, "
            "warnings, and summary."
        ),
        importance=0.7,
    ),
]


# ============================================================================
# REPORT AGENT RUBRICS
# ============================================================================

REPORT_RUBRICS = [
    Rubric(
        rubric_id="executive_summary_quality",
        description=(
            "Executive summary concisely captures scenario, overall compliance, and "
            "key findings. Should be understandable by non-technical stakeholders "
            "and highlight critical issues."
        ),
        importance=0.9,
    ),
    Rubric(
        rubric_id="findings_completeness",
        description=(
            "Key findings section covers all major violations, warnings, and notable "
            "observations from perception/motion/collision analysis. Findings are "
            "specific and evidence-based."
        ),
        importance=1.0,
    ),
    Rubric(
        rubric_id="recommendations_actionability",
        description=(
            "Recommendations are specific, actionable, and prioritized. Each "
            "recommendation addresses a concrete finding and suggests clear next "
            "steps (e.g., 'Reduce max speed to X m/s', 'Improve path planning')."
        ),
        importance=1.0,
    ),
    Rubric(
        rubric_id="risk_assessment_accuracy",
        description=(
            "Risk assessment accurately reflects the severity of compliance "
            "violations and operational risks. Risk level (low/moderate/high) "
            "should align with violation count and importance."
        ),
        importance=0.9,
    ),
    Rubric(
        rubric_id="clarity_and_structure",
        description=(
            "Report is well-structured with clear sections, logical flow, and "
            "appropriate level of detail. Avoids jargon where possible or explains "
            "technical terms."
        ),
        importance=0.7,
    ),
    Rubric(
        rubric_id="json_format_compliance",
        description=(
            "The agent output is valid JSON with required fields: executive_summary, "
            "key_findings, recommendations, risk_assessment, and metadata."
        ),
        importance=0.7,
    ),
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
