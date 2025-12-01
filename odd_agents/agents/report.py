"""
Report generation agent - Executive narrative synthesizer.

Reads from STATE only and outputs a structured human-readable report.
No tools needed - synthesizes insights into final JSON output.

v9.0.0: Hybrid schema with compliance, executive_summary, key_findings
v10.0.0: Collision advisory section, warnings for missing data
v11.0.0: Simplified - no tools, reads state only
v12.0.0: Updated to read from _summary state keys
v13.0.0: Enhanced narrative quality, specific value citations, actionable insights
v14.0.0: Separated exec summary (leadership) vs technical rationale (engineers), non-redundant writing
"""

from pathlib import Path
from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini


REPORT_AGENT_VERSION = "14.0.0"


def create_report_agent(scenario_path: Path, api_key: str, model: str) -> Agent:
    """Create Report agent - synthesizes executive narrative from analysis.

    No tools needed - reads from state and outputs structured JSON.
    """

    return Agent(
        name="ReportAgent",
        model=Gemini(model=model, api_key=api_key),
        tools=[],
        output_key="report_output",
        instruction="""You are writing a safety analysis report for an autonomy/ODD compliance system.

## TWO AUDIENCES - TWO WRITING STYLES

**Executive Summary** → Senior leadership (non-technical)
- 2-4 sentences of clear, fluent prose
- Focus on overall risk and operational implications
- Minimal numeric detail - only what's essential to understand the risk
- Plain language, no jargon

**Technical Sections** → Engineers and safety reviewers
- Structured data with specific values and ranges
- Explicit axis names, limits, and margins
- Qualitative agent alerts with context

## CRITICAL WRITING RULE

**Do NOT copy sentences between sections.** The Executive Summary and Technical Rationale must be:
- Consistent in meaning
- Different in wording
- Paraphrased, not duplicated

## INPUT DATA

**ODD Specification:**
{odd_spec}

**Evaluator Analysis (verdict + metrics):**
{evaluator_output}

**Perception Analysis:**
{perception_summary}

**Motion Analysis:**
{motion_summary}

**Collision Analysis (advisory):**
{collision_summary}

## OUTPUT FORMAT (raw JSON, no markdown)

{
  "compliance": {
    "status": "IN_ODD|BOUNDARY|OUT_ODD",
    "confidence": "HIGH|MEDIUM|LOW",
    "summary": "<TECHNICAL: 2-3 sentences for engineers explaining WHY this verdict, citing specific axes, values, and limits>"
  },
  "executive_summary": "<LEADERSHIP: 2-4 sentences in plain language describing the environment, what happened, and the safety/operational implications. No redundancy with compliance.summary>",
  "key_findings": {
    "perception": "<Environment conditions, lighting, terrain, obstacle density with key values>",
    "motion": "<Robot dynamics summary with peak values and % of limits>",
    "safety": "<Proximity to humans/animals, collision events, closest margin>",
    "temporal_trends": "<Stable/improving/degrading patterns across windows>"
  },
  "scenario_metadata": {
    "windows_analyzed": <int>,
    "environment": "<indoor_residential|indoor_commercial|outdoor|mixed>",
    "data_quality": "<complete|partial|degraded>",
    "data_source": "<simulated|real>"
  },
  "collision_advisory": {
    "collisions_detected": <int>,
    "risk_band": "LOW|MED|HIGH",
    "events": ["<window: description>"],
    "note": "Advisory only - does not affect compliance verdict"
  },
  "human_animal_detection": {
    "detected": true|false,
    "type": "human|animal|both|none",
    "proximity_m": <float or null>,
    "note": "<context if detected>"
  },
  "issues": [
    "<Specific issues with window references, or empty list if none>"
  ],
  "recommendations": [
    "<Actionable recommendations based on findings>"
  ],
  "data_warnings": [
    "<Missing data, sensor gaps, or quality concerns>"
  ]
}

## STYLE EXAMPLES

**BAD Executive Summary (too technical, redundant):**
"Verdict is BOUNDARY because multiple axes operated with less than 15% margin to their ODD limits, specifically clearance_index (min 0.8 vs 0.3-1.0 limit) and max_accel_mps2 (max 0.1455 vs 0-10 limit)."

**GOOD Executive Summary:**
"The robot navigated safely through an indoor residential environment, though it operated near the edge of its design envelope. While no hard limits were exceeded, reduced lighting in one segment degraded camera reliability, warranting attention before extended deployment."

**BAD Technical Rationale (vague):**
"Some axes were near their limits and there were perception concerns."

**GOOD Technical Rationale:**
"Verdict BOUNDARY: No axes exceeded hard limits (region_distance=0.0). clearance_index reached 0.80 (7% margin to 0.3 minimum). Perception agent flagged dim lighting in w011, degrading camera confidence despite being within nominal ODD."

Output raw JSON only - no markdown code blocks.""",
    )
