#!/usr/bin/env python3
"""Motion Agent test using multi-agent ADK workflow pattern."""

import asyncio
import json
import math
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


async def analyze_motion_tool(window_id: str, tool_context: ToolContext) -> Dict[str, Any]:
    """Tool: run a direct Gemini call to analyze raw motion sensor data."""
    try:
        scenario_name = SCENARIO_PATH.name
        motion_file = SCENARIO_PATH / \
            f"motion_{scenario_name}_w{window_id}.json"

        if not motion_file.exists():
            return {"status": "error", "window_id": window_id, "message": "Motion file not found"}

        with open(motion_file, 'r') as f:
            motion_data = json.load(f)

        # Calculate summary statistics for the prompt
        accel_x = motion_data["accel_x"]
        accel_y = motion_data["accel_y"]
        gyro_z = motion_data["gyro_z"]
        roll = motion_data["roll"]
        pitch = motion_data["pitch"]

        # Calculate horizontal acceleration magnitude
        horiz_accel = [math.sqrt(ax**2 + ay**2)
                       for ax, ay in zip(accel_x, accel_y)]
        peak_horiz_accel = max(horiz_accel) if horiz_accel else 0.0
        avg_horiz_accel = sum(horiz_accel) / \
            len(horiz_accel) if horiz_accel else 0.0

        # Calculate angular velocity stats
        peak_gyro_z = max(abs(gz) for gz in gyro_z) if gyro_z else 0.0
        avg_gyro_z = sum(abs(gz) for gz in gyro_z) / \
            len(gyro_z) if gyro_z else 0.0

        # Platform tilt stats
        max_roll = max(abs(r) for r in roll) if roll else 0.0
        max_pitch = max(abs(p) for p in pitch) if pitch else 0.0

        prompt = f"""You are a robotics motion analyst for window {window_id}.

IMU ACCELEROMETER DATA (gravity-compensated, body frame):
- Horizontal acceleration samples (sqrt(accel_x² + accel_y²)): {len(horiz_accel)} samples
- Peak horizontal accel: {peak_horiz_accel:.4f} m/s²
- Average horizontal accel: {avg_horiz_accel:.4f} m/s²
- Sample values: {horiz_accel[:10]} (first 10 of {len(horiz_accel)})

IMU GYROSCOPE DATA:
- Peak angular velocity (|gyro_z|): {peak_gyro_z:.4f} rad/s
- Average angular velocity: {avg_gyro_z:.4f} rad/s
- Sample values: {gyro_z[:10]} (first 10 of {len(gyro_z)})

PLATFORM ORIENTATION:
- Max roll: {max_roll:.1f}°
- Max pitch: {max_pitch:.1f}°

MOTION DETECTION GUIDANCE:
- Horizontal accel > 0.05 m/s² indicates translation (robot moving forward/sideways)
- Horizontal accel > 0.5 m/s² indicates strong acceleration/deceleration
- Angular velocity > 0.1 rad/s indicates rotation (turning)
- Roll/pitch > 15° indicates platform instability

TASK: Analyze this sensor data and provide a JSON object with this EXACT schema:
{{
  "window_id": "{window_id}",
  "motion_detected": true|false,
  "motion_type": "stationary|rotation|translation|complex",
  "peak_horizontal_accel_mps2": <float>,
  "peak_angular_velocity_radps": <float>,
  "platform_stability": "stable|unstable",
  "max_tilt_deg": <float>,
  "motion_confidence": 0.0-1.0,
  "evidence": "brief explanation of your analysis"
}}

No explanations outside the JSON."""

        response = GENAI_CLIENT.models.generate_content(
            model=GEMINI_MODEL,
            contents=[types.Part(text=prompt.strip())],
        )

        data = _extract_json_block(response.text or "")
        data["window_id"] = window_id
        return data

    except Exception as err:
        return {"status": "error", "window_id": window_id, "message": str(err)}


LIST_WINDOWS = FunctionTool(func=list_windows_tool)
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
Do not add commentary. Ensure valid JSON.""")

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
2. Calculate overall motion statistics:
   - Motion detection rate (% windows with motion_detected=true)
   - Motion type distribution
   - Peak values across all windows
3. Produce final JSON:
{
  "windows_analyzed": [...],
  "overall_stats": {
    "total_windows": <int>,
    "motion_detected_count": <int>,
    "motion_detection_rate": <float 0-1>,
    "motion_type_distribution": {"stationary": X, "translation": Y, ...},
    "max_horizontal_accel_mps2": <float>,
    "max_angular_velocity_radps": <float>,
    "overall_assessment": "stationary_scenario|low_activity|moderate_activity|high_activity"
  },
  "per_window_motion": [...]
}
Only output JSON.""")

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
