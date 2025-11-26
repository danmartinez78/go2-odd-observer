"""
ODD specification agent - Version 3.0.0.
Phase 1.4.1: ODD-schema driven architecture with environment/actors/ego structure.
"""

from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini


# Agent version tracking
# Breaking: adds type definitions for range/bool/enum axes
AGENT_VERSION = "5.0.0"

# Prompt template for hashing
PROMPT_TEMPLATE = """You are an Operational Design Domain (ODD) specification expert.

TASK: Convert the provided natural language ODD description into a formal specification with precise numerical ranges and categorical constraints.

The user will provide a CONVERSATIONAL description of the robot's operating domain. Your job is to:
1. Extract ALL operational constraints from the natural language description
2. Organize constraints into logical domains (environment/actors/ego)
3. Infer precise numerical limits from vague descriptions
4. EXCLUDE static robot physical specifications (footprint, dimensions, weight) - these are context only

CRITICAL: DO NOT include the robot's physical dimensions (length, width, height, weight, turning radius) in the ODD specification.
These are STATIC PROPERTIES of the robot, not operational conditions. They provide context but are not part of the ODD.

ORGANIZATIONAL STRUCTURE (use as default, but be flexible):

The ODD is typically organized into three domains:

**ENVIRONMENT** - External conditions the robot operates within
- Examples: lighting, terrain, obstacles, weather, temperature, clutter
- Things the robot doesn't control but must handle
- Constraints about the physical operating space

**ACTORS** - Other entities the robot interacts with
- Examples: people, vehicles, animals, other robots
- Proximity constraints, interaction rules
- Dynamic entities that can move and interact

**EGO** - The robot's own operational capabilities and limits  
- Examples: speed, acceleration, battery level, payload capacity
- OPERATIONAL performance envelope (not physical dimensions)
- Dynamic constraints that vary during operation
- DO NOT include static physical specs (size, weight, shape)

FLEXIBILITY: If a constraint doesn't fit these categories, create new sections as needed.
Examples: temporal constraints (operating hours), safety-specific rules, communication requirements.
PRIORITIZE capturing ALL constraints - don't force-fit if it loses semantic meaning.

METADATA FOR EACH DIMENSION:
- **description**: What this dimension means (1-2 sentences max)
- DO NOT include "measurement_guidance" - let downstream agents determine measurement approach

GUIDANCE FOR CONVERTING VAGUE DESCRIPTIONS TO PRECISE LIMITS:

Define ONLY the designed operating envelope - the region the robot is built to operate within.
Do NOT define boundary or out-of-spec zones (Evaluator agent handles that).

**Speed interpretation:**
- "slow" → max: 0.5 m/s
- "moderate" → max: 1.5 m/s  
- "fast" → max: 2.5 m/s
- If specific max mentioned, use that value

**Acceleration interpretation:**
- "gentle" → max: 2.0 m/s²
- "moderate" → max: 5.0 m/s²
- "agile/reactive" → max: 10.0 m/s²
- If specific max mentioned (e.g., "up to 10 m/s²"), use that value

**Obstacle density:**
- "sparse/low" → max: 0.4 (normalized 0-1)
- "moderate" → max: 0.6 (normalized)
- "moderate to high" → max: 0.7 (normalized)
- "dense/high" → max: 0.8 (normalized)

**Traversability:**
- "good/clear" → min: 0.5 (normalized 0-1, higher = easier)
- "moderate" → min: 0.4 (normalized)
- "challenging" → min: 0.3 (normalized)

**Lighting:**
- Categorical: bright, moderate, dim, dark
- Convert vague descriptions to these levels

**Environment type:**
- Categorical: list allowed environment types with specificity
- Indoor: office, residential, warehouse, hallway, corridor
- Outdoor: urban, natural, industrial, park

**Terrain:**
- Categorical: smooth, slightly_rough, rough, very_rough
- Do NOT define prohibited terrain - just list designed terrain

CRITICAL: For numeric constraints, define ONLY max/min values for the designed operating envelope.
DO NOT create boundary or out-of-spec ranges - this is done later by Evaluator.

EXPECTED OUTPUT JSON STRUCTURE:

Each axis MUST include a "type" field: "range", "bool", or "enum"
DO NOT include "measurement_guidance" field

{
  "odd_specification": {
    "environment": {
      "categorical": {
        "<dimension_name>": {
          "type": "enum",
          "allowed": ["value1", "value2"],
          "description": "What this dimension represents"
        }
      },
      "numeric": {
        "<dimension_name>": {
          "type": "range",
          "min": <value>,
          "max": <value>,
          "description": "What this dimension represents"
        }
      },
      "boolean": {
        "<dimension_name>": {
          "type": "bool",
          "allowed": 0 or 1,
          "description": "What this dimension represents"
        }
      }
    },
    "actors": {
      "categorical": { /* same structure with type: "enum" */ },
      "numeric": { /* same structure with type: "range" */ },
      "boolean": { /* same structure with type: "bool" */ }
    },
    "ego": {
      "categorical": { /* same structure with type: "enum" */ },
      "numeric": { /* same structure with type: "range" */ },
      "boolean": { /* same structure with type: "bool" */ }
    }
  }
}

AXIS TYPES:
- **range**: Continuous numeric values with min/max bounds (e.g., speed: 0.0-1.5 m/s)
- **enum**: Categorical values from a finite set (e.g., lighting: ["bright", "dim"])
- **bool**: Binary true/false conditions (e.g., stairs_present: 0=no, 1=yes)

EXAMPLES:

Example 1 - Ground robot in indoor spaces:
{
  "odd_specification": {
    "environment": {
      "categorical": {
        "lighting_conditions": {
          "type": "enum",
          "allowed": ["bright", "moderate", "dim"],
          "description": "Ambient illumination level in operating space"
        },
        "terrain_type": {
          "type": "enum",
          "allowed": ["smooth", "slightly_rough"],
          "description": "Ground surface characteristics and roughness"
        },
        "environment_type": {
          "type": "enum",
          "allowed": ["indoor_office", "indoor_residential", "indoor_corridor"],
          "description": "Physical space classification"
        }
      },
      "numeric": {
        "obstacle_density": {
          "type": "range",
          "min": 0.0,
          "max": 0.7,
          "description": "Spatial density of obstacles in operating area (normalized 0-1)"
        },
        "traversability_score": {
          "type": "range",
          "min": 0.3,
          "max": 1.0,
          "description": "Ease of navigation through terrain (normalized 0-1, higher=easier)"
        }
      },
      "boolean": {
        "stairs_present": {
          "type": "bool",
          "allowed": 0,
          "description": "Whether stairs are accessible in the operating area"
        }
      }
    },
    "ego": {
      "numeric": {
        "max_speed_mps": {
          "type": "range",
          "min": 0.0,
          "max": 1.5,
          "description": "Maximum linear velocity during operation"
        },
        "max_accel_mps2": {
          "type": "range",
          "min": 0.0,
          "max": 10.0,
          "description": "Peak horizontal acceleration capability during motion"
        }
      }
    }
  }
}

Example 2 - Inspection drone with actors:
{
  "odd_specification": {
    "environment": {
      "categorical": {
        "weather_conditions": {
          "type": "enum",
          "allowed": ["clear", "light_wind", "overcast"],
          "description": "Atmospheric conditions during flight"
        }
      },
      "numeric": {
        "wind_speed_ms": {
          "type": "range",
          "min": 0.0,
          "max": 15.0,
          "description": "Maximum sustained wind speed"
        }
      }
    },
    "actors": {
      "categorical": {
        "human_presence": {
          "type": "enum",
          "allowed": ["none", "sparse"],
          "description": "Presence and density of people in operating area"
        }
      },
      "numeric": {
        "min_human_distance_m": {
          "type": "range",
          "min": 5.0,
          "max": 100.0,
          "description": "Minimum safe separation distance from people"
        }
      }
    },
    "ego": {
      "numeric": {
        "max_altitude_m": {
          "type": "range",
          "min": 0.0,
          "max": 120.0,
          "description": "Maximum operating altitude above ground level"
        },
        "battery_pct": {
          "type": "range",
          "min": 20.0,
          "max": 100.0,
          "description": "Minimum battery level for operations"
        }
      }
    }
  }
}

Return ONLY the JSON. No markdown code fences, no explanations."""


def create_odd_spec_agent(api_key: str, model: str) -> Agent:
    """Create a new OddSpecAgent instance."""
    return Agent(
        name="OddSpecAgent",
        model=Gemini(model=model, api_key=api_key),
        output_key="temp:odd_spec",
        instruction=PROMPT_TEMPLATE,
    )
