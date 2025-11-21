#!/usr/bin/env python3
"""Collision Agent test using multi-agent ADK workflow pattern with multimodal fusion."""

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

from google.adk.agents import Agent, SequentialAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "runs"
SCENARIO_PATH = DATA_DIR / "sim_run_test"

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = "gemini-2.0-flash-lite"  # Testing cheaper model

if not GOOGLE_API_KEY:
    raise SystemExit(
        "❌ GOOGLE_API_KEY not found. Set it in your environment or .env file.")

GENAI_CLIENT = genai.Client(api_key=GOOGLE_API_KEY)


async def list_windows_tool() -> Dict[str, Any]:
    """Tool: list available window IDs for the scenario."""
    import pandas as pd

    if not SCENARIO_PATH.exists():
        return {"status": "error", "message": "Scenario directory not found"}

    index_files = sorted(SCENARIO_PATH.glob("index_*.csv"))
    if not index_files:
        return {"status": "error", "message": "No index CSV found"}

    index_df = pd.read_csv(index_files[0])
    scenario_name = SCENARIO_PATH.name
    windows: List[str] = []

    for _, row in index_df.iterrows():
        window_id = str(row["window_id"]).zfill(3)
        motion_file = SCENARIO_PATH / \
            f"motion_{scenario_name}_w{window_id}.json"
        if motion_file.exists():
            windows.append(window_id)

    return {
        "status": "success",
        "windows": windows,
        "count": len(windows),
    }


async def analyze_collision_risk_tool(window_id: str, tool_context: ToolContext) -> Dict[str, Any]:
    """Tool: multimodal collision risk assessment (motion + camera + BEV)."""
    try:
        scenario_name = SCENARIO_PATH.name

        # Load motion data
        motion_file = SCENARIO_PATH / \
            f"motion_{scenario_name}_w{window_id}.json"
        if not motion_file.exists():
            return {"status": "error", "window_id": window_id, "message": "Motion file not found"}

        with open(motion_file, 'r') as f:
            motion_data = json.load(f)

        # Load images
        camera_path = SCENARIO_PATH / f"cam_{scenario_name}_w{window_id}.png"
        bev_path = SCENARIO_PATH / \
            f"bev_occupancy_{scenario_name}_w{window_id}.png"

        if not camera_path.exists() or not bev_path.exists():
            return {"status": "error", "window_id": window_id, "message": "Images not found"}

        camera_bytes = camera_path.read_bytes()
        bev_bytes = bev_path.read_bytes()

        # Format motion metrics for prompt
        motion_summary = {
            "avg_forward_speed": motion_data.get("avg_forward_speed", 0.0),
            "max_forward_speed": motion_data.get("max_forward_speed", 0.0),
            "avg_angular_velocity": motion_data.get("avg_angular_velocity_z", 0.0),
            "max_abs_roll_pitch": motion_data.get("max_abs_roll_pitch_deg", 0.0),
        }

        prompt = f"""You are a collision risk assessment expert analyzing synchronized sensor data for window {window_id}.

MOTION DATA:
{json.dumps(motion_summary, indent=2)}

VISUAL DATA:
- Image A: RGB camera frame from robot's forward view
- Image B: LiDAR bird's-eye occupancy map (bright pixels = obstacles)

TASK: Perform multimodal fusion to assess collision risk.

Analyze:
1. Motion risk: Speed, turning dynamics, platform stability
2. Camera risk: Obstacles in path, visibility, proximity to hazards
3. LiDAR risk: Obstacle distances, clearance, occupancy density

Provide JSON with this EXACT schema:
{{
  "window_id": "{window_id}",
  "risk_level": "safe|caution|alert",
  "collision_likelihood_score": 0.0-1.0,
  "motion_risk_factors": ["list", "of", "motion-based", "risks"],
  "vision_risk_factors": ["list", "of", "camera-based", "risks"],
  "lidar_risk_factors": ["list", "of", "lidar-based", "risks"],
  "fusion_evidence": "brief explanation of multimodal fusion logic"
}}

No explanations outside JSON."""

        response = GENAI_CLIENT.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                types.Part(text=prompt.strip()),
                types.Part(text="Image A (camera):"),
                types.Part.from_bytes(
                    data=camera_bytes, mime_type="image/png"),
                types.Part(text="Image B (LiDAR BEV occupancy):"),
                types.Part.from_bytes(data=bev_bytes, mime_type="image/png"),
            ],
        )

        def extract_json(text: str) -> dict:
            cleaned = text.strip()
            if cleaned.startswith("```"):
                cleaned = "\n".join(line for line in cleaned.splitlines(
                ) if not line.strip().startswith("```"))
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start == -1 or end == -1:
                raise ValueError("No JSON found")
            return json.loads(cleaned[start:end + 1])

        data = extract_json(response.text or "")
        data["window_id"] = window_id
        return data

    except Exception as err:
        return {"status": "error", "window_id": window_id, "message": str(err)}


LIST_WINDOWS = FunctionTool(func=list_windows_tool)
ANALYZE_COLLISION = FunctionTool(func=analyze_collision_risk_tool)

collision_loop_agent = Agent(
    name="CollisionLoopAgent",
    model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
    tools=[LIST_WINDOWS, ANALYZE_COLLISION],
    output_key="temp:collision_observations",
    instruction="""You orchestrate collision risk analysis across all scenario windows.

Steps you MUST follow:
1. Call list_windows_tool() exactly once to get the ordered window_id list.
2. For each window_id returned (in that order), call analyze_collision_risk_tool(window_id=...).
3. Collect each tool response exactly as returned.
4. After all windows are processed, respond with JSON:
{
  "windows_analyzed": ["..."],
  "collision_events": [<tool_response_objects_in_order>]
}
Do not add commentary. Ensure valid JSON.""",
)

collision_summary_agent = Agent(
    name="CollisionSummaryAgent",
    model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
    instruction="""You finalize the collision risk report.

Input data from the previous agent:
{temp:collision_observations?}

If no data is provided, respond with:
{"error": "missing_collision_data"}

Otherwise:
1. Read the JSON string carefully.
2. Calculate overall statistics (count by risk_level, average collision_likelihood_score).
3. Produce final JSON:
{
  "windows_analyzed": [...],
  "overall_collision_stats": {
    "total_windows": <int>,
    "safe_count": <int>,
    "caution_count": <int>,
    "alert_count": <int>,
    "avg_collision_likelihood": <float>
  },
  "collision_events": [...]
}
Only output JSON.""",
)

collision_workflow = SequentialAgent(
    name="CollisionWorkflow",
    sub_agents=[collision_loop_agent, collision_summary_agent],
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


def _extract_result(events: List[Any]) -> Optional[Dict[str, Any]]:
    for event in events:
        if event.author == collision_summary_agent.name and event.content:
            for part in event.content.parts:
                if part.text:
                    try:
                        return _extract_json_block(part.text)
                    except Exception:
                        continue
    return None


async def test_collision_agent() -> Optional[Dict[str, Any]]:
    print("\n" + "=" * 80)
    print("COLLISION WORKFLOW TEST (Motion + Camera + LiDAR Fusion)")
    print("=" * 80)

    runner = InMemoryRunner(agent=collision_workflow,
                            app_name="CollisionWorkflowApp")
    events = await runner.run_debug("Analyze collision risks for all available windows using multimodal fusion")

    result = _extract_result(events)
    if result:
        print("\n✅ Final JSON output:\n")
        print(json.dumps(result, indent=2))
    else:
        print("\n❌ No valid JSON output produced")

    return result


if __name__ == "__main__":
    try:
        summary = asyncio.run(test_collision_agent())
        if summary is None:
            raise SystemExit(1)
        print("\n" + "=" * 80)
        print("✅ COLLISION AGENT TEST COMPLETED")
        print("=" * 80)
    except Exception as exc:
        print(f"\n❌ Fatal error: {exc}")
        raise
