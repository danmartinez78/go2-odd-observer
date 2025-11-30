"""
ODD workflow orchestration.
Extracted from odd_workflow_full.py (reference implementation).
"""

import json
import time
from pathlib import Path
from typing import Optional, Dict, Any
from google.adk.agents import SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService
from google.genai import Client
import google.genai.types as types

from .utils import extract_json_block
from .metadata import hash_text, extract_pipeline_metadata, build_agent_registry
from .agent_prompts import get_all_prompts
from .robot_specs import get_robot_specs
from .agents import (
    create_odd_spec_agent,
    create_perception_agent,
    create_motion_agent,
    create_collision_agent,
    create_evaluator_agent,
    create_report_agent,
    AGENT_VERSIONS,
)


# =============================================================================
# FULL WORKFLOW
# =============================================================================

def create_odd_workflow(
    scenario_path: str,
    genai_client: Client,
    api_key: str,
    model_perception: str = "gemini-2.0-flash-exp",
    model_motion: str = "gemini-2.0-flash-exp",
    model_collision: str = "gemini-2.0-flash-exp",
    model_odd_spec: str = "gemini-2.0-flash-exp",
    model_evaluator: str = "gemini-2.0-flash-exp",
    model_report: str = "gemini-2.0-flash-exp",
) -> SequentialAgent:
    """Create a new ODD workflow instance with Phase 1.4.4 architecture.

    Phase 1.4.4 - Type-driven COD construction:
    - ODD Spec v5.0.0: Adds type definitions (range/bool/enum)
    - Sensor agents v5.0.0: Output per-window typed measurements
    - Evaluator v1.0.0: Uses Python tools for COD construction
    - Report v4.0.0: File-reading tool for efficient data access

    Args:
        scenario_path: Path to the scenario directory
        genai_client: Google GenAI client instance
        api_key: Google API key
        model_*: Model names for each agent (defaults to gemini-2.0-flash-exp)

    Returns:
        SequentialAgent workflow instance
    """
    from pathlib import Path
    scenario = Path(scenario_path)

    return SequentialAgent(
        name="OddWorkflow",
        sub_agents=[
            create_odd_spec_agent(api_key, model_odd_spec),
            create_perception_agent(
                scenario, genai_client, model_perception, api_key),
            create_motion_agent(
                str(scenario), genai_client, model_motion, api_key),
            create_collision_agent(
                str(scenario), genai_client, model_collision, api_key),
            create_evaluator_agent(
                scenario, genai_client, model_evaluator, api_key),
            create_report_agent(scenario, api_key, model_report),
        ],
    )


def extract_final_report(events: list) -> Optional[Dict[str, Any]]:
    """Extract final report from ReportAgent output or tool response."""

    def _unwrap_report(data: Dict[str, Any]) -> Dict[str, Any]:
        """Unwrap double-wrapped report if needed ({"result": "escaped json"})."""
        if isinstance(data, dict) and "result" in data and len(data) == 1:
            result = data["result"]
            if isinstance(result, str):
                try:
                    return json.loads(result)
                except json.JSONDecodeError:
                    pass
        return data

    for event in events:
        if event.author == "ReportAgent" and event.content and event.content.parts:
            for part in event.content.parts:
                # Check for direct text output
                if part.text:
                    try:
                        parsed = extract_json_block(part.text)
                        return _unwrap_report(parsed)
                    except Exception:
                        continue
                # Check for function response (tool return value)
                if hasattr(part, 'function_response') and part.function_response:
                    try:
                        response = part.function_response.response
                        if isinstance(response, str):
                            parsed = extract_json_block(response)
                            return _unwrap_report(parsed)
                        elif isinstance(response, dict):
                            return _unwrap_report(response)
                    except Exception:
                        continue
    return None


def extract_agent_output(events: list, agent_name: str) -> Optional[Dict[str, Any]]:
    """Extract output from a specific agent."""
    for event in events:
        if event.author == agent_name and event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    try:
                        return extract_json_block(part.text)
                    except Exception:
                        continue
    return None


def save_sensor_outputs(events: list, scenario_path: Path):
    """Save sensor agent outputs to files for Evaluator/Report access."""
    import json

    # Extract and save each sensor agent output
    for agent_name in ["PerceptionAgent", "MotionAgent", "CollisionAgent"]:
        output = extract_agent_output(events, agent_name)
        if output:
            output_file = scenario_path / \
                f"{agent_name.lower().replace('agent', '')}_output.json"
            with open(output_file, 'w') as f:
                json.dump(output, f, indent=2)
            print(f"📝 Saved {agent_name} output to {output_file.name}")

    # Also save ODD spec for reference
    odd_spec = extract_agent_output(events, "OddSpecAgent")
    if odd_spec:
        output_file = scenario_path / "odd_spec.json"
        with open(output_file, 'w') as f:
            json.dump(odd_spec, f, indent=2)
        print(f"📝 Saved ODD specification to {output_file.name}")


async def run_odd_workflow(
    scenario_path: str,
    genai_client: Client,
    api_key: str,
    nl_odd_description: Optional[str] = None,
    model_perception: str = "gemini-2.0-flash-exp",
    model_motion: str = "gemini-2.0-flash-exp",
    model_collision: str = "gemini-2.0-flash-exp",
    model_odd_spec: str = "gemini-2.0-flash-exp",
    model_evaluator: str = "gemini-2.0-flash-exp",
    model_report: str = "gemini-2.0-flash-exp",
    knowledge_seed: Optional[Dict[str, Any]] = None,
    debug: bool = False,
) -> Optional[Dict[str, Any]]:
    """Run the complete ODD analysis workflow with Phase 1.4.4 architecture.

    Phase 1.4.4 - Type-driven COD construction:
    - Deterministic Python tools for distance calculations (massive token savings)
    - Per-window typed measurements enable temporal violation tracking
    - File-based data handoff reduces blackboard overhead

    Args:
        scenario_path: Path to the scenario directory (e.g., "data/processed/runs/sim_run_new")
        genai_client: Google GenAI client instance
        api_key: Google API key
        nl_odd_description: Natural language ODD description. If None, uses default.
        model_*: Model names for each agent (defaults to gemini-2.0-flash-exp)
        knowledge_seed: Optional dict to seed session state with knowledge references
        debug: If True, use run_debug(verbose=True) for detailed tool call output

    Returns:
        Dictionary containing:
        - report: Final analysis report
        - full_analysis: Complete agent outputs
        - pipeline_metadata: Execution metadata (versions, models, tokens, timing)

        Returns None if failed.
    """
    scenario_path_obj = Path(scenario_path)
    scenario_name = scenario_path_obj.name

    if not scenario_path_obj.exists():
        print(f"❌ Scenario not found: {scenario_path}")
        return None

    # Default ODD description
    if nl_odd_description is None:
        nl_odd_description = (
            "A quadruped robot designed for indoor office environments. "
            "Operates on smooth, flat floors with adequate lighting (bright or dim). "
            "Maximum speed 1.5 m/s. Designed for environments with moderate obstacle "
            "density and good traversability. Requires low collision risk conditions. "
            "Not designed for: outdoor environments, stairs, rough terrain, "
            "dark/low-light areas, or high-density obstacle fields."
        )

    print("\n" + "=" * 80)
    print(f"ODD WORKFLOW - PHASE 1.4.4 (Type-Driven COD Construction)")
    print(f"Scenario: {scenario_name}")
    print(f"ODD Description: {nl_odd_description[:100]}...")
    print("=" * 80)

    # Get robot specs (for context, not part of ODD)
    robot_specs = get_robot_specs("go2")

    user_query = (
        f"Analyze scenario '{scenario_name}' against this ODD specification:\n\n"
        f"{nl_odd_description}\n\n"
        f"Robot Platform Specifications (for context only, NOT part of ODD):\n"
        f"{robot_specs}"
    )

    # Build agent registry for metadata tracking
    # Extract actual prompts from agent factory functions
    agent_prompts = get_all_prompts()

    agent_registry = build_agent_registry(
        agent_versions=AGENT_VERSIONS,
        agent_prompts=agent_prompts,
        model_perception=model_perception,
        model_motion=model_motion,
        model_collision=model_collision,
        model_odd_spec=model_odd_spec,
        model_evaluator=model_evaluator,
        model_report=model_report,
    )

    # Create fresh workflow instance
    odd_workflow = create_odd_workflow(
        scenario_path=scenario_path,
        genai_client=genai_client,
        api_key=api_key,
        model_perception=model_perception,
        model_motion=model_motion,
        model_collision=model_collision,
        model_odd_spec=model_odd_spec,
        model_evaluator=model_evaluator,
        model_report=model_report,
    )

    # Create services for data handoff between agents
    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()

    runner = Runner(
        agent=odd_workflow,
        app_name="OddWorkflowApp",
        session_service=session_service,
        artifact_service=artifact_service,  # Enable artifact-based data handoff
    )

    # Run workflow and track timing
    pipeline_start = time.time()

    # Create session and run
    user_id = "odd_analysis"

    # Seed session state with knowledge references if provided
    initial_state = knowledge_seed or {}
    if initial_state:
        print(f"\n📚 Knowledge seed loaded: {list(initial_state.keys())}")

    session = await session_service.create_session(
        app_name="OddWorkflowApp",
        user_id=user_id,
        state=initial_state,
    )

    events = []
    tool_calls = []

    # Debug mode: use run_debug with verbose output
    if debug:
        print("\n🔍 DEBUG MODE: Using run_debug(verbose=True)")
        print("=" * 80)
        events = await runner.run_debug(
            user_messages=user_query,
            user_id=user_id,
            session_id=session.id,
            verbose=True,
            quiet=False,
        )
        # Extract tool calls from debug events
        for event in events:
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        tool_calls.append(
                            f"{event.author}: {part.function_call.name}")
    else:
        # Normal mode: async iteration
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=types.Content(
                role="user",
                parts=[types.Part(text=user_query)]
            )
        ):
            events.append(event)
            # Track tool calls for debugging
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        tool_calls.append(
                            f"{event.author}: {part.function_call.name}")

    # Log tool calls summary
    print(f"\n📊 Tool calls ({len(tool_calls)} total):")
    for call in tool_calls:
        print(f"   • {call}")

    # Check artifacts saved and load them for post-processing
    artifacts_data = {}
    try:
        artifacts = await artifact_service.list_artifact_keys(
            app_name="OddWorkflowApp",
            user_id=user_id,
            session_id=session.id
        )
        print(f"\n📦 Artifacts saved: {artifacts}")

        # Load each artifact for post-processing
        for artifact_key in artifacts:
            try:
                artifact_part = await artifact_service.load_artifact(
                    app_name="OddWorkflowApp",
                    user_id=user_id,
                    session_id=session.id,
                    filename=artifact_key
                )
                if artifact_part and artifact_part.inline_data:
                    artifact_bytes = artifact_part.inline_data.data
                    artifacts_data[artifact_key] = json.loads(
                        artifact_bytes.decode('utf-8'))
                    print(f"   ✅ Loaded: {artifact_key}")
            except Exception as e:
                print(f"   ⚠️ Could not load {artifact_key}: {e}")
    except Exception as e:
        print(f"\n⚠️ Could not list artifacts: {e}")

    # Dump session state to file (captures cross-window insights from agents)
    state_outputs = {}
    try:
        final_session = await session_service.get_session(
            app_name="OddWorkflowApp",
            user_id=user_id,
            session_id=session.id
        )
        # Capture known output_key values from agents
        known_output_keys = {
            'odd_spec', 'perception_summary', 'motion_summary',
            'collision_summary', 'evaluator_output', 'report_output',
            'cod_classification', 'odd_compliance'
        }
        state_outputs = {
            k: v for k, v in final_session.state.items()
            if k in known_output_keys
        }
        if state_outputs:
            state_file = scenario_path_obj / "state_outputs.json"
            with open(state_file, 'w') as f:
                json.dump(state_outputs, f, indent=2)
            print(f"\n📋 State outputs saved: {list(state_outputs.keys())}")
    except Exception as e:
        print(f"\n⚠️ Could not dump state: {e}")

    pipeline_duration = time.time() - pipeline_start

    # Extract report
    report = extract_final_report(events)

    if report:
        print("\n✅ WORKFLOW COMPLETED - Final Report:\n")
        print(json.dumps(report, indent=2))

        # Save report to file
        output_file = scenario_path_obj / "odd_analysis_report.json"
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n📄 Report saved to: {output_file}")

        # Extract pipeline metadata from events
        pipeline_metadata = extract_pipeline_metadata(
            events=events,
            agent_registry=agent_registry,
            pipeline_start_time=pipeline_start,
            pipeline_duration=pipeline_duration,
            odd_spec_hash=hash_text(nl_odd_description),
            scenario_path=scenario_path,
        )

        # Compute lightweight analysis metadata for reports
        total_tokens = sum(
            exec_data.get('token_usage', {}).get('total_tokens', 0)
            for exec_data in pipeline_metadata['agent_executions'].values()
        )

        # Calculate accurate cost based on model-specific pricing
        from .pricing import calculate_pipeline_cost
        cost_data = calculate_pipeline_cost(
            pipeline_metadata['agent_executions'])

        analysis_metadata = {
            'pipeline_version': pipeline_metadata['pipeline_version'],
            'analysis_timestamp': pipeline_metadata['pipeline_start_time'],
            'analysis_duration_seconds': round(pipeline_metadata['pipeline_duration_seconds'], 2),
            'total_agents_executed': len(pipeline_metadata['agent_executions']),
            'total_tokens_used': total_tokens,
            'estimated_cost_usd': cost_data['total_usd'],
            'cost_breakdown': cost_data['breakdown'],
            'cost_per_agent': cost_data['per_agent'],
        }

        # Extract evaluator output for full_analysis
        evaluator_output = extract_agent_output(events, "EvaluatorAgent")

        # =====================================================================
        # POST-PIPELINE REPORT GENERATION (Phase 1.6 - Artifact-based)
        # =====================================================================
        # Use report_builder to generate comprehensive reports from:
        # 1. Artifacts (full per-window data from tools)
        # 2. Session state (agent summaries with temporal analysis)
        # 3. Pipeline metadata (versions, costs, timing)
        from .report_builder import generate_reports_from_artifacts

        # Generate both executive summary and full technical report
        reports = generate_reports_from_artifacts(
            artifacts=artifacts_data,
            session_state=state_outputs,
            pipeline_metadata=pipeline_metadata,
            output_dir=scenario_path_obj,  # Save to scenario directory
        )

        # Return report + metadata
        # Phase 1.6: Artifacts have full data, session has summaries
        return {
            'report': report,  # From ReportAgent (executive summary)
            'full_analysis': artifacts_data.get('cod_construction.json', evaluator_output or {}),
            'analysis_metadata': analysis_metadata,
            'pipeline_metadata': pipeline_metadata,
            # Comprehensive reports from post-processing
            'reports': {
                'executive_summary': reports['executive_summary'],
                'full_technical': reports['full_report'],
            },
            # Artifacts contain full per-window data
            'artifacts': artifacts_data,
            # Session state contains agent summaries
            'session_state': state_outputs,
        }
    else:
        print("\n❌ No valid report generated")
        return None
