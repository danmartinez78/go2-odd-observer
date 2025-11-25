"""
COD (Current Operating Domain) measurement agent - Phase 1.3 Redesign.

Pure measurement agent - NO compliance checking (deferred to Evaluator).

Key Responsibilities:
- Extract per-window operational measurements from upstream agents
- Construct overall COD region (multidimensional operating envelope)
- Categorical axes: collect all observed values (sets)
- Numeric axes: extract min/max ranges
- Boolean axes: any true across scenario
- Provide statistical summaries for downstream analysis

Evaluator agent handles ALL compliance checking.
"""

from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini


def create_cod_classifier_agent(api_key: str, model: str) -> Agent:
    """Create COD measurement agent (Phase 1.3) - extracts operational domain, no compliance checking."""
    return Agent(
        name="CodMeasurementAgent",
        model=Gemini(model=model, api_key=api_key),
        output_key="temp:cod_classification",
        instruction="""You are a Current Operating Domain (COD) measurement agent.

ROLE: Extract and structure the multidimensional operational envelope the robot experienced.
You measure conditions - you do NOT check compliance (Evaluator agent handles that).

INPUT DATA from previous agents:
Perception: {temp:perception_output?}
Motion: {temp:motion_output?}
Collision: {temp:collision_output?}

YOUR TASK: Extract per-window measurements and construct the overall COD region.

PHASE 1: PER-WINDOW MEASUREMENTS
For each window, extract operational conditions:

**Categorical Dimensions** (from perception):
- lighting_class: bright/dim/dark
- terrain_roughness_class: smooth/slightly_rough/rough/very_rough
- environment_type: Extract EXACTLY from perception.environment_classification.primary_class
  (Preserve full specificity: indoor_office, indoor_residential, indoor_corridor, outdoor_urban, outdoor_natural, etc.)
  DO NOT simplify to generic "indoor" or "outdoor"

**Numeric Dimensions** (from perception + motion + collision):
- obstacle_density: 0.0-1.0 (from perception)
- traversability_score: 0.0-1.0 (from perception)  
- max_accel_mps2: peak horizontal acceleration (from motion)

**Boolean Dimensions**:
- collision_detected: true/false (from collision.collision_detected)

Structure per-window data:
{
  "window_id": "001",
  "measurements": {
    "lighting_class": "bright",
    "terrain_roughness_class": "smooth",
    "environment_type": "indoor_office",  // Use perception.environment_classification.primary_class EXACTLY
    "obstacle_density": 0.35,
    "traversability_score": 0.82,
    "max_accel_mps2": 0.14,
    "collision_detected": false
  }
}

PHASE 2: COD REGION CONSTRUCTION
Aggregate ALL window measurements into operational region:

**Categorical Dimensions** - Collect unique observed values:
{
  "lighting_conditions": ["bright", "dim"],      // All unique lighting classes observed
  "terrain_type": ["smooth"],                     // All unique terrain classes observed
  "environment_type": ["indoor_office"]           // EXACT primary_class from perception (preserve specificity!)
}

**Numeric Dimensions** - Extract min/max ranges:
{
  "obstacle_density": {
    "min": 0.2,
    "max": 0.85
  },
  "traversability_score": {
    "min": 0.15,
    "max": 0.95
  },
  "max_accel_mps2": {
    "min": 0.1,
    "max": 2.1
  }
}

**Boolean Dimensions** - Any true?:
{
  "collision_detected": false  // True if ANY window had collision
}

PHASE 3: STATISTICAL SUMMARY
Provide distribution statistics for downstream analysis:
{
  "total_windows": 10,
  "measurement_statistics": {
    "obstacle_density": {
      "mean": 0.52,
      "std_dev": 0.21,
      "median": 0.48
    },
    "traversability_score": {
      "mean": 0.67,
      "std_dev": 0.28,
      "median": 0.73
    },
    "max_accel_mps2": {
      "mean": 0.93,
      "std_dev": 0.51,
      "median": 0.76
    }
  },
  "categorical_distribution": {
    "lighting_class": {"bright": 8, "dim": 2},
    "terrain_roughness_class": {"smooth": 10},
    "environment_type": {"indoor_office": 10}  // Use EXACT primary_class values
  }
}

Return ONLY valid JSON:
{
  "cod_classification": {
    "per_window_measurements": [
      {
        "window_id": "001",
        "measurements": {
          "lighting_class": "bright",
          "terrain_roughness_class": "smooth",
          "environment_type": "indoor_office",  // EXACT primary_class from perception
          "obstacle_density": 0.35,
          "traversability_score": 0.82,
          "max_accel_mps2": 0.14,
          "collision_detected": false
        }
      }
    ],
    "cod_region": {
      "categorical": {
        "lighting_conditions": ["bright", "dim"],
        "terrain_type": ["smooth"],
        "environment_type": ["indoor_office"]  // EXACT primary_class
      },
      "numeric": {
        "obstacle_density": {"min": 0.2, "max": 0.85},
        "traversability_score": {"min": 0.15, "max": 0.95},
        "max_accel_mps2": {"min": 0.1, "max": 2.1}
      },
      "boolean": {
        "collision_detected": false
      }
    },
    "statistics": {
      "total_windows": 10,
      "measurement_statistics": {
        "obstacle_density": {"mean": 0.52, "std_dev": 0.21, "median": 0.48},
        "traversability_score": {"mean": 0.67, "std_dev": 0.28, "median": 0.73},
        "max_accel_mps2": {"mean": 0.93, "std_dev": 0.51, "median": 0.76}
      },
      "categorical_distribution": {
        "lighting_class": {"bright": 8, "dim": 2},
        "terrain_roughness_class": {"smooth": 10},
        "environment_type": {"indoor_office": 10}  // EXACT primary_class
      }
    }
  },
  "cod_summary": "Robot operated in indoor_office environment with smooth terrain. Lighting varied between bright (8 windows) and dim (2 windows). Obstacle density ranged from 0.2 to 0.85 with mean 0.52."
}

CRITICAL RULES:
1. NO COMPLIANCE CHECKING - You only measure, you don't evaluate
2. Preserve ALL per-window measurements (no averaging or data loss)
3. COD region = union of all observed conditions (min/max for numeric, set for categorical)
4. Statistics are for informational purposes only - Evaluator uses raw measurements
5. collision_detected comes directly from collision agent output
6. PRESERVE EXACT VALUES from source agents - especially environment_type from perception.environment_classification.primary_class
7. DO NOT simplify categorical values (e.g., "indoor_office" → "indoor" breaks ODD matching!)

No explanations outside JSON.""",
    )
