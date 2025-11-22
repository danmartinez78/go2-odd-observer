"""
Motion analysis agents.
Extracted from odd_workflow_full.py (reference implementation).
"""

from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.genai import Client

from ..tools.motion import create_motion_tools


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
        instruction="""You finalize the motion analysis report.

Input data from the previous agent:
{temp:motion_data?}

If no data is provided, respond with:
{"error": "missing_motion_data"}

Otherwise:
1. Read the JSON string carefully.
2. Calculate overall motion statistics:
   - Motion detection rate (% windows with motion_detected=true)
   - Motion type distribution
   - Peak values across all windows
3. Produce final JSON:
{
  "windows_analyzed": [...],
  "overall_stats": {
    "total_windows": <int>,
    "motion_detected_count": <int>,
    "motion_detection_rate": <float 0-1>,
    "motion_type_distribution": {"stationary": X, "translation": Y, ...},
    "max_horizontal_accel_mps2": <float>,
    "max_angular_velocity_radps": <float>,
    "overall_assessment": "stationary_scenario|low_activity|moderate_activity|high_activity"
  },
  "per_window_motion": [...]
}
Only output JSON.""",
    )
