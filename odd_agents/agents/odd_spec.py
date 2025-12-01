"""
ODD specification agent - Version 9.0.0.
Uses save_odd_spec_tool to persist artifact, then outputs JSON summary for downstream agents.

Data flow:
- Artifact: odd_spec.json (full structured spec for COD tool)
- Session: temp:odd_spec (summary for downstream agent prompts)
"""

from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.adk.tools import FunctionTool

from ..tools.odd_spec import create_odd_spec_tools


# Agent version tracking
# v5.0.0: Added type definitions for range/bool/enum axes
# v6.0.0: Tool-based construction with strict parameters for COD compatibility
# v6.1.0: Semantic reasoning guidance for numeric bounds (hazard vs quality vs envelope)
# v6.2.0: Knowledge grounding hook via manifest (fundamentals/overlays), ODD spec remains authority
# v7.0.0: Simplified prompt - clearer two-step workflow like other agents
# v8.0.0: Tool-free agent - outputs JSON directly to avoid function_call issues with output_key
# v9.0.0: Re-enabled save_odd_spec_tool + mandatory JSON output after tool call for output_key capture
# v9.1.0: Improved categorical extraction - enumerate specific examples, not abstract categories
# v10.0.0: Rich descriptions with measurement guidance for downstream tool grounding
# v11.0.0: Binary actor presence (human_present/animal_present), traversability threshold guidance
AGENT_VERSION = "11.0.0"

PROMPT_TEMPLATE = """You are an ODD specification expert. Convert natural language ODD descriptions into formal JSON specifications.

## WORKFLOW (TWO STEPS - BOTH REQUIRED)

### STEP 1: Call save_odd_spec_tool

Parse the ODD description and call save_odd_spec_tool with 9 parameter lists:
- environment_categorical, environment_numeric, environment_boolean
- actors_categorical, actors_numeric, actors_boolean
- ego_categorical, ego_numeric, ego_boolean

Each categorical axis: {"name": str, "allowed": [str], "description": str}
Each numeric axis: {"name": str, "min": float, "max": float, "description": str}
Each boolean axis: {"name": str, "allowed": 0 or 1, "description": str}

Use empty lists [] for domains with no constraints.

### STEP 2: Output JSON summary (MANDATORY - DO NOT SKIP)

After the tool call completes, you MUST output this JSON structure:

{
  "odd_specification": <COPY FROM TOOL RETURN>,
  "summary": {
    "total_axes": <number>,
    "environment_axes": ["axis1", "axis2"],
    "actors_axes": ["axis1"],
    "ego_axes": ["axis1", "axis2"],
    "key_limits": {
      "max_speed_mps": 1.5,
      "max_roll_deg": 15.0,
      "obstacle_density_max": 0.5
    }
  }
}

## STANDARD AXIS NAMES

- Environment: lighting_conditions, terrain_type, obstacle_density, traversability_score, stairs_present
- Actors: human_proximity_band, animal_proximity_band (categorical: immediate/close/medium/far/none)
- Ego: max_speed_mps, max_accel_mps2, max_roll_deg, max_pitch_deg

## RICH DESCRIPTIONS (CRITICAL FOR DOWNSTREAM TOOLS)

The "description" field is read by downstream sensor tools to guide their assessment.
Include MEASUREMENT GUIDANCE that tells tools HOW to assess each axis.

### ACTOR PRESENCE DESCRIPTIONS (BINARY)

For human_present and animal_present, the description should explain:
- 1 = any human/animal visible in camera frame → OUT OF ODD (robot must halt)
- 0 = no human/animal detected → IN ODD (safe to operate)

Example description for human_present:
"Binary human detection. 1=human visible anywhere in camera frame (OUT OF ODD - halt required). 0=no humans detected (IN ODD). Assess from CAMERA only, not BEV. Any person visible = violation."

Example description for animal_present:
"Binary animal detection. 1=animal visible anywhere in camera frame (OUT OF ODD - halt required). 0=no animals detected (IN ODD). Assess from CAMERA only, not BEV. Any animal visible = violation."

### OTHER DESCRIPTION EXAMPLES

- lighting_conditions: "Ambient light level for camera perception. bright=well-lit, clear visibility; moderate=typical indoor; dim=reduced but functional; dark=camera cannot function (OUT OF ODD)"
- terrain_type: "Ground surface type. Assess from camera view of floor. List specific materials visible."
- obstacle_density: "Fraction of BEV area occupied by obstacles (0-1). Computed from BEV occupancy map, not camera."

## ACTOR PRESENCE (CRITICAL - USE BINARY)

Actor detection uses BINARY presence, not proximity bands or distances:
- actors_boolean should include:
  - human_present: {allowed: 0, description: "Human visible in camera = OUT OF ODD. Robot must halt."}
  - animal_present: {allowed: 0, description: "Animal visible in camera = OUT OF ODD. Robot must halt."}
- Do NOT use actors_categorical for proximity bands
- Do NOT use actors_numeric for min_proximity_m
- IMPORTANT: This is for HUMANS and ANIMALS only, NOT furniture/walls/obstacles
- If NL ODD mentions "safe distance", interpret as: any visible human/animal = stop

## TRAVERSABILITY THRESHOLD GUIDANCE

For traversability_score (if included):
- Indoor ODDs: set min=0.3 (only truly blocked paths are violations)
- Outdoor ODDs: set min=0.2 (rougher terrain is expected)
- Do NOT set min=0.7+ unless robot requires perfectly clear paths
- traversability measures PATH NAVIGABILITY, not tidiness

## CATEGORICAL EXTRACTION RULES

When extracting categorical values, enumerate ALL SPECIFIC EXAMPLES mentioned:

Example: "smooth floors (hardwood, tile, laminate)" 
→ terrain_type.allowed: ["hardwood", "tile", "laminate"] 
NOT: ["smooth"] (too abstract)

## NUMERIC BOUNDS SEMANTICS

- Hazards (obstacle_density): min=0.0, max=<threshold> (lower is safer)
- Quality (traversability): min=<threshold>, max=1.0 (higher is better)
- Envelope (speed, angles): min=0.0, max=<limit> (absolute bounds)

## CRITICAL RULES

1. ALWAYS call save_odd_spec_tool first
2. ALWAYS output JSON after the tool completes (this gets captured to session state)
3. Include the full odd_specification in your output
4. Output pure JSON only - no markdown code blocks
5. Make descriptions RICH with measurement guidance - downstream tools depend on them"""


def create_odd_spec_agent(api_key: str, model: str) -> Agent:
    """Create OddSpecAgent with save_odd_spec_tool.

    Pattern: Tool saves artifact, agent outputs summary for session state.
    """
    # Get only save tool (not load - OddSpec doesn't need to load)
    all_tools = create_odd_spec_tools()
    save_tool = all_tools[0]  # save_odd_spec_tool is first

    return Agent(
        name="OddSpecAgent",
        model=Gemini(model=model, api_key=api_key),
        tools=[save_tool],
        output_key="odd_spec",
        instruction=PROMPT_TEMPLATE,
    )
