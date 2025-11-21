# 📚 REFERENCE: Loop + Summary Pattern

> **⚠️ This file is a REFERENCE implementation - DO NOT DELETE**

This file demonstrates the **proven ADK pattern** that eliminated hallucinations in vision workflows. It was used as the foundation for `odd_workflow_full.py` and all agents in `agent_tests/`.

---

## 🎯 Purpose

When we initially tried returning image `Part` objects from ADK tools, Gemini hallucinated descriptions instead of analyzing actual images. This file solved that problem.

---

## ✅ The Proven Pattern

### 1. Tools Call Gemini Directly

```python
async def describe_image_with_agent(image_path: str, tool_context: ToolContext):
    """✅ CORRECT: Tool calls Gemini directly and returns text"""
    image_bytes = Path(image_path).read_bytes()
    
    response = GENAI_CLIENT.models.generate_content(
        model="gemini-2.5-pro",
        contents=[
            types.Part(text=prompt),
            types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
        ]
    )
    
    return response.text  # Return text/JSON, NOT Part objects
```

❌ **WRONG** (causes hallucinations):
```python
def bad_tool():
    return types.Part.from_bytes(image_data, mime_type="image/png")
```

### 2. Loop Agent Processes Items

```python
loop_agent = Agent(
    name="ImageLoopAgent",
    tools=[DESCRIBE_IMAGE],
    output_key="temp:all_descriptions",
    instruction="""
    You will receive image paths. For each:
    1. Call describe_image_with_agent(image_path=...)
    2. Collect all results
    3. Output as JSON array
    """
)
```

### 3. Summary Agent Aggregates

```python
summary_agent = Agent(
    name="StoryAgent",
    instruction="""
    Input: {temp:all_descriptions}
    Task: Synthesize into coherent narrative
    Output: Story using all images
    """
)
```

### 4. Sequential Orchestration

```python
workflow = SequentialAgent(
    sub_agents=[loop_agent, summary_agent]
)
```

---

## 📊 How This Pattern Was Applied

### In `odd_workflow_full.py`:

**Perception Analysis** (Loop + Summary):
- `PerceptionLoopAgent` - Analyze camera + BEV for each window
- `PerceptionSummaryAgent` - Aggregate environment classification

**Motion Analysis** (Loop + Summary):
- `MotionLoopAgent` - Extract metrics from each window
- `MotionSummaryAgent` - Compute overall statistics

**Collision Analysis** (Loop + Summary):
- `CollisionLoopAgent` - Multimodal fusion per window
- `CollisionSummaryAgent` - Risk aggregation

Then: `OddSpecAgent` → `CodAgent` → `ReportAgent` for synthesis

---

## 🔬 Validation Results

**Tested on**:
- ✅ 4-image story generation (this file)
- ✅ 13-window perception analysis (sim_run_new)
- ✅ Multi-modal collision detection

**Results**:
- 0% hallucination rate
- Complete data preservation
- Accurate multimodal fusion

---

## 🎓 Key Learnings

1. **Hallucination Prevention**: Never return `Part` objects from tools
2. **Data Preservation**: Use 2.5-pro for complex aggregation (flash-lite loses arrays)
3. **Clean Separation**: Loop = iteration, Summary = aggregation
4. **Model Selection**: Vision requires 2.5-pro, simple synthesis can use flash-lite

---

## 📖 Related Files

- **Production**: `odd_workflow_full.py` - Full 9-agent pipeline
- **Examples**: `agent_tests/test_*_agent.py` - Individual agent implementations
- **Archive**: `.archive/exploration/REFERENCE_PATTERN.md` - Detailed pattern documentation
- **Documentation**: `docs/MODEL_SELECTION_GUIDE.md` - Model selection rationale

---

## 🚫 DO NOT

- ❌ Delete this file (it's the reference implementation)
- ❌ Modify the core pattern (it's proven to work)
- ❌ Return `Part` objects from tools (causes hallucinations)

## ✅ DO

- ✅ Study this pattern before creating new agents
- ✅ Apply loop+summary for any multi-item processing
- ✅ Call Gemini directly from tools for vision tasks
- ✅ Use output_key for state passing between agents

---

**Last validated**: November 21, 2025  
**Status**: ✅ Production-ready reference implementation
