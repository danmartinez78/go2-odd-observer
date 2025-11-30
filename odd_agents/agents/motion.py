"""
Motion analysis agent (v9.0.0 - single batch tool).
Calls one tool that processes all windows, auto-saves artifact, and returns full data.
"""

from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.genai import Client

from ..tools.motion import create_motion_tools


# Agent version
# v8.0.0: Full data output to state (per_window included), save tool now optional
# v9.0.0: Single batch tool - one call processes all windows, auto-saves artifact
# v10.0.0: Temporal analysis - agent does higher-order analysis, outputs summary not raw data
MOTION_AGENT_VERSION = "10.0.0"


MOTION_AGENT_PROMPT = """You are a motion analysis agent performing TEMPORAL ANALYSIS across windows.

INPUT: ODD Specification: {temp:odd_spec}

## WORKFLOW

### Step 1: Call the Tool
Extract relevant ODD dimensions (ego motion: speed, accel, stability) and call:
analyze_all_motion_tool(odd_context)

The tool processes ALL windows and returns per-window IMU analysis. Artifact auto-saved.

### Step 2: TEMPORAL ANALYSIS (Your Job)
After receiving tool results, analyze ACROSS windows:
- MOTION TRANSITIONS: stationary → moving → rotating sequences
- STABILITY TRENDS: Is roll/pitch envelope stable or degrading?
- ANOMALIES: Sudden acceleration spikes, unexpected jerk?
- STATIONARY DETECTION: Which windows show robot at rest?

### Step 3: Output SUMMARY JSON (Not Raw Data)

Output this summary format - do NOT echo raw per_window data:

{
  "windows_analyzed": <count>,
  "temporal_analysis": {
    "motion_transitions": ["stationary→moving at w002", "rotating in w003"],
    "stability_trend": "stable|degrading|improving",
    "anomalies": ["acceleration spike in w002"]
  },
  "summary": {
    "dominant_motion_state": "stationary|moving|rotating|complex",
    "max_accel_mps2": <peak across all windows>,
    "max_roll_deg": <peak>,
    "max_pitch_deg": <peak>,
    "max_angular_velocity_radps": <peak>,
    "peak_jerk_mps3": <peak>,
    "stationary_windows": ["w001", "w003"]
  },
  "issues": ["Peak pitch 12.1° in w003 approaches limit"],
  "alerts": ["High jerk detected in w002"]
}

CRITICAL: The artifact has full per-window data. Your output is the SUMMARY for downstream agents.
"""


def create_motion_agent(
    scenario_path: str, genai_client: Client, model: str, api_key: str
) -> Agent:
    """Create motion agent with single batch tool."""
    (analyze_all,) = create_motion_tools(scenario_path, genai_client, model)

    return Agent(
        name="MotionAgent",
        model=Gemini(model=model, api_key=api_key),
        tools=[analyze_all],
        output_key="temp:motion_summary",
        instruction=MOTION_AGENT_PROMPT,
    )
