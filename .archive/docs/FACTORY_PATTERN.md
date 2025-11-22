# Factory Function Pattern for ADK Agents

## Problem

ADK agents enforce a constraint: **an agent can only have one parent agent** (enforced via Pydantic validation). This creates issues when using module-level singleton pattern:

```python
# ❌ PROBLEMATIC: Singleton pattern
# agents/perception.py
perception_loop_agent = Agent(...)  # Created on import

# workflow.py
from agents.perception import perception_loop_agent
workflow = SequentialAgent(sub_agents=[perception_loop_agent])  # Sets parent

# test_perception.py  
from agents.perception import perception_loop_agent
test_workflow = SequentialAgent(sub_agents=[perception_loop_agent])  # ❌ FAILS!
# Error: Agent already has a parent
```

When the workflow imports and uses the singleton agent, it becomes the parent. Tests can't reuse the same instance.

## Solution: Factory Functions

Instead of creating instances at module level, export **functions that create instances**:

```python
# ✅ CORRECT: Factory function pattern
# agents/perception.py
def create_perception_loop_agent() -> Agent:
    """Create a fresh perception loop agent instance."""
    return Agent(...)

# workflow.py
from agents.perception import create_perception_loop_agent
workflow = SequentialAgent(sub_agents=[create_perception_loop_agent()])

# test_perception.py
from agents.perception import create_perception_loop_agent
test_workflow = SequentialAgent(sub_agents=[create_perception_loop_agent()])
# ✅ Works! Each context gets a fresh instance
```

## Implementation Pattern

### 1. Agent Module Structure

Each agent module (`perception.py`, `motion.py`, etc.) follows this pattern:

```python
from google.adk.agents import Agent

def create_my_agent() -> Agent:
    """Create a fresh MyAgent instance."""
    return Agent(
        name="MyAgent",
        instruction="...",
        tools=[...],
    )

# ❌ DO NOT create module-level instances:
# my_agent = create_my_agent()  # This defeats the factory pattern!
```

### 2. Module Exports

Export factory functions in `__init__.py`:

```python
# agents/__init__.py
from .perception import create_perception_loop_agent, create_perception_summary_agent
from .motion import create_motion_loop_agent, create_motion_summary_agent
# ... etc

__all__ = [
    "create_perception_loop_agent",
    "create_perception_summary_agent",
    # ... etc
]
```

### 3. Workflow Usage

Create fresh instances when building workflows:

```python
# workflow.py
from odd_agents.agents import (
    create_perception_loop_agent,
    create_perception_summary_agent,
)

def create_odd_workflow() -> SequentialAgent:
    """Create a fresh ODD workflow instance."""
    return SequentialAgent(
        name="ODDWorkflow",
        sub_agents=[
            create_perception_loop_agent(),  # Fresh instance
            create_perception_summary_agent(),  # Fresh instance
            # ... etc
        ],
    )

# Create instance for main execution
odd_workflow = create_odd_workflow()
```

### 4. Test Usage

Each test creates its own instances:

```python
# tests/test_perception_agent.py
from odd_agents.agents import create_perception_loop_agent, create_perception_summary_agent

async def test_perception_agent():
    # Create fresh instances for this test
    workflow = SequentialAgent(
        name="PerceptionWorkflow",
        sub_agents=[
            create_perception_loop_agent(),
            create_perception_summary_agent(),
        ],
    )
    
    runner = InMemoryRunner(agent=workflow, app_name="TestApp")
    events = await runner.run_debug("Test prompt")
    # ... assertions
```

## Benefits

1. **No Parent Conflicts**: Each context (main workflow, tests) gets fresh instances
2. **Test Isolation**: Tests don't interfere with each other or the main workflow
3. **Flexibility**: Easy to create multiple workflows with different configurations
4. **Clear Dependencies**: Factory functions make agent creation explicit
5. **ADK Compliance**: Respects the "one parent per agent" constraint

## Migration Checklist

When converting from singletons to factory functions:

- [ ] Convert agent instances to factory functions in agent modules
- [ ] Remove module-level instance creation (e.g., `agent = create_agent()`)
- [ ] Update `__init__.py` exports to factory function names
- [ ] Update workflow to call factory functions
- [ ] Update all test files to call factory functions
- [ ] Update extraction/parsing logic to use string names instead of `agent.name`
- [ ] Verify all tests pass without "agent already has parent" errors

## Common Pitfalls

### ❌ Leftover Module-Level Instances

```python
# agents/perception.py
def create_perception_loop_agent() -> Agent:
    return Agent(...)

# ❌ BAD: Creates instance on import
perception_loop_agent = create_perception_loop_agent()
```

This defeats the factory pattern - the module-level instance gets created on import and causes the same parent conflict.

### ❌ Importing Wrong Name

```python
# ❌ BAD: Trying to import the old singleton
from odd_agents.agents import perception_loop_agent  # Doesn't exist!

# ✅ GOOD: Import the factory function
from odd_agents.agents import create_perception_loop_agent
```

### ❌ Forgetting to Call the Factory

```python
# ❌ BAD: Passing the function itself
workflow = SequentialAgent(sub_agents=[create_perception_loop_agent])

# ✅ GOOD: Call the function to get an instance
workflow = SequentialAgent(sub_agents=[create_perception_loop_agent()])
```

## References

- ADK Documentation: [Agent Parent Constraints](https://google.adk.dev/agents)
- Python Pattern: [Factory Method](https://refactoring.guru/design-patterns/factory-method/python/example)
- Project Refactor: See commit "feat: Convert agents to factory functions"
