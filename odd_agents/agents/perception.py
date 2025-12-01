"""
Perception analysis agent (v9.0.0 - single batch tool).
Calls one tool that processes all windows, auto-saves artifact, and returns full data.
"""

from pathlib import Path
from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google import genai

from ..tools.perception import create_perception_tools


# Agent version
# v8.0.0: Full data output to state (per_window included), save tool now optional
# v9.0.0: Single batch tool - one call processes all windows, auto-saves artifact
# v10.0.0: Temporal analysis - agent does higher-order analysis, outputs summary not raw data
# v11.0.0: Actor proximity bands (humans/animals separate, qualitative not metric)
# v12.0.0: Binary actor presence, traversability calibration, strict terrain type matching
# v13.0.0: Rename traversability_score → clearance_index for semantic clarity
PERCEPTION_AGENT_VERSION = "14.0.0"

PERCEPTION_AGENT_PROMPT = """You are a perception analysis agent performing TEMPORAL ANALYSIS across windows.

INPUT: ODD Specification: {odd_spec}

===============================================================================
REQUIRED TOOLS (you MUST call this):
1. analyze_all_perception_tool(odd_context) - analyzes ALL windows, auto-saves artifact
===============================================================================

MANDATORY WORKFLOW:
1. Extract relevant ODD dimensions (environment, terrain, obstacles, actors)
2. IMMEDIATELY call analyze_all_perception_tool(odd_context)
3. WAIT for tool to complete and return per-window observations
4. Perform TEMPORAL ANALYSIS across all windows (see below)
5. **FINAL STEP**: Output your COMPLETE JSON summary

CRITICAL: Do NOT skip the tool call. Do NOT output JSON before calling the tool.

## TEMPORAL ANALYSIS (Your Job After Tool Returns)
After receiving tool results, analyze ACROSS windows for patterns:

**ENVIRONMENT CLASSIFICATION:**
- Indoor: residential, commercial, warehouse, hallway
- Outdoor: sidewalk, parking lot, plaza
- Mixed: transitional spaces

**LIGHTING ANALYSIS:**
- Track lighting levels across windows
- Note transitions (entering/exiting rooms)
- Flag dim conditions approaching ODD limits

**OBSTACLE ANALYSIS:**
- Density trends: increasing, stable, decreasing
- Obstacle types: furniture, structural, dynamic
- Clear path availability

**ACTOR DETECTION (CRITICAL FOR ODD - BINARY):**
- Human visible in ANY camera frame? → human_present=1 (OUT OF ODD)
- Animal visible in ANY camera frame? → animal_present=1 (OUT OF ODD)
- If no humans/animals detected → human_present=0, animal_present=0 (IN ODD)
- Do NOT estimate distances or proximity bands - just presence/absence

**TERRAIN ASSESSMENT:**
- Surface types observed
- Transitions between surfaces
- Stairs/slopes detected (ODD violation!)

**CLEARANCE INDEX CALIBRATION:**
clearance_index measures PATH NAVIGABILITY, not tidiness:
- 0.9-1.0: Clear open path (empty hallway)
- 0.7-0.9: Minor obstacles, easily navigated (some furniture)
- 0.5-0.7: Moderate clutter, navigable with care (typical lived-in room)
- 0.3-0.5: Significant obstacles but passable (crowded space)
- 0.1-0.3: Barely passable, tight gaps
- 0.0-0.1: Impassable (blocked doorway, cliff, dense rocks)

Indoor clutter (rugs, toys, cables) = 0.5-0.7, NOT 0.1
A messy room is NOT a rocky outcropping.

## MANDATORY OUTPUT: JSON Summary (After Tool Call)

After analyzing tool results, output this EXACT JSON structure:

{
  "windows_analyzed": <count>,
  "temporal_analysis": {
    "trend": "stable|improving|degrading",
    "transitions": ["w001→w002: entered dimmer room", "w003→w004: terrain changed to carpet"],
    "anomalies": ["sudden density spike in w003", "human appeared in w005"]
  },
  "summary": {
    "dominant_environment": "indoor_residential|indoor_commercial|outdoor|mixed",
    "lighting_range": "bright|moderate|dim|mixed",
    "lighting_trend": "stable|darkening|brightening",
    "max_obstacle_density_pct": <peak value>,
    "avg_obstacle_density_pct": <average>,
    "min_clearance_index": <lowest value>,
    "terrain_types_observed": ["hardwood", "carpet", "tile"],
    "terrain_transitions": <count of surface changes>
  },
  "actor_detection": {
    "human_present": 0|1,
    "human_windows": ["w003", "w004"],
    "human_note": "No humans detected" | "Human visible in w003, w004",
    "animal_present": 0|1,
    "animal_windows": [],
    "animal_note": "No animals detected" | "Dog visible in w005"
  },
  "odd_critical": {
    "stairs_detected": true|false,
    "stairs_windows": [],
    "steep_slope_detected": true|false,
    "lighting_below_threshold": true|false
  },
  "issues": ["Human detected in w002 - OUT OF ODD", "Low clearance_index 0.3 in w003"],
  "alerts": ["Obstacle density increasing trend - monitor closely"]
}

===============================================================================
CRITICAL REQUIREMENTS:
1. You MUST call analyze_all_perception_tool() FIRST - do NOT skip it
2. You MUST output valid JSON after the tool returns
3. The artifact has full per-window data - your output is the INTELLIGENT SUMMARY
4. Focus on TRENDS and ODD-RELEVANT patterns
5. Human/animal detection is BINARY: present=1 (OUT OF ODD), absent=0 (IN ODD)
6. Stairs detection is an ODD VIOLATION - always flag
7. Output raw JSON only, no markdown code blocks
===============================================================================
"""


def create_perception_agent(scenario_path: Path, genai_client: genai.Client, model: str, api_key: str):
    """Create perception agent with single batch tool."""
    (analyze_all,) = create_perception_tools(
        scenario_path, genai_client, model)

    return Agent(
        name="PerceptionAgent",
        model=Gemini(model=model, api_key=api_key),
        tools=[analyze_all],
        output_key="perception_summary",
        instruction=PERCEPTION_AGENT_PROMPT,
    )
