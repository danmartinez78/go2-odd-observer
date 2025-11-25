"""
Collision detection agents.
Implements binary collision detection based on IMU data.
"""

from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.genai import Client

from ..tools.collision import create_collision_tools


def create_collision_loop_agent(
    scenario_path: str, genai_client: Client, model: str, api_key: str
) -> Agent:
    """Create a new CollisionLoopAgent instance for binary collision detection."""
    from ..tools.perception import create_perception_tools

    list_windows_tool, _ = create_perception_tools(
        scenario_path, genai_client, model)
    detect_collision_tool = create_collision_tools(scenario_path)

    return Agent(
        name="CollisionLoopAgent",
        model=Gemini(model=model, api_key=api_key),
        tools=[list_windows_tool, detect_collision_tool],
        output_key="temp:collision_data",
        instruction="""You orchestrate collision detection across all scenario windows.

AVAILABLE TOOLS:
- list_windows_tool
- detect_collision_tool

MOTION DATA AVAILABLE:
{temp:motion_output?}

COLLISION DETECTION APPROACH:
This is BINARY detection - we only detect actual collisions that occurred, not risk levels.
Detection is based on IMU data thresholds:
- Acceleration spikes >10 m/s² (sudden impact)
- Angular velocity anomalies >5 rad/s (severe rotation/spin-out)
- Jerk spikes >50 m/s³ (sudden acceleration change)

Steps you MUST follow:
1. Call list_windows_tool() exactly once to get the ordered window_id list.
2. Parse the motion data from {temp:motion_output?} to extract per_window_motion array.
3. For each window_id returned (in that order):
   a. Find the corresponding motion metrics from per_window_motion (match by window_id)
   b. Call detect_collision_tool(window_id=..., motion_metrics=...)
   IMPORTANT: Tool name is exactly "detect_collision_tool" - no typos, no extra characters.
   IMPORTANT: Pass the full motion metrics object for that window.
4. Collect each tool response exactly as returned.
5. After all windows are processed, respond with JSON:
{
  "windows_analyzed": ["..."],
  "collision_detections": [<tool_response_objects_in_order>]
}
Do not add commentary. Ensure valid JSON.""",
    )


def create_collision_summary_agent(api_key: str, model: str) -> Agent:
    """Create a new CollisionSummaryAgent instance."""
    return Agent(
        name="CollisionSummaryAgent",
        model=Gemini(model=model, api_key=api_key),
        output_key="temp:collision_output",
        instruction="""You finalize the collision detection report.

Input data from the previous agent:
{temp:collision_data?}

If no data is provided, respond with:
{"error": "missing_collision_data"}

Otherwise:
1. Read the JSON string carefully.
2. Calculate overall statistics:
   - Total windows analyzed
   - Number of windows with collisions detected
   - Number of windows without collisions
   - List of collision evidence from detected windows
3. Produce final JSON:
{
  "windows_analyzed": [...],
  "overall_collision_stats": {
    "total_windows": <int>,
    "collisions_detected_count": <int>,
    "no_collision_count": <int>
  },
  "collisions_detected": [
    {
      "window_id": "...",
      "evidence": [...],
      "imu_metrics": {...}
    }
  ],
  "all_detections": [<complete list from collision_detections>]
}
Only output JSON.""",
    )
