# Pipeline Metadata/Telemetry Tracking System Design

**Date:** November 24, 2025  
**Status:** Design Document  
**Context:** Architecture redesign pipeline metadata requirements (ARCHITECTURE_REDESIGN.md § Pipeline Metadata & Telemetry)

## Executive Summary

This document evaluates **five approaches** for tracking pipeline metadata (agent versions, prompt hashes, ODD specs, execution stats) to enable reproducibility, debugging, and A/B testing. After analyzing ADK compatibility, implementation complexity, and robustness tradeoffs, **we recommend a two-tier strategy:**

1. **PRIMARY: Approach E (Callback-Based)** - If ADK callbacks are verified as available
2. **FALLBACK: Approach D (Hybrid)** - If callbacks are unavailable or unstable

**Approach E (Callback-Based) - Preferred if Available:**
- ✅ **Official ADK API:** Uses documented callback system
- ✅ **Simplest:** ~100 lines of code
- ✅ **Automatic:** Tracks metadata, timing, and tokens without prompt changes
- ✅ **Clean Separation:** Metadata logic completely separate from agents
- ⚠️ **Requires Verification:** Must confirm callbacks work in current ADK version

**Approach D (Hybrid) - Proven Fallback:**
- ✅ **ADK Compatible:** No breaking changes to agent framework
- ✅ **Proven:** Works with existing ADK SequentialAgent chains
- ✅ **Self-Documenting:** Metadata visible in agent outputs
- ✅ **Robust Fallback:** Workflow validates and supplements missing metadata
- ✅ **Moderate Complexity:** ~230 lines of code, no fragile wrappers

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

### Approach E: Callback-Based (ADK Callbacks)

**Description:** Use ADK's built-in callback system to automatically track metadata during agent execution.

**Background:** ADK provides a callback API (https://google.github.io/adk-docs/callbacks/) that allows hooking into the agent execution lifecycle. This could provide an official, non-invasive way to track metadata.

**Implementation:**
```python
from google.adk.callbacks import BaseCallback
import time
from datetime import datetime, timezone

class OddMetadataCallback(BaseCallback):
    """Callback to automatically track agent metadata and execution stats."""
    
    def __init__(self, agent_versions: dict, prompt_hashes: dict):
        self.agent_versions = agent_versions
        self.prompt_hashes = prompt_hashes
        self.agent_metadata = {}
        self.execution_stats = {}
        self._start_times = {}
        self._pipeline_start = datetime.now(timezone.utc)
    
    def on_agent_start(self, agent_name: str, inputs: dict, **kwargs):
        """Track when agent starts execution."""
        self._start_times[agent_name] = time.time()
        self.execution_stats.setdefault(agent_name, {})
        self.execution_stats[agent_name]['start_time'] = datetime.now(timezone.utc).isoformat()
    
    def on_agent_end(self, agent_name: str, outputs: dict, **kwargs):
        """Track when agent completes and build metadata."""
        # Calculate duration
        if agent_name in self._start_times:
            duration = time.time() - self._start_times[agent_name]
            self.execution_stats.setdefault(agent_name, {})
            self.execution_stats[agent_name]['duration_seconds'] = round(duration, 2)
        
        # Build metadata from registry
        self.agent_metadata[agent_name] = {
            'agent_name': agent_name,
            'version': self.agent_versions.get(agent_name, 'unknown'),
            'prompt_hash': self.prompt_hashes.get(agent_name, ''),
            'model': kwargs.get('model', 'unknown'),
            'analysis_timestamp': datetime.now(timezone.utc).isoformat(),
        }
    
    def on_llm_end(self, agent_name: str, response: dict, **kwargs):
        """Track LLM token usage."""
        # Initialize stats dict if not present (handles out-of-order callbacks)
        self.execution_stats.setdefault(agent_name, {})
        
        # Extract token counts from LLM response
        usage = response.get('usage', {})
        self.execution_stats[agent_name]['tokens'] = {
            'prompt_tokens': usage.get('prompt_tokens', 0),
            'completion_tokens': usage.get('completion_tokens', 0),
            'total_tokens': usage.get('total_tokens', 0),
        }
    
    def get_pipeline_metadata(self, pipeline_version: str, odd_spec_hash: str, scenario_info: dict) -> dict:
        """Build complete pipeline metadata."""
        return {
            'pipeline_version': pipeline_version,
            'analysis_timestamp': self._pipeline_start.isoformat(),  # Use consistent timestamp
            'odd_specification': {
                'hash': odd_spec_hash,
                'version': 'embedded',
            },
            'agent_executions': self.agent_metadata,
            'execution_stats': self.execution_stats,
            'scenario_info': scenario_info,
        }

# Usage in workflow
async def run_odd_workflow(...):
    # Create metadata callback
    callback = OddMetadataCallback(
        agent_versions=AGENT_VERSIONS,
        prompt_hashes=PROMPT_HASHES,
    )
    
    # Create workflow
    odd_workflow = create_odd_workflow(...)
    
    # Run with callback registered
    runner = InMemoryRunner(
        agent=odd_workflow,
        app_name="ODD",
        callbacks=[callback]  # Register callback
    )
    events = await runner.run_debug(user_query)
    
    # Extract final report
    result = extract_final_report(events)
    
    # Inject metadata from callback
    result['pipeline_metadata'] = callback.get_pipeline_metadata(
        pipeline_version=PIPELINE_VERSION,
        odd_spec_hash=odd_spec_hash,
        scenario_info={'scenario_id': scenario_name, ...}
    )
    
    return result
```

**Example Output:**
```json
{
  "report": { "executive_summary": "..." },
  
  "pipeline_metadata": {
    "pipeline_version": "2.0.0-metadata-tracking",
    "analysis_timestamp": "2025-11-24T17:30:00Z",
    "agent_executions": {
      "CodClassifierAgent": {
        "agent_name": "CodClassifierAgent",
        "version": "2.0.0",
        "model": "gemini-2.0-flash-lite",
        "prompt_hash": "d1f7c8a3",
        "analysis_timestamp": "2025-11-24T17:29:45Z"
      }
    },
    "execution_stats": {
      "CodClassifierAgent": {
        "start_time": "2025-11-24T17:29:42Z",
        "duration_seconds": 3.2,
        "tokens": {
          "prompt_tokens": 1250,
          "completion_tokens": 340,
          "total_tokens": 1590
        }
      }
    }
  }
}
```

#### Pros
- ✅ **Official ADK API** - Uses framework-supported callbacks, not workarounds
- ✅ **Non-invasive** - No changes to agent prompts or logic
- ✅ **Automatic tracking** - Metadata collected without manual extraction
- ✅ **Centralized** - All tracking logic in callback class
- ✅ **Comprehensive** - Access to lifecycle events (start, end, error)
- ✅ **Token usage** - Built-in access to LLM usage statistics
- ✅ **Per-agent timing** - Automatic duration tracking
- ✅ **Clean separation** - Metadata tracking separate from business logic
- ✅ **No validation needed** - Registry is source of truth, no hallucinations

#### Cons
- ⚠️ **API availability** - Need to verify callbacks are fully implemented in ADK
- ⚠️ **API stability** - Callback interface might change between ADK versions
- ⚠️ **Less self-documenting** - Metadata not visible in agent outputs during debugging
- ⚠️ **Documentation** - Callback API may be less documented than core features
- ❌ **Requires verification** - Need to test if callbacks work with current ADK version

#### ADK Compatibility
⚠️ **NEEDS VERIFICATION** - Callbacks are documented but need to confirm:
- Are callbacks fully implemented in the ADK version used?
- Does `InMemoryRunner` support the `callbacks` parameter?
- Are all lifecycle hooks (`on_agent_start`, `on_agent_end`, `on_llm_end`) available?
- Is the callback API stable across ADK versions?

#### Risk Assessment
- **API availability risk:** MEDIUM - Need to verify callbacks are implemented
- **API stability risk:** LOW-MEDIUM - ADK APIs generally stable but callbacks might evolve
- **Debugging complexity:** LOW - Straightforward callback logic
- **Maintenance risk:** LOW - If API is stable, minimal maintenance needed

#### Comparison with Other Approaches

**vs Prompt-Only (A):**
- ✅ No hallucination risk
- ✅ Guaranteed accuracy
- ✅ No prompt pollution

**vs Infrastructure/Wrapper (B):**
- ✅ Uses official API instead of monkey-patching
- ✅ More stable and maintainable
- ✅ Supported by ADK team

**vs Workflow-Level Only (C):**
- ✅ Per-agent tracking automatically
- ✅ Built-in timing and token stats
- ✅ No manual event parsing

**vs Hybrid (D):**
- ✅ Simpler - no prompt modifications
- ✅ More reliable - no validation needed
- ✅ Automatic token tracking
- ❌ Less self-documenting (metadata not in outputs)
- ⚠️ Depends on callback API availability

**Verdict:** ⚠️ **CONDITIONALLY RECOMMENDED** - If ADK callbacks are fully available and stable, this becomes the **best approach**. Otherwise, fall back to Hybrid (D).

#### Verification Checklist

Before adopting Approach E, verify:
- [ ] ADK version supports callbacks
- [ ] `BaseCallback` class is available in `google.adk.callbacks`
- [ ] `InMemoryRunner` accepts `callbacks` parameter
- [ ] Lifecycle hooks (`on_agent_start`, `on_agent_end`, `on_llm_end`) are functional
- [ ] Token usage is accessible in `on_llm_end`
- [ ] Callback API is documented and stable

**Recommendation Logic:**
```
IF callbacks_verified AND callbacks_stable:
    USE Approach E (Callback-Based)
ELSE:
    USE Approach D (Hybrid)
```

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

#### 2.5 ADK Callbacks System
**Finding:** ⚠️ **Callbacks documented but availability needs verification**

ADK documentation (https://google.github.io/adk-docs/callbacks/) describes a callback system for tracking agent execution lifecycle. Key features include:

**Documented Capabilities:**
- `BaseCallback` class for implementing custom callbacks
- Lifecycle hooks: `on_agent_start`, `on_agent_end`, `on_agent_error`
- Tool hooks: `on_tool_start`, `on_tool_end`, `on_tool_error`
- LLM hooks: `on_llm_start`, `on_llm_end`, `on_llm_error`
- Runner support: `callbacks` parameter in `InMemoryRunner`

**Potential Use Cases:**
- Automatic metadata tracking without prompt modifications
- Per-agent timing and token usage statistics
- Centralized telemetry collection
- Error tracking and debugging

**Verification Needed:**
```python
# Need to verify this works:
from google.adk.callbacks import BaseCallback

class MetadataCallback(BaseCallback):
    def on_agent_end(self, agent_name: str, outputs: dict, **kwargs):
        # Track metadata automatically
        pass

runner = InMemoryRunner(
    agent=workflow,
    app_name="ODD",
    callbacks=[MetadataCallback()]  # Does this work?
)
```

**Status:** 
- ✅ **Documented:** Callback API is documented in ADK docs
- ⚠️ **Not verified:** Need to test with actual ADK installation
- ⚠️ **Stability unknown:** API maturity and version stability unclear

**Impact on Recommendation:**
- **If callbacks work:** Approach E (Callback-Based) becomes the best option
- **If callbacks don't work:** Stick with Approach D (Hybrid)

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

### Primary Recommendation: **E - Callback-Based (If Available)**

#### Decision Tree

```
1. Can ADK callbacks be verified as working?
   ├─ YES → Use Approach E (Callback-Based)
   │         • Simplest and most robust
   │         • Official ADK API
   │         • Automatic tracking
   │
   └─ NO → Use Approach D (Hybrid)
             • Proven to work
             • Good balance of simplicity and robustness
```

#### Why Approach E (Callback-Based) is Preferred

**If callbacks are available and stable:**

1. ✅ **Official API** - Uses ADK's supported callback system
2. ✅ **Simplest** - ~100 lines of code (vs ~230 for Hybrid)
3. ✅ **Most robust** - No hallucination risk, no validation needed
4. ✅ **Automatic** - Metadata tracked without prompt changes
5. ✅ **Comprehensive** - Built-in token usage and timing
6. ✅ **Clean** - Complete separation of metadata logic from agents

**Advantages over Approach D:**
- 50% less code (~100 vs ~230 lines)
- No prompt modifications needed
- Automatic token usage tracking
- No validation logic required
- Cleaner separation of concerns

**Requirements:**
- ADK version must support callbacks
- `google.adk.callbacks.BaseCallback` must be available
- `InMemoryRunner` must accept `callbacks` parameter
- Lifecycle hooks must be functional

#### Fallback: Approach D (Hybrid)

**If callbacks are not available or unstable:**

Use Approach D (Hybrid - Prompt + Validation) as documented in Section 1.

**Justification:**
1. ✅ **Proven** - Works with current ADK patterns
2. ✅ **No dependencies** - Uses event stream (stable API)
3. ✅ **Self-documenting** - Metadata visible in outputs
4. ✅ **Robust** - Validation ensures correctness
5. ✅ **Gradual adoption** - Can add incrementally

**Why Not Others:**
- **Approach A (Prompt-Only):** Too unreliable, no enforcement
- **Approach B (Infrastructure/Wrapper):** ADK doesn't support execution hooks, requires fragile monkey-patching
- **Approach C (Workflow-Only):** Works but lacks per-agent attribution

### Implementation Complexity Comparison

| Approach | Code Lines | Complexity | Token Tracking | Timing |
|----------|-----------|------------|----------------|--------|
| **E (Callbacks)** | ~100 | VERY LOW | ✅ Built-in | ✅ Built-in |
| **D (Hybrid)** | ~230 | LOW | ⚠️ Manual | ⚠️ Manual |
| C (Workflow-Only) | ~50 | VERY LOW | ❌ | ⚠️ Total only |
| A (Prompt-Only) | ~20 | VERY LOW | ❌ | ❌ |
| B (Infrastructure) | ~300+ | HIGH | ⚠️ Possible | ⚠️ Possible |

### Implementation Plan

#### Phase 1: Verification (1 day)
1. Check ADK version and callback availability
2. Test callback implementation with single agent
3. Verify lifecycle hooks work as expected
4. Verify token usage is accessible

#### Phase 2A: If Callbacks Work (2-3 days)
1. Implement `OddMetadataCallback` class
2. Integrate with workflow runner
3. Test on complete pipeline
4. Add metadata to HTML reports

#### Phase 2B: If Callbacks Don't Work (4-6 days)
1. Implement `odd_agents/metadata.py` utilities
2. Modify `odd_agents/workflow.py` 
3. Add metadata self-reporting to agent prompts
4. Test validation logic
5. Add metadata to HTML reports

### Risks and Mitigation

#### Approach E (Callbacks)

| Risk | Severity | Mitigation |
|------|----------|------------|
| Callbacks not available in ADK version | HIGH | Verify first, fall back to Approach D |
| Callback API unstable/changes | MEDIUM | Pin ADK version, add integration tests |
| Incomplete lifecycle hooks | MEDIUM | Test all hooks, fall back to Approach D if missing |

#### Approach D (Hybrid - Fallback)

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
- ✅ Metadata persists through HTML report generation

**Approach-Specific:**

*For Approach E (Callbacks):*
- ✅ Per-agent timing automatically tracked
- ✅ Token usage automatically tracked
- ✅ No validation mismatches (no hallucinations possible)

*For Approach D (Hybrid):*
- ✅ Validation detects and logs version mismatches
- ⚠️ Per-agent timing (manual implementation)
- ⚠️ Token usage tracking (future enhancement)

### Future Enhancements

**Phase 2 (After Initial Implementation):**

*If using Approach E (Callbacks):*
1. **Enhanced Callbacks** - Add error tracking, retries monitoring
2. **Metadata Visualization** - Dashboard showing metadata trends
3. **Callback Chaining** - Multiple callbacks for different purposes

*If using Approach D (Hybrid):*
1. **Token Usage Tracking** - Instrument ADK to capture per-agent token counts
2. **Per-Agent Timing** - Extract timestamps from ADK events
3. **Automated Version Management** - Git pre-commit hook to validate version bumps
4. **Metadata Visualization** - Dashboard showing metadata trends over time

---

## Appendix: ADK Documentation References

### Relevant ADK Docs
- [ADK Agents](https://google.github.io/adk-docs/agents/) - Agent creation patterns
- [ADK Callbacks](https://google.github.io/adk-docs/callbacks/) - Callback system for lifecycle hooks
- [ADK Evaluation](https://google.github.io/adk-docs/evaluate/) - Evaluation framework
- [SequentialAgent](https://google.github.io/adk-docs/agents/#sequential-agent) - Workflow orchestration
- [InMemoryRunner](https://google.github.io/adk-docs/runners/) - Event stream extraction

### Key ADK Findings
1. **No built-in metadata tracking** - Must implement custom solution
2. **Callbacks documented** - But availability needs verification in current ADK version
3. **Event stream is stable** - Fallback pattern for extracting agent outputs
4. **SequentialAgent is composable** - No restrictions on sub-agent design
5. **Callback API potential** - If available, provides cleanest metadata solution

---

## Conclusion

**Two-Tier Recommendation:**

1. **FIRST CHOICE: Approach E (Callback-Based)** - If ADK callbacks are available
   - Official ADK API (not a workaround)
   - Simplest implementation (~100 lines)
   - Automatic tracking of metadata, timing, and tokens
   - Clean separation of concerns
   - **Requires verification** that callbacks work in current ADK version

2. **FALLBACK: Approach D (Hybrid)** - If callbacks unavailable or unstable
   - Proven to work with current ADK patterns
   - Robust validation fallback
   - Self-documenting metadata in outputs
   - Moderate complexity (~230 lines)
   - No dependency on unverified ADK features

**Next Steps:**
1. **VERIFY** ADK callbacks availability and stability
   - Test `google.adk.callbacks.BaseCallback`
   - Test `InMemoryRunner(callbacks=[...])`
   - Test lifecycle hooks functionality
2. **CHOOSE** implementation approach based on verification results
3. Review and approve this design
4. Implement chosen approach (`odd_agents/metadata.py`)
5. Update `odd_agents/workflow.py` with metadata injection
6. Incrementally add metadata self-reporting to agent prompts (if using Hybrid)
7. Update HTML reports to display metadata
8. Add CI/CD validation for version consistency
