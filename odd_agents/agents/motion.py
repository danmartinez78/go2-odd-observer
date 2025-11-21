"""
Motion analysis agents.
Extracted from odd_workflow_full.py (reference implementation).
"""

from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini

from ..config import GEMINI_MODEL_MOTION, GOOGLE_API_KEY
from ..tools import LIST_WINDOWS, ANALYZE_MOTION


motion_loop_agent = Agent(
    name="MotionLoopAgent",
    model=Gemini(model=GEMINI_MODEL_MOTION, api_key=GOOGLE_API_KEY),
    tools=[LIST_WINDOWS, ANALYZE_MOTION],
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

motion_summary_agent = Agent(
    name="MotionSummaryAgent",
    model=Gemini(model=GEMINI_MODEL_MOTION, api_key=GOOGLE_API_KEY),
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
