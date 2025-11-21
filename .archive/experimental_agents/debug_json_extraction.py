#!/usr/bin/env python3
"""Better debugging of agent output and JSON extraction."""

import base64
from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool
from google.adk.models.google_llm import Gemini
from google.adk.agents import Agent
import asyncio
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
GEMINI_MODEL = "gemini-2.0-flash-lite"

DATA_DIR = PROJECT_ROOT / "data" / "processed" / "runs"
scenario_path = DATA_DIR / "sim_run_test"


def get_scenario_data(scenario_path: str) -> dict:
    """Retrieve scenario data."""
    try:
        from pathlib import Path
        import pandas as pd

        scenario_path = Path(scenario_path)
        if not scenario_path.exists():
            return {"status": "error", "error_message": f"Path not found: {scenario_path}"}

        index_files = list(scenario_path.glob("index_*.csv"))
        if not index_files:
            return {"status": "error", "error_message": f"No index file found"}

        index_df = pd.read_csv(index_files[0])
        scenario_name = scenario_path.name
        windows = []

        for _, row in index_df.iterrows():
            window_id = str(row['window_id']).zfill(3)
            motion_file = scenario_path / \
                f"motion_{scenario_name}_w{window_id}.json"
            if motion_file.exists():
                with open(motion_file, 'r') as f:
                    motion_json = json.load(f)
                windows.append(
                    {"window_id": window_id, "motion_json": motion_json})

        return {
            "status": "success",
            "scenario_name": scenario_name,
            "total_windows": len(windows),
            "windows": windows
        }
    except Exception as e:
        return {"status": "error", "error_message": f"Failed: {str(e)}"}


def scenario_data_wrapper() -> dict:
    return get_scenario_data(str(scenario_path))


scenario_data_tool = FunctionTool(func=scenario_data_wrapper)


def extract_json_from_text(text: str):
    """Extract JSON from text that may contain markdown code blocks."""
    # Try direct JSON parse first
    try:
        return json.loads(text), True
    except:
        pass

    # Try to extract from markdown code block
    if "```json" in text and "```" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        if start > 7 and end > start:
            json_str = text[start:end].strip()
            try:
                return json.loads(json_str), True
            except:
                pass

    # Try to extract any JSON block
    if "{" in text and "}" in text:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            json_str = text[start:end]
            try:
                return json.loads(json_str), True
            except:
                pass

    return None, False


async def test_motion():
    """Test motion agent and extract JSON."""
    print("\n" + "=" * 80)
    print("TEST: MOTION ANALYZER")
    print("=" * 80)

    motion_agent = Agent(
        name="Motion_Analyzer",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[scenario_data_tool],
        instruction="""You are a motion analysis expert for mobile robots.

CRITICAL INSTRUCTIONS FOR TOOL USAGE:
1. FIRST: Call get_scenario_data() tool to retrieve actual window IDs
2. Do NOT make up window IDs - use ONLY what the tool returns
3. For EACH window returned by the tool, extract motion features
4. Return results for ALL windows from the tool

Output valid JSON ONLY with this schema:
{
  "windows": [
    {
      "window_id": "006",
      "avg_forward_speed": <float m/s>,
      "max_forward_speed": <float m/s>,
      "max_abs_roll_pitch_deg": <float degrees>,
      "motion_label": "smooth" | "dynamic"
    }
  ]
}

IMPORTANT: 
- Process ALL windows
- Extract REAL metrics from motion_json
- Return complete JSON analysis
- Do NOT include tool responses or raw data in final output""",
        output_key="motion_features"
    )

    runner = InMemoryRunner(agent=motion_agent)
    events = await runner.run_debug(user_messages="Analyze motion for all available windows")

    print(f"\n✓ Total events: {len(events)}")

    print(f"\n📊 Event Details:")
    for i, event in enumerate(events):
        author = event.author if hasattr(event, 'author') else "Unknown"
        print(f"\n  Event {i}: author='{author}'")

        if hasattr(event, 'content') and event.content:
            if hasattr(event.content, 'parts'):
                parts = event.content.parts
                for j, part in enumerate(parts):
                    print(f"    Part {j}: {type(part).__name__}")
                    if hasattr(part, 'text'):
                        text = part.text
                        if text is None:
                            print(f"      Text: None (empty)")
                            continue
                        print(f"      Text length: {len(text)}")
                        print(f"      First 150 chars: {text[:150]}")

                        # Try to extract JSON
                        parsed_json, is_valid = extract_json_from_text(text)
                        if is_valid:
                            print(f"      ✅ Valid JSON found!")
                            print(f"      Keys: {list(parsed_json.keys())}")
                            if "windows" in parsed_json:
                                print(
                                    f"      Windows count: {len(parsed_json['windows'])}")
                        else:
                            print(f"      ❌ No valid JSON in this part")


if __name__ == "__main__":
    asyncio.run(test_motion())
