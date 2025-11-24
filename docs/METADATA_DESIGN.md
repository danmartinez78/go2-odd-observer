# Pipeline Metadata/Telemetry Tracking System Design

**Date:** November 24, 2025  
**Status:** Design Document  
**Context:** Architecture redesign pipeline metadata requirements (ARCHITECTURE_REDESIGN.md § Pipeline Metadata & Telemetry)

## Executive Summary

This document evaluates four approaches for tracking pipeline metadata (agent versions, prompt hashes, ODD specs, execution stats) to enable reproducibility, debugging, and A/B testing. After analyzing ADK compatibility, implementation complexity, and robustness tradeoffs, **we recommend the Hybrid Approach (D)** combining prompt-based self-reporting with workflow-level validation and injection.

**Key Decision Factors:**
- ✅ **ADK Compatible:** No breaking changes to agent framework
- ✅ **Zero Infrastructure:** Works with existing ADK SequentialAgent chains
- ✅ **Simple Migration:** Add metadata instructions to agent prompts incrementally
- ✅ **Robust Fallback:** Workflow validates and supplements missing metadata
- ✅ **Minimal Complexity:** ~150 lines of code, no wrappers/decorators

---

## 1. Approach Comparison

### Approach A: Prompt-Only

**Description:** Agents self-report metadata in their JSON outputs via prompt instructions.

**Implementation:**
```python
# In each agent's instruction prompt
def create_cod_classifier_agent(api_key: str, model: str) -> Agent:
    return Agent(
        name="CodClassifierAgent",
        model=Gemini(model=model, api_key=api_key),
        output_key="temp:cod_classification",
        instruction="""You are a Current Operating Domain (COD) classifier.

TASK: Classify the robot's CURRENT operating domain from sensor analysis.

[... existing instructions ...]

METADATA REPORTING:
Include this metadata in your JSON output:
{
  "agent_metadata": {
    "agent_name": "CodClassifierAgent",
    "version": "2.0.0",
    "model": "gemini-2.0-flash-lite",
    "analysis_timestamp": "<ISO 8601 timestamp>"
  },
  "cod_classification": {
    [... your analysis ...]
  }
}
""",
    )
```

**Example Output:**
```json
{
  "agent_metadata": {
    "agent_name": "CodClassifierAgent",
    "version": "2.0.0",
    "model": "gemini-2.0-flash-lite",
    "analysis_timestamp": "2025-11-24T15:30:00Z"
  },
  "cod_classification": {
    "categorical": { "lighting_conditions": "bright" },
    "numeric": { "obstacle_density": 0.42 }
  }
}
```

#### Pros
- ✅ **Zero infrastructure code** - No wrappers, decorators, or middleware
- ✅ **100% ADK compatible** - Pure prompt modification, no framework changes
- ✅ **Self-documenting** - Metadata visible in agent outputs during debugging
- ✅ **Incremental adoption** - Add to agents one at a time
- ✅ **No performance overhead** - No additional code execution

#### Cons
- ❌ **Unreliable** - Agent may hallucinate version numbers or forget to include metadata
- ❌ **No enforcement** - Can't guarantee metadata presence or correctness
- ❌ **Prompt pollution** - Adds complexity to agent instructions
- ❌ **Model dependency** - Less capable models may struggle with metadata requirements
- ❌ **No prompt hash** - Agent can't compute hash of its own prompt

#### ADK Compatibility
✅ **Perfect** - No ADK API usage required, just prompt text changes

#### Risk Assessment
- **Hallucination risk:** HIGH - Model may invent version numbers
- **Omission risk:** MEDIUM - Model may forget metadata in JSON
- **Format risk:** LOW - JSON structure usually consistent

**Verdict:** ❌ **Not Recommended** as standalone approach due to reliability issues

---

### Approach B: Infrastructure/Wrapper

**Description:** Python code wraps agent execution to inject metadata before/after agent runs.

**Implementation:**
```python
import hashlib
import time
from datetime import datetime, timezone
from typing import Any, Dict
from google.adk.agents import Agent
from functools import wraps

# Metadata decorator approach
def with_metadata(version: str, prompt_template: str):
    """Decorator to add metadata tracking to agent factory functions."""
    def decorator(agent_factory_func):
        @wraps(agent_factory_func)
        def wrapper(*args, **kwargs):
            # Create agent normally
            agent = agent_factory_func(*args, **kwargs)
            
            # Compute prompt hash
            prompt_hash = hashlib.sha256(
                prompt_template.encode()
            ).hexdigest()[:16]
            
            # Store metadata on agent instance
            agent._metadata = {
                "version": version,
                "prompt_hash": prompt_hash,
                "agent_name": agent.name,
            }
            
            # Wrap agent execution (if possible)
            # NOTE: ADK Agent doesn't expose easy hook for this
            # Would require monkey-patching or subclassing
            
            return agent
        return wrapper
    return decorator

# Usage
AGENT_VERSION = "2.0.0"
PROMPT_TEMPLATE = """You are a COD classifier..."""

@with_metadata(version=AGENT_VERSION, prompt_template=PROMPT_TEMPLATE)
def create_cod_classifier_agent(api_key: str, model: str) -> Agent:
    return Agent(
        name="CodClassifierAgent",
        model=Gemini(model=model, api_key=api_key),
        instruction=PROMPT_TEMPLATE,
        # ...
    )
```

**Metadata Injection at Workflow Level:**
```python
async def run_odd_workflow(scenario_path: str, ...) -> Dict[str, Any]:
    start_time = time.time()
    
    # Create agents
    cod_agent = create_cod_classifier_agent(api_key, model_cod)
    
    # Collect metadata from agents
    agent_metadata = {
        "cod_classifier": cod_agent._metadata,
        # ... other agents
    }
    
    # Run workflow
    odd_workflow = SequentialAgent(
        name="OddWorkflow",
        sub_agents=[cod_agent, ...]
    )
    runner = InMemoryRunner(agent=odd_workflow, app_name="ODD")
    events = await runner.run_debug(user_query)
    
    # Extract result
    result = extract_final_report(events)
    
    # Inject metadata into final output
    result["pipeline_metadata"] = {
        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
        "pipeline_version": PIPELINE_VERSION,
        "agent_versions": agent_metadata,
        "execution_stats": {
            "total_duration_seconds": time.time() - start_time,
            # Token counts would require ADK instrumentation
        }
    }
    
    return result
```

#### Pros
- ✅ **Guaranteed correctness** - Code-computed values, no hallucination
- ✅ **Centralized control** - Metadata logic in one place
- ✅ **Prompt hash automation** - Automatically computed from template
- ✅ **Execution stats** - Can track timing, token usage (with ADK hooks)

#### Cons
- ❌ **ADK limitations** - No built-in execution hooks for per-agent metadata injection
- ❌ **Requires monkey-patching** - Would need to subclass Agent or patch internals
- ❌ **Breaking changes risk** - ADK updates could break wrapper logic
- ❌ **Complexity** - ~200-300 lines of wrapper/decorator infrastructure
- ❌ **Testing burden** - Need tests for wrapper logic, not just agents

#### ADK Compatibility
⚠️ **Limited** - ADK Agent class doesn't expose execution lifecycle hooks.
- No `before_execute()` or `after_execute()` methods
- No middleware pattern in SequentialAgent
- Would require:
  - Subclassing `Agent` (fragile, may break on updates)
  - Monkey-patching (dangerous, maintenance burden)
  - Custom runner (bypasses ADK features)

**ADK Investigation Results:**
```python
# What we need but ADK doesn't provide:
class MetadataAgent(Agent):
    def before_execute(self, input_data):
        # Inject metadata before execution
        pass
    
    def after_execute(self, output_data):
        # Inject metadata after execution
        return {**output_data, "metadata": self._metadata}

# ADK SequentialAgent doesn't support:
SequentialAgent(
    sub_agents=[...],
    middleware=[metadata_injector],  # Not available
)
```

#### Risk Assessment
- **Maintenance risk:** HIGH - Fragile wrapper code, ADK updates may break
- **Complexity risk:** MEDIUM - Additional infrastructure to maintain
- **Migration risk:** HIGH - Requires refactoring all agent factories

**Verdict:** ❌ **Not Recommended** - ADK doesn't support execution hooks, would require fragile workarounds

---

### Approach C: Workflow-Level Only

**Description:** Single metadata injection at workflow completion, no per-agent tracking.

**Implementation:**
```python
# Agent versioning constants
AGENT_VERSIONS = {
    "perception_loop": "1.3.0",
    "motion_summary": "1.2.0",
    "cod_classifier": "2.0.0",
    "evaluator": "2.0.0",
    # ... all agents
}

PIPELINE_VERSION = "2.0.0-cod-region-redesign"

# Prompt hashes computed at module load
PROMPT_HASHES = {
    "cod_classifier": hashlib.sha256(
        create_cod_classifier_agent.__doc__.encode()
    ).hexdigest()[:16],
    # ... other agents (if prompt stored in constant)
}

async def run_odd_workflow(
    scenario_path: str,
    genai_client: Client,
    api_key: str,
    nl_odd_description: Optional[str] = None,
    model_cod: str = "gemini-2.0-flash-lite",
    # ... other params
) -> Dict[str, Any]:
    start_time = time.time()
    
    # Run workflow normally (no agent changes)
    odd_workflow = create_odd_workflow(
        scenario_path, genai_client, api_key,
        model_cod=model_cod, ...
    )
    runner = InMemoryRunner(agent=odd_workflow, app_name="ODD")
    events = await runner.run_debug(user_query)
    result = extract_final_report(events)
    
    # Inject metadata at END
    result["pipeline_metadata"] = {
        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
        "pipeline_version": PIPELINE_VERSION,
        
        "agent_versions": {
            "cod_classifier": {
                "version": AGENT_VERSIONS["cod_classifier"],
                "model": model_cod,
                "prompt_hash": PROMPT_HASHES["cod_classifier"],
            },
            # ... all agents
        },
        
        "execution_stats": {
            "total_duration_seconds": time.time() - start_time,
        }
    }
    
    return result
```

**Example Output:**
```json
{
  "report": { "executive_summary": "..." },
  "full_analysis": { "cod_classification": {...}, ... },
  
  "pipeline_metadata": {
    "analysis_timestamp": "2025-11-24T15:30:00Z",
    "pipeline_version": "2.0.0-cod-region-redesign",
    "agent_versions": {
      "cod_classifier": {
        "version": "2.0.0",
        "model": "gemini-2.0-flash-lite",
        "prompt_hash": "a3f5e9d2c8b1f7a4"
      },
      "evaluator": { "version": "2.0.0", ... }
    },
    "execution_stats": {
      "total_duration_seconds": 45.3
    }
  }
}
```

#### Pros
- ✅ **Simplest implementation** - ~50 lines of code
- ✅ **100% ADK compatible** - No agent changes required
- ✅ **Guaranteed correctness** - All metadata code-computed
- ✅ **Easy to maintain** - Single source of truth for versions
- ✅ **No performance impact** - Single operation at end of workflow

#### Cons
- ❌ **No per-agent tracking** - Can't tell which agent produced which data
- ❌ **Limited debugging** - No intermediate metadata for troubleshooting
- ❌ **Manual version updates** - Must update constants when agents change
- ❌ **No validation** - Can't verify agent actually used declared version/model

#### ADK Compatibility
✅ **Perfect** - No ADK modifications required

#### Risk Assessment
- **Version drift risk:** MEDIUM - Manual updates may fall out of sync
- **Debugging limitation:** MEDIUM - No per-agent attribution in outputs

**Verdict:** ✅ **Acceptable** for minimal viable solution, but limited

---

### Approach D: Hybrid (Prompt + Validation)

**Description:** Agents self-report metadata in prompts (best-effort), workflow validates and fills gaps.

**Implementation:**

**Step 1: Agent Prompt Self-Reporting (Best-Effort)**
```python
# Add metadata instruction to agent prompts
def create_cod_classifier_agent(api_key: str, model: str) -> Agent:
    return Agent(
        name="CodClassifierAgent",
        model=Gemini(model=model, api_key=api_key),
        output_key="temp:cod_classification",
        instruction="""You are a Current Operating Domain (COD) classifier.

[... existing task instructions ...]

METADATA: Include this in your JSON response:
{
  "agent_metadata": {
    "agent_name": "CodClassifierAgent",
    "version": "2.0.0"
  },
  "cod_classification": { ... }
}
""",
    )
```

**Step 2: Workflow-Level Validation & Injection**
```python
# Version registry (source of truth)
AGENT_VERSIONS = {
    "CodClassifierAgent": "2.0.0",
    "EvaluatorAgent": "2.0.0",
    # ... all agents
}

def validate_and_enrich_metadata(
    agent_output: Dict[str, Any],
    agent_name: str,
    model_used: str,
    prompt_hash: str,
) -> Dict[str, Any]:
    """Validate agent-reported metadata and fill missing fields."""
    
    # Extract agent's self-reported metadata (if any)
    reported_metadata = agent_output.get("agent_metadata", {})
    
    # Build complete metadata
    complete_metadata = {
        "agent_name": agent_name,
        "version": AGENT_VERSIONS.get(agent_name, "unknown"),
        "model": model_used,
        "prompt_hash": prompt_hash,
        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    # Validate if agent reported metadata
    if reported_metadata:
        # Check version match
        if reported_metadata.get("version") != complete_metadata["version"]:
            print(f"⚠️  Version mismatch in {agent_name}: "
                  f"reported {reported_metadata.get('version')} vs "
                  f"expected {complete_metadata['version']}")
    
    # Inject complete metadata
    agent_output["agent_metadata"] = complete_metadata
    return agent_output

async def run_odd_workflow(...) -> Dict[str, Any]:
    start_time = time.time()
    
    # Create workflow
    odd_workflow = create_odd_workflow(...)
    runner = InMemoryRunner(agent=odd_workflow, app_name="ODD")
    events = await runner.run_debug(user_query)
    
    # Extract intermediate outputs from events
    agent_outputs = extract_agent_outputs(events)
    
    # Validate and enrich each agent's metadata
    enriched_outputs = {}
    for agent_name, output in agent_outputs.items():
        enriched_outputs[agent_name] = validate_and_enrich_metadata(
            output,
            agent_name=agent_name,
            model_used=get_model_for_agent(agent_name),
            prompt_hash=compute_prompt_hash(agent_name),
        )
    
    # Build final report with pipeline metadata
    result = build_final_report(enriched_outputs)
    result["pipeline_metadata"] = build_pipeline_metadata(
        start_time, enriched_outputs
    )
    
    return result
```

**Utility Functions:**
```python
def extract_agent_outputs(events: list) -> Dict[str, Dict[str, Any]]:
    """Extract structured outputs from each agent in the workflow."""
    outputs = {}
    for event in events:
        if event.author and event.content:
            try:
                output = extract_json_block(event.content.parts[0].text)
                outputs[event.author] = output
            except Exception:
                continue
    return outputs

def compute_prompt_hash(agent_name: str) -> str:
    """Compute hash of agent's prompt template."""
    # Store prompt templates in registry or extract from agent factory
    prompt = PROMPT_REGISTRY.get(agent_name, "")
    return hashlib.sha256(prompt.encode()).hexdigest()[:16]

def build_pipeline_metadata(
    start_time: float,
    agent_outputs: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """Build comprehensive pipeline metadata."""
    return {
        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
        "pipeline_version": PIPELINE_VERSION,
        "agent_executions": {
            agent_name: output.get("agent_metadata", {})
            for agent_name, output in agent_outputs.items()
        },
        "execution_stats": {
            "total_duration_seconds": time.time() - start_time,
        }
    }
```

#### Pros
- ✅ **Best of both worlds** - Self-documentation + guaranteed accuracy
- ✅ **ADK compatible** - No framework modifications
- ✅ **Robust fallback** - Workflow fills missing/incorrect metadata
- ✅ **Self-documenting** - Metadata visible in agent outputs during debugging
- ✅ **Validation** - Detects version mismatches between prompt and registry
- ✅ **Gradual adoption** - Can add prompt metadata incrementally
- ✅ **Low complexity** - ~150 lines total (validation + utilities)

#### Cons
- ⚠️ **Modest complexity** - More code than Approach C, but manageable
- ⚠️ **Manual registry maintenance** - Must update AGENT_VERSIONS when changing agents
- ⚠️ **Event parsing dependency** - Relies on extracting agent outputs from ADK events

#### ADK Compatibility
✅ **Excellent** - Uses ADK's event stream for intermediate outputs, no monkey-patching

#### Risk Assessment
- **Hallucination risk:** LOW - Workflow overrides with correct values
- **Version drift risk:** LOW - Validation detects mismatches
- **Maintenance risk:** LOW - Simple validation logic

**Verdict:** ✅ **RECOMMENDED** - Best balance of simplicity, robustness, and ADK compatibility

---

## 2. ADK Compatibility Research

### ADK Features Investigated

#### 2.1 Built-in Metadata/Telemetry
**Finding:** ❌ **No built-in metadata tracking**

ADK agents do not automatically track:
- Agent versions
- Prompt hashes
- Model configurations
- Execution statistics

**Evidence:**
```python
from google.adk.agents import Agent

agent = Agent(name="MyAgent", model=..., instruction="...")
# No .metadata attribute
# No .version property
# No automatic telemetry
```

#### 2.2 SequentialAgent Metadata Handling
**Finding:** ❌ **No per-agent metadata in SequentialAgent chains**

`SequentialAgent` orchestrates sub-agents but doesn't track:
- Which agent produced which output
- Agent execution order (except via output_key dependencies)
- Per-agent timing or token usage

**Evidence:**
```python
workflow = SequentialAgent(
    name="OddWorkflow",
    sub_agents=[agent1, agent2, agent3]
)
# No workflow.get_agent_metadata()
# No per-agent execution hooks
```

#### 2.3 Lifecycle Hooks
**Finding:** ❌ **No execution lifecycle hooks**

ADK `Agent` class does not expose:
- `before_execute()` hook
- `after_execute()` hook
- Middleware pattern

**Workaround:** Use event stream from `InMemoryRunner.run_debug()` to extract intermediate outputs:
```python
runner = InMemoryRunner(agent=workflow, app_name="ODD")
events = await runner.run_debug(user_query)

# Events contain:
# - event.author: Agent name
# - event.content: Agent output
# - event.timestamp: (not exposed, would need custom tracking)
```

#### 2.4 Idiomatic ADK Pattern
**Finding:** ✅ **Event stream extraction is idiomatic**

The recommended ADK pattern for accessing intermediate outputs:
```python
async def extract_agent_data(workflow, user_query):
    runner = InMemoryRunner(agent=workflow, app_name="MyApp")
    events = await runner.run_debug(user_query)
    
    agent_outputs = {}
    for event in events:
        if event.author and event.content:
            agent_outputs[event.author] = parse_output(event.content)
    
    return agent_outputs
```

This pattern is used throughout ADK examples and is stable across versions.

### ADK Recommendations

✅ **DO:**
- Use event stream for extracting intermediate agent outputs
- Store metadata in agent outputs (via prompt instructions or post-processing)
- Track execution timing at workflow level
- Use output_key for data flow between agents

❌ **DON'T:**
- Subclass Agent to add metadata hooks (fragile, breaks on updates)
- Monkey-patch ADK internals (dangerous, unmaintainable)
- Create custom runners (loses ADK features)

---

## 3. Proof of Concept (Recommended Approach D)

### Implementation Code

**File: `odd_agents/metadata.py`** (New file)
```python
"""
Pipeline metadata tracking utilities.
Implements Hybrid Approach: agent self-reporting + workflow validation.
"""

import hashlib
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# =============================================================================
# VERSION REGISTRY (Source of Truth)
# =============================================================================

PIPELINE_VERSION = "2.0.0-metadata-tracking"

AGENT_VERSIONS = {
    "OddSpecAgent": "1.0.0",
    "PerceptionLoopAgent": "1.3.0",
    "PerceptionSummaryAgent": "1.3.0",
    "MotionLoopAgent": "1.2.0",
    "MotionSummaryAgent": "1.2.0",
    "CollisionLoopAgent": "1.1.0",
    "CollisionSummaryAgent": "1.1.0",
    "CodClassifierAgent": "2.0.0",  # Updated in redesign
    "OddComplianceAgent": "1.0.0",
    "ReportAgent": "1.0.0",
}

# Prompt templates for hash computation (store in constants for reproducibility)
PROMPT_REGISTRY = {
    "CodClassifierAgent": """You are a Current Operating Domain (COD) classifier.

TASK: Classify the robot's CURRENT operating domain from sensor analysis.

METADATA: Include this in your JSON response:
{
  "agent_metadata": {"agent_name": "CodClassifierAgent", "version": "2.0.0"},
  "cod_classification": { ... }
}
""",
    # ... other agents (can be extracted from agent factory functions)
}


# =============================================================================
# METADATA UTILITIES
# =============================================================================

def compute_prompt_hash(prompt_template: str) -> str:
    """Compute deterministic hash of prompt template."""
    return hashlib.sha256(prompt_template.encode()).hexdigest()[:16]


def validate_agent_metadata(
    agent_output: Dict[str, Any],
    expected_agent_name: str,
    model_used: str,
    prompt_template: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Validate and enrich agent-reported metadata.
    
    Args:
        agent_output: Raw agent output (may contain agent_metadata)
        expected_agent_name: Expected agent name from workflow
        model_used: Model name used for this agent
        prompt_template: Prompt template string (for hash computation)
    
    Returns:
        Agent output with validated/enriched metadata
    """
    # Extract self-reported metadata (if present)
    reported_metadata = agent_output.get("agent_metadata", {})
    
    # Build canonical metadata
    canonical_metadata = {
        "agent_name": expected_agent_name,
        "version": AGENT_VERSIONS.get(expected_agent_name, "unknown"),
        "model": model_used,
        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    # Add prompt hash if template provided
    if prompt_template:
        canonical_metadata["prompt_hash"] = compute_prompt_hash(prompt_template)
    
    # Validate if agent self-reported
    if reported_metadata:
        # Check version consistency
        reported_version = reported_metadata.get("version")
        if reported_version and reported_version != canonical_metadata["version"]:
            print(f"⚠️  Version mismatch in {expected_agent_name}: "
                  f"reported '{reported_version}' vs expected '{canonical_metadata['version']}'")
        
        # Check agent name consistency
        reported_name = reported_metadata.get("agent_name")
        if reported_name and reported_name != expected_agent_name:
            print(f"⚠️  Agent name mismatch: "
                  f"reported '{reported_name}' vs expected '{expected_agent_name}'")
    
    # Inject canonical metadata (overrides any self-reported values)
    agent_output["agent_metadata"] = canonical_metadata
    
    return agent_output


def extract_agent_outputs(events: list) -> Dict[str, Dict[str, Any]]:
    """
    Extract structured outputs from each agent in the event stream.
    
    Args:
        events: List of events from InMemoryRunner.run_debug()
    
    Returns:
        Dictionary mapping agent names to their parsed outputs
    """
    from odd_agents.utils import extract_json_block
    
    outputs = {}
    for event in events:
        if event.author and event.content:
            for part in event.content.parts:
                if part.text:
                    try:
                        output = extract_json_block(part.text)
                        outputs[event.author] = output
                        break  # Take first valid JSON from this agent
                    except Exception:
                        continue
    
    return outputs


def build_pipeline_metadata(
    start_time: float,
    agent_outputs: Dict[str, Dict[str, Any]],
    scenario_info: Dict[str, Any],
    odd_spec_hash: str,
) -> Dict[str, Any]:
    """
    Build comprehensive pipeline metadata.
    
    Args:
        start_time: Workflow start timestamp (from time.time())
        agent_outputs: Validated agent outputs with metadata
        scenario_info: Scenario identification info
        odd_spec_hash: Hash of ODD specification used
    
    Returns:
        Complete pipeline metadata dictionary
    """
    return {
        "pipeline_version": PIPELINE_VERSION,
        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
        
        "odd_specification": {
            "hash": odd_spec_hash,
            "version": "embedded",  # Or version tag if versioned externally
        },
        
        "agent_executions": {
            agent_name: output.get("agent_metadata", {})
            for agent_name, output in agent_outputs.items()
        },
        
        "execution_stats": {
            "total_duration_seconds": round(time.time() - start_time, 2),
            "total_agents": len(agent_outputs),
            # Token counts require ADK instrumentation (future enhancement)
        },
        
        "scenario_info": scenario_info,
    }
```

**File: `odd_agents/workflow.py`** (Modifications)
```python
# Add imports at top
import time
from .metadata import (
    validate_agent_metadata,
    extract_agent_outputs,
    build_pipeline_metadata,
    compute_prompt_hash,
    PROMPT_REGISTRY,
)

# Modify run_odd_workflow function
async def run_odd_workflow(
    scenario_path: str,
    genai_client: Client,
    api_key: str,
    nl_odd_description: Optional[str] = None,
    model_perception: str = "gemini-2.0-flash-lite",
    model_motion: str = "gemini-2.0-flash-lite",
    model_collision: str = "gemini-2.0-flash-lite",
    model_odd_spec: str = "gemini-2.0-flash-lite",
    model_cod: str = "gemini-2.0-flash-lite",
    model_report: str = "gemini-2.0-flash-lite",
) -> Optional[Dict[str, Any]]:
    """Run the complete ODD analysis workflow with metadata tracking."""
    
    start_time = time.time()  # Start timing
    
    scenario_path_obj = Path(scenario_path)
    scenario_name = scenario_path_obj.name

    if not scenario_path_obj.exists():
        print(f"❌ Scenario not found: {scenario_path}")
        return None

    # Default ODD description
    if nl_odd_description is None:
        nl_odd_description = (
            "A quadruped robot designed for indoor office environments..."
        )

    # Compute ODD spec hash
    odd_spec_hash = compute_prompt_hash(nl_odd_description)

    print("\n" + "=" * 80)
    print(f"ODD WORKFLOW - FULL PIPELINE")
    print(f"Scenario: {scenario_name}")
    print(f"ODD Hash: {odd_spec_hash}")
    print("=" * 80)

    user_query = (
        f"Analyze scenario '{scenario_name}' against this ODD specification:\n\n"
        f"{nl_odd_description}"
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
        model_cod=model_cod,
        model_report=model_report,
    )

    # Run workflow
    runner = InMemoryRunner(agent=odd_workflow, app_name="ODD")
    print("⏳ Running workflow...")
    
    events = await runner.run_debug(user_query)

    # Extract agent outputs from event stream
    agent_outputs = extract_agent_outputs(events)
    
    # Validate and enrich metadata for each agent
    model_mapping = {
        "PerceptionLoopAgent": model_perception,
        "PerceptionSummaryAgent": model_perception,
        "MotionLoopAgent": model_motion,
        "MotionSummaryAgent": model_motion,
        "CollisionLoopAgent": model_collision,
        "CollisionSummaryAgent": model_collision,
        "OddSpecAgent": model_odd_spec,
        "CodClassifierAgent": model_cod,
        "OddComplianceAgent": model_cod,
        "ReportAgent": model_report,
    }
    
    enriched_outputs = {}
    for agent_name, output in agent_outputs.items():
        enriched_outputs[agent_name] = validate_agent_metadata(
            output,
            expected_agent_name=agent_name,
            model_used=model_mapping.get(agent_name, "unknown"),
            prompt_template=PROMPT_REGISTRY.get(agent_name),
        )

    # Extract final report
    final_report = extract_final_report(events)
    
    if not final_report:
        print("❌ Failed to extract final report")
        return None

    # Build scenario info
    scenario_info = {
        "scenario_id": scenario_name,
        "scenario_path": str(scenario_path),
    }

    # Inject pipeline metadata
    final_report["pipeline_metadata"] = build_pipeline_metadata(
        start_time=start_time,
        agent_outputs=enriched_outputs,
        scenario_info=scenario_info,
        odd_spec_hash=odd_spec_hash,
    )

    print(f"✅ Workflow complete in {time.time() - start_time:.1f}s")
    
    return final_report
```

### Example Output Structure

```json
{
  "report": {
    "executive_summary": "Scenario analyzed successfully...",
    "scenario_metadata": {
      "total_windows_analyzed": 10,
      "scenario_name": "real_01_173442"
    }
  },
  
  "full_analysis": {
    "perception": { "agent_metadata": {...}, "windows_analyzed": [...] },
    "motion": { "agent_metadata": {...}, "per_window_motion": [...] },
    "cod_classification": { "agent_metadata": {...}, "cod_classification": {...} },
    "odd_compliance": { "agent_metadata": {...}, "odd_compliance": {...} }
  },
  
  "pipeline_metadata": {
    "pipeline_version": "2.0.0-metadata-tracking",
    "analysis_timestamp": "2025-11-24T15:45:32Z",
    
    "odd_specification": {
      "hash": "a3f5e9d2c8b1f7a4",
      "version": "embedded"
    },
    
    "agent_executions": {
      "PerceptionLoopAgent": {
        "agent_name": "PerceptionLoopAgent",
        "version": "1.3.0",
        "model": "gemini-2.5-pro",
        "prompt_hash": "b7c2d4e1f8a3c9d2",
        "analysis_timestamp": "2025-11-24T15:45:15Z"
      },
      "CodClassifierAgent": {
        "agent_name": "CodClassifierAgent",
        "version": "2.0.0",
        "model": "gemini-2.0-flash-lite",
        "prompt_hash": "d1f7c8a3e4b9f2a1",
        "analysis_timestamp": "2025-11-24T15:45:28Z"
      },
      "OddComplianceAgent": {
        "agent_name": "OddComplianceAgent",
        "version": "1.0.0",
        "model": "gemini-2.0-flash-lite",
        "prompt_hash": "c9e2b4f7a8d3c1f6",
        "analysis_timestamp": "2025-11-24T15:45:30Z"
      }
    },
    
    "execution_stats": {
      "total_duration_seconds": 45.32,
      "total_agents": 10
    },
    
    "scenario_info": {
      "scenario_id": "real_01_173442",
      "scenario_path": "data/processed/runs/real_01_173442"
    }
  }
}
```

### Migration Path

**Phase 1: Infrastructure Setup** (1 day)
1. Create `odd_agents/metadata.py` with utilities
2. Modify `odd_agents/workflow.py` to inject metadata
3. Test on single scenario, verify metadata appears in output

**Phase 2: Agent Prompt Updates** (Incremental, 2-3 days)
1. Add metadata self-reporting to critical agents first (COD, Evaluator)
2. Update `PROMPT_REGISTRY` with templates
3. Verify validation detects mismatches
4. Gradually add to remaining agents

**Phase 3: Report Integration** (1 day)
1. Update `ReportAgent` to preserve `pipeline_metadata`
2. Add metadata footer to HTML reports
3. Test end-to-end workflow

**Total Estimated Time:** 4-6 days

---

## 4. Recommendation

### Selected Approach: **D - Hybrid (Prompt + Validation)**

#### Justification

**Best Balance of:**
1. ✅ **Simplicity** - ~150 lines of code, no complex wrappers
2. ✅ **Robustness** - Workflow validation ensures correctness
3. ✅ **ADK Compatibility** - Zero breaking changes, uses event stream idiomatically
4. ✅ **Debuggability** - Metadata visible in intermediate outputs
5. ✅ **Gradual Adoption** - Can add prompt metadata incrementally

**Why Not Others:**
- **Approach A (Prompt-Only):** Too unreliable, no enforcement
- **Approach B (Infrastructure/Wrapper):** ADK doesn't support execution hooks, would require fragile monkey-patching
- **Approach C (Workflow-Only):** Works but lacks per-agent attribution and debugging visibility

### Implementation Complexity

**Code Volume:**
- New file: `odd_agents/metadata.py` (~150 lines)
- Modifications: `odd_agents/workflow.py` (~30 lines added)
- Agent prompt updates: ~5 lines per agent × 10 agents = ~50 lines

**Total:** ~230 lines of code

**Complexity Rating:** LOW
- No decorators, no monkey-patching, no subclassing
- Straightforward validation logic
- Uses existing ADK patterns (event stream extraction)

### Risks and Mitigation

| Risk | Severity | Mitigation |
|------|----------|------------|
| Agent hallucinations in self-reported metadata | LOW | Workflow overrides with canonical values from registry |
| Version registry falls out of sync | MEDIUM | Add validation in CI/CD, fail if mismatch detected |
| Event parsing breaks on ADK update | LOW | Event structure stable since ADK 1.0, add tests |
| Prompt templates not in registry | LOW | Validation still works, just no prompt_hash computed |

### Success Metrics

**Must Have:**
- ✅ Every analysis output contains `pipeline_metadata`
- ✅ `agent_executions` includes all 10 agents with version, model, hash
- ✅ Validation detects and logs version mismatches
- ✅ Metadata persists through HTML report generation

**Nice to Have:**
- ✅ Per-agent timing (requires ADK event timestamps - future enhancement)
- ✅ Token usage tracking (requires ADK instrumentation - future enhancement)
- ✅ Automated version bump on agent changes (CI/CD hook - future enhancement)

### Future Enhancements

**Phase 2 (After Initial Implementation):**
1. **Token Usage Tracking** - Instrument ADK to capture per-agent token counts
2. **Per-Agent Timing** - Extract timestamps from ADK events
3. **Automated Version Management** - Git pre-commit hook to validate version bumps
4. **Metadata Visualization** - Dashboard showing metadata trends over time

---

## Appendix: ADK Documentation References

### Relevant ADK Docs
- [ADK Agents](https://google.github.io/adk-docs/agents/) - Agent creation patterns
- [ADK Evaluation](https://google.github.io/adk-docs/evaluate/) - Evaluation framework
- [SequentialAgent](https://google.github.io/adk-docs/agents/#sequential-agent) - Workflow orchestration
- [InMemoryRunner](https://google.github.io/adk-docs/runners/) - Event stream extraction

### Key ADK Findings
1. **No built-in metadata tracking** - Must implement custom solution
2. **No execution hooks** - Event stream is only access point for intermediate data
3. **Event stream is stable** - Recommended pattern for extracting agent outputs
4. **SequentialAgent is composable** - No restrictions on sub-agent design

---

## Conclusion

The **Hybrid Approach (D)** provides the optimal solution for pipeline metadata tracking:
- Respects ADK's architecture (no monkey-patching or workarounds)
- Provides robustness through validation fallback
- Enables debugging with visible metadata in agent outputs
- Remains simple and maintainable (~150 lines of code)
- Supports incremental adoption

**Next Steps:**
1. Review and approve this design
2. Implement `odd_agents/metadata.py`
3. Update `odd_agents/workflow.py` with metadata injection
4. Incrementally add metadata self-reporting to agent prompts
5. Update HTML reports to display metadata
6. Add CI/CD validation for version consistency
