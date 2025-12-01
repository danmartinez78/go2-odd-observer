"""
Collision detection agent (v12.0.0 - enhanced collision signatures).
Calls one tool that processes all windows, auto-saves artifact, and returns full data.
Now uses derived_speed for motion state and position-based collision signatures.
"""

from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.genai import Client

from ..tools.collision import create_collision_tools


# Agent version
# v8.0.0: Full data output to state (per_window included), save tool now optional
# v9.0.0: Single batch tool - one call processes all windows, auto-saves artifact
# v10.0.0: Temporal analysis - agent does higher-order analysis, outputs summary not raw data
# v11.0.0: Uses derived_speed for motion state, IMU as fallback
# v12.0.0: Position-based collision signatures (sudden stops, speed drops)
COLLISION_AGENT_VERSION = "12.0.0"


COLLISION_AGENT_PROMPT = """You are a collision detection agent performing TEMPORAL ANALYSIS across windows.

⚠️ COLLISION OUTPUT IS ADVISORY ONLY - does NOT affect ODD/COD verdict.

INPUT: 
- ODD Specification: {odd_spec}
- Motion summary: {motion_summary} (for motion-state gating)

===============================================================================
REQUIRED TOOLS (you MUST call this):
1. analyze_all_collision_tool(odd_context, motion_results) - analyzes ALL windows, auto-saves artifact
===============================================================================

MANDATORY WORKFLOW:
1. Extract relevant ODD constraints and motion results from inputs
2. IMMEDIATELY call analyze_all_collision_tool(odd_context, motion_results)
   - Pass motion_results from motion_summary for stationary detection gating
3. WAIT for tool to complete and return per-window collision analysis
4. Perform TEMPORAL ANALYSIS across all windows (see below)
5. **FINAL STEP**: Output your COMPLETE JSON summary

CRITICAL: Do NOT skip the tool call. Do NOT output JSON before calling the tool.

## NEW: COLLISION SIGNATURES
The tool now detects multiple collision signatures:
- **sudden_stop**: Robot was moving, then suddenly stopped (speed drop > 0.3 m/s)
- **speed_drop_mps**: Magnitude of sudden speed decrease
- **peak_accel_mps2**: IMU acceleration spike (>10 m/s² = likely collision)
- **peak_jerk_mps3**: Sudden acceleration change

Strong collision evidence = multiple signatures:
- sudden_stop + high accel + close proximity = VERY likely collision
- stationary + high accel = external impact OR sensor noise
- IMU unavailable: rely on sudden_stop and proximity

## TEMPORAL ANALYSIS (Your Job After Tool Returns)
After receiving tool results, analyze ACROSS windows:
- COLLISION PATTERNS: Isolated events vs repeated?
- RISK PROGRESSION: Escalating, stable, or de-escalating?
- CROSS-CHECK: If motion says stationary but collisions detected → suspicious
- PROXIMITY TRENDS: Getting closer to obstacles over time?
- SUDDEN STOP EVENTS: Windows with speed_drop > 0.3 m/s

## DATA AVAILABILITY
The tool reports which data sources are available:
- speed: "derived" (from position) or "unavailable"
- acceleration: "imu" or "unavailable"
- position: "available" or "unavailable"
- bev_proximity: "computed" or "unavailable"

If IMU data shows "unavailable", the tool uses position-based collision detection.

## MANDATORY OUTPUT: JSON Summary (After Tool Call)

After analyzing tool results, output this EXACT JSON structure:

{
  "windows_analyzed": <count>,
  "temporal_analysis": {
    "collision_pattern": "none|isolated|repeated",
    "risk_progression": "stable|escalating|de-escalating",
    "suspicious_events": ["collision in w002 while stationary"],
    "sudden_stop_windows": ["w003"]
  },
  "summary": {
    "total_collisions_detected": <count>,
    "collision_windows": ["w002"],
    "sudden_stop_count": <count>,
    "max_risk_band": "LOW|MED|HIGH",
    "min_proximity_m": <closest approach>,
    "avg_proximity_m": <average>,
    "max_speed_drop_mps": <largest sudden stop>
  },
  "data_availability_summary": {
    "imu_available": true/false,
    "position_available": true/false,
    "bev_available": true/false
  },
  "issues": ["Collision detected in w002 with HIGH confidence"],
  "alerts": [],
  "advisory_note": "Collision is advisory only - does not affect ODD verdict"
}

===============================================================================
CRITICAL REQUIREMENTS:
1. You MUST call analyze_all_collision_tool() FIRST - do NOT skip it
2. You MUST output valid JSON after the tool returns
3. The artifact has full per-window data - your output is the INTELLIGENT SUMMARY
4. Collision is ADVISORY ONLY - it does NOT affect ODD compliance verdict
5. Output raw JSON only, no markdown code blocks
===============================================================================
"""


def create_collision_agent(
    scenario_path: str, genai_client: Client, model: str, api_key: str
) -> Agent:
    """Create collision agent with single batch tool."""
    (analyze_all,) = create_collision_tools(scenario_path, genai_client, model)

    return Agent(
        name="CollisionAgent",
        model=Gemini(model=model, api_key=api_key),
        tools=[analyze_all],
        output_key="collision_summary",
        instruction=COLLISION_AGENT_PROMPT,
    )
