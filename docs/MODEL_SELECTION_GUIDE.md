# Model Selection Guide for ODD Workflow Agents

## Current Configuration (Nov 22, 2025)

All agents default to `gemini-2.0-flash-lite` for cost-effective operation. The parameterized workflow allows per-agent model customization.

### Default Configuration

The workflow uses `gemini-2.0-flash-lite` for all agents by default:

```python
from google.genai import Client
from odd_agents import run_odd_workflow

client = Client(api_key=api_key)

result = await run_odd_workflow(
    scenario_path="data/processed/runs/sim_run_test",
    genai_client=client,
    api_key=api_key,
    # All agents default to gemini-2.0-flash-lite
)
```

### Per-Agent Model Override

For cost optimization or quality requirements, override specific agents:

```python
result = await run_odd_workflow(
    scenario_path="data/processed/runs/sim_run_test",
    genai_client=client,
    api_key=api_key,
    model_perception="gemini-2.5-pro",      # Vision-heavy analysis
    model_motion="gemini-2.5-pro",          # Data structure preservation
    model_collision="gemini-2.5-pro",       # Multimodal fusion
    model_odd_spec="gemini-2.0-flash-lite", # JSON synthesis (default)
    model_cod="gemini-2.0-flash-lite",      # Simple comparison (default)
    model_report="gemini-2.5-pro"           # High-quality reports
)
```

### Agent-Specific Recommendations

| Agent | Default Model | Recommended Upgrade | When to Upgrade |
|-------|--------------|---------------------|-----------------|
| **Perception** | flash-lite | `gemini-2.5-pro` | Need highly accurate vision analysis, detailed environment classification |
| **Motion** | flash-lite | `gemini-2.5-pro` | Complex motion patterns, need perfect data structure preservation |
| **Collision** | flash-lite | `gemini-2.5-pro` | High-stakes scenarios requiring sophisticated multimodal fusion |
| **ODD Spec** | flash-lite | *(keep default)* | JSON synthesis works well with flash-lite |
| **COD Classifier** | flash-lite | *(keep default)* | Simple comparison logic doesn't require advanced model |
| **Compliance** | flash-lite | `gemini-2.5-pro` | Need detailed compliance reasoning and violation analysis |
| **Report** | flash-lite | `gemini-2.5-pro` | Professional reports for stakeholders, comprehensive summaries |

### Cost/Performance Strategy

**Start with defaults (all flash-lite):**
- Fast execution (~2-3 minutes for 2 windows)
- Low cost (~$0.01 per analysis)
- Suitable for development and testing

**Upgrade selectively for production:**
- Perception, Motion, Collision → `gemini-2.5-pro` for critical analysis
- Keep ODD Spec and COD Classifier on flash-lite
- Upgrade Report for stakeholder deliverables

**Estimated Cost Impact:**
- All flash-lite: **baseline cost** (cheapest)
- Selective upgrade (3-4 agents to 2.5-pro): **~3-5x increase**
- All 2.5-pro: **~6-8x increase**

### Model Capabilities

**gemini-2.0-flash-lite:**
- ✅ Fast and cost-effective
- ✅ Good for JSON synthesis and simple reasoning
- ⚠️ Less detailed vision analysis
- ⚠️ May simplify complex data structures

**gemini-2.5-pro:**
- ✅ Superior vision understanding
- ✅ Preserves complex nested data structures
- ✅ Sophisticated multimodal fusion
- ✅ Higher quality reports
- ⚠️ ~5-8x more expensive per token
- ⚠️ Slower response time

### Implementation Example

```python
# Demo notebook configuration cell
MODEL_PERCEPTION = "gemini-2.5-pro"      # High-quality vision
MODEL_MOTION = "gemini-2.0-flash-lite"   # Good enough for IMU analysis
MODEL_COLLISION = "gemini-2.5-pro"       # Critical safety analysis
MODEL_ODD_SPEC = "gemini-2.0-flash-lite" # JSON synthesis
MODEL_COD = "gemini-2.0-flash-lite"      # Simple comparison
MODEL_REPORT = "gemini-2.5-pro"          # Professional output

result = await run_odd_workflow(
    scenario_path=SCENARIO_PATH,
    genai_client=genai_client,
    api_key=GOOGLE_API_KEY,
    model_perception=MODEL_PERCEPTION,
    model_motion=MODEL_MOTION,
    model_collision=MODEL_COLLISION,
    model_odd_spec=MODEL_ODD_SPEC,
    model_cod=MODEL_COD,
    model_report=MODEL_REPORT
)
```

### Future Optimization

Consider exploring:
- **gemini-1.5-flash**: Even cheaper alternative for simple agents
- **Caching**: Reuse ODD spec across multiple scenario analyses
- **Batch processing**: Amortize agent orchestration overhead
- **Model routing**: Dynamically select model based on window complexity
