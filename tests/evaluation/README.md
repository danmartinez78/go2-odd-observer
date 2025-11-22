# ADK Agent Evaluation Framework

This directory contains **automated evaluation tests** for ODD analysis agents using Google's Agent Development Kit (ADK) built-in evaluation framework.

---

## 🎯 Overview

We evaluate agent quality using ADK's evaluation criteria:
- ✅ **Tool Trajectory** - Validates correct tool calling sequences
- ✅ **Rubric-Based** - LLM-as-judge quality assessment using custom rubrics
- ✅ **Hallucinations** - Detects when agents fabricate information

**Key Insight**: Loop agent tests evaluate BOTH orchestration AND inference quality because loop agents call tools which make actual LLM inference calls. When you test a loop agent with rubrics, you're testing the multimodal vision/NLP inference, not just JSON validation.

---

## 📂 Directory Structure

```
tests/evaluation/
├── README.md                    # This file
├── TEST_DATA.md                 # Test data documentation (windows 006, 007)
├── test_config_simple.json      # Simple config example
├── perception/                  # Perception agent evaluation
│   ├── README.md                # Perception-specific docs
│   ├── perception_agent.py      # Agent export for ADK
│   ├── perception_agent.test.json  # EvalSet test cases
│   ├── test_config.json         # Main config (tool + rubric)
│   ├── test_config_tool_only.json
│   ├── test_config_rubric_only.json
│   ├── test_config_comprehensive.json
│   └── test_config_response_only.json
├── motion/                      # Motion agent evaluation
│   ├── README.md                # Motion-specific docs
│   ├── motion_agent.py
│   ├── motion_agent.test.json
│   ├── test_config.json
│   ├── test_config_tool_only.json
│   ├── test_config_rubric_only.json
│   └── test_config_comprehensive.json
├── toy_examples/                # Reference implementations
│   ├── README.md
│   ├── simple_agent.py
│   ├── simple_agent.test.json
│   └── test_config_*.json (5 configs)
└── LESSONS_LEARNED.md           # Critical insights from development
```

---

## 🧪 Test Patterns

Each agent has **3 test types** with different speed/coverage tradeoffs:

### 1. Tool Trajectory Only (~20-25s)
**Purpose**: Fast validation of orchestration logic

**Tests**: Tool calling sequence matches expected pattern

**Threshold**: **1.0** (strict - must be exact)

**Use Case**: 
- PR validation (fast feedback)
- Smoke tests
- Tool call regression detection

**Example**:
```python
def test_perception_tool_trajectory_only():
    """Fast test - validates tool calling sequence only (~23s)."""
    result = evaluate_agent(
        agent=perception_loop_agent,
        config_path="test_config_tool_only.json",
        test_json_path="perception_agent.test.json"
    )
    assert result.overall_score >= 1.0  # Must be perfect
```

### 2. Rubric Quality Only (~70-80s)
**Purpose**: Validate inference quality without trajectory overhead

**Tests**: LLM judges output quality using custom rubrics

**Threshold**: **0.7** (industry standard for LLM evaluation)

**Use Case**:
- Inference quality regression
- Model comparison
- Rubric development/tuning

**Runtime Evidence**: 71 seconds proves actual LLM inference calls are happening (not just JSON validation which would take 2-3s)

**Example**:
```python
def test_motion_rubric_quality():
    """Medium test - validates output quality via rubrics (~80s).
    
    Note: This test validates BOTH orchestration AND inference quality!
    The motion loop agent calls analyze_motion_tool which makes actual
    LLM inference calls analyzing IMU sensor data. The rubrics evaluate
    the quality of those LLM-generated analyses.
    """
    result = evaluate_agent(
        agent=motion_loop_agent,
        config_path="test_config_rubric_only.json",
        test_json_path="motion_agent.test.json"
    )
    assert result.overall_score >= 0.7
```

### 3. Comprehensive (~120-200s)
**Purpose**: Full validation (trajectory + rubrics + hallucinations)

**Tests**: All ADK evaluation criteria

**Thresholds**: 
- Tool trajectory: 1.0 (strict)
- Rubrics: 0.7 (standard)
- Hallucinations: 1.0 (no fabrication allowed)

**Use Case**:
- Pre-release validation
- Scheduled nightly tests
- Full agent certification

---

## 🏗️ Architecture: Why Loop Tests = Inference Tests

**Critical Understanding**: Testing loop agents with rubrics validates BOTH orchestration AND inference quality.

### Call Chain
```
1. Test invokes: PerceptionLoopAgent
2. Loop agent calls: list_windows_tool → analyze_window_perception_tool
3. analyze_window_perception_tool makes: genai_client.models.generate_content()
   ├─ Input: Camera image + 4 BEV images (multimodal)
   └─ Output: Environment analysis, obstacles, traversability
4. Tool returns: LLM inference result to loop agent
5. Loop agent aggregates: All window analyses into JSON
6. Rubric evaluator (LLM judge) assesses: Quality of inference outputs
```

**Evidence**: `test_perception_rubric_quality` takes **71 seconds** (not 2-3s for JSON validation)

### Agent Types

**Loop Agents** (Orchestrators):
- `PerceptionLoopAgent` - Iterate windows, call perception tool, aggregate
- `MotionLoopAgent` - Iterate windows, call motion tool, aggregate
- `CollisionLoopAgent` - Iterate windows, call collision tool, aggregate

**Tools** (Inference Engines):
- `analyze_window_perception_tool()` - Multimodal LLM call (vision)
- `analyze_motion_tool()` - LLM call (IMU data analysis)
- `analyze_collision_tool()` - LLM call (risk assessment)

**Summary Agents** (Aggregators):
- `PerceptionSummaryAgent` - Calculate overall perception statistics
- `MotionSummaryAgent` - Calculate motion statistics
- `CollisionSummaryAgent` - Calculate collision statistics

### Why We DON'T Test Tools Separately

We initially created separate tool-level tests but realized they were:
1. **Redundant** - Loop tests already exercise the same tools
2. **Problematic** - Tool wrapping caused ADK evaluator issues (timeouts)
3. **Unnecessary** - Rubrics already evaluate tool output quality
4. **Slower** - Added no value while doubling test time

**Decision**: Test loop agents only. Rubrics validate inference quality.

---

## 📋 EvalSet Schema (test.json)

Test cases use ADK's `EvalSet` Pydantic schema:

```json
{
  "name": "Perception Agent Evaluation",
  "description": "Tests PerceptionLoopAgent on sim_run_test windows",
  "test_cases": [
    {
      "name": "Window 006 perception analysis",
      "user_request": "Analyze perception for windows 006 and 007",
      "expected_tool_uses": [
        {
          "tool_name": "list_windows_tool",
          "match_type": "EXACT"
        },
        {
          "tool_name": "analyze_window_perception_tool",
          "args": {"window_id": "006"}
        },
        {
          "tool_name": "analyze_window_perception_tool",
          "args": {"window_id": "007"}
        }
      ],
      "expected_responses": [
        {
          "criteria": [
            {
              "name": "json_structure",
              "rubric": "Output must be valid JSON with required keys...",
              "grading_context": "Evaluate JSON structure and completeness"
            }
          ]
        }
      ]
    }
  ]
}
```

**Critical**: Always include `"args": {}` in `expected_tool_uses`, even if empty! ADK requires this.

---

## 🎨 Rubric Design

Rubrics are LLM-as-judge evaluation criteria. Each rubric specifies:

- **name**: Unique identifier (e.g., `json_structure`)
- **rubric**: Detailed evaluation instructions for LLM judge
- **grading_context**: Additional context/examples
- **pass_threshold**: Minimum score (typically 7/10)

### Example Rubric (Perception)
```json
{
  "name": "complete_analysis",
  "rubric": "Check if all windows were analyzed:\n- Look for windows_analyzed list\n- Verify per_window_perception has entries for each window\n- Score 10/10 if all windows present, 0/10 if any missing",
  "grading_context": "Window IDs should be 006 and 007",
  "pass_threshold": 7
}
```

### Rubric Best Practices

✅ **DO**:
- Be specific and concrete
- Provide clear pass/fail criteria
- Include examples in grading_context
- Use 0-10 scale explicitly
- Test expectations against actual data (see TEST_DATA.md)

❌ **DON'T**:
- Be vague ("check if good")
- Use subjective criteria
- Set unrealistic thresholds
- Lower thresholds to make tests pass (anti-pattern!)
- Expect odometry data (it's stuck at zero)

---

## 🚀 Adding a New Agent

Follow this checklist to add evaluation for a new agent:

### 1. Create Agent Directory
```bash
mkdir tests/evaluation/{agent_name}/
```

### 2. Create Agent Export (`{agent}_agent.py`)
```python
"""Export {Agent}LoopAgent for ADK evaluation."""
from odd_agents.agents.{agent} import create_{agent}_loop_agent
from pathlib import Path
import os
from google.genai import Client
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ.get("GOOGLE_API_KEY")
GENAI_CLIENT = Client(api_key=API_KEY)
MODEL = "gemini-2.0-flash-lite"
SCENARIO_PATH = str(Path("data/processed/runs/sim_run_test").absolute())

# Export agent instance
{agent}_loop_agent = create_{agent}_loop_agent(
    SCENARIO_PATH, GENAI_CLIENT, MODEL, API_KEY
)
```

### 3. Create Test Cases (`{agent}_agent.test.json`)
See `perception/perception_agent.test.json` as reference. Must include:
- Test case names
- User requests
- Expected tool uses (with `"args": {}`)
- Expected responses with rubrics

### 4. Create Test Configs
Create 4 config files (see `perception/` for examples):
- `test_config.json` - Main (tool + rubric)
- `test_config_tool_only.json` - Fast validation
- `test_config_rubric_only.json` - Quality only
- `test_config_comprehensive.json` - All criteria

### 5. Design Rubrics
Create 3-5 rubrics evaluating:
- JSON structure validity
- Completeness (all windows analyzed)
- Data integrity (tool outputs preserved)
- Domain-specific quality (e.g., risk scores, classifications)

**Reference TEST_DATA.md** for expected data ranges!

### 6. Add Tests to `test_adk_evaluation.py`
```python
def test_{agent}_tool_trajectory_only():
    """Fast test - validates tool calling sequence only (~20s)."""
    result = evaluate_agent(
        agent={agent}_loop_agent,
        config_path="tests/evaluation/{agent}/test_config_tool_only.json",
        test_json_path="tests/evaluation/{agent}/{agent}_agent.test.json"
    )
    assert result.overall_score >= 1.0

def test_{agent}_rubric_quality():
    """Medium test - validates output quality via rubrics (~70-80s).
    
    Note: Tests BOTH orchestration AND inference quality!
    """
    result = evaluate_agent(
        agent={agent}_loop_agent,
        config_path="tests/evaluation/{agent}/test_config_rubric_only.json",
        test_json_path="tests/evaluation/{agent}/{agent}_agent.test.json"
    )
    assert result.overall_score >= 0.7

def test_{agent}_comprehensive():
    """Slow test - validates all criteria (~120-200s)."""
    result = evaluate_agent(
        agent={agent}_loop_agent,
        config_path="tests/evaluation/{agent}/test_config_comprehensive.json",
        test_json_path="tests/evaluation/{agent}/{agent}_agent.test.json"
    )
    assert result.overall_score >= 0.7
```

### 7. Create Agent README
Document agent-specific details (see template in next section)

### 8. Run Tests
```bash
# Fast validation
pytest tests/test_adk_evaluation.py::test_{agent}_tool_trajectory_only -v

# Quality check
pytest tests/test_adk_evaluation.py::test_{agent}_rubric_quality -v

# Full certification
pytest tests/test_adk_evaluation.py::test_{agent}_comprehensive -v
```

---

## 📖 Agent README Template

Each agent subdirectory should have a README.md:

```markdown
# {Agent} Agent Evaluation

## Agent Purpose
{Brief description of what this agent does}

## Test Cases
- **Windows**: 006, 007 from sim_run_test
- **Expected tool calls**: {list tools}
- **Expected outputs**: {describe output structure}

## Rubrics
### {rubric_name}
- **Purpose**: {what it evaluates}
- **Pass criteria**: {specific requirements}
- **Threshold**: {score}/10

## Running Tests
\`\`\`bash
# Fast (~20s)
pytest tests/test_adk_evaluation.py::test_{agent}_tool_trajectory_only -v

# Quality (~70s)
pytest tests/test_adk_evaluation.py::test_{agent}_rubric_quality -v

# Comprehensive (~120s)
pytest tests/test_adk_evaluation.py::test_{agent}_comprehensive -v
\`\`\`

## Expected Results
{Describe what good outputs look like for windows 006/007}
```

---

## 🐛 Troubleshooting

### Tool Trajectory Score 0.0
**Issue**: `tool_trajectory` criterion returning 0.0

**Cause**: Missing `"args": {}` in `expected_tool_uses`

**Fix**: Always include args, even if empty:
```json
{
  "tool_name": "list_windows_tool",
  "args": {},  // Required!
  "match_type": "EXACT"
}
```

### Tests Timing Out
**Issue**: Tests hang for >180s

**Cause**: Possibly testing tools instead of loop agents (wrapping issues)

**Fix**: Test loop agents directly, not wrapped tools

### Low Rubric Scores
**Issue**: Rubrics scoring below 0.7

**Root Cause Analysis**:
1. Is the agent actually producing bad output? (inspect manually)
2. Are rubric expectations realistic? (check against TEST_DATA.md)
3. Are you testing the right output format? (JSON vs prose)

**Anti-Pattern**: Don't lower thresholds to make tests pass!

**Proper Fix**: Either fix the agent OR adjust rubric expectations to match actual good behavior

### Odometry Expectations Failing
**Issue**: Test expects velocity from odometry

**Cause**: Odometry stuck at zero in sim data (known issue)

**Fix**: Use IMU data (gyro + accel) for motion assertions. See TEST_DATA.md.

---

## 📚 Related Documentation

- **Test data specs**: `TEST_DATA.md`
- **Lessons learned**: `LESSONS_LEARNED.md`
- **Toy examples**: `toy_examples/README.md`
- **Agent implementations**: `../../odd_agents/agents/`
- **Tool implementations**: `../../odd_agents/tools/`
- **Manual testing scripts**: `../../tests/test_*_agent.py` (root level)

---

## 📊 Current Coverage

| Agent | Tool Tests | Rubric Tests | Comprehensive | Status |
|-------|------------|--------------|---------------|--------|
| Perception | ✅ (23s) | ✅ (71s) | ⏳ Ready | Complete |
| Motion | ✅ (21s) | ⏳ Ready | ⏳ Ready | Complete |
| Collision | ❌ | ❌ | ❌ | TODO |
| ODD Spec | ❌ | ❌ | ❌ | TODO |
| Compliance | ❌ | ❌ | ❌ | TODO |
| COD Classifier | ❌ | ❌ | ❌ | TODO |
| Report | ❌ | ❌ | ❌ | TODO |

---

## 🎯 Next Steps

1. ✅ Perception evaluation complete
2. ✅ Motion evaluation complete
3. ⏳ Extend to remaining 5 agents:
   - Collision (loop + summary)
   - ODD Spec (single agent)
   - Compliance (single agent)
   - COD Classifier (single agent)
   - Report (single agent)

**Pattern is proven** - fast to replicate! 🚀

---

**Last Updated**: November 22, 2025  
**Maintainer**: Go2 ODD Observer Team
