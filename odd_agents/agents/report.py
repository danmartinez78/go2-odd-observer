"""
Report generation agent - Narrative synthesizer.

Reads qualitative insights from STATE and synthesizes into human-readable report.
v9.0.0: Hybrid schema with compliance (not verdict), executive_summary, key_findings
"""

from pathlib import Path
from typing import List
from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.adk.tools import FunctionTool


REPORT_AGENT_VERSION = "9.1.0"


def create_report_tools(scenario_path: Path):
    """Create tools for Report Agent."""
    from google.adk.tools.tool_context import ToolContext
    import json

    async def generate_report_tool(
        compliance_status: str,
        compliance_confidence: str,
        compliance_summary: str,
        executive_summary: str,
        finding_perception: str,
        finding_motion: str,
        finding_safety: str,
        finding_temporal: str,
        scenario_environment: str,
        scenario_windows_analyzed: int,
        scenario_data_quality: str,
        scenario_data_source: str,
        issues: List[str],
        recommendations: List[str],
        tool_context: ToolContext
    ) -> str:
        """
        Generate the final ODD compliance report.

        Args:
            compliance_status: "IN_ODD", "BOUNDARY", or "OUT_ODD"
            compliance_confidence: "HIGH", "MEDIUM", or "LOW"
            compliance_summary: One sentence explaining the compliance result
            executive_summary: 2-3 sentence high-level narrative for stakeholders
            finding_perception: Key perception findings (lighting, obstacles, terrain)
            finding_motion: Key motion findings (speed, stability, dynamics)
            finding_safety: Key safety findings (collision risk, proximity)
            finding_temporal: How conditions changed over time
            scenario_environment: Type of environment (e.g., "indoor commercial")
            scenario_windows_analyzed: Number of time windows analyzed
            scenario_data_quality: "complete", "partial", or "degraded"
            scenario_data_source: "simulated" or "real" - whether data is from simulation or real-world
            issues: List of identified issues (empty list if none)
            recommendations: List of recommended actions

        Returns:
            JSON report structure
        """
        print(f"\n📋 [GENERATE_REPORT] Creating report...")
        print(
            f"📋 [GENERATE_REPORT] Compliance: {compliance_status} ({compliance_confidence})")
        print(
            f"📋 [GENERATE_REPORT] Issues: {len(issues)}, Recommendations: {len(recommendations)}")

        report = {
            "compliance": {
                "status": compliance_status,
                "confidence": compliance_confidence,
                "summary": compliance_summary
            },
            "executive_summary": executive_summary,
            "key_findings": {
                "perception": finding_perception,
                "motion": finding_motion,
                "safety": finding_safety,
                "temporal_trends": finding_temporal
            },
            "scenario_metadata": {
                "windows_analyzed": scenario_windows_analyzed,
                "environment": scenario_environment,
                "data_quality": scenario_data_quality,
                "data_source": scenario_data_source
            },
            "issues": issues if issues else [],
            "recommendations": recommendations if recommendations else ["Continue normal operation"]
        }

        # Save report as artifact
        try:
            import google.genai.types as gtypes
            report_json = json.dumps(report, indent=2)
            artifact = gtypes.Part.from_bytes(
                data=report_json.encode('utf-8'),
                mime_type="application/json"
            )
            version = await tool_context.save_artifact(
                filename="odd_compliance_report.json",
                artifact=artifact
            )
            print(
                f"📋 [GENERATE_REPORT] ✓ Saved artifact v{version}: odd_compliance_report.json")
        except Exception as e:
            print(f"📋 [GENERATE_REPORT] Warning: Could not save artifact: {e}")

        return json.dumps(report, indent=2)

    return [FunctionTool(func=generate_report_tool)]


def create_report_agent(scenario_path: Path, api_key: str, model: str) -> Agent:
    """Create Report agent - synthesizes narrative from state insights."""

    tools = create_report_tools(scenario_path)

    return Agent(
        name="ReportAgent",
        model=Gemini(model=model, api_key=api_key),
        tools=tools,
        output_key="temp:report_output",
        instruction="""You synthesize a narrative report from pipeline insights.

## INPUT FROM SESSION STATE

You have insights from upstream agents:

**Evaluator output:**
{temp:evaluator_output?}

**Perception insights:**
{temp:perception_output?}

**Motion insights:**
{temp:motion_output?}

**Collision insights:**
{temp:collision_output?}

## YOUR TASK

Read the insights above and call generate_report_tool() to create the final report.

Extract and synthesize the following:

### COMPLIANCE (from evaluator)
1. **compliance_status**: From evaluator's compliance_verdict.verdict (IN_ODD, BOUNDARY, or OUT_ODD)
2. **compliance_confidence**: Convert evaluator's confidence: >0.8=HIGH, 0.5-0.8=MEDIUM, <0.5=LOW  
3. **compliance_summary**: One sentence explaining the compliance result

### EXECUTIVE SUMMARY
4. **executive_summary**: 2-3 sentences for stakeholders. Include: what the robot did, where, and whether it stayed within operational limits. This should be readable by someone unfamiliar with the technical details.

### KEY FINDINGS (one sentence each)
5. **finding_perception**: What the environment looked like (lighting, obstacles, terrain type)
6. **finding_motion**: How the robot moved (speed range, stability, any dynamics concerns)
7. **finding_safety**: Collision/proximity status (any risks, minimum distances)
8. **finding_temporal**: How conditions changed (stable, improving, degrading, transition detected)

### SCENARIO METADATA
9. **scenario_environment**: Environment type from perception (e.g., "indoor commercial", "outdoor pathway")
10. **scenario_windows_analyzed**: Count of windows from the data
11. **scenario_data_quality**: "complete" if all sensors worked, "partial" if some gaps, "degraded" if significant issues
12. **scenario_data_source**: "simulated" or "real" from perception's data_source assessment

### ISSUES & RECOMMENDATIONS
13. **issues**: List specific problems found (empty list if none - don't add fake issues!)
14. **recommendations**: Actionable suggestions for the operator

## RULES

1. **ALWAYS call generate_report_tool()** with ALL parameters
2. Use plain English - this is for human operators
3. Include specific numbers when relevant (e.g., "speeds up to 0.5 m/s")
4. If IN_ODD with no issues, recommendations can be ["Continue normal operation"]
5. Keep findings concise - one sentence each
6. Base everything on actual data - never invent or assume""",
    )
