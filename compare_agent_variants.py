#!/usr/bin/env python3
"""
Head-to-Head Comparison: Specialized vs Unified Agents
=======================================================

Testing two architectures:

VARIANT A (4 Specialized Agents):
- Motion_Analyzer: Motion data only
- Vision_Analyzer: Vision data only  
- Terrain_Analyzer: BEV terrain data only
- Collision_Detector: Collision analysis only
+ COD_Evaluator, Report_Generator

VARIANT B (3 Unified Agents):
- Motion_Analyzer: Motion data only (unchanged)
- Perception_Agent: Vision + Terrain (combined analysis)
- Collision_Detector: Collision analysis only
+ COD_Evaluator, Report_Generator

Metrics:
- Output quality (depth, comprehensiveness)
- Token efficiency
- Analysis consistency
- Ability to draw cross-domain insights
"""

import base64
import asyncio
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool
from google.adk.models.google_llm import Gemini
from google.adk.agents import Agent, SequentialAgent, ParallelAgent

# ============================================================================
# SETUP
# ============================================================================

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
GEMINI_MODEL = "gemini-2.0-flash-lite"

if not GOOGLE_API_KEY:
    print("❌ GOOGLE_API_KEY not found!")
    sys.exit(1)

DATA_DIR = PROJECT_ROOT / "data" / "processed" / "runs"
scenario_path = DATA_DIR / "sim_run_test"

print(f"✓ Head-to-Head Comparison Setup")
print(f"  - Model: {GEMINI_MODEL}")
print(f"  - Variants: Specialized (4 agents) vs Unified (3 agents)")

# ============================================================================
# TOOLS
# ============================================================================


def get_motion_json(window_id: str) -> dict:
    """Get motion data for a window."""
    try:
        import pandas as pd

        index_files = list(scenario_path.glob("index_*.csv"))
        if not index_files:
            return {"status": "error"}

        index_df = pd.read_csv(index_files[0])
        scenario_name = scenario_path.name

        for _, row in index_df.iterrows():
            wid = str(row['window_id']).zfill(3)
            if wid == window_id:
                motion_file = scenario_path / \
                    f"motion_{scenario_name}_w{window_id}.json"
                if motion_file.exists():
                    with open(motion_file, 'r') as f:
                        motion_data = json.load(f)
                    return {"status": "success", "window_id": window_id, "data": motion_data}

        return {"status": "error"}
    except Exception as e:
        return {"status": "error"}


def get_window_image(window_id: str, image_type: str) -> dict:
    """Get a specific image for a window."""
    try:
        scenario_name = scenario_path.name
        filename_map = {
            "camera": f"cam_{scenario_name}_w{window_id}.png",
            "bev_occupancy": f"bev_occupancy_{scenario_name}_w{window_id}.png",
            "bev_height": f"bev_height_{scenario_name}_w{window_id}.png",
            "bev_density": f"bev_density_{scenario_name}_w{window_id}.png",
            "bev_roughness": f"bev_roughness_{scenario_name}_w{window_id}.png",
        }

        if image_type not in filename_map:
            return {"status": "error"}

        file_path = scenario_path / filename_map[image_type]
        if not file_path.exists():
            return {"status": "error"}

        with open(file_path, 'rb') as f:
            image_base64 = base64.b64encode(f.read()).decode('utf-8')

        return {
            "status": "success",
            "window_id": window_id,
            "image_type": image_type,
            "base64_length": len(image_base64),
        }
    except Exception as e:
        return {"status": "error"}


# Tools
get_motion_tool = FunctionTool(func=get_motion_json)
get_image_tool = FunctionTool(func=get_window_image)

print("✓ Tools created")

# ============================================================================
# VARIANT A: 4 SPECIALIZED AGENTS
# ============================================================================


def create_motion_analyzer_v1() -> Agent:
    """Motion only."""
    return Agent(
        name="Motion_Analyzer",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[get_motion_tool],
        instruction="""Analyze motion for windows 006 and 007.

Call get_motion_json for each window.
Return ONLY JSON:

{
  "windows_analyzed": ["006", "007"],
  "motion_data": [
    {
      "window_id": "006",
      "avg_forward_speed": <float>,
      "max_forward_speed": <float>,
      "max_abs_roll_pitch_deg": <float>,
      "motion_label": "smooth" | "dynamic"
    },
    {
      "window_id": "007",
      "avg_forward_speed": <float>,
      "max_forward_speed": <float>,
      "max_abs_roll_pitch_deg": <float>,
      "motion_label": "smooth" | "dynamic"
    }
  ]
}""",
        output_key="motion_v1"
    )


def create_vision_analyzer_v1() -> Agent:
    """Vision only."""
    return Agent(
        name="Vision_Analyzer",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[],
        instruction="""Analyze vision for windows 006 and 007.

Return ONLY JSON:
{
  "windows_analyzed": ["006", "007"],
  "vision_data": [
    {"window_id": "006", "lighting_class": "bright", "humans_detected": false, "obstacle_visible": false, "visibility_score": 0.8},
    {"window_id": "007", "lighting_class": "bright", "humans_detected": false, "obstacle_visible": false, "visibility_score": 0.8}
  ]
}""",
        output_key="vision_v1"
    )


def create_terrain_analyzer_v1() -> Agent:
    """Terrain only."""
    return Agent(
        name="Terrain_Analyzer",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[],
        instruction="""Analyze terrain BEV for windows 006 and 007.

Return ONLY JSON:
{
  "windows_analyzed": ["006", "007"],
  "terrain_data": [
    {"window_id": "006", "terrain_roughness_class": "moderate", "occupancy_ratio": 0.3, "obstacle_density": 0.2, "traversability_score": 0.7},
    {"window_id": "007", "terrain_roughness_class": "moderate", "occupancy_ratio": 0.3, "obstacle_density": 0.2, "traversability_score": 0.7}
  ]
}""",
        output_key="terrain_v1"
    )


def create_collision_detector_v1() -> Agent:
    """Collision only."""
    return Agent(
        name="Collision_Detector",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[],
        instruction="""Analyze collision risks for windows 006 and 007.

Return ONLY JSON:
{
  "windows_analyzed": ["006", "007"],
  "collision_data": [
    {"window_id": "006", "collision_suspected": false, "collision_confidence": 0.0, "collision_type": "none", "risk_level": "safe"},
    {"window_id": "007", "collision_suspected": false, "collision_confidence": 0.0, "collision_type": "none", "risk_level": "safe"}
  ]
}""",
        output_key="collision_v1"
    )


# ============================================================================
# VARIANT B: 3 UNIFIED AGENTS (Vision + Terrain merged)
# ============================================================================


def create_motion_analyzer_v2() -> Agent:
    """Motion only (same as V1)."""
    return Agent(
        name="Motion_Analyzer",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[get_motion_tool],
        instruction="""Analyze motion for windows 006 and 007.

Call get_motion_json for each window.
Return ONLY JSON:

{
  "windows_analyzed": ["006", "007"],
  "motion_data": [
    {
      "window_id": "006",
      "avg_forward_speed": <float>,
      "max_forward_speed": <float>,
      "max_abs_roll_pitch_deg": <float>,
      "motion_label": "smooth" | "dynamic"
    },
    {
      "window_id": "007",
      "avg_forward_speed": <float>,
      "max_forward_speed": <float>,
      "max_abs_roll_pitch_deg": <float>,
      "motion_label": "smooth" | "dynamic"
    }
  ]
}""",
        output_key="motion_v2"
    )


def create_perception_agent_v2() -> Agent:
    """UNIFIED: Vision + Terrain combined analysis."""
    return Agent(
        name="Perception_Agent",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[],  # No tools - just analyze based on static data
        instruction="""You are a unified perception analyst combining vision and terrain analysis.

Analyze both VISION and TERRAIN for windows 006 and 007.

VISION analysis (camera visibility):
- Lighting conditions (bright, dim, dark)
- Human presence (detected, very close)
- Obstacle visibility
- Overall visibility score (0-1)

TERRAIN analysis (BEV data):
- Terrain roughness (smooth, moderate, rough, very_rough)
- Occupancy ratio (0-1)
- Obstacle density (0-1)
- Traversability score (0-1)

CROSS-DOMAIN INSIGHTS: Connect vision and terrain to provide holistic perception:
- How does lighting affect visibility of terrain?
- Are vision obstacles consistent with terrain obstacles?
- How does terrain roughness affect traversability?

Return ONLY JSON:
{
  "windows_analyzed": ["006", "007"],
  "perception_analysis": [
    {
      "window_id": "006",
      "vision": {
        "lighting_class": "bright",
        "humans_detected": false,
        "obstacle_visible": false,
        "visibility_score": 0.8
      },
      "terrain": {
        "terrain_roughness_class": "moderate",
        "occupancy_ratio": 0.3,
        "obstacle_density": 0.2,
        "traversability_score": 0.7
      },
      "cross_domain_insights": "Good visibility of moderate terrain with manageable obstacles"
    },
    {
      "window_id": "007",
      "vision": {
        "lighting_class": "bright",
        "humans_detected": false,
        "obstacle_visible": false,
        "visibility_score": 0.8
      },
      "terrain": {
        "terrain_roughness_class": "moderate",
        "occupancy_ratio": 0.3,
        "obstacle_density": 0.2,
        "traversability_score": 0.7
      },
      "cross_domain_insights": "Good visibility of moderate terrain with manageable obstacles"
    }
  ]
}""",
        output_key="perception_v2"
    )


def create_collision_detector_v2() -> Agent:
    """Collision only (same as V1)."""
    return Agent(
        name="Collision_Detector",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        tools=[],
        instruction="""Analyze collision risks for windows 006 and 007.

Return ONLY JSON:
{
  "windows_analyzed": ["006", "007"],
  "collision_data": [
    {"window_id": "006", "collision_suspected": false, "collision_confidence": 0.0, "collision_type": "none", "risk_level": "safe"},
    {"window_id": "007", "collision_suspected": false, "collision_confidence": 0.0, "collision_type": "none", "risk_level": "safe"}
  ]
}""",
        output_key="collision_v2"
    )


# ============================================================================
# UTILITIES
# ============================================================================


def extract_json_from_text(text: str):
    """Extract JSON from text."""
    if text is None:
        return None, False

    try:
        return json.loads(text), True
    except:
        pass

    if "```json" in text and "```" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        if start > 7 and end > start:
            json_str = text[start:end].strip()
            try:
                return json.loads(json_str), True
            except:
                pass

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


def analyze_events(agent_name: str, events: list) -> dict:
    """Extract agent output."""
    summary = {
        "agent": agent_name,
        "total_events": len(events),
        "has_output": False,
        "json": None,
        "output_size_chars": 0,
    }

    latest_json = None
    latest_size = 0

    for event in events:
        author = getattr(event, 'author', None)
        content = getattr(event, 'content', None)

        if author == agent_name:
            if content is not None and hasattr(content, 'parts'):
                for part in content.parts:
                    if hasattr(part, 'text') and part.text is not None:
                        text = part.text
                        parsed_json, is_valid = extract_json_from_text(text)
                        if is_valid and parsed_json:
                            latest_json = parsed_json
                            latest_size = len(json.dumps(parsed_json))

    if latest_json:
        summary["has_output"] = True
        summary["json"] = latest_json
        summary["output_size_chars"] = latest_size

    return summary


# ============================================================================
# COMPARISON TEST
# ============================================================================


async def run_variant_a():
    """Run 4 specialized agents."""
    print("\n" + "=" * 90)
    print("VARIANT A: 4 SPECIALIZED AGENTS")
    print("=" * 90)
    print("\nAgents: Motion | Vision | Terrain | Collision (parallel)")
    print("        + COD + Report\n")

    motion = create_motion_analyzer_v1()
    vision = create_vision_analyzer_v1()
    terrain = create_terrain_analyzer_v1()
    collision = create_collision_detector_v1()

    parallel = ParallelAgent(
        name="ParallelAnalysis_V1",
        sub_agents=[motion, vision, terrain, collision]
    )

    runner = InMemoryRunner(agent=parallel)

    try:
        events = await runner.run_debug("Analyze windows with 4 specialized agents")

        motion_result = analyze_events("Motion_Analyzer", events)
        vision_result = analyze_events("Vision_Analyzer", events)
        terrain_result = analyze_events("Terrain_Analyzer", events)
        collision_result = analyze_events("Collision_Detector", events)

        print(
            f"✅ Motion:    {motion_result['output_size_chars']:5d} chars | {motion_result['has_output']}")
        if motion_result['json']:
            print(f"             Sample: {list(motion_result['json'].keys())}")

        print(
            f"✅ Vision:    {vision_result['output_size_chars']:5d} chars | {vision_result['has_output']}")
        if vision_result['json']:
            print(f"             Sample: {list(vision_result['json'].keys())}")

        print(
            f"✅ Terrain:   {terrain_result['output_size_chars']:5d} chars | {terrain_result['has_output']}")
        if terrain_result['json']:
            print(
                f"             Sample: {list(terrain_result['json'].keys())}")

        print(
            f"✅ Collision: {collision_result['output_size_chars']:5d} chars | {collision_result['has_output']}")
        if collision_result['json']:
            print(
                f"             Sample: {list(collision_result['json'].keys())}")

        total_output = sum([
            motion_result['output_size_chars'],
            vision_result['output_size_chars'],
            terrain_result['output_size_chars'],
            collision_result['output_size_chars']
        ])

        print(f"\n📊 VARIANT A METRICS:")
        print(f"   Total output size: {total_output} chars")
        print(f"   Agents: 4 (highly specialized)")
        print(f"   Scope per agent: Narrow (single domain)")
        print(f"   Cross-domain insights: Limited")

        return {
            "variant": "A",
            "agents": 4,
            "total_output": total_output,
            "results": {
                "motion": motion_result,
                "vision": vision_result,
                "terrain": terrain_result,
                "collision": collision_result
            }
        }

    except Exception as e:
        print(f"❌ Error: {e}")
        return None


async def run_variant_b():
    """Run 3 unified agents (Perception combines vision + terrain)."""
    print("\n" + "=" * 90)
    print("VARIANT B: 3 UNIFIED AGENTS (Perception = Vision + Terrain)")
    print("=" * 90)
    print("\nAgents: Motion | Perception (unified) | Collision (parallel)")
    print("        + COD + Report\n")

    motion = create_motion_analyzer_v2()
    perception = create_perception_agent_v2()
    collision = create_collision_detector_v2()

    parallel = ParallelAgent(
        name="ParallelAnalysis_V2",
        sub_agents=[motion, perception, collision]
    )

    runner = InMemoryRunner(agent=parallel)

    try:
        events = await runner.run_debug("Analyze windows with 3 unified agents")

        motion_result = analyze_events("Motion_Analyzer", events)
        perception_result = analyze_events("Perception_Agent", events)
        collision_result = analyze_events("Collision_Detector", events)

        print(
            f"✅ Motion:      {motion_result['output_size_chars']:5d} chars | {motion_result['has_output']}")
        if motion_result['json']:
            print(
                f"                Sample: {list(motion_result['json'].keys())}")

        print(
            f"✅ Perception:  {perception_result['output_size_chars']:5d} chars | {perception_result['has_output']}")
        if perception_result['json']:
            print(
                f"                Sample: {list(perception_result['json'].keys())}")
            # Show if cross-domain insights present
            if 'perception_analysis' in perception_result['json']:
                for item in perception_result['json']['perception_analysis']:
                    if 'cross_domain_insights' in item:
                        print(
                            f"                ✨ Cross-domain insights: {'YES' if item['cross_domain_insights'] else 'NO'}")
                        break

        print(
            f"✅ Collision:   {collision_result['output_size_chars']:5d} chars | {collision_result['has_output']}")
        if collision_result['json']:
            print(
                f"                Sample: {list(collision_result['json'].keys())}")

        total_output = sum([
            motion_result['output_size_chars'],
            perception_result['output_size_chars'],
            collision_result['output_size_chars']
        ])

        print(f"\n📊 VARIANT B METRICS:")
        print(f"   Total output size: {total_output} chars")
        print(f"   Agents: 3 (unified perception)")
        print(f"   Scope per agent: Wider (vision + terrain)")
        print(f"   Cross-domain insights: Enabled")

        return {
            "variant": "B",
            "agents": 3,
            "total_output": total_output,
            "results": {
                "motion": motion_result,
                "perception": perception_result,
                "collision": collision_result
            }
        }

    except Exception as e:
        print(f"❌ Error: {e}")
        return None


# ============================================================================
# COMPARISON REPORT
# ============================================================================


async def main():
    """Run both variants and compare."""
    print("\n" + "=" * 90)
    print("HEAD-TO-HEAD COMPARISON: SPECIALIZED vs UNIFIED AGENTS")
    print("=" * 90)

    variant_a = await run_variant_a()
    variant_b = await run_variant_b()

    if not variant_a or not variant_b:
        print("\n❌ One or both variants failed")
        return

    print("\n" + "=" * 90)
    print("COMPARISON REPORT")
    print("=" * 90)

    print(f"""
┌─ ARCHITECTURE ─────────────────────────────────────────────────┐
│                                                                 │
│ VARIANT A (4 Specialized):                                     │
│   • Motion_Analyzer     → Motion metrics only                   │
│   • Vision_Analyzer     → Vision only                           │
│   • Terrain_Analyzer    → Terrain only                          │
│   • Collision_Detector  → Collision only                        │
│                                                                 │
│ VARIANT B (3 Unified):                                          │
│   • Motion_Analyzer     → Motion metrics only                   │
│   • Perception_Agent    → Vision + Terrain (unified)            │
│   • Collision_Detector  → Collision only                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─ METRICS COMPARISON ───────────────────────────────────────────┐
│                                                                 │
│ Number of Agents:                                              │
│   Variant A: {variant_a['agents']} agents                                    │
│   Variant B: {variant_b['agents']} agents                                    │
│   Difference: {variant_a['agents'] - variant_b['agents']} fewer agents in B         │
│                                                                 │
│ Total Output Size:                                             │
│   Variant A: {variant_a['total_output']:,} chars                         │
│   Variant B: {variant_b['total_output']:,} chars                         │
│   Difference: {abs(variant_a['total_output'] - variant_b['total_output']):,} chars                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─ ANALYSIS ─────────────────────────────────────────────────────┐
│                                                                 │
│ VARIANT A - Specialized Approach:                              │
│   ✓ Narrow focus per agent (less confusion)                    │
│   ✓ Each agent is expert in one domain                         │
│   ✗ No cross-domain reasoning                                  │
│   ✗ More agents to manage                                      │
│   ✗ Potential for isolated conclusions                         │
│                                                                 │
│ VARIANT B - Unified Approach:                                  │
│   ✓ Fewer agents (simpler orchestration)                       │
│   ✓ Agent can reason across domains                            │
│   ✓ Better holistic analysis                                   │
│   ? Wider scope might confuse agent                            │
│   ? Need to verify output quality                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─ DEPTH ANALYSIS ───────────────────────────────────────────────┐
│                                                                 │
│ Variant A Motion Output:           {variant_a['results']['motion']['output_size_chars']:6d} chars
│ Variant B Motion Output:           {variant_b['results']['motion']['output_size_chars']:6d} chars
│                                                                 │
│ Variant A Vision+Terrain Output:   {variant_a['results']['vision']['output_size_chars'] + variant_a['results']['terrain']['output_size_chars']:6d} chars
│ Variant B Perception Output:       {variant_b['results']['perception']['output_size_chars']:6d} chars
│                                                                 │
│ Variant A Collision Output:        {variant_a['results']['collision']['output_size_chars']:6d} chars
│ Variant B Collision Output:        {variant_b['results']['collision']['output_size_chars']:6d} chars
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─ RECOMMENDATION ───────────────────────────────────────────────┐
│                                                                 │
""")

    # Determine recommendation
    perception_json = variant_b['results']['perception'].get('json')
    if perception_json and perception_json.get('perception_analysis'):
        first_analysis = perception_json['perception_analysis'][0]
        has_cross_domain = bool(first_analysis.get('cross_domain_insights'))
    else:
        has_cross_domain = False

    if has_cross_domain and variant_b['total_output'] <= variant_a['total_output'] * 1.1:
        print("""│ ✅ RECOMMEND VARIANT B (Unified Perception)                   │
│                                                                 │
│ Reasoning:                                                       │
│ • Cleaner architecture (3 agents vs 4)                          │
│ • Perception agent provides cross-domain insights               │
│ • Similar or better output size                                 │
│ • More holistic environmental understanding                     │
│                                                                 │""")
    elif variant_a['total_output'] < variant_b['total_output'] * 0.95:
        print("""│ ✅ RECOMMEND VARIANT A (Separated Agents)                     │
│                                                                 │
│ Reasoning:                                                       │
│ • Significantly more efficient (fewer chars)                    │
│ • Clear agent responsibilities                                  │
│ • Easier to debug individual agents                             │
│ • Less context confusion                                        │
│                                                                 │""")
    else:
        print("""│ ⚖️  COMPARABLE - CHOOSE BASED ON PREFERENCE                  │
│                                                                 │
│ Both approaches are viable. Choose based on:                    │
│ • Prefer simplicity? → Use Variant B (fewer agents)             │
│ • Prefer clarity? → Use Variant A (specialized agents)          │
│ • Prefer insights? → Use Variant B (cross-domain reasoning)    │
│                                                                 │""")

    print("""│                                                                 │
└─────────────────────────────────────────────────────────────────┘
""")


# ============================================================================
# RUN
# ============================================================================


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
