"""
Motion analysis agents - Version 3.0.0.
Phase 1.4.1: ODD-schema driven architecture with dual-output structure.
"""

from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.genai import Client

from ..tools.motion import create_motion_tools


# Agent versions
MOTION_LOOP_VERSION = "3.0.0"  # Breaking: ODD-guided + observations structure
MOTION_SUMMARY_VERSION = "3.0.0"  # Breaking: ODD-guided + observations structure


def create_motion_loop_agent(
    scenario_path: str, genai_client: Client, model: str, api_key: str
) -> Agent:
    """Create a new MotionLoopAgent instance."""
    from ..tools.perception import create_perception_tools

    list_windows_tool, _ = create_perception_tools(
        scenario_path, genai_client, model)
    analyze_motion_tool = create_motion_tools(
        scenario_path, genai_client, model)

    return Agent(
        name="MotionLoopAgent",
        model=Gemini(model=model, api_key=api_key),
        tools=[list_windows_tool, analyze_motion_tool],
        output_key="temp:motion_data",
        instruction="""You orchestrate motion analysis across all scenario windows.

Steps you MUST follow:
1. Call list_windows_tool() exactly once to get the ordered window_id list.
2. For each window_id returned (in that order), call analyze_motion_tool(window_id=...).
3. Collect each tool response exactly as returned.
4. After all windows are processed, respond with JSON:
{
  "windows_analyzed": ["..."],
  "per_window_motion": [<tool_response_objects_in_order>]
}
Do not add commentary. Ensure valid JSON.""",
    )


def create_motion_summary_agent(api_key: str, model: str) -> Agent:
    """Create a new MotionSummaryAgent instance."""
    return Agent(
        name="MotionSummaryAgent",
        model=Gemini(model=model, api_key=api_key),
        output_key="temp:motion_output",
        instruction="""You finalize the motion analysis report with ODD-guided measurements and general observations.

INPUT DATA:
- ODD Specification: {temp:odd_spec?}
- Per-window motion: {temp:motion_data?}

If no data is provided, respond with:
{"error": "missing_motion_data"}

Otherwise, extract TWO types of information:

**1. ODD-GUIDED MEASUREMENTS** (for compliance checking):
- Read the ODD spec's ego section (robot capabilities)
- For each numeric dimension related to motion, calculate metrics as specified in measurement_guidance
- Common ego dimensions: max_accel_mps2, max_angular_rate_rad_s, max_speed_mps (when available)
- Use dimension names from ODD spec as keys
- Calculate peak values across all windows for max constraints

**2. GENERAL OBSERVATIONS** (for safety/reliability/effectiveness context):
- Motion patterns: walking gait, stationary periods, turning maneuvers
- IMU data quality: gaps, noise, anomalies
- Camera-IMU alignment: visual motion matching inertial readings
- Unusual patterns: sudden stops, vibrations, irregular movement
- Any other motion-related context not captured in ODD measurements

OUTPUT STRUCTURE:
{
  "windows_analyzed": [...],
  "overall_stats": {
    "total_windows": <int>,
    "motion_detected_count": <int>,
    "motion_detection_rate": <float 0-1>,
    "motion_type_distribution": {"stationary": X, "translation": Y, ...},
    "overall_assessment": "stationary_scenario|low_activity|moderate_activity|high_activity"
  },
  "odd_measurements": {
    // Use ODD dimension names as keys
    // Calculate peak values for max constraints
    // Example: "max_accel_mps2": 0.14, "max_angular_rate_rad_s": 0.12
  },
  "observations": [
    "Consistent walking gait pattern across all windows",
    "No sudden movements or IMU anomalies detected",
    "Camera shows smooth forward motion matching IMU data"
    // Add any safety/reliability/performance notes
  ],
  "per_window_motion": [...]
}
Only output JSON.

PRIORITY: Capture both ODD-aligned measurements AND broader motion context.""",
    )
