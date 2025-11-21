#!/usr/bin/env python3
"""
Full ODD Workflow - Multi-Agent Pipeline
Orchestrates perception, motion, collision, ODD spec, COD analysis, and reporting.
"""

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

# =============================================================================
# Configuration
# =============================================================================

# Go up from scripts/ to project root
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "runs"
SCENARIO_PATH = DATA_DIR / "sim_run_new"  # Full dataset (13 windows)

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise SystemExit(
        "❌ GOOGLE_API_KEY not found. Set it in your environment or .env file.")

# Model assignments per agent (optimized for cost/performance)
# Vision-heavy agents use 2.5-pro for accuracy
# Data aggregation agents use 2.5-pro to preserve structure
# Simple processing agents use flash-lite for cost savings
GEMINI_MODEL_PERCEPTION = "gemini-2.5-pro"  # Vision analysis needs accuracy
# Data aggregation needs structure preservation
GEMINI_MODEL_MOTION = "gemini-2.5-pro"
GEMINI_MODEL_COLLISION = "gemini-2.5-pro"  # Complex multimodal fusion
GEMINI_MODEL_ODD_SPEC = "gemini-2.0-flash-lite"  # JSON synthesis only
GEMINI_MODEL_COD = "gemini-2.0-flash-lite"  # Comparison logic
GEMINI_MODEL_REPORT = "gemini-2.5-pro"  # High-quality report generation

GENAI_CLIENT = genai.Client(api_key=GOOGLE_API_KEY)

# =============================================================================
# Utility Functions
# =============================================================================


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


# =============================================================================
# PERCEPTION AGENT TOOLS
# =============================================================================

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


async def analyze_window_perception_tool(window_id: str, tool_context: ToolContext) -> Dict[str, Any]:
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
            model=GEMINI_MODEL_PERCEPTION,
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

    except Exception as err:
        return {"status": "error", "window_id": window_id, "message": str(err)}


LIST_WINDOWS = FunctionTool(func=list_windows_tool)
ANALYZE_WINDOW_PERCEPTION = FunctionTool(func=analyze_window_perception_tool)

# =============================================================================
# MOTION AGENT TOOLS
# =============================================================================


async def analyze_motion_tool(window_id: str, tool_context: ToolContext) -> Dict[str, Any]:
    """Tool: run a direct Gemini call to analyze raw IMU motion sensor data."""
    try:
        scenario_name = SCENARIO_PATH.name
        motion_file = SCENARIO_PATH / f"motion_{scenario_name}_w{window_id}.json"

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
        horiz_accel = [math.sqrt(ax**2 + ay**2) for ax, ay in zip(accel_x, accel_y)]
        peak_horiz_accel = max(horiz_accel) if horiz_accel else 0.0
        avg_horiz_accel = sum(horiz_accel) / len(horiz_accel) if horiz_accel else 0.0
        
        # Calculate angular velocity stats
        peak_gyro_z = max(abs(gz) for gz in gyro_z) if gyro_z else 0.0
        avg_gyro_z = sum(abs(gz) for gz in gyro_z) / len(gyro_z) if gyro_z else 0.0
        
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
            model=GEMINI_MODEL_MOTION,
            contents=[types.Part(text=prompt.strip())],
        )

        data = _extract_json_block(response.text or "")
        data["window_id"] = window_id
        return data

    except Exception as err:
        return {"status": "error", "window_id": window_id, "message": str(err)}


ANALYZE_MOTION = FunctionTool(func=analyze_motion_tool)

# =============================================================================
# COLLISION AGENT TOOLS
# =============================================================================


async def analyze_collision_risk_tool(window_id: str, tool_context: ToolContext) -> Dict[str, Any]:
    """Tool: multimodal collision risk assessment (motion + camera + BEV)."""
    try:
        scenario_name = SCENARIO_PATH.name

        motion_file = SCENARIO_PATH / \
            f"motion_{scenario_name}_w{window_id}.json"
        if not motion_file.exists():
            return {"status": "error", "window_id": window_id, "message": "Motion file not found"}

        with open(motion_file, 'r') as f:
            motion_data = json.load(f)

        camera_path = SCENARIO_PATH / f"cam_{scenario_name}_w{window_id}.png"
        bev_path = SCENARIO_PATH / \
            f"bev_occupancy_{scenario_name}_w{window_id}.png"

        if not camera_path.exists() or not bev_path.exists():
            return {"status": "error", "window_id": window_id, "message": "Images not found"}

        camera_bytes = camera_path.read_bytes()
        bev_bytes = bev_path.read_bytes()

        # Calculate motion metrics from raw IMU data
        accel_x = motion_data["accel_x"]
        accel_y = motion_data["accel_y"]
        gyro_z = motion_data["gyro_z"]
        roll = motion_data["roll"]
        pitch = motion_data["pitch"]
        
        horiz_accel = [math.sqrt(ax**2 + ay**2) for ax, ay in zip(accel_x, accel_y)]
        peak_horiz_accel = max(horiz_accel) if horiz_accel else 0.0
        peak_gyro_z = max(abs(gz) for gz in gyro_z) if gyro_z else 0.0
        max_tilt = max(max(abs(r) for r in roll) if roll else 0.0,
                       max(abs(p) for p in pitch) if pitch else 0.0)
        
        motion_summary = {
            "peak_horizontal_accel_mps2": round(peak_horiz_accel, 3),
            "peak_angular_velocity_radps": round(peak_gyro_z, 3),
            "max_tilt_deg": round(max_tilt, 1),
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
            model=GEMINI_MODEL_COLLISION,
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

    except Exception as err:
        return {"status": "error", "window_id": window_id, "message": str(err)}


ANALYZE_COLLISION = FunctionTool(func=analyze_collision_risk_tool)

# =============================================================================
# PERCEPTION AGENTS
# =============================================================================

perception_loop_agent = Agent(
    name="PerceptionLoopAgent",
    model=Gemini(model=GEMINI_MODEL_PERCEPTION, api_key=GOOGLE_API_KEY),
    tools=[LIST_WINDOWS, ANALYZE_WINDOW_PERCEPTION],
    output_key="temp:perception_data",
    instruction="""You orchestrate perception analysis across all scenario windows.

Steps you MUST follow:
1. Call list_windows_tool() exactly once to get the ordered window_id list.
2. For each window_id returned (in that order), call analyze_window_perception_tool(window_id=...).
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
    model=Gemini(model=GEMINI_MODEL_PERCEPTION, api_key=GOOGLE_API_KEY),
    output_key="temp:perception_output",
    instruction="""You finalize the ODD perception report.

Input data from the previous agent:
{temp:perception_data?}

If no data is provided, respond with:
{"error": "missing_perception_data"}

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

# =============================================================================
# MOTION AGENTS
# =============================================================================

motion_loop_agent = Agent(
    name="MotionLoopAgent",
    model=Gemini(model=GEMINI_MODEL_MOTION, api_key=GOOGLE_API_KEY),
    tools=[LIST_WINDOWS, ANALYZE_MOTION],
    output_key="temp:motion_data",
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
    model=Gemini(model=GEMINI_MODEL_MOTION, api_key=GOOGLE_API_KEY),
    output_key="temp:motion_output",
    instruction="""You finalize the motion analysis report.

Input data from the previous agent:
{temp:motion_data?}

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
Only output JSON.""",
)

# =============================================================================
# COLLISION AGENTS
# =============================================================================

collision_loop_agent = Agent(
    name="CollisionLoopAgent",
    model=Gemini(model=GEMINI_MODEL_COLLISION, api_key=GOOGLE_API_KEY),
    tools=[LIST_WINDOWS, ANALYZE_COLLISION],
    output_key="temp:collision_data",
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
    model=Gemini(model=GEMINI_MODEL_COLLISION, api_key=GOOGLE_API_KEY),
    output_key="temp:collision_output",
    instruction="""You finalize the collision risk report.

Input data from the previous agent:
{temp:collision_data?}

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

# =============================================================================
# ODD SPECIFICATION AGENT
# =============================================================================

odd_spec_agent = Agent(
    name="OddSpecAgent",
    model=Gemini(model=GEMINI_MODEL_ODD_SPEC, api_key=GOOGLE_API_KEY),
    output_key="temp:odd_spec_output",
    instruction="""You are an Operational Design Domain (ODD) classification specialist.

TASK: Classify the robot's operational domain using multimodal analysis data.

INPUT DATA from previous agents:
Perception: {temp:perception_output?}
Motion: {temp:motion_output?}
Collision: {temp:collision_output?}

SYNTHESIS LOGIC:
**Categorical Axes:**
- environment_type: Use perception.environment_classification.primary_class
- lighting_conditions: Aggregate from perception.per_window_perception[*].lighting_class
- terrain_type: Aggregate from perception.per_window_perception[*].terrain_roughness_class

**Numeric Axes (extract ranges):**
- motion_detection_rate: from motion.overall_stats.motion_detection_rate
- peak_horizontal_accel: from motion.overall_stats.max_horizontal_accel_mps2
- obstacle_density: [min, max] from perception.per_window_perception[*].obstacle_density
- traversability: [min, max] from perception.per_window_perception[*].traversability_score
- collision_risk: [min, max] from collision.collision_events[*].collision_likelihood_score

Return ONLY valid JSON:
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
    "environment_type": ["evidence"],
    "lighting_conditions": ["evidence"],
    "terrain_type": ["evidence"]
  },
  "summary": "Brief natural language summary of the ODD"
}

No explanations outside JSON.""",
)

# =============================================================================
# COD ANALYSIS AGENT
# =============================================================================

cod_agent = Agent(
    name="CodAgent",
    model=Gemini(model=GEMINI_MODEL_COD, api_key=GOOGLE_API_KEY),
    output_key="temp:cod_output",
    instruction="""You are a Conditions of Design (COD) analysis specialist.

TASK: Compare observed ODD against expected design parameters.

INPUT DATA from previous agent:
{temp:odd_spec_output?}

DESIGN PARAMETERS (expected ODD):
- environment_type: indoor_office, indoor_corridor (designed for indoor only)
- lighting_conditions: bright, dim (requires adequate lighting)
- terrain_type: smooth_floor (designed for smooth surfaces only)
- speed_range: [0.0, 1.5] m/s (max design speed)
- obstacle_density: [0.0, 0.6] (moderate obstacles)
- traversability: [0.5, 1.0] (requires navigable space)
- collision_risk: [0.0, 0.3] (low risk threshold)

ANALYSIS:
For each axis, classify as:
- "IN_ODD": Observed value within expected parameters
- "ODD_BOUNDARY": Close to design limits
- "OUT_ODD": Exceeds design parameters

Return ONLY valid JSON:
{
  "cod_analysis": {
    "categorical_compliance": {
      "environment_type": "IN_ODD|OUT_ODD",
      "lighting_conditions": "IN_ODD|OUT_ODD",
      "terrain_type": "IN_ODD|OUT_ODD"
    },
    "numeric_compliance": {
      "speed_range": "IN_ODD|ODD_BOUNDARY|OUT_ODD",
      "obstacle_density": "IN_ODD|ODD_BOUNDARY|OUT_ODD",
      "traversability": "IN_ODD|ODD_BOUNDARY|OUT_ODD",
      "collision_risk": "IN_ODD|ODD_BOUNDARY|OUT_ODD"
    },
    "overall_compliance": "IN_ODD|ODD_BOUNDARY|OUT_ODD",
    "violations": ["list of any parameters OUT_ODD"],
    "warnings": ["list of any parameters at ODD_BOUNDARY"],
    "summary": "Brief assessment of COD compliance"
  }
}

No explanations outside JSON.""",
)

# =============================================================================
# REPORT GENERATION AGENT
# =============================================================================

report_agent = Agent(
    name="ReportAgent",
    model=Gemini(model=GEMINI_MODEL_REPORT, api_key=GOOGLE_API_KEY),
    instruction="""You are a technical report generator for ODD/COD analysis.

TASK: Produce a comprehensive human-readable report.

INPUT DATA from all previous agents:
Perception: {temp:perception_output?}
Motion: {temp:motion_output?}
Collision: {temp:collision_output?}
ODD Spec: {temp:odd_spec_output?}
COD Analysis: {temp:cod_output?}

Return ONLY valid JSON with this structure:
{
  "report": {
    "executive_summary": "2-3 sentence overview of the scenario",
    "scenario_metadata": {
      "total_windows_analyzed": <int>,
      "scenario_path": "<path>"
    },
    "perception_summary": "Brief summary of perception findings",
    "motion_summary": "Brief summary of motion characteristics",
    "collision_summary": "Brief summary of collision risk assessment",
    "odd_classification_summary": "Brief summary of ODD classification",
    "cod_compliance_summary": "Brief summary of COD compliance",
    "key_findings": ["finding1", "finding2", "finding3"],
    "recommendations": ["recommendation1", "recommendation2"],
    "timestamp": "<current_datetime>"
  },
  "full_analysis": {
    "perception": <perception_output>,
    "motion": <motion_output>,
    "collision": <collision_output>,
    "odd_spec": <odd_spec_output>,
    "cod": <cod_output>
  }
}

No explanations outside JSON.""",
)

# =============================================================================
# FULL WORKFLOW
# =============================================================================

odd_workflow = SequentialAgent(
    name="OddWorkflow",
    sub_agents=[
        perception_loop_agent,
        perception_summary_agent,
        motion_loop_agent,
        motion_summary_agent,
        collision_loop_agent,
        collision_summary_agent,
        odd_spec_agent,
        cod_agent,
        report_agent,
    ],
)


def _extract_final_report(events: list) -> Optional[Dict[str, Any]]:
    """Extract final report from ReportAgent output."""
    for event in events:
        if event.author == report_agent.name and event.content:
            for part in event.content.parts:
                if part.text:
                    try:
                        return _extract_json_block(part.text)
                    except Exception:
                        continue
    return None


async def run_odd_workflow(scenario_name: str = "sim_run_new") -> Optional[Dict[str, Any]]:
    """Run the complete ODD analysis workflow."""
    global SCENARIO_PATH
    SCENARIO_PATH = DATA_DIR / scenario_name

    if not SCENARIO_PATH.exists():
        print(f"❌ Scenario not found: {scenario_name}")
        return None

    print("\n" + "=" * 80)
    print(f"ODD WORKFLOW - FULL PIPELINE")
    print(f"Scenario: {scenario_name}")
    print("=" * 80)

    runner = InMemoryRunner(agent=odd_workflow, app_name="OddWorkflowApp")
    events = await runner.run_debug(f"Analyze scenario: {scenario_name}")

    report = _extract_final_report(events)

    if report:
        print("\n✅ WORKFLOW COMPLETED - Final Report:\n")
        print(json.dumps(report, indent=2))

        # Save report to file
        output_file = SCENARIO_PATH / "odd_analysis_report.json"
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n📄 Report saved to: {output_file}")
    else:
        print("\n❌ No valid report generated")

    return report


if __name__ == "__main__":
    try:
        result = asyncio.run(run_odd_workflow())
        if result is None:
            raise SystemExit(1)
        print("\n" + "=" * 80)
        print("✅ ODD WORKFLOW COMPLETED SUCCESSFULLY")
        print("=" * 80)
    except Exception as exc:
        print(f"\n❌ Fatal error: {exc}")
        import traceback
        traceback.print_exc()
        raise
