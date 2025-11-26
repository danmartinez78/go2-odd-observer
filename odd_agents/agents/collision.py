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
    """Create a new CollisionLoopAgent instance for multimodal collision detection."""
    from ..tools.perception import create_perception_tools

    list_windows_tool, _ = create_perception_tools(
        scenario_path, genai_client, model)
    analyze_collision_tool = create_collision_tools(
        scenario_path, genai_client, model)

    return Agent(
        name="CollisionLoopAgent",
        model=Gemini(model=model, api_key=api_key),
        tools=[list_windows_tool, analyze_collision_tool],
        output_key="temp:collision_data",
        instruction="""You orchestrate collision detection with intelligent ODD filtering and cross-window reasoning.

**INPUT**:
- ODD Specification: {temp:odd_spec?}
- Available tools: list_windows_tool, analyze_collision_tool

**YOUR RESPONSIBILITIES**:

1. **ODD FILTERING** (minimal for collision detection):
   - Collision detection typically needs minimal ODD context
   - May include: robot physical dimensions (for contact geometry), safety constraints
   - Most collision detection is about binary event detection, not ODD compliance
   - Pass minimal relevant context or empty dict - use your judgment

2. **PER-WINDOW ANALYSIS**:
   - Call list_windows_tool() to get window IDs
   - For each window, call analyze_collision_tool(window_id=..., odd_context=<filtered_odd>)
   - Collect all tool responses

3. **CROSS-WINDOW REASONING**:
   After collecting all results, analyze collision patterns:
   - Collision clustering: Do collisions occur in bursts or isolated?
   - Temporal context: What precedes/follows collision events?
   - False positive patterns: Repeated detections that may be artifacts?
   - Impact severity progression: Are collisions getting worse/better?
   - Environmental correlation: Do collisions relate to terrain/obstacles?

**OUTPUT JSON**:
{
  "windows_analyzed": [...],
  "collision_detections": [...],
  "cross_window_observations": [
    "Collision pattern: [temporal distribution of collision events]",
    "Event clustering: [isolated vs sequential collisions]",
    "Severity trends: [are impacts increasing/decreasing]",
    "Context analysis: [what conditions precede collisions]",
    "Overall assessment: [collision-free vs problematic scenario]"
  ]
}

Provide temporal insights about collision events, not just per-window detections.""",
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
   - Collect detailed evidence from detected collisions
3. Produce final JSON:
{
  "windows_analyzed": [...],
  "overall_collision_stats": {
    "total_windows": <int>,
    "collisions_detected_count": <int>,
    "no_collision_count": <int>,
    "collision_detection_rate": <float 0-1>
  },
  "collisions_detected": [
    {
      "window_id": "...",
      "confidence": <float>,
      "evidence": {
        "imu_analysis": "...",
        "camera_analysis": "...",
        "bev_analysis": "...",
        "multimodal_reasoning": "..."
      },
      "imu_metrics": {...}
    }
  ],
  "all_detections": [<complete list from collision_detections>]
}
Only output JSON.""",
    )
