#!/usr/bin/env python3
"""Perception Agent test leveraging the proven multi-agent ADK workflow pattern."""

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


def _build_image_path(prefix: str, window_id: str) -> Path:
    scenario_name = SCENARIO_PATH.name
    filename = f"{prefix}_{scenario_name}_w{window_id}.png"
    return SCENARIO_PATH / filename


def _ensure_image_bytes(path: Path) -> bytes:
    if not path.exists():
        raise FileNotFoundError(f"Missing image: {path}")
    return path.read_bytes()


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


async def list_windows_tool() -> Dict[str, Any]:
    """Tool: list available window IDs for the scenario."""
    import pandas as pd  # local import keeps optional dependency scoped

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


async def analyze_window_tool(window_id: str, tool_context: ToolContext) -> Dict[str, Any]:
    """Tool: run a direct multimodal Gemini call for one window (camera + BEV)."""
    try:
        camera_path = _build_image_path("cam", window_id)
        bev_path = _build_image_path("bev_occupancy", window_id)

        camera_bytes = _ensure_image_bytes(camera_path)
        bev_bytes = _ensure_image_bytes(bev_path)

        prompt = f"""
        You are a perception expert analyzing synchronized robot sensors for window {window_id}.
        You will receive two images:
        - Image A: RGB camera frame from the robot's forward camera.
        - Image B: LiDAR bird's-eye occupancy map where bright pixels indicate obstacles.

        Provide a JSON object with this EXACT schema:
        {{
          "window_id": "{window_id}",
          "camera_summary": "concise natural-language observation",
          "bev_summary": "concise LiDAR occupancy observation",
          "lighting_class": "bright|dim|dark",
          "visibility_score": 0.0-1.0,
          "terrain_roughness_class": "smooth|moderate|rough|very_rough",
          "occupancy_ratio": 0.0-1.0,
          "obstacle_density": 0.0-1.0,
          "traversability_score": 0.0-1.0,
          "humans_detected": true|false,
          "environmental_constraints": ["list", "of", "observed", "constraints"]
        }}

        No explanations, just the JSON.
        """

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

        data = _extract_json_block(response.text or "")
        data["window_id"] = window_id
        return data

    except Exception as err:  # pragma: no cover - aids debugging
        return {"status": "error", "window_id": window_id, "message": str(err)}


LIST_WINDOWS = FunctionTool(func=list_windows_tool)
ANALYZE_WINDOW = FunctionTool(func=analyze_window_tool)


perception_loop_agent = Agent(
    name="PerceptionLoopAgent",
    model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
    tools=[LIST_WINDOWS, ANALYZE_WINDOW],
    output_key="temp:window_observations",
    instruction="""You orchestrate perception analysis across all scenario windows.

Steps you MUST follow:
1. Call list_windows_tool() exactly once to get the ordered window_id list.
2. For each window_id returned (in that order), call analyze_window_tool(window_id=...).
3. Collect each tool response exactly as returned.
4. After all windows are processed, respond with JSON:
{
  "windows_analyzed": ["..."],
  "per_window_perception": [<tool_response_objects_in_order>]
}
Do not add commentary. Ensure valid JSON.""",
)

perception_summary_agent = Agent(
    name="PerceptionSummaryAgent",
    model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
    instruction="""You finalize the ODD perception report.

Input data from the previous agent:
{temp:window_observations?}

If no data is provided, respond with:
{"error": "missing_window_data"}

Otherwise:
1. Read the JSON string carefully.
2. Determine overall environment class (choose from: indoor_office, indoor_corridor, indoor, outdoor_urban, outdoor_natural, open_space).
3. Produce final JSON:
{
  "windows_analyzed": [...],
  "environment_classification": {
    "primary_class": "one_of_allowed_values",
    "confidence": 0.0-1.0,
    "evidence": ["short", "observations"]
  },
  "per_window_perception": [...]
}
Only output JSON.""",
)

perception_workflow = SequentialAgent(
    name="PerceptionWorkflow",
    sub_agents=[perception_loop_agent, perception_summary_agent],
)


def _extract_result(events: List[Any]) -> Optional[Dict[str, Any]]:
    for event in events:
        if event.author == perception_summary_agent.name and event.content:
            for part in event.content.parts:
                if part.text:
                    try:
                        return _extract_json_block(part.text)
                    except Exception:
                        continue
    return None


async def test_perception_agent() -> Optional[Dict[str, Any]]:
    print("\n" + "=" * 80)
    print("PERCEPTION WORKFLOW TEST (Camera + LiDAR BEV)")
    print("=" * 80)

    runner = InMemoryRunner(agent=perception_workflow,
                            app_name="PerceptionWorkflowApp")
    events = await runner.run_debug("Analyze perception for all available windows")

    result = _extract_result(events)
    if result:
        print("\n✅ Final JSON output:\n")
        print(json.dumps(result, indent=2))
    else:
        print("\n❌ No valid JSON output produced")

    return result


if __name__ == "__main__":
    try:
        summary = asyncio.run(test_perception_agent())
        if summary is None:
            raise SystemExit(1)
        print("\n" + "=" * 80)
        print("✅ PERCEPTION AGENT TEST COMPLETED")
        print("=" * 80)
    except Exception as exc:  # pragma: no cover - debug aid
        print(f"\n❌ Fatal error: {exc}")
        raise
