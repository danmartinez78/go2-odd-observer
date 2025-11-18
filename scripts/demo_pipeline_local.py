"""
Demo Pipeline - Local Testing with Mock ADK Agents

Mirrors the notebooks/odd_cod_workflow.ipynb ADK agent architecture
using mock agents that return fake JSON without API calls.

This validates the complete data flow, file schema, and orchestration
pattern locally before running the real notebook with Gemini.

Architecture:
    1. ODD Spec Agent (mock) - NL → structured JSON
    2. ParallelAgent (mock):
       - Motion Agent
       - Vision Agent  
       - Terrain Agent
       - Collision Agent
    3. COD Evaluator Agent (mock) - aggregation + distance
    4. Report Generator Agent (mock) - markdown report

Matches: notebooks/odd_cod_workflow.ipynb Sections 4-7
"""

from odd_cod.odd_spec_schema import (
    OddSpec,
    AxisSpecNumeric,
    AxisSpecCategorical,
)
import sys
from pathlib import Path
import json
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from PIL import Image

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================================
# TOOL FUNCTIONS (copied from notebook Section 4)
# ============================================================================

def load_window_data(scenario_path: Path, window_id: str, run_id: str = None) -> Tuple[Dict, Image.Image, Dict[str, Image.Image]]:
    """
    Load motion, camera, and LiDAR BEV data for a single window.

    Matches the flat file structure created by extract_windows.py:
    - motion_{run_id}_w{window_id}.json
    - cam_{run_id}_w{window_id}.png
    - bev_{channel}_{run_id}_w{window_id}.png
    """
    if run_id is None:
        run_id = scenario_path.name

    motion_file = scenario_path / f"motion_{run_id}_w{window_id}.json"
    camera_file = scenario_path / f"cam_{run_id}_w{window_id}.png"

    if not motion_file.exists():
        raise FileNotFoundError(f"Motion file not found: {motion_file}")
    with open(motion_file, 'r') as f:
        motion_data = json.load(f)

    if not camera_file.exists():
        raise FileNotFoundError(f"Camera file not found: {camera_file}")
    camera_img = Image.open(camera_file)

    bev_images = {}
    for channel in ['occupancy', 'height', 'density', 'roughness']:
        bev_file = scenario_path / f"bev_{channel}_{run_id}_w{window_id}.png"
        if bev_file.exists():
            bev_images[channel] = Image.open(bev_file)

    return motion_data, camera_img, bev_images


def load_scenario_index(scenario_path: Path) -> pd.DataFrame:
    """Load the window index CSV for a scenario."""
    index_files = list(scenario_path.glob("index_*.csv"))
    if not index_files:
        raise FileNotFoundError(f"No index file found in {scenario_path}")
    return pd.read_csv(index_files[0])


def build_odd_spec_from_json(spec_json: Dict) -> OddSpec:
    """Construct OddSpec object from JSON (matches notebook)."""
    axes = {}
    for axis_name, axis_data in spec_json["axes"].items():
        if axis_data["type"] == "numeric":
            axes[axis_name] = AxisSpecNumeric(
                feature=axis_data["feature"],
                units=axis_data["units"],
                in_odd=tuple(axis_data["in_odd"]),
                near_boundary=tuple(axis_data["near_boundary"]),
                hard_limit=tuple(axis_data["hard_limit"])
            )
        elif axis_data["type"] == "categorical":
            axes[axis_name] = AxisSpecCategorical(
                feature=axis_data["feature"],
                allowed_in_odd=set(axis_data["allowed_in_odd"]),
                allowed_all=set(axis_data["allowed_all"])
            )

    return OddSpec(
        version=spec_json["version"],
        description=spec_json["description"],
        axes=axes,
        importance=spec_json["importance"]
    )


# ============================================================================
# MOCK ADK AGENTS (return fake JSON matching real agent schemas)
# ============================================================================

class MockODDSpecAgent:
    """Mock ODD Specification Agent - converts NL → structured JSON."""

    def __init__(self, name="Mock_ODD_Spec_Agent"):
        self.name = name

    def run(self, nl_odd_description: str) -> Dict:
        """Return fake but valid ODD spec JSON."""
        print(f"[{self.name}] Parsing natural language ODD...")

        # Hardcoded spec matching typical indoor robot ODD
        return {
            "version": "1.0",
            "description": "Mock ODD for indoor delivery robot",
            "axes": {
                "speed": {
                    "type": "numeric",
                    "feature": "forward_velocity",
                    "units": "m/s",
                    "in_odd": [0.0, 1.5],
                    "near_boundary": [0.0, 1.8],
                    "hard_limit": [0.0, 2.0]
                },
                "roll_pitch": {
                    "type": "numeric",
                    "feature": "max_abs_roll_pitch",
                    "units": "degrees",
                    "in_odd": [0.0, 10.0],
                    "near_boundary": [0.0, 15.0],
                    "hard_limit": [0.0, 20.0]
                },
                "terrain": {
                    "type": "categorical",
                    "feature": "terrain_type",
                    "allowed_in_odd": ["smooth", "moderate"],
                    "allowed_all": ["smooth", "moderate", "rough", "very_rough"]
                },
                "lighting": {
                    "type": "categorical",
                    "feature": "lighting_condition",
                    "allowed_in_odd": ["bright", "dim"],
                    "allowed_all": ["bright", "dim", "dark"]
                },
                "humans": {
                    "type": "categorical",
                    "feature": "human_proximity",
                    "allowed_in_odd": ["none", "visible_far"],
                    "allowed_all": ["none", "visible_far", "very_close"]
                },
                "collision": {
                    "type": "categorical",
                    "feature": "collision_state",
                    "allowed_in_odd": ["no_collision"],
                    "allowed_all": ["no_collision", "collision_suspected"]
                }
            },
            "importance": {
                "collision": 2.0,
                "humans": 1.5,
                "roll_pitch": 1.2,
                "speed": 1.0,
                "terrain": 1.0,
                "lighting": 0.8
            }
        }


class MockMotionAgent:
    """Mock Motion Analysis Agent."""

    def __init__(self, name="Mock_Motion_Agent"):
        self.name = name

    def run(self, motion_data: Dict) -> Dict:
        """Analyze motion JSON with simple heuristics."""
        print(f"  [{self.name}] Analyzing motion data...")

        avg_speed = np.mean(motion_data.get("odom_vx", [0.0]))
        max_speed = np.max(np.abs(motion_data.get("odom_vx", [0.0])))

        rolls = motion_data.get("roll", [0.0])
        pitches = motion_data.get("pitch", [0.0])
        max_roll_pitch = max(np.max(np.abs(rolls)), np.max(np.abs(pitches)))

        return {
            "avg_forward_speed": float(avg_speed),
            "max_forward_speed": float(max_speed),
            "max_abs_roll_pitch_deg": float(max_roll_pitch),
            "motion_compliant": max_speed < 1.5 and max_roll_pitch < 10.0
        }


class MockVisionAgent:
    """Mock Vision Analysis Agent."""

    def __init__(self, name="Mock_Vision_Agent"):
        self.name = name

    def run(self, camera_img: Image.Image) -> Dict:
        """Analyze camera image (fake analysis)."""
        print(f"  [{self.name}] Analyzing camera image...")

        # Fake: assume good indoor conditions
        return {
            "lighting_class": "bright",
            "humans_visible": False,
            "humans_very_close": False,
            "environment_type": "indoor_office",
            "vision_compliant": True
        }


class MockTerrainAgent:
    """Mock Terrain Analysis Agent."""

    def __init__(self, name="Mock_Terrain_Agent"):
        self.name = name

    def run(self, bev_images: Dict[str, Image.Image]) -> Dict:
        """Analyze LiDAR BEV images (fake analysis)."""
        print(
            f"  [{self.name}] Analyzing LiDAR BEV ({len(bev_images)} channels)...")

        # Fake: assume smooth terrain
        return {
            "terrain_roughness_class": "smooth",
            "terrain_roughness_score": 0.1,
            "obstacle_density": "low",
            "terrain_compliant": True
        }


class MockCollisionAgent:
    """Mock Collision Detection Agent."""

    def __init__(self, name="Mock_Collision_Agent"):
        self.name = name

    def run(self, motion_result: Dict, vision_result: Dict, terrain_result: Dict) -> Dict:
        """Multi-modal collision detection (fake analysis)."""
        print(f"  [{self.name}] Performing multi-modal collision analysis...")

        # Simple heuristic: no collision suspected in demo data
        return {
            "collision_suspected": False,
            "collision_confidence": 0.0,
            "collision_type": "none",
            "collision_compliant": True
        }


class MockCODEvaluatorAgent:
    """Mock COD Evaluator Agent."""

    def __init__(self, name="Mock_COD_Evaluator"):
        self.name = name

    def run(self, odd_spec: OddSpec, motion_results: List[Dict],
            vision_results: List[Dict], terrain_results: List[Dict],
            collision_results: List[Dict]) -> Dict:
        """Aggregate sensor analyses and compute ODD violations."""
        print(f"[{self.name}] Evaluating {len(motion_results)} windows...")

        violations = []
        for i, (motion, vision, terrain, collision) in enumerate(
            zip(motion_results, vision_results,
                terrain_results, collision_results)
        ):
            window_violations = []

            # Check speed
            if motion["max_forward_speed"] > 1.5:
                window_violations.append(
                    f"Speed: {motion['max_forward_speed']:.2f} m/s > 1.5 m/s")

            # Check roll/pitch
            if motion["max_abs_roll_pitch_deg"] > 10.0:
                window_violations.append(
                    f"Roll/Pitch: {motion['max_abs_roll_pitch_deg']:.1f}° > 10.0°")

            # Check collision
            if collision["collision_suspected"]:
                window_violations.append("Collision detected")

            if window_violations:
                violations.append({
                    "window_id": f"{i:03d}",
                    "violations": window_violations
                })

        return {
            "total_windows": len(motion_results),
            "compliant_windows": len(motion_results) - len(violations),
            "violation_windows": len(violations),
            "violations": violations,
            "overall_status": "IN_ODD" if not violations else "ODD_EXIT"
        }


class MockReportAgent:
    """Mock Report Generator Agent."""

    def __init__(self, name="Mock_Report_Generator"):
        self.name = name

    def run(self, odd_spec: OddSpec, cod_eval_result: Dict) -> str:
        """Generate markdown report."""
        print(f"[{self.name}] Generating analysis report...")

        total = cod_eval_result["total_windows"]
        compliant = cod_eval_result["compliant_windows"]
        violations = cod_eval_result["violation_windows"]

        report = f"""# ODD Compliance Analysis Report

## Executive Summary
- **Total Windows Analyzed**: {total}
- **Compliant Windows**: {compliant} ({compliant/total*100:.1f}%)
- **Violation Windows**: {violations} ({violations/total*100:.1f}%)
- **Overall Status**: {cod_eval_result['overall_status']}

## ODD Specification
- Version: {odd_spec.version}
- Description: {odd_spec.description}
- Axes: {', '.join(odd_spec.axes.keys())}

## Violations Detected
"""

        if cod_eval_result["violations"]:
            for v in cod_eval_result["violations"]:
                report += f"\n### Window {v['window_id']}\n"
                for violation in v["violations"]:
                    report += f"- {violation}\n"
        else:
            report += "\nNo violations detected. All windows are ODD-compliant.\n"

        report += "\n## Recommendations\n"
        report += "- Continue monitoring for edge cases\n"
        report += "- Validate with real-world deployment data\n"

        return report


# ============================================================================
# MOCK ORCHESTRATION (mimics ADK ParallelAgent + SequentialAgent)
# ============================================================================

class MockParallelAgent:
    """Mock parallel execution of sensor agents."""

    def __init__(self, name: str, agents: List):
        self.name = name
        self.agents = agents

    def run(self, inputs: Dict) -> Dict:
        """Run all agents in 'parallel' (sequential for mock)."""
        print(f"\n[{self.name}] Running {len(self.agents)} agents...")
        results = {}
        for agent in self.agents:
            # Each agent gets appropriate inputs
            if "Motion" in agent.name:
                results["motion"] = agent.run(inputs["motion_data"])
            elif "Vision" in agent.name:
                results["vision"] = agent.run(inputs["camera_img"])
            elif "Terrain" in agent.name:
                results["terrain"] = agent.run(inputs["bev_images"])
            elif "Collision" in agent.name:
                results["collision"] = agent.run(
                    results["motion"], results["vision"], results["terrain"]
                )
        return results


class MockSequentialAgent:
    """Mock sequential execution of workflow stages."""

    def __init__(self, name: str, agents: List):
        self.name = name
        self.agents = agents

    def run(self, user_input: str, scenario_path: Path) -> Dict:
        """Run agents sequentially, passing data between them."""
        print(f"\n[{self.name}] Starting sequential workflow...")

        session_state = {}

        # Stage 1: ODD Spec Agent
        odd_spec_json = self.agents[0].run(user_input)
        session_state["odd_spec_json"] = odd_spec_json
        session_state["odd_spec"] = build_odd_spec_from_json(odd_spec_json)

        # Load window index
        index_df = load_scenario_index(scenario_path)
        print(f"\nLoaded {len(index_df)} windows from {scenario_path.name}")

        # Stage 2: Analyze each window with ParallelAgent (sensor team)
        motion_results = []
        vision_results = []
        terrain_results = []
        collision_results = []

        for idx, row in index_df.iterrows():
            window_id = f"{row['window_id']:03d}"
            print(f"\n--- Window {window_id} ---")

            # Load window data
            motion_data, camera_img, bev_images = load_window_data(
                scenario_path, window_id
            )

            # Run sensor team (ParallelAgent)
            sensor_results = self.agents[1].run({
                "motion_data": motion_data,
                "camera_img": camera_img,
                "bev_images": bev_images
            })

            motion_results.append(sensor_results["motion"])
            vision_results.append(sensor_results["vision"])
            terrain_results.append(sensor_results["terrain"])
            collision_results.append(sensor_results["collision"])

        # Stage 3: COD Evaluator
        cod_eval_result = self.agents[2].run(
            session_state["odd_spec"],
            motion_results,
            vision_results,
            terrain_results,
            collision_results
        )
        session_state["cod_eval"] = cod_eval_result

        # Stage 4: Report Generator
        final_report = self.agents[3].run(
            session_state["odd_spec"],
            cod_eval_result
        )
        session_state["final_report"] = final_report

        return session_state


# ============================================================================
# MAIN WORKFLOW (mimics notebook Section 7)
# ============================================================================

def main():
    """Main entry point - mirrors notebook workflow."""
    print("=" * 80)
    print("Go2 ODD/COD Demo Pipeline - Mock ADK Agents")
    print("=" * 80)
    print("\nThis script mirrors notebooks/odd_cod_workflow.ipynb using mock agents.")
    print("It validates the complete data flow without requiring Gemini API calls.\n")

    # User inputs (Section 3 in notebook)
    nl_odd_description = """
Indoor Delivery Robot ODD:
- Maximum speed: 1.5 m/s
- Terrain: smooth or moderate (office floors, carpet)
- Lighting: bright or dim (not dark)
- Human proximity: maintain safe distance (>1m)
- Zero collision tolerance
"""

    DATA_DIR = Path(__file__).parent.parent / "data" / "processed" / "runs"
    scenario_path = DATA_DIR / "sim_run_new"
    
    if not scenario_path.exists():
        # Fall back to demo_run if sim_run_new doesn't exist
        scenario_path = DATA_DIR / "demo_run"
        if not scenario_path.exists():
            print(f"Error: No scenario data found in {DATA_DIR}")
            print("Please run scripts/extract_windows.py first.")
            return 1
    
    print(f"User Input (NL ODD):\n{nl_odd_description}")
    print(f"\nDataset: {scenario_path}")

    # Create mock agents (Section 5 in notebook)
    print("\n" + "=" * 80)
    print("Creating Mock Agents...")
    print("=" * 80)

    odd_spec_agent = MockODDSpecAgent()
    motion_agent = MockMotionAgent()
    vision_agent = MockVisionAgent()
    terrain_agent = MockTerrainAgent()
    collision_agent = MockCollisionAgent()
    cod_evaluator = MockCODEvaluatorAgent()
    report_generator = MockReportAgent()

    # Create orchestration (Section 6 in notebook)
    sensor_team = MockParallelAgent(
        name="Mock_SensorAnalysisTeam",
        agents=[motion_agent, vision_agent, terrain_agent, collision_agent]
    )

    workflow = MockSequentialAgent(
        name="Mock_ODDAnalysisWorkflow",
        agents=[odd_spec_agent, sensor_team, cod_evaluator, report_generator]
    )

    # Execute workflow (Section 7 in notebook)
    print("\n" + "=" * 80)
    print("Executing Workflow...")
    print("=" * 80)

    try:
        result = workflow.run(nl_odd_description, scenario_path)

        print("\n" + "=" * 80)
        print("FINAL REPORT")
        print("=" * 80)
        print(result["final_report"])

        print("\n✓ Demo pipeline complete!")
        print("\nNext step: Run notebooks/odd_cod_workflow.ipynb with real Gemini agents")

        return 0

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
