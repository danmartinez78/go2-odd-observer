"""
Collision risk analysis agents.
Extracted from odd_workflow_full.py (reference implementation).
"""

from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini

from ..config import GEMINI_MODEL_COLLISION, GOOGLE_API_KEY
from ..tools import LIST_WINDOWS, ANALYZE_COLLISION_RISK


def create_collision_loop_agent() -> Agent:
    """Create a new CollisionLoopAgent instance."""
    return Agent(
        name="CollisionLoopAgent",
        model=Gemini(model=GEMINI_MODEL_COLLISION, api_key=GOOGLE_API_KEY),
        tools=[LIST_WINDOWS, ANALYZE_COLLISION_RISK],
        output_key="temp:collision_data",
        instruction="""You orchestrate collision risk analysis across all scenario windows.

Steps you MUST follow:
1. Call list_windows_tool() exactly once to get the ordered window_id list.
2. For each window_id returned (in that order), call analyze_collision_risk_tool(window_id=...).
3. Collect each tool response exactly as returned.
4. After all windows are processed, respond with JSON:
{
  "windows_analyzed": ["..."],
  "collision_events": [<tool_response_objects_in_order>]
}
Do not add commentary. Ensure valid JSON.""",
    )


def create_collision_summary_agent() -> Agent:
    """Create a new CollisionSummaryAgent instance."""
    return Agent(
        name="CollisionSummaryAgent",
        model=Gemini(model=GEMINI_MODEL_COLLISION, api_key=GOOGLE_API_KEY),
        output_key="temp:collision_output",
        instruction="""You finalize the collision risk report.

Input data from the previous agent:
{temp:collision_data?}

If no data is provided, respond with:
{"error": "missing_collision_data"}

Otherwise:
1. Read the JSON string carefully.
2. Calculate overall statistics (count by risk_level, average collision_likelihood_score).
3. Produce final JSON:
{
  "windows_analyzed": [...],
  "overall_collision_stats": {
    "total_windows": <int>,
    "safe_count": <int>,
    "caution_count": <int>,
    "alert_count": <int>,
    "avg_collision_likelihood": <float>
  },
  "collision_events": [...]
}
Only output JSON.""",
    )
