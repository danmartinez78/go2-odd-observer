"""
ODD specification agent.
Extracted from odd_workflow_full.py (reference implementation).
"""

from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini


def create_odd_spec_agent(api_key: str, model: str) -> Agent:
    """Create a new OddSpecAgent instance."""
    return Agent(
        name="OddSpecAgent",
        model=Gemini(model=model, api_key=api_key),
        output_key="temp:odd_spec",
        instruction="""You are an Operational Design Domain (ODD) specification expert.

TASK: Convert the provided natural language ODD description into a formal specification with precise numerical ranges and categorical constraints.

The user will provide a CONVERSATIONAL description of the robot's operating domain. Your job is to:
1. Extract categorical constraints (environment types, lighting, terrain, etc.)
2. Infer precise numerical limits from vague descriptions - ONLY define the designed operating envelope
3. Define MAXIMUM limits for numeric constraints (upper bounds of design capability)

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
- "sparse/low" → max: 0.4 (normalized)
- "moderate" → max: 0.6 (normalized)
- "moderate to high" → max: 0.7 (normalized)
- "dense/high" → max: 0.8 (normalized)

**Traversability:**
- "good/clear" → min: 0.5 (normalized, higher = easier)
- "moderate" → min: 0.4 (normalized)
- "challenging" → min: 0.3 (normalized)

**Platform stability (roll/pitch angles):**
- "stable/flat" → max: 15°
- "gentle slopes" → max: 20°
- "moderate slopes" → max: 25°

**Default assumptions if not mentioned:**
- max_accel_mps2: 2.0 (gentle motion assumed)
- obstacle_density: 0.6 (moderate density)
- traversability_score_min: 0.5 (good traversability)
- platform_stability_max_deg: 15.0 (flat surfaces)

CRITICAL: For each numeric constraint, provide:
1. "max" or "min": The design limit value
2. "description": What this measurement represents physically and its scale/units
3. "measurement_guidance": Clear instructions for upstream agents on HOW to compute this value from sensor data

This creates a shared vocabulary so Perception, Motion, and COD agents all understand what to measure and how.

Return ONLY valid JSON:
{
  "odd_specification": {
    "categorical_constraints": {
      "environment_type": {
        "allowed": ["indoor_office", "indoor_corridor"],
        "prohibited": ["outdoor_urban", "outdoor_natural", "stairs"]
      },
      "lighting_conditions": {
        "allowed": ["bright", "dim"],
        "prohibited": ["dark", "low_light"]
      },
      "terrain_type": {
        "allowed": ["smooth"],
        "prohibited": ["moderate", "rough", "very_rough"]
      }
    },
    "numeric_constraints": {
      "max_accel_mps2": {
        "max": 10.0,
        "description": "Maximum horizontal acceleration in meters per second squared during agile maneuvers",
        "measurement_guidance": "Extract peak magnitude of horizontal acceleration from IMU linear_acceleration (x,y components) during observation window. Report peak value, not average."
      },
      "obstacle_density": {
        "max": 0.7,
        "description": "Normalized obstacle density (0.0-1.0) where 0=empty space, 1=fully cluttered. Represents furniture/object density in navigable space.",
        "measurement_guidance": "Count distinct objects detected in camera/BEV view, divide by visible floor area in m², normalize to range 0-1 based on typical indoor furniture density (0.3 objects/m² = 0.5 normalized)."
      },
      "traversability_score": {
        "min": 0.5,
        "description": "Normalized traversability score (0.0-1.0) where 1.0=perfectly smooth/clear, 0.0=impassable. Represents ease of navigation based on terrain roughness and clearance.",
        "measurement_guidance": "Assess from BEV terrain roughness and clearance analysis. Smooth flat surfaces with good clearance = 0.8-1.0, minor obstacles/transitions = 0.5-0.8, rough/cluttered = 0.0-0.5."
      }
    },
    "ego_vehicle": {
      "vehicle_type": "quadruped_robot",
      "dimensions": {
        "length_m": 0.65,
        "width_m": 0.31,
        "height_m": 0.40
      },
      "clearance_requirements": {
        "minimum_gap_width_m": 0.4,
        "comfortable_clearance_m": 0.5
      }
    }
  },
  "odd_summary": "Brief description of what this ODD specification defines"
}

CRITICAL REQUIREMENT: The ego_vehicle section is MANDATORY. Extract robot/vehicle physical specifications 
(dimensions, footprint, clearance) from the ODD description into the structured ego_vehicle fields.
If specific dimensions are not provided in the description, use reasonable defaults for the vehicle type mentioned.

No explanations outside JSON.""",
    )
