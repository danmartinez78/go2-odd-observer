#!/usr/bin/env python3
"""Motion Agent test using multi-agent ADK workflow pattern."""

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from google.adk.agents import Agent, SequentialAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "runs"
SCENARIO_PATH = DATA_DIR / "sim_run_test"

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = "gemini-2.0-flash-lite"  # Testing cheaper model

if not GOOGLE_API_KEY:
    raise SystemExit(
        "❌ GOOGLE_API_KEY not found. Set it in your environment or .env file.")


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


async def analyze_motion_tool(window_id: str) -> Dict[str, Any]:
    """Tool: analyze motion metrics for one window."""
    try:
        scenario_name = SCENARIO_PATH.name
        motion_file = SCENARIO_PATH / \
            f"motion_{scenario_name}_w{window_id}.json"

        if not motion_file.exists():
            return {"status": "error", "window_id": window_id, "message": "Motion file not found"}

        with open(motion_file, 'r') as f:
            motion_data = json.load(f)

        # Extract key metrics
        avg_speed = motion_data.get("avg_forward_speed", 0.0)
        max_speed = motion_data.get("max_forward_speed", 0.0)
        max_roll_pitch = motion_data.get("max_abs_roll_pitch_deg", 0.0)

        # Classify motion dynamics
        if max_speed > 1.0 or max_roll_pitch > 10.0:
            motion_label = "dynamic"
        else:
            motion_label = "smooth"

        return {
            "window_id": window_id,
            "avg_forward_speed": round(avg_speed, 3),
            "max_forward_speed": round(max_speed, 3),
            "max_abs_roll_pitch_deg": round(max_roll_pitch, 2),
            "motion_label": motion_label,
        }

    except Exception as err:
        return {"status": "error", "window_id": window_id, "message": str(err)}


LIST_WINDOWS = FunctionTool(func=list_windows_tool)
ANALYZE_MOTION = FunctionTool(func=analyze_motion_tool)

motion_loop_agent = Agent(
    name="MotionLoopAgent",
    model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
    tools=[LIST_WINDOWS, ANALYZE_MOTION],
    output_key="temp:motion_observations",
    instruction="""You orchestrate motion analysis across all scenario windows.

Steps you MUST follow:
1. Call list_windows_tool() exactly once to get the ordered window_id list.
2. For each window_id returned (in that order), call analyze_motion_tool(window_id=...).
3. Collect each tool response exactly as returned.
4. After all windows are processed, respond with JSON:
{
  "windows_analyzed": ["..."],
  "per_window_motion": [<tool_response_objects_in_order>]
}
Do not add commentary. Ensure valid JSON.""",
)

motion_summary_agent = Agent(
    name="MotionSummaryAgent",
    model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
    instruction="""You finalize the motion analysis report.

Input data from the previous agent:
{temp:motion_observations?}

If no data is provided, respond with:
{"error": "missing_motion_data"}

Otherwise:
1. Read the JSON string carefully.
2. Calculate overall motion statistics (average speed across windows, max observed speed, etc.)
3. Produce final JSON:
{
  "windows_analyzed": [...],
  "overall_motion_stats": {
    "avg_speed_across_windows": <float>,
    "max_observed_speed": <float>,
    "predominant_motion_class": "smooth|dynamic"
  },
  "per_window_motion": [...]
}
Only output JSON.""",
)

motion_workflow = SequentialAgent(
    name="MotionWorkflow",
    sub_agents=[motion_loop_agent, motion_summary_agent],
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
        if event.author == motion_summary_agent.name and event.content:
            for part in event.content.parts:
                if part.text:
                    try:
                        return _extract_json_block(part.text)
                    except Exception:
                        continue
    return None


async def test_motion_agent() -> Optional[Dict[str, Any]]:
    print("\n" + "=" * 80)
    print("MOTION WORKFLOW TEST")
    print("=" * 80)

    runner = InMemoryRunner(agent=motion_workflow,
                            app_name="MotionWorkflowApp")
    events = await runner.run_debug("Analyze motion for all available windows")

    result = _extract_result(events)
    if result:
        print("\n✅ Final JSON output:\n")
        print(json.dumps(result, indent=2))
    else:
        print("\n❌ No valid JSON output produced")

    return result


if __name__ == "__main__":
    try:
        summary = asyncio.run(test_motion_agent())
        if summary is None:
            raise SystemExit(1)
        print("\n" + "=" * 80)
        print("✅ MOTION AGENT TEST COMPLETED")
        print("=" * 80)
    except Exception as exc:
        print(f"\n❌ Fatal error: {exc}")
        raise
