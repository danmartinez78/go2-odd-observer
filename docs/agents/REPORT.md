# Report Agent

## Overview

The **ReportAgent** is the final agent in the ODD analysis workflow. It synthesizes all previous analysis stages into a comprehensive, human-readable report with executive summary, key findings, and actionable recommendations.

**Purpose**: Transform technical sensor data and compliance metrics into actionable insights for engineers, operators, and decision-makers.

---

## ReportAgent

### Purpose

Generates the final comprehensive report by synthesizing outputs from the 9 preceding agents in the workflow.

**Problem it solves**: Raw sensor analysis and compliance data is not directly actionable. This agent provides:
- Executive summary for stakeholders
- Domain-specific summaries for engineers
- Key findings highlighting critical issues
- Actionable recommendations for improvements
- Complete audit trail of all analysis stages

### Inputs

**From All Previous Agents:**
- `{temp:perception_output?}`: Perception analysis
- `{temp:motion_output?}`: Motion analysis
- `{temp:collision_output?}`: Collision risk analysis
- `{temp:odd_spec?}`: ODD specification
- `{temp:cod_classification?}`: COD classification
- `{temp:odd_compliance?}`: Compliance status

**No tool dependencies** - Pure synthesis of previous outputs.

### Outputs

**No explicit output_key** - This is the terminal agent, producing final workflow result.

**Schema:**
```json
{
  "report": {
    "executive_summary": "2-3 sentence overview",
    "scenario_metadata": {
      "total_windows_analyzed": 13,
      "scenario_name": "sim_run_new",
      "environment_class": "indoor_office",
      "data_source": "simulation",
      "data_source_confidence": 1.0
    },
    "perception_summary": "Brief summary of perception findings",
    "motion_summary": "Brief summary of motion characteristics",
    "collision_summary": "Brief summary of collision risk assessment",
    "odd_spec_summary": "Brief summary of ODD specification",
    "cod_classification_summary": "Brief summary of current operating domain",
    "odd_compliance_summary": "Brief summary of ODD compliance",
    "key_findings": ["finding1", "finding2", "finding3"],
    "recommendations": ["recommendation1", "recommendation2"]
  },
  "full_analysis": {
    "perception": {...},
    "motion": {...},
    "collision": {...},
    "odd_spec": {...},
    "cod_classification": {...},
    "odd_compliance": {...}
  }
}
```

### Prompting Strategy

The agent follows a **structured synthesis process**:

#### 1. Extract Metadata
```
- total_windows_analyzed: From perception.windows_analyzed.length
- scenario_name: From scenario path or inferred
- environment_class: From perception.environment_classification.primary_class
- data_source: From perception.data_source_classification.source
- data_source_confidence: From perception.data_source_classification.confidence
```

#### 2. Generate Executive Summary
**Guidelines:**
- 2-3 sentences maximum
- High-level overview of scenario
- Mention compliance status (IN_ODD, ODD_BOUNDARY, OUT_ODD)
- Highlight most critical finding if OUT_ODD

**Example:**
> "The Unitree Go2 robot is operating in a simulated indoor office environment. While the environment generally aligns with the ODD, a low traversability score and high collision risk, coupled with multiple instances of near-collision scenarios, suggest a need for caution and potential adjustments to the operating strategy."

#### 3. Create Domain Summaries
**For each domain (perception, motion, collision, etc.):**
- 1-2 sentence summary
- Highlight key metrics
- Note any anomalies or concerns

**Examples:**
```
perception_summary: "Robot operated in indoor office environment with bright lighting and smooth terrain. Average obstacle density 0.53 with traversability score 0.38 indicating constrained navigation space."

motion_summary: "Moderate activity level with 85% motion detection rate. Peak acceleration 1.23 m/s² with predominantly smooth motion patterns."

collision_summary: "8 high-risk collision events detected across 13 windows. Average collision likelihood 0.412 approaching safety boundary."
```

#### 4. Identify Key Findings
**Criteria for key findings:**
- ODD violations (always included)
- ODD boundary warnings (if multiple)
- Unexpected patterns (e.g., 100% motion detection in supposedly stationary scenario)
- Safety concerns (high collision risk, unstable platform)
- Data quality issues (simulation artifacts, sensor failures)

**Format:**
```json
[
  "The robot is frequently positioned in environments with high obstacle density and reduced traversability.",
  "The robot is often positioned in close proximity to static obstacles which causes high collision risk",
  "The robot has a high average collision risk."
]
```

#### 5. Generate Recommendations
**Criteria for recommendations:**
- Actionable (specific steps to take)
- Prioritized (most critical first)
- Feasible (within robot's capabilities)
- Targeted (address root causes, not symptoms)

**Categories:**
- Path planning improvements
- Sensor calibration
- ODD threshold adjustments
- Deployment restrictions
- Further investigation

**Format:**
```json
[
  "Implement path planning and obstacle avoidance strategies to reduce the likelihood of close proximity to obstacles and prevent potential collisions.",
  "Investigate and address the factors contributing to the low traversability score in order to operate more reliably."
]
```

#### 6. Package Full Analysis
**Include complete outputs from all agents:**
```json
{
  "perception": <perception_output>,
  "motion": <motion_output>,
  "collision": <collision_output>,
  "odd_spec": <odd_spec>,
  "cod_classification": <cod_classification>,
  "odd_compliance": <odd_compliance>
}
```

### Key Instruction Patterns

1. **Read all inputs**: Extract data from all 6 previous agent outputs
2. **Synthesize metadata**: Extract scenario-level information
3. **Write executive summary**: 2-3 sentence high-level overview
4. **Summarize domains**: 1-2 sentences per analysis domain
5. **Identify findings**: 3-5 key insights from data
6. **Generate recommendations**: 2-4 actionable next steps
7. **Package full analysis**: Include complete raw data
8. **Return ONLY JSON**: No explanations outside schema

**CRITICAL**: 
- Extract `environment_class` from `perception.environment_classification.primary_class`
- Extract `data_source` from `perception.data_source_classification.source`
- Both must be included in `scenario_metadata`

### Model Selection

**Default:** `gemini-2.0-flash-lite`  
**Recommended Upgrade:** `gemini-2.5-pro`

**Rationale:**
- Report generation requires sophisticated synthesis and writing
- **Flash-lite sufficient** for basic reports
- **Upgrade to 2.5-pro if**:
  - Need high-quality executive summaries for stakeholders
  - Complex scenarios requiring nuanced analysis
  - Production deployment with external reporting

**Cost Impact:** flash-lite saves ~70% vs. pro

**Quality Difference:**
- Flash-lite: Functional summaries, basic recommendations
- 2.5-pro: Polished writing, insightful recommendations, better prioritization

### Tool Dependencies

**None** - Pure synthesis agent using only LLM reasoning.

### Example Output

**Scenario: sim_run_new (13 windows, indoor office, OUT_ODD due to low traversability)**

```json
{
  "report": {
    "executive_summary": "The Unitree Go2 robot is operating in a simulated indoor office environment. While the environment generally aligns with the ODD, a low traversability score and high collision risk, coupled with multiple instances of near-collision scenarios, suggest a need for caution and potential adjustments to the operating strategy.",
    "scenario_metadata": {
      "total_windows_analyzed": 13,
      "scenario_name": "sim_run_new",
      "environment_class": "indoor_office",
      "data_source": "simulation",
      "data_source_confidence": 1.0
    },
    "perception_summary": "Robot operated in indoor office environment with bright lighting and smooth terrain. Average obstacle density 0.53 within ODD limits, but traversability score 0.38 below minimum threshold of 0.5, indicating constrained navigation space with blocked or narrow paths.",
    "motion_summary": "Moderate activity level with 85% motion detection rate (11/13 windows). Peak horizontal acceleration 1.23 m/s² with predominantly smooth motion. Platform remained stable with maximum tilt <5°.",
    "collision_summary": "8 high-risk collision events detected across 13 windows. Average collision likelihood 0.412 in boundary zone [0.3-0.5], approaching unsafe threshold. Multiple instances of near-collision scenarios with static obstacles (sofas, tables, furniture).",
    "odd_spec_summary": "Quadruped robot designed for indoor office environments with smooth floors, controlled lighting, and low obstacle density. Maximum speed 1.5 m/s with strict low collision risk tolerance (<0.3).",
    "cod_classification_summary": "Robot operating in indoor office with bright lighting, smooth terrain, moderate obstacle density (0.53), reduced traversability (0.38), and elevated collision risk (0.412).",
    "odd_compliance_summary": "Robot is OUT_ODD due to low traversability score (0.38 < 0.5 minimum). Collision risk in boundary zone (0.412), approaching safety limit. Environment type, lighting, and terrain compliant.",
    "key_findings": [
      "The robot is frequently positioned in environments with high obstacle density and reduced traversability.",
      "The robot is often positioned in close proximity to static obstacles which causes high collision risk.",
      "The robot has a high average collision risk approaching the safety boundary."
    ],
    "recommendations": [
      "Implement path planning and obstacle avoidance strategies to reduce the likelihood of close proximity to obstacles and prevent potential collisions.",
      "Investigate and address the factors contributing to the low traversability score in order to operate more reliably.",
      "Consider pre-deployment site surveys to identify and mitigate high-risk areas with constrained navigation space."
    ]
  },
  "full_analysis": {
    "perception": {
      "windows_analyzed": ["001", "002", ..., "013"],
      "environment_classification": {
        "primary_class": "indoor_office",
        "confidence": 0.95,
        "evidence": [...]
      },
      "data_source_classification": {
        "source": "simulation",
        "confidence": 1.0,
        "evidence": [...]
      },
      "per_window_perception": [...]
    },
    "motion": {
      "windows_analyzed": ["001", "002", ..., "013"],
      "overall_stats": {
        "total_windows": 13,
        "motion_detected_count": 11,
        "motion_detection_rate": 0.85,
        "max_horizontal_accel_mps2": 1.23,
        "overall_assessment": "moderate_activity"
      },
      "per_window_motion": [...]
    },
    "collision": {
      "windows_analyzed": ["001", "002", ..., "013"],
      "overall_collision_stats": {
        "total_windows": 13,
        "safe_count": 5,
        "caution_count": 3,
        "alert_count": 5,
        "avg_collision_likelihood": 0.412
      },
      "collision_events": [...]
    },
    "odd_spec": {
      "odd_specification": {
        "categorical_constraints": {...},
        "numeric_constraints": {...}
      },
      "odd_summary": "..."
    },
    "cod_classification": {
      "cod_classification": {
        "categorical": {...},
        "numeric": {...}
      },
      "cod_summary": "..."
    },
    "odd_compliance": {
      "odd_compliance": {
        "categorical_compliance": {...},
        "numeric_compliance": {...},
        "overall_compliance": "OUT_ODD",
        "violations": ["traversability_score: 0.38 is below the minimum allowed value of 0.5"],
        "warnings": ["collision_risk: 0.412 is within the boundary zone [0.3, 0.5]"],
        "compliance_summary": "..."
      }
    }
  }
}
```

### Common Issues

**Issue 1: Missing scenario metadata**
- **Symptom**: scenario_name, environment_class, or data_source missing
- **Cause**: Agent not extracting from correct source fields
- **Fix**: Verify perception agent output includes required fields

**Issue 2: Vague recommendations**
- **Symptom**: Recommendations like "improve performance" or "investigate further"
- **Cause**: Agent not generating specific, actionable recommendations
- **Fix**: Usually acceptable; if critical, upgrade to 2.5-pro for better quality

**Issue 3: Key findings don't match compliance status**
- **Symptom**: OUT_ODD status but findings don't mention violations
- **Cause**: Agent not prioritizing compliance results in findings
- **Fix**: Ensure agent includes violations/warnings in key findings

**Issue 4: Full analysis missing data**
- **Symptom**: Some previous agent outputs not included in full_analysis
- **Cause**: Agent not reading all input context
- **Fix**: Check ADK context passing and agent output_keys

### Design Rationale

#### Two-Level Reporting

**High-Level (report section):**
- For executives, operators, decision-makers
- Focus on insights, not raw data
- Actionable recommendations
- Brief, readable summaries

**Full-Detail (full_analysis section):**
- For engineers, analysts, investigators
- Complete audit trail
- All raw sensor data and metrics
- Debugging and deep analysis

This dual structure serves different audiences without duplication.

#### Executive Summary Guidelines

**What makes a good executive summary:**
- ✅ Scenario context (what robot, where, what doing)
- ✅ Compliance status (IN_ODD, OUT_ODD, BOUNDARY)
- ✅ Critical issue (if any)
- ✅ Overall assessment (safe, caution, unsafe)

**What to avoid:**
- ❌ Technical jargon (m/s², rad/s, BEV, LiDAR specifics)
- ❌ Excessive detail (specific window numbers, exact metrics)
- ❌ Vague language ("some issues", "generally okay")

#### Recommendation Quality

**Good recommendations:**
- Specific: "Implement improved obstacle avoidance"
- Actionable: "Pre-deployment site survey"
- Prioritized: Most critical first
- Feasible: Within robot/team capabilities

**Poor recommendations:**
- Vague: "Improve performance"
- Non-actionable: "Be more careful"
- Unrealistic: "Replace all sensors"
- Symptoms-focused: "Reduce collision risk" (how?)

---

## Output Formats

### Compact Executive Summary (for dashboards)
Extract from full report:
```json
{
  "scenario": "sim_run_new",
  "executive_summary": "...",
  "key_findings": [...],
  "recommendations": [...],
  "metadata": {...},
  "compliance": {
    "overall_compliance": "OUT_ODD",
    "violations": [...],
    "warnings": [...]
  }
}
```

### Full Analysis (for audits)
Complete report with all raw data:
```json
{
  "report": {...},
  "full_analysis": {
    "perception": {...},
    "motion": {...},
    "collision": {...},
    "odd_spec": {...},
    "cod_classification": {...},
    "odd_compliance": {...}
  }
}
```

---

## Integration Example

```python
from odd_agents.agents import create_report_agent
from google.genai import Client

client = Client(api_key=api_key)

# Create report agent
report_agent = create_report_agent(
    api_key=api_key,
    model="gemini-2.5-pro"  # Upgrade for high-quality reports
)

# Use as final agent in workflow
from google.adk.agents import SequentialAgent
workflow = SequentialAgent(
    name="OddWorkflow",
    sub_agents=[
        # ... all 9 previous agents ...
        report_agent  # Final synthesis and reporting
    ]
)

# Run and extract report
from odd_agents.workflow import extract_final_report
result = await runner.run(agent=workflow, user_message=nl_odd_description)
report = extract_final_report(result)

# Save compact summary
import json
executive_summary = {
    "scenario": report["report"]["scenario_metadata"]["scenario_name"],
    "executive_summary": report["report"]["executive_summary"],
    "key_findings": report["report"]["key_findings"],
    "recommendations": report["report"]["recommendations"],
    "compliance": report["full_analysis"]["odd_compliance"]["odd_compliance"]
}

with open("executive_summary.json", "w") as f:
    json.dump(executive_summary, f, indent=2)

# Save full analysis
with open("full_analysis.json", "w") as f:
    json.dump(report, f, indent=2)
```

---

## Related Documentation

- **[Main Agent Architecture](README.md)**: Overall workflow context
- **[All Previous Agents](README.md)**: Input sources for report
- **[Getting Started Guide](../guides/GETTING_STARTED.md)**: How to use reports
- **[Example Reports](../../data/examples/)**: Sample output files
- **[Agent Implementation](../../odd_agents/agents/report.py)**: Source code
