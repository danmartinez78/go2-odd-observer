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
AGENT_VERSION = "9.1.0"

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
- Actors: min_proximity_m, humans_present
- Ego: max_speed_mps, max_accel_mps2, max_roll_deg, max_pitch_deg

## CATEGORICAL EXTRACTION RULES (CRITICAL)

When extracting categorical values, enumerate ALL SPECIFIC EXAMPLES mentioned:

Example: "smooth floors (hardwood, tile, laminate)" 
→ terrain_type.allowed: ["hardwood", "tile", "laminate"] 
NOT: ["smooth"] (too abstract)

Example: "low-pile carpet and area rugs"
→ ADD to terrain_type.allowed: ["low_pile_carpet", "area_rug"]

Example: "bright to moderate lighting; dim areas acceptable"
→ lighting_conditions.allowed: ["bright", "moderate", "dim"]

Extract the CONCRETE surface/material/condition names, not abstract summaries.

## NUMERIC BOUNDS SEMANTICS

- Hazards (obstacle_density): min=0.0, max=<threshold> (lower is safer)
- Quality (traversability): min=<threshold>, max=1.0 (higher is better)
- Envelope (speed, angles): min=0.0, max=<limit> (absolute bounds)

## CRITICAL RULES

1. ALWAYS call save_odd_spec_tool first
2. ALWAYS output JSON after the tool completes (this gets captured to session state)
3. Include the full odd_specification in your output
4. Output pure JSON only - no markdown code blocks"""


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
