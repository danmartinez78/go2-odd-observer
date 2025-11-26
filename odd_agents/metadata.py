"""
Pipeline Metadata Extraction Utilities

Event-based metadata tracking for agent versioning, prompt hashing,
and telemetry collection. Uses ADK event stream to extract execution
metadata without modifying agent prompts.

Approach: Event Stream Extraction
- Parse events from runner.run_debug()
- Extract per-agent metadata (version, model, tokens, timing)
- No prompt modifications needed
- No callback system dependencies
"""

import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional


def hash_text(text: str) -> str:
    """Generate deterministic SHA-256 hash of text (16-char hex).

    Used for tracking prompt changes and ODD specification versions.

    Args:
        text: Text to hash (prompt template, ODD description, etc.)

    Returns:
        First 16 characters of SHA-256 hash in hex format

    Example:
        >>> hash_text("You are a COD classifier...")
        'a1b2c3d4e5f6g7h8'
    """
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def build_agent_registry(
    agent_versions: Dict[str, str],
    agent_prompts: Dict[str, str],
    model_perception: str,
    model_motion: str,
    model_collision: str,
    model_odd_spec: str,
    model_cod: str,
    model_report: str,
) -> Dict[str, Dict[str, Any]]:
    """Build agent registry with versions, models, and prompt hashes.

    Registry maps agent names to their declared configuration:
    - version: Agent version (from AGENT_VERSION constants)
    - model: Declared model name
    - prompt_hash: Hash of prompt template

    Args:
        agent_versions: Map of agent_name -> version string
        agent_prompts: Map of agent_name -> prompt template text
        model_*: Model names for each agent type

    Returns:
        Registry dict: {agent_name: {version, model, prompt_hash}}

    Example:
        >>> registry = build_agent_registry(
        ...     agent_versions={'CodClassifierAgent': '2.0.0'},
        ...     agent_prompts={'CodClassifierAgent': 'You are...'},
        ...     model_cod='gemini-2.5-flash',
        ...     ...
        ... )
        >>> registry['CodClassifierAgent']
        {'version': '2.0.0', 'model': 'gemini-2.5-flash', 'prompt_hash': 'a1b2c3d4'}
    """
    return {
        'OddSpecAgent': {
            'version': agent_versions.get('OddSpecAgent', 'unknown'),
            'model': model_odd_spec,
            'prompt_hash': hash_text(agent_prompts.get('OddSpecAgent', '')),
        },
        'PerceptionAgent': {
            'version': agent_versions.get('PerceptionAgent', 'unknown'),
            'model': model_perception,
            'prompt_hash': hash_text(agent_prompts.get('PerceptionAgent', '')),
        },
        'MotionAgent': {
            'version': agent_versions.get('MotionAgent', 'unknown'),
            'model': model_motion,
            'prompt_hash': hash_text(agent_prompts.get('MotionAgent', '')),
        },
        'CollisionAgent': {
            'version': agent_versions.get('CollisionAgent', 'unknown'),
            'model': model_collision,
            'prompt_hash': hash_text(agent_prompts.get('CollisionAgent', '')),
        },
        'CodMeasurementAgent': {
            'version': agent_versions.get('CodMeasurementAgent', 'unknown'),
            'model': model_cod,
            'prompt_hash': hash_text(agent_prompts.get('CodMeasurementAgent', '')),
        },
        'OddComplianceAgent': {
            'version': agent_versions.get('OddComplianceAgent', 'unknown'),
            'model': model_cod,
            'prompt_hash': hash_text(agent_prompts.get('OddComplianceAgent', '')),
        },
        'ReportAgent': {
            'version': agent_versions.get('ReportAgent', 'unknown'),
            'model': model_report,
            'prompt_hash': hash_text(agent_prompts.get('ReportAgent', '')),
        },
    }


def extract_pipeline_metadata(
    events: List[Any],
    agent_registry: Dict[str, Dict[str, Any]],
    pipeline_start_time: float,
    pipeline_duration: float,
    odd_spec_hash: str,
    scenario_path: str,
    pipeline_version: str = "2.0.0",
) -> Dict[str, Any]:
    """Extract metadata from ADK event stream.

    Parses events from runner.run_debug() to build comprehensive metadata:
    - Per-agent execution data (version, model, tokens, timing)
    - Pipeline-level stats (duration, total agents)
    - ODD specification tracking
    - Model verification (declared vs actual)

    Args:
        events: List of Event objects from runner.run_debug()
        agent_registry: Registry from build_agent_registry()
        pipeline_start_time: Unix timestamp when pipeline started
        pipeline_duration: Total pipeline duration in seconds
        odd_spec_hash: Hash of ODD description text
        scenario_path: Path to scenario being analyzed
        pipeline_version: Version string for pipeline

    Returns:
        Metadata dict with:
        - pipeline_version: Pipeline version string
        - pipeline_start_time: ISO timestamp
        - pipeline_duration_seconds: Execution time
        - odd_specification: {hash, version}
        - scenario_info: {path, name}
        - agent_executions: Per-agent metadata
        - total_agents_executed: Count of agents run

    Example:
        >>> metadata = extract_pipeline_metadata(
        ...     events=event_list,
        ...     agent_registry=registry,
        ...     pipeline_start_time=time.time(),
        ...     pipeline_duration=45.2,
        ...     odd_spec_hash='a1b2c3d4',
        ...     scenario_path='data/production/sim_test',
        ... )
        >>> metadata['agent_executions']['CodClassifierAgent']
        {
            'agent_name': 'CodClassifierAgent',
            'version': '2.0.0',
            'declared_model': 'gemini-2.5-flash',
            'actual_model': 'gemini-2.0-flash-exp',
            'prompt_hash': 'c9e2b4f7',
            'timestamp': '2025-11-25T15:30:00Z',
            'invocation_id': 'e-1479377d...',
            'token_usage': {'prompt_tokens': 890, ...}
        }
    """
    agent_executions = {}

    # Process events to extract per-agent metadata
    for event in events:
        agent_name = event.author

        # Skip non-agent events (user messages, system events)
        if agent_name not in agent_registry:
            continue

        # First event for this agent = execution record
        # (Subsequent events are ignored - we only need first occurrence)
        if agent_name not in agent_executions:
            registry_entry = agent_registry[agent_name]

            # Build agent execution metadata
            agent_exec = {
                'agent_name': agent_name,
                'version': registry_entry['version'],
                'declared_model': registry_entry['model'],
                'prompt_hash': registry_entry['prompt_hash'],
                'timestamp': datetime.fromtimestamp(event.timestamp, tz=timezone.utc).isoformat(),
                'invocation_id': event.invocation_id,
            }

            # Add actual model from event (for verification)
            if hasattr(event, 'model_version') and event.model_version:
                agent_exec['actual_model'] = event.model_version

            # Add token usage if available
            if hasattr(event, 'usage_metadata') and event.usage_metadata:
                agent_exec['token_usage'] = {
                    'prompt_tokens': event.usage_metadata.prompt_token_count,
                    'completion_tokens': event.usage_metadata.candidates_token_count,
                    'total_tokens': event.usage_metadata.total_token_count,
                }

            agent_executions[agent_name] = agent_exec

    # Build complete pipeline metadata
    return {
        'pipeline_version': pipeline_version,
        'pipeline_start_time': datetime.fromtimestamp(pipeline_start_time, tz=timezone.utc).isoformat(),
        'pipeline_duration_seconds': round(pipeline_duration, 2),

        'odd_specification': {
            'hash': odd_spec_hash,
            'version': 'embedded',  # Could be versioned separately in future
        },

        'scenario_info': {
            'scenario_path': scenario_path,
            'scenario_name': Path(scenario_path).name,
        },

        'agent_executions': agent_executions,
        'total_agents_executed': len(agent_executions),
    }
