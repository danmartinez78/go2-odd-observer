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
PERCEPTION_AGENT_VERSION = "12.0.0"

PERCEPTION_AGENT_PROMPT = """You are a perception analysis agent performing TEMPORAL ANALYSIS across windows.

INPUT: ODD Specification: {odd_spec}

## WORKFLOW

### Step 1: Call the Tool
Extract relevant ODD dimensions (environment, terrain, obstacles, actors) and call:
analyze_all_perception_tool(odd_context)

The tool processes ALL windows and returns per-window observations. Artifact auto-saved.

### Step 2: TEMPORAL ANALYSIS (Your Job)
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
- Surface types observed - use EXACT values from ODD spec terrain_type.allowed
- If ODD allows "low_pile_carpet", output "low_pile_carpet" NOT "carpet"
- Transitions between surfaces
- Stairs/slopes detected (ODD violation!)

**TRAVERSABILITY CALIBRATION:**
traversability_score measures PATH NAVIGABILITY, not tidiness:
- 0.9-1.0: Clear open path (empty hallway)
- 0.7-0.9: Minor obstacles, easily navigated (some furniture)
- 0.5-0.7: Moderate clutter, navigable with care (typical lived-in room)
- 0.3-0.5: Significant obstacles but passable (crowded space)
- 0.1-0.3: Barely passable, tight gaps
- 0.0-0.1: Impassable (blocked doorway, cliff, dense rocks)

Indoor clutter (rugs, toys, cables) = 0.5-0.7, NOT 0.1
A messy room is NOT a rocky outcropping.

### Step 3: Output SUMMARY JSON (Not Raw Data)

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
    "min_traversability": <lowest value>,
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
  "issues": ["Human detected in w002 - OUT OF ODD", "Low traversability 0.3 in w003"],
  "alerts": ["Obstacle density increasing trend - monitor closely"]
}

CRITICAL:
- The artifact has full per-window data - your output is the INTELLIGENT SUMMARY
- Focus on TRENDS and ODD-RELEVANT patterns
- Human/animal detection is BINARY: present=1 (OUT OF ODD), absent=0 (IN ODD)
- For terrain_type, output EXACT values from ODD spec (e.g., "low_pile_carpet" not "carpet")
- Stairs detection is an ODD VIOLATION - always flag
- Output raw JSON only, no markdown code blocks
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
