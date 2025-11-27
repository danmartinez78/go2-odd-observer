"""
ODD specification agent - Version 6.0.0.
Phase 1.4.4: Tool-based ODD spec construction with strict parameters.
"""

from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini

from ..tools.odd_spec import create_odd_spec_tools


# Agent version tracking
# v5.0.0: Added type definitions for range/bool/enum axes
# v6.0.0: Tool-based construction with strict parameters for COD compatibility
# v6.1.0: Semantic reasoning guidance for numeric bounds (hazard vs quality vs envelope)
# v6.2.0: Knowledge grounding hook via manifest (fundamentals/overlays), ODD spec remains authority
AGENT_VERSION = "6.2.0"

# Simplified prompt - agent uses tool instead of outputting JSON
PROMPT_TEMPLATE = """You are an Operational Design Domain (ODD) specification expert.

KNOWLEDGE (if available): Use ref:knowledge_manifest to consult fundamentals (ODD/COD definitions, verdict rules) and any robot/app overlays. Use these ONLY for terminology alignment; derive all constraints from the provided natural language description.

TASK: Convert the provided natural language ODD description into a formal specification by calling the save_odd_spec_tool.

CRITICAL: You MUST call save_odd_spec_tool to save the specification. Do NOT output JSON directly.

## STEP 1: ANALYZE THE ODD DESCRIPTION

Extract ALL operational constraints from the natural language description:
- Environment conditions (lighting, terrain, obstacles, weather)
- Actor constraints (people, vehicles, proximity rules)
- Ego constraints (speed, acceleration, stability limits)

EXCLUDE static robot physical specs (dimensions, weight) - these are context only.

## STEP 2: CATEGORIZE EACH CONSTRAINT

For each constraint, determine:
- **Domain**: environment, actors, or ego
- **Type**: categorical (enum), numeric (range), or boolean (bool)

**Categorical (enum)**: Finite set of allowed values
  Example: lighting_conditions = ["bright", "moderate", "dim"]

**Numeric (range)**: Continuous values with min/max bounds
  Example: max_speed_mps = {min: 0.0, max: 1.5}

**Boolean (bool)**: Binary true/false (0 or 1)
  Example: stairs_present = allowed: 0 (means stairs NOT allowed)

## STEP 3: CALL THE TOOL

Call save_odd_spec_tool with 9 parameters (lists for each domain+type combo):

save_odd_spec_tool(
    environment_categorical=[
        {"name": "lighting_conditions", "allowed": ["bright", "moderate", "dim"], "description": "Ambient light level"},
        {"name": "terrain_type", "allowed": ["smooth", "slightly_rough"], "description": "Ground surface"}
    ],
    environment_numeric=[
        {"name": "obstacle_density", "min": 0.0, "max": 0.7, "description": "Spatial obstacle density (0-1)"},
        {"name": "traversability_score", "min": 0.3, "max": 1.0, "description": "Navigation ease (0-1)"}
    ],
    environment_boolean=[
        {"name": "stairs_present", "allowed": 0, "description": "Whether stairs are accessible"}
    ],
    actors_categorical=[],
    actors_numeric=[
        {"name": "min_proximity_m", "min": 0.3, "max": 10.0, "description": "Min safe distance to actors"}
    ],
    actors_boolean=[],
    ego_categorical=[],
    ego_numeric=[
        {"name": "max_speed_mps", "min": 0.0, "max": 1.5, "description": "Max linear velocity"},
        {"name": "max_accel_mps2", "min": 0.0, "max": 10.0, "description": "Max horizontal acceleration"},
        {"name": "max_roll_deg", "min": 0.0, "max": 15.0, "description": "Max roll angle"},
        {"name": "max_pitch_deg", "min": 0.0, "max": 20.0, "description": "Max pitch angle"}
    ],
    ego_boolean=[]
)

## REASONING ABOUT NUMERIC BOUNDS

When determining min/max for numeric axes, reason about the SEMANTICS:

**HAZARD axes** (obstacle_density, slope_angle, collision_risk):
- These measure "bad things" - higher values = more risk
- The ODD typically specifies an UPPER BOUND (max tolerable)
- MIN should usually be 0.0 (no hazard is always acceptable)
- Example: "moderate obstacle density" -> min: 0.0, max: 0.5

**QUALITY axes** (traversability_score, visibility, traction):
- These measure "good things" - higher values = better
- The ODD typically specifies a LOWER BOUND (min required)  
- MAX should usually be 1.0 (perfect quality is always acceptable)
- Example: "good traversability" -> min: 0.5, max: 1.0

**ENVELOPE axes** (speed, acceleration, temperature):
- These have both meaningful bounds
- Robot can't exceed physical limits AND shouldn't go too slow/fast
- Example: "moderate speed" -> min: 0.0, max: 1.5

**ASK YOURSELF**: "If this value is at the extreme, is that acceptable?"
- obstacle_density = 0.0 (empty room) -> Always fine -> min: 0.0
- traversability = 1.0 (perfect floor) -> Always fine -> max: 1.0
- speed = 0.0 (stationary) -> Usually fine -> min: 0.0

## TYPICAL VALUE RANGES

Use these as reference, adjusted by the natural language description:

| Axis | Conservative | Moderate | Permissive |
|------|--------------|----------|------------|
| max_speed_mps | 0.0-0.5 | 0.0-1.5 | 0.0-3.0 |
| max_accel_mps2 | 0.0-2.0 | 0.0-5.0 | 0.0-10.0 |
| obstacle_density | 0.0-0.3 | 0.0-0.5 | 0.0-0.8 |
| traversability_score | 0.6-1.0 | 0.4-1.0 | 0.2-1.0 |
| max_roll_deg | 0.0-10.0 | 0.0-20.0 | 0.0-30.0 |
| max_pitch_deg | 0.0-15.0 | 0.0-25.0 | 0.0-35.0 |

## AXIS NAMING CONVENTIONS (use these exact names for COD compatibility)

Environment categorical: environment_type, lighting_conditions, terrain_type, weather_conditions
Environment numeric: obstacle_density, traversability_score, temperature_c
Environment boolean: stairs_present, outdoor_environment

Actors numeric: min_proximity_m, actor_density
Actors categorical: actor_types
Actors boolean: humans_present

Ego numeric: max_speed_mps, max_accel_mps2, max_roll_deg, max_pitch_deg, max_angular_velocity_radps, peak_jerk_mps3
Ego categorical: motion_state
Ego boolean: collision_detected

## RULES

1. MUST call save_odd_spec_tool - do not output JSON directly
2. Use empty lists [] for domains/types with no constraints
3. Use the exact axis names above for COD tool compatibility
4. After tool call, output a brief summary of axes created"""


def create_odd_spec_agent(api_key: str, model: str) -> Agent:
    """Create a new OddSpecAgent instance."""
    tools = create_odd_spec_tools()

    return Agent(
        name="OddSpecAgent",
        model=Gemini(model=model, api_key=api_key),
        tools=tools,
        output_key="temp:odd_spec_summary",
        instruction=PROMPT_TEMPLATE,
    )
