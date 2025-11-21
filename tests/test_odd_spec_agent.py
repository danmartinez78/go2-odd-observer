#!/usr/bin/env python3
"""ODD Specification Agent test - classifies operational domain from perception/motion/collision data."""

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool

PROJECT_ROOT = Path(__file__).parent.parent

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = "gemini-2.0-flash-lite"  # Testing cheaper model

if not GOOGLE_API_KEY:
    raise SystemExit(
        "❌ GOOGLE_API_KEY not found. Set it in your environment or .env file.")


# Mock upstream agent outputs (in real workflow, these come from actual agents)
MOCK_PERCEPTION_OUTPUT = {
    "windows_analyzed": ["006", "007"],
    "environment_classification": {
        "primary_class": "indoor_office",
        "confidence": 0.95,
        "evidence": [
            "Consistent indoor scene descriptions",
            "Presence of office furniture (couches, sofas, tables)",
            "Smooth, finished floors reported in all windows"
        ]
    },
    "per_window_perception": [
        {
            "window_id": "006",
            "camera_summary": "Indoor scene with two black couches and glass coffee table",
            "bev_summary": "LiDAR detects two large obstacles with traversable space between",
            "lighting_class": "bright",
            "visibility_score": 1.0,
            "terrain_roughness_class": "smooth",
            "occupancy_ratio": 0.2,
            "obstacle_density": 0.25,
            "traversability_score": 0.9,
            "humans_detected": False,
            "environmental_constraints": ["large_furniture", "narrow_passage", "transparent_obstacle"]
        },
        {
            "window_id": "007",
            "camera_summary": "Well-lit indoor scene with black sofa, armchair, and glass table",
            "bev_summary": "LiDAR detects large obstacles with narrow passage to left",
            "lighting_class": "bright",
            "visibility_score": 1.0,
            "terrain_roughness_class": "smooth",
            "occupancy_ratio": 0.35,
            "obstacle_density": 0.5,
            "traversability_score": 0.3,
            "humans_detected": False,
            "environmental_constraints": ["large_furniture", "narrow_passages"]
        }
    ]
}

MOCK_MOTION_OUTPUT = {
    "windows_analyzed": ["006", "007"],
    "overall_motion_stats": {
        "avg_speed_across_windows": 0.0,
        "max_observed_speed": 0.0,
        "predominant_motion_class": "smooth"
    },
    "per_window_motion": [
        {
            "window_id": "006",
            "avg_forward_speed": 0.0,
            "max_forward_speed": 0.0,
            "max_abs_roll_pitch_deg": 0.0,
            "motion_label": "smooth"
        },
        {
            "window_id": "007",
            "avg_forward_speed": 0.0,
            "max_forward_speed": 0.0,
            "max_abs_roll_pitch_deg": 0.0,
            "motion_label": "smooth"
        }
    ]
}

MOCK_COLLISION_OUTPUT = {
    "windows_analyzed": ["006", "007"],
    "overall_collision_stats": {
        "total_windows": 2,
        "safe_count": 2,
        "caution_count": 0,
        "alert_count": 0,
        "avg_collision_likelihood": 0.0
    },
    "collision_events": [
        {
            "window_id": "006",
            "risk_level": "safe",
            "collision_likelihood_score": 0.0,
            "motion_risk_factors": ["Robot is stationary"],
            "vision_risk_factors": ["Path blocked by coffee table", "Close proximity to furniture"],
            "lidar_risk_factors": ["High-density obstacle cluster directly in front"],
            "fusion_evidence": "Robot stationary, zero immediate collision risk despite blocked path"
        },
        {
            "window_id": "007",
            "risk_level": "safe",
            "collision_likelihood_score": 0.0,
            "motion_risk_factors": ["Stationary, no motion-induced risk"],
            "vision_risk_factors": ["Multiple static obstacles in forward path"],
            "lidar_risk_factors": ["Path blocked by high-density obstacles"],
            "fusion_evidence": "Stationary robot, immediate collision risk zero despite obstacles"
        }
    ]
}


async def get_perception_data_tool() -> Dict[str, Any]:
    """Tool: returns mock perception analysis data."""
    return MOCK_PERCEPTION_OUTPUT


async def get_motion_data_tool() -> Dict[str, Any]:
    """Tool: returns mock motion analysis data."""
    return MOCK_MOTION_OUTPUT


async def get_collision_data_tool() -> Dict[str, Any]:
    """Tool: returns mock collision analysis data."""
    return MOCK_COLLISION_OUTPUT


GET_PERCEPTION = FunctionTool(func=get_perception_data_tool)
GET_MOTION = FunctionTool(func=get_motion_data_tool)
GET_COLLISION = FunctionTool(func=get_collision_data_tool)


odd_spec_agent = Agent(
    name="OddSpecAgent",
    model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
    tools=[GET_PERCEPTION, GET_MOTION, GET_COLLISION],
    instruction="""You are an Operational Design Domain (ODD) classification specialist.

TASK: Classify the robot's operational domain using multimodal analysis data.

STEP-BY-STEP:
1. Call get_perception_data_tool() to get environment classification and perception metrics
2. Call get_motion_data_tool() to get motion dynamics and speed data
3. Call get_collision_data_tool() to get collision risk assessment

THEN synthesize an ODD specification with these axes:

**Categorical Axes:**
- environment_type: Choose from [indoor_office, indoor_corridor, indoor_warehouse, outdoor_urban, outdoor_natural, mixed]
- lighting_conditions: Choose from [bright, dim, dark, variable]
- terrain_type: Choose from [smooth_floor, rough_floor, paved, unpaved, mixed]

**Numeric Axes (provide ranges based on observed data):**
- speed_range: [min_observed, max_observed] in m/s
- obstacle_density: [min_observed, max_observed] ratio 0.0-1.0
- traversability: [min_observed, max_observed] score 0.0-1.0
- collision_risk: [min_observed, max_observed] score 0.0-1.0

**Classification Logic:**
- Use perception.environment_classification.primary_class as primary signal
- Aggregate lighting_class from all windows (predominant value)
- Aggregate terrain_roughness_class from all windows
- Extract speed range from motion data
- Extract obstacle_density range from perception data
- Extract traversability range from perception data
- Extract collision_likelihood range from collision data

Return ONLY valid JSON with this structure:
{
  "odd_classification": {
    "categorical": {
      "environment_type": "<value>",
      "lighting_conditions": "<value>",
      "terrain_type": "<value>"
    },
    "numeric": {
      "speed_range": [<min>, <max>],
      "obstacle_density": [<min>, <max>],
      "traversability": [<min>, <max>],
      "collision_risk": [<min>, <max>]
    }
  },
  "confidence_scores": {
    "environment_type": 0.0-1.0,
    "lighting_conditions": 0.0-1.0,
    "terrain_type": 0.0-1.0
  },
  "supporting_evidence": {
    "environment_type": ["evidence1", "evidence2"],
    "lighting_conditions": ["evidence1"],
    "terrain_type": ["evidence1"]
  },
  "summary": "Brief natural language summary of the ODD"
}

No explanations outside JSON.""",
)


def _extract_json_block(text: str) -> Dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = "\n".join(line for line in cleaned.splitlines()
                            if not line.strip().startswith("```"))
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object found in response: {text}")
    return json.loads(cleaned[start:end + 1])


def _extract_result(events: list) -> Optional[Dict[str, Any]]:
    for event in events:
        if event.author == odd_spec_agent.name and event.content:
            for part in event.content.parts:
                if part.text:
                    try:
                        return _extract_json_block(part.text)
                    except Exception:
                        continue
    return None


async def test_odd_spec_agent() -> Optional[Dict[str, Any]]:
    print("\n" + "=" * 80)
    print("ODD SPECIFICATION AGENT TEST")
    print("=" * 80)

    runner = InMemoryRunner(agent=odd_spec_agent, app_name="OddSpecAgentApp")
    events = await runner.run_debug("Classify the operational design domain from multimodal analysis")

    result = _extract_result(events)
    if result:
        print("\n✅ Final JSON output:\n")
        print(json.dumps(result, indent=2))
    else:
        print("\n❌ No valid JSON output produced")

    return result


if __name__ == "__main__":
    try:
        summary = asyncio.run(test_odd_spec_agent())
        if summary is None:
            raise SystemExit(1)
        print("\n" + "=" * 80)
        print("✅ ODD SPEC AGENT TEST COMPLETED")
        print("=" * 80)
    except Exception as exc:
        print(f"\n❌ Fatal error: {exc}")
        raise
