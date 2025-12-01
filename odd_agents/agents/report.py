"""
Report generation agent - Narrative synthesizer.

Reads from STATE only and outputs a structured human-readable report.
No tools needed - just synthesizes insights into final JSON output.

v9.0.0: Hybrid schema with compliance (not verdict), executive_summary, key_findings
v10.0.0: Collision advisory section, warnings for missing data, strong rationale
v11.0.0: Simplified - no tools, reads state only, outputs structured JSON directly
v12.0.0: Updated to read from _summary state keys (temporal analysis pattern)
v12.1.0: Added temp:odd_spec to state references per architecture doc
"""

from pathlib import Path
from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini


REPORT_AGENT_VERSION = "12.1.0"


def create_report_agent(scenario_path: Path, api_key: str, model: str) -> Agent:
    """Create Report agent - synthesizes narrative from state insights.

    No tools needed - reads from state and outputs structured JSON.
    State dump captures the output via output_key.
    """

    return Agent(
        name="ReportAgent",
        model=Gemini(model=model, api_key=api_key),
        tools=[],  # No tools needed
        output_key="report_output",
        instruction="""You synthesize a human-readable report from pipeline state.

## YOUR ROLE

You are a **summarizer** - read the upstream agent outputs and produce a clear, structured report for human operators. No tools needed - just output JSON directly.

## INPUT FROM SESSION STATE

**ODD specification (operational constraints):**
{odd_spec}

**Evaluator output (verdict + COD analysis):**
{evaluator_output}

**Perception summary (environment analysis):**
{perception_summary}

**Motion summary (robot dynamics):**
{motion_summary}

**Collision summary (safety advisory):**
{collision_summary}

## OUTPUT FORMAT

Output this exact JSON structure (no markdown, just raw JSON):

{
  "compliance": {
    "status": "IN_ODD" | "BOUNDARY" | "OUT_ODD",
    "confidence": "HIGH" | "MEDIUM" | "LOW",
    "summary": "One sentence explaining WHY this verdict, with specific values"
  },
  "executive_summary": "2-3 sentences for stakeholders: what happened, where, outcome",
  "key_findings": {
    "perception": "One sentence: lighting, obstacles, terrain, density %",
    "motion": "One sentence: speed, stability, roll/pitch values",
    "safety": "One sentence: proximity, clearance_index (NOT collisions)",
    "temporal_trends": "One sentence: stable/improving/degrading"
  },
  "scenario_metadata": {
    "windows_analyzed": <int>,
    "environment": "indoor/outdoor + type",
    "data_quality": "complete" | "partial" | "degraded",
    "data_source": "simulated" | "real"
  },
  "collision_advisory": {
    "collisions_detected": <int>,
    "risk_band": "LOW" | "MED" | "HIGH",
    "events": ["brief description if any"],
    "note": "Advisory only - does not affect compliance verdict"
  },
  "human_animal_detection": {
    "detected": true | false,
    "type": "human" | "animal" | "both" | "none",
    "proximity_m": <float or null>,
    "note": "description"
  },
  "issues": ["specific issue 1", "issue 2"] or [],
  "recommendations": ["actionable suggestion 1", "suggestion 2"],
  "data_warnings": ["warning if data missing"] or []
}

## FIELD EXTRACTION GUIDE

1. **compliance.status**: From evaluator's compliance_verdict.verdict
2. **compliance.confidence**: evaluator confidence >0.8=HIGH, 0.5-0.8=MEDIUM, <0.5=LOW
3. **compliance.summary**: Include specific axis values and distances from limits
4. **executive_summary**: Plain English for non-technical stakeholders
5. **key_findings**: One sentence each, include numbers (e.g., "35% density", "8.5° pitch")
6. **scenario_metadata**: From perception's data_source and window count
7. **collision_advisory**: From collision output - ADVISORY ONLY, not part of verdict
8. **human_animal_detection**: From perception if detected
9. **issues**: Only real issues - empty list if none found
10. **recommendations**: Actionable - or ["Continue normal operation"] if IN_ODD
11. **data_warnings**: Note any missing sensor data

## RULES

1. Output pure JSON only - no markdown code blocks
2. Use plain English for human readability
3. Include specific numbers from the data
4. COLLISION IS ADVISORY - never affects compliance status
5. Don't invent issues - empty list is fine
6. Base everything on actual state data - never assume""",
    )
