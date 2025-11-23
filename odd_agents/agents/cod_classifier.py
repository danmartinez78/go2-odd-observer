"""
COD (Current Operating Domain) classifier agent.
Extracted from odd_workflow_full.py (reference implementation).
"""

from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini


def create_cod_classifier_agent(api_key: str, model: str) -> Agent:
    """Create a new CodClassifierAgent instance."""
    return Agent(
        name="CodClassifierAgent",
        model=Gemini(model=model, api_key=api_key),
        output_key="temp:cod_classification",
        instruction="""You are a Current Operating Domain (COD) classifier.

TASK: Classify the robot's CURRENT operating domain from sensor analysis.

INPUT DATA from previous agents:
Perception: {temp:perception_output?}
Motion: {temp:motion_output?}
Collision: {temp:collision_output?}

SYNTHESIS LOGIC:
**Categorical Axes:**
- environment_type: Use perception.environment_classification.primary_class
- lighting_conditions: Aggregate from perception.per_window_perception[*].lighting_class (majority vote)
- terrain_type: Aggregate from perception.per_window_perception[*].terrain_roughness_class (majority vote)

**Numeric Axes (extract ranges/averages):**
- max_accel_mps2: from motion.overall_stats.max_horizontal_accel_mps2 (peak acceleration)
- obstacle_density: average from perception.per_window_perception[*].obstacle_density
- traversability_score: average from perception.per_window_perception[*].traversability_score
- collision_risk: average from collision.collision_events[*].collision_likelihood_score

Return ONLY valid JSON:
{
  "cod_classification": {
    "categorical": {
      "environment_type": "<value>",
      "lighting_conditions": "<value>",
      "terrain_type": "<value>"
    },
    "numeric": {
      "max_accel_mps2": <float>,
      "obstacle_density": <float>,
      "traversability_score": <float>,
      "collision_risk": <float>
    }
  },
  "cod_summary": "Brief description of current operating conditions"
}

No explanations outside JSON.""",
    )
