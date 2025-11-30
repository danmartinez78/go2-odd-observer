# Tool VLA Architecture: Observation-Driven Reasoning

**Version:** 1.0.0  
**Date:** 2025-11-30  
**Status:** Research/Implementation Planning

## Problem Statement

Current tool prompts are **over-constrained**, forcing VLA models to select from predefined menus rather than intelligently reasoning about observations:

```
# BAD: Forced menu selection
"lighting_conditions": "bright|moderate|dim|dark",
"proximity_band": "immediate|close|medium|far|none"
```

This approach:
- Treats LLMs as enum selectors, wasting their reasoning capability
- Creates brittleness at category boundaries
- Loses nuance and context
- Results in false precision (e.g., "0.76m proximity" when camera can't measure distance)

## Architectural Solution

### Two-Pronged Approach

#### 1. Rich ODD Specification (ODD Spec Agent)

The ODD spec should be a **knowledge document**, not just a schema:

```json
{
  "actor_proximity": {
    "type": "categorical",
    "allowed": ["medium", "far", "none"],
    "violation": ["immediate", "close"],
    "description": "Safe distance to humans/animals during navigation",
    "measurement_guidance": {
      "method": "camera-based visual estimation",
      "robot_context": "Camera at 35cm height, low angle view",
      "interpretation": {
        "immediate": "Actor fills frame, within arm's reach - only feet/legs visible for humans",
        "close": "Actor in foreground, detailed features - legs to waist for humans",
        "medium": "Actor at mid-distance, full context - most of body visible",
        "far": "Actor in background, small in frame - full person head to toe"
      }
    },
    "rationale": "Robot cannot safely navigate near unpredictable moving actors",
    "safety_criticality": "high"
  }
}
```

#### 2. Hardcoded Robot Knowledge (Tool Prompts)

Tool VLA prompts need baked-in knowledge about the ego robot and sensors:

```
## ROBOT PLATFORM: Unitree Go2
- Footprint: 0.65m × 0.31m
- Camera height: ~35cm (low angle perspective)
- Camera FOV: ~120° horizontal

## SENSOR INTERPRETATION

### Camera Image
- Low angle: humans show legs first, full body only at 6m+
- Cannot measure distance directly - use visual cues
- Good for: actor detection, surface type, lighting, semantic understanding

### BEV Occupancy
- Robot at CENTER, facing UP
- Resolution: 0.05m per pixel
- Self-hit radius: 15px center (robot's own body - ignore)
- Shows: obstacles only (ground filtered out)
- Good for: obstacle density, clear path detection, proximity to static objects

### BEV Height  
- Full terrain including ground
- Shows: elevation variations, steps, ramps
- Good for: terrain assessment, stair detection

### BEV Roughness
- Terrain height variance per pixel
- High values: uneven/rough terrain
- Good for: traversability assessment

## CRITICAL LIMITATIONS
- BEV cannot identify WHAT an obstacle is (human vs furniture vs wall)
- Camera cannot measure exact distance
- Actor proximity must be estimated from visual cues, not BEV metrics
```

### Data Flow

```
┌─────────────────┐
│  ODD Spec Agent │ → Rich spec with guidance + rationale
└────────┬────────┘
         │
         ▼
┌─────────────────┐    ┌──────────────────────────┐
│ Perception Tool │ ←──│ Hardcoded robot knowledge │
│      (VLA)      │    │ + ODD spec (passed in)    │
└────────┬────────┘    └──────────────────────────┘
         │
         ▼
┌─────────────────┐
│  Observations   │ → Natural descriptions + reasoned assessments
│  + Assessments  │   (grounded in images AND ODD)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ COD Semantic LLM│ → Maps observations to ODD axes
│                 │   Handles edge cases, synonyms
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  COD Distance   │ → Compliance verdict
│   Calculation   │
└─────────────────┘
```

### Tool Output Pattern

Instead of forced menus, tools output **observations + assessments**:

```json
{
  "window_id": "010",
  "observations": {
    "lighting": "Room is well-lit with natural light from windows on the right. No shadows obscuring the view.",
    "terrain": "Hardwood floor with an area rug in the center. The rug has a low pile texture.",
    "obstacles": "Couch to the right (~2m), coffee table ahead (~1.5m). Clear path to the left.",
    "actors": "No humans or animals visible in the frame."
  },
  "assessments": {
    "lighting": {
      "level": "bright",
      "confidence": 0.9,
      "reasoning": "Natural light, no dark areas, camera exposure looks normal"
    },
    "terrain": {
      "traversability": 0.85,
      "confidence": 0.8,
      "reasoning": "Hardwood is smooth, area rug is low-pile (allowed per ODD). Minor transition at rug edge."
    },
    "actors": {
      "detected": false,
      "safety_concern": "none",
      "reasoning": "No humans or animals visible. Scene appears static."
    }
  },
  "odd_flags": []
}
```

The model **observes first, then assesses** - with reasoning visible.

## Current vs Target Comparison

| Aspect | Current | Target |
|--------|---------|--------|
| ODD Spec | Minimal schema | Rich guidance + rationale |
| Tool prompts | Forced menus | Hardcoded robot knowledge |
| Tool output | Enum selection | Observations + reasoned assessments |
| Actor proximity | `proximity_m: 0.76` (fake precision) | "Legs visible in lower frame, ~1-2m estimated" |
| Downstream | Deterministic math | Semantic LLM reasoning + math |

## Future Improvement: Knowledge Base Access

### Current Limitation

Tool VLAs cannot access the knowledge base (`docs/agent_knowledge/`). Robot platform details, sensor interpretation guides, and domain expertise are siloed.

### Future Options

#### Option A: Direct Knowledge Base Access
```python
# Tool has access to knowledge retrieval
async def analyze_perception_tool(odd_context, tool_context):
    # Retrieve relevant knowledge
    robot_specs = knowledge_base.get("robot_platform.md")
    sensor_guide = knowledge_base.get("sensor_interpretation.md")
    
    # Include in VLA prompt
    prompt = f"""
    {robot_specs}
    {sensor_guide}
    {odd_context}
    Analyze the following images...
    """
```

#### Option B: Injected Knowledge Snippets
```python
# Parent agent selects and injects relevant knowledge
def create_perception_tools(scenario_path, knowledge_snippets):
    # knowledge_snippets passed from workflow
    # Contains pre-selected relevant sections
    
    ROBOT_KNOWLEDGE = knowledge_snippets.get("perception_context", DEFAULT_CONTEXT)
```

#### Option C: Embedded Constants (Current Approach)
```python
# Hardcode essential knowledge in tool module
ROBOT_KNOWLEDGE = """
## ROBOT PLATFORM: Unitree Go2
Camera height: 35cm, FOV: 120°
...
"""
```

### Recommendation

**Phase 1 (Now):** Option C - Embed critical knowledge directly in tool prompts  
**Phase 2 (Future):** Option B - Workflow injects relevant knowledge snippets  
**Phase 3 (Future):** Option A - Tools have direct knowledge retrieval capability

## Implementation Plan

### Step 1: ODD Definition Update
- Update `odd_agents/odd_definition.py` with richer natural language
- Include measurement guidance, interpretation hints, rationale

### Step 2: ODD Spec Agent Update  
- Modify agent to output verbose specs with `guidance` and `rationale` fields
- Update tool schema to accept richer axis definitions

### Step 3: Perception Tool Prompt Update
- Add hardcoded robot knowledge section
- Change output schema to observations + assessments
- Remove forced enum menus

### Step 4: COD Semantic LLM Enhancement
- Update to handle rich observation text
- Map natural language assessments to ODD axes
- Provide distance scores for non-exact matches

### Step 5: Motion/Collision Tool Updates
- Apply same pattern: observations + assessments
- Hardcode relevant robot knowledge (IMU interpretation, etc.)

## Success Metrics

1. **Reduced false violations**: Actor proximity no longer triggers on furniture distance
2. **Richer explanations**: Reports contain actual reasoning, not just enum values
3. **Better edge case handling**: Semantic LLM handles ambiguous observations
4. **Maintained structure**: COD math still works, artifacts still parseable

## References

- `docs/agent_knowledge/` - Knowledge base documents
- `odd_agents/odd_definition.py` - ODD natural language definition
- `odd_agents/tools/cod_construction.py` - COD semantic LLM implementation
