"""
COD (Current Operating Domain) classifier agent.
Extracted from odd_workflow_full.py (reference implementation).
"""

from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini

from ..config import GEMINI_MODEL_COD, GOOGLE_API_KEY


cod_classifier_agent = Agent(
    name="CodClassifierAgent",
    model=Gemini(model=GEMINI_MODEL_COD, api_key=GOOGLE_API_KEY),
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
- max_speed_mps: from motion.overall_stats.max_horizontal_accel_mps2 (convert accel to speed estimate)
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
      "obstacle_density": <float>,
      "traversability_score": <float>,
      "collision_risk": <float>
    }
  },
  "cod_summary": "Brief description of current operating conditions"
}

No explanations outside JSON.""",
)
